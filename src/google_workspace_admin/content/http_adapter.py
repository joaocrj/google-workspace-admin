"""Internal fixed-endpoint HTTP-to-DTO adapter for Content reads.

Raw responses and decoded mappings stay inside a lexical send/parse helper.
Only operation-specific typed callables are returned to the sealed runtime.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import math
import threading
import time

import httpx

from google_workspace_admin.content.auth.handles import (
    AuthorizedOperationContext,
    _OperationAuthority,
)
from google_workspace_admin.content.auth.scopes import ApprovedScopeProfile
from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError
from google_workspace_admin.content.operations import (
    ContentOperation,
    _NormalizedOperationRequest,
    get_operation_contract,
)
from google_workspace_admin.content.results import (
    DriveFileListPage,
    DriveGetResult,
    DriveListPage,
    parse_drive_files_list,
    parse_drive_get,
    parse_drive_list,
)
from google_workspace_admin.content.transport import RetryPolicy, _sleep_with_cancellation
from google_workspace_admin.http_errors import WorkspaceApiError, parse_json_object, request_safe


ContentTypedResult = DriveListPage | DriveGetResult | DriveFileListPage


@dataclass(frozen=True, slots=True)
class _HttpAdapterPorts:
    drive_list: Callable[[AuthorizedOperationContext, _NormalizedOperationRequest], DriveListPage]
    drive_get: Callable[[AuthorizedOperationContext, _NormalizedOperationRequest], DriveGetResult]
    drive_files_list: Callable[
        [AuthorizedOperationContext, _NormalizedOperationRequest], DriveFileListPage
    ]
    close: Callable[[], None]


def _build_http_adapter(
    *,
    client: httpx.Client,
    require_context: Callable[[object], object],
    token_provider: Callable[[object, ApprovedScopeProfile], str],
    timeout: float = 30.0,
    retry_policy: RetryPolicy | None = None,
    sleeper: Callable[[float], None] = time.sleep,
) -> _HttpAdapterPorts:
    if type(client) is not httpx.Client:
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.TRANSPORT)
    if not callable(require_context):
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.TRANSPORT)
    if not callable(token_provider):
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.TRANSPORT)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.TRANSPORT)
    if not math.isfinite(float(timeout)) or timeout <= 0 or not callable(sleeper):
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.TRANSPORT)
    policy = retry_policy or RetryPolicy()
    if type(policy) is not RetryPolicy:
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.RETRY_POLICY,
        )

    error_operations = {
        ContentOperation.DRIVE_LIST: ContentErrorOperation.DRIVE_LIST,
        ContentOperation.DRIVE_GET: ContentErrorOperation.DRIVE_GET,
        ContentOperation.DRIVE_FILES_LIST: ContentErrorOperation.DRIVE_FILES_LIST,
    }

    def send_and_parse(
        context: AuthorizedOperationContext,
        request: _NormalizedOperationRequest,
        expected_operation: ContentOperation,
        parser: Callable[[dict], ContentTypedResult],
        cancel_event: threading.Event | None = None,
    ) -> ContentTypedResult:
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
            or authority.operation is not expected_operation
            or request.operation is not expected_operation
        ):
            raise ContentSafeError(
                code="READ_ONLY_OPERATION_FORBIDDEN",
                operation=ContentErrorOperation.TRANSPORT,
            )
        safe_operation = error_operations[expected_operation]
        contract = get_operation_contract(expected_operation)
        try:
            access_token = token_provider(context, contract.scope_profile)
        except ContentSafeError:
            raise
        except Exception:
            raise ContentSafeError(
                code="UNEXPECTED_LOCAL",
                operation=ContentErrorOperation.AUTH_BROKER,
            ) from None
        if (
            not isinstance(access_token, str)
            or not access_token
            or len(access_token) > 8192
            or any(
                character.isspace()
                or ord(character) < 32
                or 0x7F <= ord(character) <= 0x9F
                for character in access_token
            )
        ):
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.AUTH_BROKER,
            )
        endpoint = contract.endpoint_template
        query: dict[str, str | int | bool] = {
            "fields": contract.default_fields,
        }
        if expected_operation is ContentOperation.DRIVE_LIST:
            if request.page_size is None or request.response_item_limit is None:
                raise ContentSafeError(
                    code="RESPONSE_VALIDATION",
                    operation=ContentErrorOperation.TRANSPORT,
                )
            query["pageSize"] = request.page_size
            if request.page_token is not None:
                query["pageToken"] = request.page_token
            if request.admin_mode:
                query["useDomainAdminAccess"] = True
        elif expected_operation is ContentOperation.DRIVE_GET:
            if request.drive_id is None:
                raise ContentSafeError(
                    code="RESPONSE_VALIDATION",
                    operation=ContentErrorOperation.TRANSPORT,
                )
            from urllib.parse import quote

            encoded_drive_id = quote(request.drive_id, safe="")
            if request.drive_id in {".", ".."}:
                encoded_drive_id = request.drive_id.replace(".", "%2E")
            endpoint = contract.endpoint_template.format(
                drive_id=encoded_drive_id
            )
            if request.admin_mode:
                query["useDomainAdminAccess"] = True
        elif expected_operation is ContentOperation.DRIVE_FILES_LIST:
            if (
                request.drive_id is None
                or request.page_size is None
                or request.response_item_limit is None
            ):
                raise ContentSafeError(
                    code="RESPONSE_VALIDATION",
                    operation=ContentErrorOperation.TRANSPORT,
                )
            query.update(
                {
                    "pageSize": request.page_size,
                    "corpora": "drive",
                    "driveId": request.drive_id,
                    "includeItemsFromAllDrives": True,
                    "supportsAllDrives": True,
                    "spaces": "drive",
                    "q": "trashed = false",
                }
            )
            if request.page_token is not None:
                query["pageToken"] = request.page_token

        response: httpx.Response | None = None
        for attempt in range(policy.max_attempts):
            if cancel_event is not None and cancel_event.is_set():
                raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.TRANSPORT)
            try:
                response = request_safe(
                    client,
                    "get",
                    endpoint,
                    expected_operation.value,
                    headers={"Authorization": f"Bearer {access_token}"},
                    params=query,
                    timeout=float(timeout),
                )
                if 300 <= response.status_code < 400:
                    raise ContentSafeError(
                        code="WORKSPACE_HTTP",
                        operation=safe_operation,
                        http_status=response.status_code,
                        category="http_error",
                    )
                break
            except WorkspaceApiError as error:
                if not policy._can_retry(
                    idempotent_read=contract.idempotent_read,
                    attempt_number=attempt,
                    error=error,
                ):
                    raise ContentSafeError(
                        code=("QUOTA_EXCEEDED" if error.http_status == 429 else "WORKSPACE_HTTP"),
                        operation=safe_operation,
                        http_status=error.http_status,
                        category=error.category,
                    ) from None
                _sleep_with_cancellation(
                    policy.delay_for(attempt + 1), cancel_event, sleeper
                )
            except ContentSafeError:
                raise
            except Exception:
                raise ContentSafeError(
                    code="WORKSPACE_HTTP",
                    operation=safe_operation,
                    category="transport_error",
                ) from None
        if response is None:
            raise ContentSafeError(code="WORKSPACE_HTTP", operation=safe_operation)
        try:
            payload = parse_json_object(response, expected_operation.value)
        except WorkspaceApiError as error:
            raise ContentSafeError(
                code="RESPONSE_VALIDATION",
                operation=safe_operation,
                http_status=error.http_status,
                category=error.category,
            ) from None
        return parser(payload)

    def drive_list(
        context: AuthorizedOperationContext,
        request: _NormalizedOperationRequest,
    ) -> DriveListPage:
        if request.response_item_limit is None:
            raise ContentSafeError(code="RESPONSE_VALIDATION", operation=ContentErrorOperation.RESPONSE_DRIVE_LIST)
        return send_and_parse(
            context,
            request,
            ContentOperation.DRIVE_LIST,
            lambda payload: parse_drive_list(payload, max_items=request.response_item_limit),
        )

    def drive_get(
        context: AuthorizedOperationContext,
        request: _NormalizedOperationRequest,
    ) -> DriveGetResult:
        return send_and_parse(
            context,
            request,
            ContentOperation.DRIVE_GET,
            parse_drive_get,
        )

    def drive_files_list(
        context: AuthorizedOperationContext,
        request: _NormalizedOperationRequest,
    ) -> DriveFileListPage:
        if request.response_item_limit is None:
            raise ContentSafeError(code="RESPONSE_VALIDATION", operation=ContentErrorOperation.RESPONSE_DRIVE_FILES_LIST)
        return send_and_parse(
            context,
            request,
            ContentOperation.DRIVE_FILES_LIST,
            lambda payload: parse_drive_files_list(
                payload, max_items=request.response_item_limit
            ),
        )

    return _HttpAdapterPorts(
        drive_list=drive_list,
        drive_get=drive_get,
        drive_files_list=drive_files_list,
        close=client.close,
    )
