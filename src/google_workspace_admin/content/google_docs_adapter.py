"""Closed HTTP sequence for Drive snapshot checks and Google Docs reads."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import json
import threading
import time
from urllib.parse import quote

import httpx

from google_workspace_admin.content.auth.handles import AuthorizedOperationContext, _OperationAuthority
from google_workspace_admin.content.auth.scopes import ApprovedScopeProfile
from google_workspace_admin.content.bounded_http import (
    BoundedBodyFailure,
    read_bounded_response_body,
)
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
    DriveFileMetadata,
    DriveFileMetadataReadResult,
    _DriveFileMetadataReadFailure,
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
    """Preserve the Docs adapter's closed failure type over the shared cap."""

    received = read_bounded_response_body(
        response,
        raw_cap=raw_cap,
        decoded_cap=decoded_cap,
    )
    if type(received) is BoundedBodyFailure:
        return _FetchFailure(received.kind)
    return received


def _decode_drive_metadata(
    raw: bytes,
    *,
    expected_file_id: str,
) -> DriveFileMetadataReadResult:
    class DuplicateKey(ValueError):
        pass

    def pairs(values: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in values:
            if key in result:
                raise DuplicateKey
            result[key] = value
        return result

    try:
        payload = json.loads(
            raw.decode("utf-8", "strict"),
            object_pairs_hook=pairs,
        )
    except (UnicodeError, json.JSONDecodeError, DuplicateKey, ValueError):
        return _DriveFileMetadataReadFailure("json")
    if type(payload) is not dict:
        return _DriveFileMetadataReadFailure("json")
    try:
        return parse_drive_file_metadata(payload, expected_file_id=expected_file_id)
    except ContentSafeError:
        return _DriveFileMetadataReadFailure("response_validation")


def _build_google_drive_file_metadata_read_port(
    *,
    client: httpx.Client,
    require_context: Callable[[object], object],
    token_provider: Callable[[object, ApprovedScopeProfile], str],
) -> Callable[[AuthorizedOperationContext, object], DriveFileMetadataReadResult]:
    """Build a one-send, exact-ID Drive metadata GET with closed request policy."""

    if (
        type(client) is not httpx.Client
        or not callable(require_context)
        or not callable(token_provider)
    ):
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.TRANSPORT,
        )

    def read(
        context: AuthorizedOperationContext,
        file_id: object,
    ) -> DriveFileMetadataReadResult:
        try:
            snapshot = InventorySnapshot(file_id, GOOGLE_DOC_MIME_TYPE)
        except ContentSafeError:
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.DRIVE_FILE_METADATA_GET,
            ) from None
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
            type(authority) is not _OperationAuthority
            or authority.operation
            not in {
                ContentOperation.FILE_CONTENT_READ,
                ContentOperation.SHEETS_WORKBOOK_METADATA,
            }
            or authority.approved_scope_profile is not ApprovedScopeProfile.DRIVE_DISCOVERY
            or authority.admin_mode_authorized is not False
        ):
            raise ContentSafeError(
                code="READ_ONLY_OPERATION_FORBIDDEN",
                operation=ContentErrorOperation.CAPABILITY_MATRIX,
            )
        try:
            access_token = token_provider(context, ApprovedScopeProfile.DRIVE_DISCOVERY)
        except ContentSafeError:
            raise
        except Exception:
            return _DriveFileMetadataReadFailure("transport")
        if (
            type(access_token) is not str
            or not access_token
            or len(access_token) > 8192
            or any(
                character.isspace()
                or ord(character) < 32
                or 0x7F <= ord(character) <= 0x9F
                for character in access_token
            )
        ):
            return _DriveFileMetadataReadFailure("transport")

        response: httpx.Response | None = None
        endpoint = f"https://www.googleapis.com/drive/v3/files/{_encoded_id(snapshot.file_id)}"
        try:
            request = client.build_request(
                "GET",
                endpoint,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept-Encoding": "gzip, deflate",
                },
                params={
                    "fields": DRIVE_FILE_METADATA_FIELDS,
                    "supportsAllDrives": True,
                },
            )
            response = client.send(request, stream=True, follow_redirects=False)
            if not 200 <= response.status_code < 300:
                return _DriveFileMetadataReadFailure("http", response.status_code)
            body = _bounded_response_body(
                response,
                raw_cap=_DRIVE_METADATA_CAP,
                decoded_cap=_DRIVE_METADATA_CAP,
            )
            if type(body) is _FetchFailure:
                return _DriveFileMetadataReadFailure(body.kind)
            return _decode_drive_metadata(body, expected_file_id=snapshot.file_id)
        except httpx.TimeoutException:
            return _DriveFileMetadataReadFailure("timeout")
        except httpx.RequestError:
            return _DriveFileMetadataReadFailure("transport")
        except ContentSafeError:
            raise
        except Exception:
            return _DriveFileMetadataReadFailure("transport")
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass

    return read


def _build_google_docs_read_port(
    *,
    client: httpx.Client,
    require_context: Callable[[object], object],
    token_provider: Callable[[object, ApprovedScopeProfile], str],
    drive_file_metadata_read: Callable[
        [AuthorizedOperationContext, object], DriveFileMetadataReadResult
    ],
    retry_policy: RetryPolicy,
    sleeper: Callable[[float], None] = time.sleep,
    continuation_manager: DocsContinuationManager,
    public_file_ref_provider: Callable[[str], str] | None = None,
) -> Callable[[AuthorizedOperationContext, _NormalizedOperationRequest], BoundedReadResult]:
    budgets = DEFAULT_CONTENT_READING_BUDGETS
    if not callable(drive_file_metadata_read):
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.TRANSPORT,
        )

    def read_drive_metadata(
        context: AuthorizedOperationContext,
        file_id: str,
    ) -> DriveFileMetadata | _FetchFailure:
        for attempt in range(retry_policy.max_attempts):
            result = drive_file_metadata_read(context, file_id)
            if type(result) is DriveFileMetadata:
                return result
            if type(result) is not _DriveFileMetadataReadFailure:
                return _FetchFailure("response_malformed")
            failure = _FetchFailure(result.kind, result.status)
            if result.kind == "response_validation":
                return failure
            if result.kind == "http":
                category = "http_error"
            elif result.kind == "timeout":
                category = "timeout"
            elif result.kind == "transport":
                category = "transport_error"
            else:
                return failure
            error = WorkspaceApiError(
                ContentErrorOperation.DRIVE_FILE_METADATA_GET.value,
                category,
                result.status,
            )
            if not retry_policy._can_retry(
                idempotent_read=True,
                attempt_number=attempt,
                error=error,
            ):
                return failure
            _sleep_with_cancellation(retry_policy.delay_for(attempt + 1), None, sleeper)
        return _FetchFailure("transport")

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
        if public_file_ref_provider is None:
            return failure_result(
                ProcessingStatus.EXTRACTION_FAILED,
                SafeContentErrorCode.CONTENT_NOT_SUPPORTED,
            )
        try:
            public_file_ref = public_file_ref_provider(snapshot.file_id)
        except ContentSafeError:
            return failure_result(
                ProcessingStatus.EXTRACTION_FAILED,
                SafeContentErrorCode.LOCAL_VALIDATION,
            )
        except Exception:
            return failure_result(
                ProcessingStatus.EXTRACTION_FAILED,
                SafeContentErrorCode.LOCAL_VALIDATION,
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

        preflight_result = read_drive_metadata(context, snapshot.file_id)
        if type(preflight_result) is _FetchFailure:
            stage = (
                FailureStage.PREFLIGHT_VALIDATION
                if preflight_result.kind == "response_validation"
                else FailureStage.PREFLIGHT_FETCH
            )
            return _failure_result(preflight_result, stage=stage)
        preflight = preflight_result
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

        encoded = _encoded_id(snapshot.file_id)
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
                public_file_ref=public_file_ref,
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

        postflight_result = read_drive_metadata(context, snapshot.file_id)
        if type(postflight_result) is _FetchFailure:
            stage = (
                FailureStage.POSTFLIGHT_VALIDATION
                if postflight_result.kind == "response_validation"
                else FailureStage.POSTFLIGHT_FETCH
            )
            return _failure_result(postflight_result, stage=stage)
        postflight = postflight_result
        if postflight != preflight or postflight.trashed:
            return failure_result(
                ProcessingStatus.CHANGED_DURING_AUDIT,
                SafeContentErrorCode.CHANGED_DURING_AUDIT,
                FailureStage.POSTFLIGHT_VALIDATION,
            )
        return candidate

    return read
