"""Closed HTTP sequence for Drive snapshot checks and Google Docs reads."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import json
import threading
import time
from urllib.parse import quote
import zlib

import httpx

from google_workspace_admin.content.auth.handles import AuthorizedOperationContext, _OperationAuthority
from google_workspace_admin.content.auth.scopes import ApprovedScopeProfile
from google_workspace_admin.content.budgets import DEFAULT_CONTENT_READING_BUDGETS
from google_workspace_admin.content.continuation import DocsContinuationManager
from google_workspace_admin.content.errors import (
    ContentErrorOperation,
    ContentSafeError,
    FailureStage,
)
from google_workspace_admin.content.google_docs import (
    GOOGLE_DOC_MIME_TYPE,
    GOOGLE_DOCS_READER_VERSION,
    build_bounded_docs_result,
    failure_result,
    parse_drive_file_metadata,
    parse_google_document,
)
from google_workspace_admin.content.inventory import InventorySnapshot
from google_workspace_admin.content.operations import (
    DOCS_GET_FIELDS,
    DRIVE_FILE_METADATA_FIELDS,
    ContentOperation,
    _NormalizedOperationRequest,
)
from google_workspace_admin.content.outcomes import ProcessingStatus, SafeContentErrorCode
from google_workspace_admin.content.readers import BoundedReadResult
from google_workspace_admin.content.transport import RetryPolicy, _sleep_with_cancellation
from google_workspace_admin.http_errors import WorkspaceApiError


_DRIVE_METADATA_CAP = 64 * 1024
_RAW_STREAM_CHUNK_BYTES = 64 * 1024
_SUPPORTED_CONTENT_ENCODINGS = frozenset({"identity", "gzip", "deflate"})


@dataclass(frozen=True, slots=True)
class _FetchFailure:
    kind: str
    status: int | None = None


def _encoded_id(value: str) -> str:
    encoded = quote(value, safe="")
    return value.replace(".", "%2E") if value in {".", ".."} else encoded


def _failure_result(
    failure: _FetchFailure,
    *,
    stage: FailureStage,
) -> BoundedReadResult:
    effective_stage = stage
    if stage is FailureStage.DOCS_REQUEST:
        if failure.kind == "json":
            effective_stage = FailureStage.DOCS_JSON_PARSE
        elif failure.kind in {
            "transport",
            "timeout",
            "response_malformed",
            "unsupported_encoding",
            "too_large",
        }:
            effective_stage = FailureStage.DOCS_RESPONSE_TRANSPORT
    if failure.kind == "too_large":
        return failure_result(
            ProcessingStatus.TOO_LARGE,
            SafeContentErrorCode.TOO_LARGE,
            effective_stage,
        )
    if failure.status in {401, 403}:
        return failure_result(
            ProcessingStatus.ACCESS_DENIED,
            SafeContentErrorCode.ACCESS_DENIED,
            effective_stage,
        )
    if failure.status == 404:
        return failure_result(
            ProcessingStatus.NOT_FOUND,
            SafeContentErrorCode.NOT_FOUND,
            effective_stage,
        )
    if failure.status in {408, 429}:
        error_code = (
            SafeContentErrorCode.QUOTA_EXCEEDED
            if failure.status == 429
            else SafeContentErrorCode.TRANSIENT_UPSTREAM
        )
        return failure_result(ProcessingStatus.TRANSIENT_UPSTREAM, error_code, effective_stage)
    if failure.kind in {"timeout", "transport"} or (failure.status is not None and failure.status >= 500):
        return failure_result(
            ProcessingStatus.TRANSIENT_UPSTREAM,
            SafeContentErrorCode.TRANSIENT_UPSTREAM,
            effective_stage,
        )
    return failure_result(
        ProcessingStatus.EXTRACTION_FAILED,
        SafeContentErrorCode.RESPONSE_VALIDATION,
        effective_stage,
    )


def _decode_json_object(raw: bytes) -> Mapping[str, object]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        raise ContentSafeError(
            code="RESPONSE_VALIDATION",
            operation=ContentErrorOperation.RESPONSE_DOCS_GET,
        ) from None
    if not isinstance(value, Mapping):
        raise ContentSafeError(
            code="RESPONSE_VALIDATION",
            operation=ContentErrorOperation.RESPONSE_DOCS_GET,
        )
    return value


def _bounded_response_body(
    response: httpx.Response,
    *,
    raw_cap: int,
    decoded_cap: int,
) -> bytes | _FetchFailure:
    """Read one response with independent encoded and decoded hard limits.

    ``iter_raw`` is the public HTTPX streaming API that yields the encoded
    response representation before Content-Encoding decoding.  The adapter
    counts that stream first and performs only allowlisted, output-limited
    decompression locally.
    """

    content_length = response.headers.get("content-length")
    if content_length is not None:
        if not content_length.isascii() or not content_length.isdigit():
            return _FetchFailure("response_malformed")
        if int(content_length) > raw_cap:
            return _FetchFailure("too_large")

    raw_encoding = response.headers.get("content-encoding")
    encoding = "identity" if raw_encoding is None else raw_encoding.strip().lower()
    if encoding not in _SUPPORTED_CONTENT_ENCODINGS:
        return _FetchFailure("unsupported_encoding")

    if encoding == "gzip":
        decoder: zlib.Decompress | None = zlib.decompressobj(16 + zlib.MAX_WBITS)
    elif encoding == "deflate":
        decoder = zlib.decompressobj(zlib.MAX_WBITS)
    else:
        decoder = None

    raw_count = 0
    decoded = bytearray()
    try:
        for raw_chunk in response.iter_raw(chunk_size=_RAW_STREAM_CHUNK_BYTES):
            raw_count += len(raw_chunk)
            if raw_count > raw_cap:
                return _FetchFailure("too_large")

            remaining = decoded_cap + 1 - len(decoded)
            if remaining <= 0:
                return _FetchFailure("too_large")
            if decoder is None:
                decoded.extend(raw_chunk[:remaining])
            else:
                decoded.extend(decoder.decompress(raw_chunk, remaining))
            if len(decoded) > decoded_cap:
                return _FetchFailure("too_large")
            if decoder is not None and decoder.unconsumed_tail:
                return _FetchFailure("too_large")
    except (httpx.StreamError, zlib.error):
        return _FetchFailure("response_malformed")

    if decoder is not None and (
        not decoder.eof or decoder.unconsumed_tail or decoder.unused_data
    ):
        return _FetchFailure("response_malformed")
    return bytes(decoded)


def _build_google_docs_read_port(
    *,
    client: httpx.Client,
    require_context: Callable[[object], object],
    token_provider: Callable[[object, ApprovedScopeProfile], str],
    retry_policy: RetryPolicy,
    sleeper: Callable[[float], None] = time.sleep,
    continuation_manager: DocsContinuationManager,
) -> Callable[[AuthorizedOperationContext, _NormalizedOperationRequest], BoundedReadResult]:
    budgets = DEFAULT_CONTENT_READING_BUDGETS

    def send_bounded(
        *,
        endpoint: str,
        params: Mapping[str, str | bool],
        access_token: str,
        raw_cap: int,
        decoded_cap: int,
        operation: ContentErrorOperation,
        cancel_event: threading.Event | None = None,
    ) -> Mapping[str, object] | _FetchFailure:
        for attempt in range(retry_policy.max_attempts):
            response: httpx.Response | None = None
            try:
                request = client.build_request(
                    "GET",
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept-Encoding": "gzip, deflate",
                    },
                    params=dict(params),
                )
                response = client.send(request, stream=True)
                status = response.status_code
                if not 200 <= status < 300:
                    error = WorkspaceApiError(operation.value, "http_error", status)
                    response.close()
                    if retry_policy._can_retry(
                        idempotent_read=True,
                        attempt_number=attempt,
                        error=error,
                    ):
                        _sleep_with_cancellation(
                            retry_policy.delay_for(attempt + 1), cancel_event, sleeper
                        )
                        continue
                    return _FetchFailure("http", status)
                received = _bounded_response_body(
                    response,
                    raw_cap=raw_cap,
                    decoded_cap=decoded_cap,
                )
                response.close()
                if type(received) is _FetchFailure:
                    return received
                try:
                    return _decode_json_object(received)
                except ContentSafeError:
                    return _FetchFailure("json")
            except ContentSafeError:
                if response is not None:
                    response.close()
                raise
            except httpx.TimeoutException:
                if response is not None:
                    response.close()
                error = WorkspaceApiError(operation.value, "timeout")
                if retry_policy._can_retry(idempotent_read=True, attempt_number=attempt, error=error):
                    _sleep_with_cancellation(retry_policy.delay_for(attempt + 1), cancel_event, sleeper)
                    continue
                return _FetchFailure("timeout")
            except httpx.RequestError:
                if response is not None:
                    response.close()
                error = WorkspaceApiError(operation.value, "transport_error")
                if retry_policy._can_retry(idempotent_read=True, attempt_number=attempt, error=error):
                    _sleep_with_cancellation(retry_policy.delay_for(attempt + 1), cancel_event, sleeper)
                    continue
                return _FetchFailure("transport")
            except Exception:
                if response is not None:
                    response.close()
                return _FetchFailure("transport")
        return _FetchFailure("transport")

    def read(
        context: AuthorizedOperationContext,
        request: _NormalizedOperationRequest,
    ) -> BoundedReadResult:
        try:
            authority = require_context(context)
        except ContentSafeError:
            raise
        except Exception:
            raise ContentSafeError(
                code="READ_ONLY_OPERATION_FORBIDDEN",
                operation=ContentErrorOperation.AUTH_CONTEXT_PROVENANCE,
            ) from None
        if (
            type(request) is not _NormalizedOperationRequest
            or type(authority) is not _OperationAuthority
            or authority.operation is not ContentOperation.FILE_CONTENT_READ
            or request.operation is not ContentOperation.FILE_CONTENT_READ
            or request.file_id is None
            or request.expected_mime_type is None
            or request.modified_time is None
        ):
            raise ContentSafeError(
                code="READ_ONLY_OPERATION_FORBIDDEN",
                operation=ContentErrorOperation.FILE_CONTENT_READ,
            )
        snapshot = InventorySnapshot(
            request.file_id,
            request.expected_mime_type,
            request.modified_time,
        )
        continuation_state = None
        if request.continuation_token is not None:
            continuation_state = continuation_manager.resolve(
                request.continuation_token,
                snapshot=snapshot,
                reader_version=GOOGLE_DOCS_READER_VERSION,
            )
        try:
            access_token = token_provider(context, ApprovedScopeProfile.DRIVE_DISCOVERY)
        except ContentSafeError:
            raise
        except Exception:
            raise ContentSafeError(
                code="UNEXPECTED_LOCAL",
                operation=ContentErrorOperation.AUTH_BROKER,
            ) from None
        if type(access_token) is not str or not access_token or len(access_token) > 8192 or any(
            character.isspace() or ord(character) < 32 for character in access_token
        ):
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.AUTH_BROKER)

        encoded = _encoded_id(snapshot.file_id)
        metadata_endpoint = f"https://www.googleapis.com/drive/v3/files/{encoded}"
        metadata_params: Mapping[str, str | bool] = {
            "fields": DRIVE_FILE_METADATA_FIELDS,
            "supportsAllDrives": True,
        }
        preflight_payload = send_bounded(
            endpoint=metadata_endpoint,
            params=metadata_params,
            access_token=access_token,
            raw_cap=_DRIVE_METADATA_CAP,
            decoded_cap=_DRIVE_METADATA_CAP,
            operation=ContentErrorOperation.DRIVE_FILE_METADATA_GET,
        )
        if type(preflight_payload) is _FetchFailure:
            return _failure_result(preflight_payload, stage=FailureStage.PREFLIGHT_FETCH)
        try:
            preflight = parse_drive_file_metadata(preflight_payload, expected_file_id=snapshot.file_id)
        except ContentSafeError:
            return failure_result(
                ProcessingStatus.EXTRACTION_FAILED,
                SafeContentErrorCode.RESPONSE_VALIDATION,
                FailureStage.PREFLIGHT_VALIDATION,
            )
        if (
            preflight.trashed
            or preflight.mime_type != GOOGLE_DOC_MIME_TYPE
            or preflight.mime_type != snapshot.expected_mime_type
            or preflight.modified_time != snapshot.modified_time
        ):
            return failure_result(
                ProcessingStatus.CHANGED_DURING_AUDIT,
                SafeContentErrorCode.CHANGED_DURING_AUDIT,
                FailureStage.PREFLIGHT_VALIDATION,
            )

        docs_endpoint = f"https://docs.googleapis.com/v1/documents/{encoded}"
        docs_payload = send_bounded(
            endpoint=docs_endpoint,
            params={
                "fields": DOCS_GET_FIELDS,
                "includeTabsContent": True,
                "suggestionsViewMode": "SUGGESTIONS_INLINE",
            },
            access_token=access_token,
            raw_cap=budgets.max_download_bytes,
            decoded_cap=budgets.max_parser_input_bytes,
            operation=ContentErrorOperation.DOCS_GET,
        )
        if type(docs_payload) is _FetchFailure:
            return _failure_result(docs_payload, stage=FailureStage.DOCS_REQUEST)
        try:
            document = parse_google_document(
                docs_payload,
                expected_document_id=snapshot.file_id,
                budgets=budgets,
            )
        except ContentSafeError as error:
            if error.code == "CONTEXT_LIMIT_EXCEEDED":
                return failure_result(
                    ProcessingStatus.TOO_LARGE,
                    SafeContentErrorCode.TOO_LARGE,
                    error.failure_stage or FailureStage.DOCS_STRUCTURAL_EXTRACTION,
                    error.structural_failure_kind,
                    error.paragraph_failure_kind,
                )
            return failure_result(
                ProcessingStatus.EXTRACTION_FAILED,
                SafeContentErrorCode.RESPONSE_VALIDATION,
                error.failure_stage or FailureStage.DOCS_SCHEMA_PARSE,
                error.structural_failure_kind,
                error.paragraph_failure_kind,
            )
        if (
            continuation_state is not None
            and continuation_state.revision_id is not None
            and document.revision_id != continuation_state.revision_id
        ):
            return failure_result(
                ProcessingStatus.CHANGED_DURING_AUDIT,
                SafeContentErrorCode.CHANGED_DURING_AUDIT,
            )
        try:
            candidate = build_bounded_docs_result(
                document,
                snapshot=snapshot,
                budgets=budgets,
                continuation_manager=continuation_manager,
                continuation_state=continuation_state,
            )
        except ContentSafeError as error:
            if error.code == "CONTEXT_LIMIT_EXCEEDED":
                return failure_result(
                    ProcessingStatus.TOO_LARGE,
                    SafeContentErrorCode.TOO_LARGE,
                    error.failure_stage or FailureStage.DOCS_STRUCTURAL_EXTRACTION,
                    error.structural_failure_kind,
                    error.paragraph_failure_kind,
                )
            raise

        postflight_payload = send_bounded(
            endpoint=metadata_endpoint,
            params=metadata_params,
            access_token=access_token,
            raw_cap=_DRIVE_METADATA_CAP,
            decoded_cap=_DRIVE_METADATA_CAP,
            operation=ContentErrorOperation.DRIVE_FILE_METADATA_GET,
        )
        if type(postflight_payload) is _FetchFailure:
            return _failure_result(postflight_payload, stage=FailureStage.POSTFLIGHT_FETCH)
        try:
            postflight = parse_drive_file_metadata(postflight_payload, expected_file_id=snapshot.file_id)
        except ContentSafeError:
            return failure_result(
                ProcessingStatus.EXTRACTION_FAILED,
                SafeContentErrorCode.RESPONSE_VALIDATION,
                FailureStage.POSTFLIGHT_VALIDATION,
            )
        if postflight != preflight or postflight.trashed:
            return failure_result(
                ProcessingStatus.CHANGED_DURING_AUDIT,
                SafeContentErrorCode.CHANGED_DURING_AUDIT,
                FailureStage.POSTFLIGHT_VALIDATION,
            )
        return candidate

    return read
