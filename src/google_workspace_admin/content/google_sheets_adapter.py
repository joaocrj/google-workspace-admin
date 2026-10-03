"""Closed GET-only request construction and bounded transport for Sheets v4."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import json
import re
from typing import Mapping
from urllib.parse import quote

import httpx

from google_workspace_admin.content.auth.handles import (
    AuthorizedOperationContext,
    _OperationAuthority,
)
from google_workspace_admin.content.auth.scopes import ApprovedScopeProfile
from google_workspace_admin.content.bounded_http import (
    BoundedBodyFailure,
    read_bounded_response_body,
)
from google_workspace_admin.content.budgets import MAX_SHEETS_RESPONSE_BYTES
from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError
from google_workspace_admin.content.google_sheets import (
    _SheetsA1Range,
    _sheets_a1_range_to_a1_range,
    SheetsGridWindow,
    window_to_a1_range,
)
from google_workspace_admin.content.operations import (
    ContentOperation,
    SHEETS_API_ROOT,
    SHEETS_GRIDDATA_FIELDS,
    SHEETS_WORKBOOK_METADATA_FIELDS,
)


_SHEETS_API_ROOT = SHEETS_API_ROOT + "/"
_SPREADSHEET_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,256}\Z", re.ASCII)
_SHEETS_REQUEST_ERROR = ContentErrorOperation.SHEETS_GET
_SHEETS_RESPONSE_ERROR = ContentErrorOperation.RESPONSE_SHEETS_GET
_RICH_GRIDDATA_FIELDS = (
    "spreadsheetId,properties(locale,timeZone),sheets("
    "properties(sheetId,title,index,hidden,sheetType,gridProperties(rowCount,columnCount)),"
    "data(startRow,startColumn,rowData(values(userEnteredValue,effectiveValue,formattedValue,"
    "userEnteredFormat(numberFormat(type,pattern))))))"
)
_MAX_RICH_RANGES = 3


@dataclass(frozen=True, slots=True)
class _WorkbookMetadataRequest:
    spreadsheet_id: str

    def __post_init__(self) -> None:
        _validate_spreadsheet_id(self.spreadsheet_id)


@dataclass(frozen=True, slots=True)
class _GridDataWindowRequest:
    spreadsheet_id: str
    window: SheetsGridWindow

    def __post_init__(self) -> None:
        _validate_spreadsheet_id(self.spreadsheet_id)
        if type(self.window) is not SheetsGridWindow:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.SHEETS_GRIDDATA_WINDOW)


@dataclass(frozen=True, slots=True)
class _RichCellDataRequest:
    spreadsheet_id: str
    ranges: tuple[_SheetsA1Range, ...]

    def __post_init__(self) -> None:
        _validate_spreadsheet_id(self.spreadsheet_id)
        if (
            type(self.ranges) is not tuple
            or not 1 <= len(self.ranges) <= _MAX_RICH_RANGES
            or any(type(a1_range) is not _SheetsA1Range for a1_range in self.ranges)
        ):
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.SHEETS_GRIDDATA_WINDOW,
            )
        origins = tuple(
            (item.sheet_title, item.row, item.column_start)
            for item in self.ranges
        )
        if len(set(origins)) != len(origins):
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.SHEETS_GRIDDATA_WINDOW,
            )


class _DuplicateJSONKey(ValueError):
    pass


def _validate_spreadsheet_id(value: object) -> str:
    if type(value) is not str or _SPREADSHEET_ID_PATTERN.fullmatch(value) is None:
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.SHEETS_GET)
    return value


def build_workbook_metadata_request(spreadsheet_id: object) -> _WorkbookMetadataRequest:
    """Build the single fixed metadata request family; no query input is accepted."""

    return _WorkbookMetadataRequest(_validate_spreadsheet_id(spreadsheet_id))


def build_griddata_window_request(
    spreadsheet_id: object,
    window: object,
) -> _GridDataWindowRequest:
    """Build one internally ranged one-row GridData request."""

    if type(window) is not SheetsGridWindow:
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.SHEETS_GRIDDATA_WINDOW)
    return _GridDataWindowRequest(_validate_spreadsheet_id(spreadsheet_id), window)


def _build_rich_cell_data_request(
    spreadsheet_id: object,
    ranges: object,
) -> _RichCellDataRequest:
    """Build a fixed private observation request with one to three typed ranges."""

    if type(ranges) is not tuple:
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.SHEETS_GRIDDATA_WINDOW,
        )
    return _RichCellDataRequest(_validate_spreadsheet_id(spreadsheet_id), ranges)


def _endpoint(spreadsheet_id: str) -> str:
    return _SHEETS_API_ROOT + quote(spreadsheet_id, safe="-_")


def _request_params(
    request: _WorkbookMetadataRequest | _GridDataWindowRequest | _RichCellDataRequest,
) -> tuple[tuple[str, str | bool], ...]:
    if type(request) is _WorkbookMetadataRequest:
        return (
            ("fields", SHEETS_WORKBOOK_METADATA_FIELDS),
            ("includeGridData", False),
        )
    if type(request) is _GridDataWindowRequest:
        return (
            ("ranges", window_to_a1_range(request.window)),
            ("fields", SHEETS_GRIDDATA_FIELDS),
            ("includeGridData", True),
        )
    if type(request) is _RichCellDataRequest:
        request = _RichCellDataRequest(request.spreadsheet_id, request.ranges)
        return (
            *(("ranges", _sheets_a1_range_to_a1_range(item)) for item in request.ranges),
            ("fields", _RICH_GRIDDATA_FIELDS),
            ("includeGridData", True),
        )
    raise ContentSafeError(code="READ_ONLY_OPERATION_FORBIDDEN", operation=_SHEETS_REQUEST_ERROR)


def _object_pairs_no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJSONKey
        result[key] = value
    return result


def _reject_json_constant(_: str) -> None:
    raise ValueError


def _decode_sheets_json(raw: bytes) -> Mapping[str, object]:
    try:
        payload = json.loads(
            raw.decode("utf-8", "strict"),
            object_pairs_hook=_object_pairs_no_duplicates,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeError, json.JSONDecodeError, _DuplicateJSONKey, ValueError):
        raise ContentSafeError(code="RESPONSE_VALIDATION", operation=_SHEETS_RESPONSE_ERROR) from None
    if type(payload) is not dict:
        raise ContentSafeError(code="RESPONSE_VALIDATION", operation=_SHEETS_RESPONSE_ERROR)
    return payload


def _http_failure(status: int) -> ContentSafeError:
    if status in {401, 403}:
        code = "ACCESS_DENIED"
    elif status == 404:
        code = "NOT_FOUND"
    elif status == 429:
        code = "QUOTA_EXCEEDED"
    elif status >= 500 or status in {408, 425}:
        code = "TRANSIENT_UPSTREAM"
    else:
        code = "RESPONSE_VALIDATION"
    return ContentSafeError(code=code, operation=_SHEETS_REQUEST_ERROR, http_status=status)


def _request_operation(
    request: object,
) -> ContentOperation:
    if type(request) is _WorkbookMetadataRequest:
        return ContentOperation.SHEETS_WORKBOOK_METADATA
    if type(request) in {_GridDataWindowRequest, _RichCellDataRequest}:
        return ContentOperation.SHEETS_GRIDDATA_WINDOW
    raise ContentSafeError(code="READ_ONLY_OPERATION_FORBIDDEN", operation=_SHEETS_REQUEST_ERROR)


def _build_google_sheets_request_port(
    *,
    client: httpx.Client,
    require_context: Callable[[object], object],
    token_provider: Callable[[object, ApprovedScopeProfile], str],
) -> Callable[
    [AuthorizedOperationContext, _WorkbookMetadataRequest | _GridDataWindowRequest | _RichCellDataRequest],
    Mapping[str, object],
]:
    """Bind fixed Sheets requests to the sealed Content capability boundary."""

    if type(client) is not httpx.Client or not callable(require_context) or not callable(token_provider):
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.SHEETS_GET)

    def execute(
        request: _WorkbookMetadataRequest | _GridDataWindowRequest | _RichCellDataRequest,
        *,
        access_token: object,
    ) -> Mapping[str, object]:
        if type(request) not in {
            _WorkbookMetadataRequest,
            _GridDataWindowRequest,
            _RichCellDataRequest,
        }:
            raise ContentSafeError(code="READ_ONLY_OPERATION_FORBIDDEN", operation=_SHEETS_REQUEST_ERROR)
        _validate_spreadsheet_id(request.spreadsheet_id)
        if type(request) is _GridDataWindowRequest and type(request.window) is not SheetsGridWindow:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.SHEETS_GRIDDATA_WINDOW)
        if (
            type(access_token) is not str
            or not access_token
            or len(access_token) > 8192
            or any(character.isspace() or ord(character) < 32 for character in access_token)
        ):
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.AUTH_BROKER)

        response: httpx.Response | None = None
        try:
            http_request = client.build_request(
                "GET",
                _endpoint(request.spreadsheet_id),
                params=_request_params(request),
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept-Encoding": "gzip, deflate",
                },
            )
            response = client.send(http_request, stream=True, follow_redirects=False)
            if not 200 <= response.status_code < 300:
                raise _http_failure(response.status_code)
            body = read_bounded_response_body(
                response,
                raw_cap=MAX_SHEETS_RESPONSE_BYTES,
                decoded_cap=MAX_SHEETS_RESPONSE_BYTES,
            )
            if type(body) is BoundedBodyFailure:
                code = "TOO_LARGE" if body.kind == "too_large" else "RESPONSE_VALIDATION"
                raise ContentSafeError(code=code, operation=_SHEETS_RESPONSE_ERROR)
            return _decode_sheets_json(body)
        except ContentSafeError:
            raise
        except httpx.TimeoutException:
            raise ContentSafeError(code="TRANSIENT_UPSTREAM", operation=_SHEETS_REQUEST_ERROR) from None
        except httpx.RequestError:
            raise ContentSafeError(code="TRANSIENT_UPSTREAM", operation=_SHEETS_REQUEST_ERROR) from None
        except Exception:
            raise ContentSafeError(code="RESPONSE_VALIDATION", operation=_SHEETS_REQUEST_ERROR) from None
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    # A close failure must not replace a safe primary result/error.
                    pass

    def read(
        context: AuthorizedOperationContext,
        request: _WorkbookMetadataRequest | _GridDataWindowRequest | _RichCellDataRequest,
    ) -> Mapping[str, object]:
        operation = _request_operation(request)
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
            or authority.operation is not operation
            or authority.approved_scope_profile is not ApprovedScopeProfile.DRIVE_DISCOVERY
            or type(authority.admin_mode_authorized) is not bool
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
            raise ContentSafeError(code="UNEXPECTED_LOCAL", operation=ContentErrorOperation.AUTH_BROKER) from None
        return execute(request, access_token=access_token)

    return read
