from __future__ import annotations

import json
import gzip
import inspect
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier
from urllib.parse import parse_qs

import httpx
import pytest

from google_workspace_admin import server
from google_workspace_admin.content.auth.handles import _OperationAuthority
from google_workspace_admin.content.auth.capabilities import (
    AdminCapability,
    ContentCapability,
    SubjectCapability,
    capability_rule,
)
from google_workspace_admin.content.auth.scopes import ApprovedScopeProfile, scopes_for
from google_workspace_admin.content.budgets import (
    DEFAULT_CONTENT_READING_BUDGETS,
    MAX_SHEETS_GRIDDATA_CELLS_PER_INVOCATION,
    MAX_SHEETS_GRIDDATA_REQUESTS_PER_INVOCATION,
    MAX_SHEETS_REQUEST_WINDOW_CELLS,
    MAX_SHEETS_RESPONSE_BYTES,
)
from google_workspace_admin.content.continuation import (
    DocsContinuationManager,
    SheetsContinuationState,
)
from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError
from google_workspace_admin.content.google_sheets import (
    _SheetsA1Range,
    SheetHandling,
    SheetMetadata,
    SheetType,
    SheetsCoverageGap,
    SheetsGridWindow,
    cell_to_a1,
    extract_griddata_content,
    parse_griddata_envelope,
    parse_workbook_metadata,
    utf16_code_unit_length,
    window_to_a1_range,
    zero_based_column_to_a1,
)
from google_workspace_admin.content.google_sheets_adapter import (
    _GridDataWindowRequest,
    _RICH_GRIDDATA_FIELDS,
    _RichCellDataRequest,
    _WorkbookMetadataRequest,
    _build_google_sheets_request_port,
    _build_rich_cell_data_request,
    _request_params,
    build_griddata_window_request,
    build_workbook_metadata_request,
)
from google_workspace_admin.content.operations import (
    ContentOperation,
    DRIVE_FILE_METADATA_FIELDS,
    FileContentReadRequest,
    SHEETS_API_ROOT,
    SHEETS_GRIDDATA_FIELDS,
    SHEETS_WORKBOOK_METADATA_FIELDS,
    get_operation_contract,
    _operation_for_request,
)
from google_workspace_admin.content.routing import ContentClass, route_mime_type
from google_workspace_admin.content.provenance import SheetsContentComponent
from google_workspace_admin.content.outcomes import ProcessingStatus
from google_workspace_admin.content.inventory import InventorySnapshot
from google_workspace_admin.content.safety import (
    NEVER_EXECUTE_FILE_CONTENT,
    ReaderDispatch,
    fixed_reader_dispatch,
)
from google_workspace_admin.content import google_sheets_reader
from google_workspace_admin.content import google_docs_adapter
from google_workspace_admin.content.google_docs import (
    DriveFileMetadata,
    _DriveFileMetadataReadFailure,
)
from google_workspace_admin.content.runtime import ContentRuntime
from content_runtime_harness import content_runtime_harness


SPREADSHEET_MIME = "application/vnd.google-apps.spreadsheet"
SHEET_MIME = "application/vnd.google-apps.spreadsheet"
TEST_PUBLIC_FILE_REF = "gdrv_v1_" + "A" * 43


def _properties(
    *,
    sheet_id: int = 10,
    index: int = 0,
    title: str = "Main",
    hidden: bool = False,
    sheet_type: str = "GRID",
    rows: int = 10,
    columns: int = 20,
) -> dict[str, object]:
    properties: dict[str, object] = {
        "sheetId": sheet_id,
        "index": index,
        "title": title,
        "hidden": hidden,
        "sheetType": sheet_type,
    }
    if sheet_type == "GRID":
        properties["gridProperties"] = {"rowCount": rows, "columnCount": columns}
    return properties


def _metadata_sheet(**kwargs: object) -> SheetMetadata:
    parsed = parse_workbook_metadata({"sheets": [{"properties": _properties(**kwargs)}]})
    return parsed.sheets[0]


def _window(
    *,
    title: str = "Main",
    row_start: int = 0,
    column_start: int = 0,
    column_count: int = 2,
    rows: int = 10,
    columns: int = 40,
) -> SheetsGridWindow:
    sheet = _metadata_sheet(title=title, rows=rows, columns=columns)
    return SheetsGridWindow(sheet, row_start, 1, column_start, column_count)


def _extract_cells(window: SheetsGridWindow, values: list[dict[str, object]]):
    envelope = parse_griddata_envelope(_grid_envelope(window, values=values), window=window)
    return extract_griddata_content(
        envelope,
        window=window,
        file_ref=TEST_PUBLIC_FILE_REF,
    )


def _grid_envelope(window: SheetsGridWindow, *, values: list[dict[str, object]] | None = None):
    return {
        "sheets": [
            {
                "properties": {
                    "sheetId": window.sheet.sheet_id,
                    "index": window.sheet.index,
                    "sheetType": "GRID",
                },
                "data": [
                    {
                        "startRow": window.row_start,
                        "startColumn": window.column_start,
                        "rowData": [{"values": values or []}],
                    }
                ],
            }
        ]
    }


class _Chunks(httpx.SyncByteStream):
    def __init__(self, *, total: int, chunk_size: int = 32 * 1024, byte: bytes = b"x") -> None:
        self.total = total
        self.chunk_size = chunk_size
        self.byte = byte
        self.yielded = 0
        self.closed = False

    def __iter__(self):
        while self.yielded < self.total:
            size = min(self.chunk_size, self.total - self.yielded)
            self.yielded += size
            yield self.byte * size

    def close(self) -> None:
        self.closed = True


class _FailIfRead(httpx.SyncByteStream):
    def __init__(self) -> None:
        self.iterated = False

    def __iter__(self):
        self.iterated = True
        raise AssertionError("oversized Content-Length must stop before body iteration")
        yield b""


class _FailClose(httpx.SyncByteStream):
    def __iter__(self):
        yield b"ignored"

    def close(self) -> None:
        raise RuntimeError("private-stream-close-sentinel")


class _Payload(httpx.SyncByteStream):
    def __init__(self, raw: bytes) -> None:
        self.raw = raw
        self.closed = False

    def __iter__(self):
        yield self.raw

    def close(self) -> None:
        self.closed = True


def _json_response(payload: object) -> httpx.Response:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return httpx.Response(200, headers={"Content-Length": str(len(raw))}, stream=_Payload(raw))


def _authorized_port(client: httpx.Client, operation: ContentOperation):
    context = object()
    authority = _OperationAuthority(
        profile_handle=None,  # type: ignore[arg-type]
        subject_handle=None,  # type: ignore[arg-type]
        operation=operation,
        approved_scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
        admin_mode_authorized=False,
    )

    def require_context(candidate: object) -> object:
        if candidate is not context:
            raise ContentSafeError(
                code="READ_ONLY_OPERATION_FORBIDDEN",
                operation=ContentErrorOperation.AUTH_CONTEXT_PROVENANCE,
            )
        return authority

    def token_provider(candidate: object, profile: ApprovedScopeProfile) -> str:
        assert candidate is context
        assert profile is ApprovedScopeProfile.DRIVE_DISCOVERY
        return "synthetic-secret"

    return (
        _build_google_sheets_request_port(
            client=client,
            require_context=require_context,
            token_provider=token_provider,
        ),
        context,
    )


def test_metadata_request_uses_fixed_get_endpoint_fields_and_no_griddata():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _json_response({"sheets": []})

    request = build_workbook_metadata_request("file_id_123")
    assert type(request) is _WorkbookMetadataRequest
    assert _request_params(request) == (
        ("fields", SHEETS_WORKBOOK_METADATA_FIELDS),
        ("includeGridData", False),
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        port, context = _authorized_port(client, ContentOperation.SHEETS_WORKBOOK_METADATA)
        payload = port(context, request)

    assert payload == {"sheets": []}
    assert len(seen) == 1
    assert seen[0].method == "GET"
    assert seen[0].url.scheme == "https"
    assert seen[0].url.host == "sheets.googleapis.com"
    assert seen[0].url.path == "/v4/spreadsheets/file_id_123"
    query = parse_qs(seen[0].url.query.decode())
    assert query == {
        "fields": [SHEETS_WORKBOOK_METADATA_FIELDS],
        "includeGridData": ["false"],
    }
    assert "ranges" not in query
    assert seen[0].headers["authorization"] == "Bearer synthetic-secret"
    assert "synthetic-secret" not in repr(payload)


def test_griddata_request_has_one_generated_range_and_fixed_mask():
    window = _window(title="Quarter '東京'!A1:B2", row_start=4, column_start=26)
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _json_response(_grid_envelope(window, values=[{}, {}]))

    request = build_griddata_window_request("sheet_file_1", window)
    assert type(request) is _GridDataWindowRequest
    assert _request_params(request) == (
        ("ranges", "'Quarter ''東京''!A1:B2'!AA5:AB5"),
        ("fields", SHEETS_GRIDDATA_FIELDS),
        ("includeGridData", True),
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        port, context = _authorized_port(client, ContentOperation.SHEETS_GRIDDATA_WINDOW)
        port(context, request)

    assert len(seen) == 1
    assert seen[0].method == "GET"
    assert seen[0].url.host == "sheets.googleapis.com"
    assert seen[0].url.path == "/v4/spreadsheets/sheet_file_1"
    query = parse_qs(seen[0].url.query.decode())
    assert query["ranges"] == ["'Quarter ''東京''!A1:B2'!AA5:AB5"]
    assert query["fields"] == [SHEETS_GRIDDATA_FIELDS]
    assert query["includeGridData"] == ["true"]


def test_a1_conversion_is_zero_based_and_deterministic():
    assert [zero_based_column_to_a1(value) for value in (0, 25, 26, 27, 51, 52, 701, 702)] == [
        "A",
        "Z",
        "AA",
        "AB",
        "AZ",
        "BA",
        "ZZ",
        "AAA",
    ]
    assert window_to_a1_range(_window(row_start=8, column_start=1, column_count=3)) == "'Main'!B9:D9"
    assert window_to_a1_range(_window(title="A1:B2 'Δ'", row_start=0)) == "'A1:B2 ''Δ'''!A1:B1"


def test_metadata_is_strict_and_uses_authoritative_api_index_order():
    parsed = parse_workbook_metadata(
        {
            "sheets": [
                {"properties": _properties(sheet_id=2, index=2, title="Hidden", hidden=True)},
                {"properties": _properties(sheet_id=1, index=0, title="Visible")},
                {"properties": {"sheetId": 3, "index": 1, "title": "Object", "sheetType": "OBJECT"}},
                {"properties": {"sheetId": 4, "index": 3, "title": "Data", "sheetType": "DATA_SOURCE"}},
            ]
        }
    )
    assert [sheet.sheet_id for sheet in parsed.sheets] == [1, 3, 2, 4]
    assert parsed.sheets[2].hidden is True
    assert parsed.sheets[1].handling is SheetHandling.OBJECT_COVERAGE_GAP
    assert parsed.sheets[3].handling is SheetHandling.DATA_SOURCE_COVERAGE_GAP
    assert parsed.sheets[0].handling is SheetHandling.GRIDDATA_ELIGIBLE


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {},
        {"sheets": {}},
        {"sheets": [None]},
        {"sheets": [{"properties": []}]},
        {"sheets": [{"properties": {**_properties(), "sheetId": True}}]},
        {"sheets": [{"properties": {**_properties(), "index": -1}}]},
        {"sheets": [{"properties": {**_properties(), "hidden": "false"}}]},
        {"sheets": [{"properties": {**_properties(), "sheetType": "CHART"}}]},
        {"sheets": [{"properties": {**_properties(), "gridProperties": {"rowCount": 1}}}]},
        {"sheets": [{"properties": {**_properties(), "gridProperties": {"rowCount": -1, "columnCount": 2}}}]},
        {"sheets": [{"properties": {**_properties(), "title": "bad\ud800"}}]},
    ],
)
def test_malformed_metadata_fails_closed(payload: object):
    with pytest.raises(ContentSafeError) as caught:
        parse_workbook_metadata(payload)
    assert caught.value.code == "RESPONSE_VALIDATION"
    assert caught.value.operation == ContentErrorOperation.RESPONSE_SHEETS_METADATA.value


def test_duplicate_metadata_sheet_ids_and_indexes_fail_closed():
    for second in (
        _properties(sheet_id=10, index=1, title="Other"),
        _properties(sheet_id=11, index=0, title="Other"),
    ):
        with pytest.raises(ContentSafeError):
            parse_workbook_metadata(
                {"sheets": [{"properties": _properties()}, {"properties": second}]}
            )


def test_sheet_limit_is_reused_from_existing_budget():
    too_many = [
        {"properties": _properties(sheet_id=index, index=index, title=f"S{index}")}
        for index in range(201)
    ]
    with pytest.raises(ContentSafeError) as caught:
        parse_workbook_metadata({"sheets": too_many})
    assert caught.value.code == "TOO_LARGE"


def test_grid_window_is_one_row_bounded_and_inside_metadata_dimensions():
    window = _window(row_start=9, column_start=18, column_count=2)
    assert window.row_count == 1
    assert window.column_count <= MAX_SHEETS_REQUEST_WINDOW_CELLS

    invalid = (
        (SheetMetadata(10, 0, "Main", False, SheetType.GRID, 10, 20), -1, 1, 0, 1),
        (SheetMetadata(10, 0, "Main", False, SheetType.GRID, 10, 20), 0, 2, 0, 1),
        (SheetMetadata(10, 0, "Main", False, SheetType.GRID, 10, 20), 0, 1, 0, 1001),
        (SheetMetadata(10, 0, "Main", False, SheetType.GRID, 10, 20), 10, 1, 0, 1),
        (SheetMetadata(10, 0, "Main", False, SheetType.GRID, 10, 20), 0, 1, 20, 1),
        (SheetMetadata(10, 0, "Main", False, SheetType.OBJECT, None, None), 0, 1, 0, 1),
    )
    for args in invalid:
        with pytest.raises(ContentSafeError):
            SheetsGridWindow(args[0], args[1], args[2], args[3], args[4])
    with pytest.raises(ContentSafeError):
        SheetsGridWindow(window.sheet, True, 1, 0, 1)


def test_griddata_envelope_validates_identity_origin_and_containers():
    window = _window(row_start=4, column_start=6)
    parsed = parse_griddata_envelope(
        _grid_envelope(window, values=[{}, {}]),
        window=window,
    )
    assert (
        parsed.sheet_id,
        parsed.sheet_index,
        parsed.start_row,
        parsed.start_column,
        parsed.returned_rows,
        parsed.returned_cells,
    ) == (10, 0, 4, 6, 1, 2)
    assert len(parsed.cells) == 2
    assert parse_griddata_envelope(
        {"sheets": [{"properties": {"sheetId": 10, "index": 0, "sheetType": "GRID"}, "data": []}]},
        window=window,
    ).returned_cells == 0

    malformed = (
        None,
        {"sheets": {}},
        {"sheets": []},
        {"sheets": [{"properties": {"sheetId": 10, "index": 0, "sheetType": "GRID"}, "data": {}}]},
        {"sheets": [{"properties": {"sheetId": 11, "index": 0, "sheetType": "GRID"}, "data": []}]},
        {"sheets": [{"properties": {"sheetId": 10, "index": 0, "sheetType": "GRID"}, "data": [{"startRow": True, "startColumn": 6}]}]},
        {"sheets": [{"properties": {"sheetId": 10, "index": 0, "sheetType": "GRID"}, "data": [{"startRow": 5, "startColumn": 6}]}]},
        {"sheets": [{"properties": {"sheetId": 10, "index": 0, "sheetType": "GRID"}, "data": [{"rowData": []}]}]},
        {"sheets": [{"properties": {"sheetId": 10, "index": 0, "sheetType": "GRID"}, "data": [{"startRow": 4, "startColumn": 6, "rowData": {}}]}]},
        {"sheets": [{"properties": {"sheetId": 10, "index": 0, "sheetType": "GRID"}, "data": [{"startRow": 4, "startColumn": 6, "rowData": [{"values": {}}]}]}]},
        {"sheets": [{"properties": {"sheetId": 10, "index": 0, "sheetType": "GRID"}, "data": [{"startRow": 4, "startColumn": 6}, {"startRow": 4, "startColumn": 6}]}]},
    )
    for payload in malformed:
        with pytest.raises(ContentSafeError) as caught:
            parse_griddata_envelope(payload, window=window)
        assert caught.value.code == "RESPONSE_VALIDATION"
        assert caught.value.operation == ContentErrorOperation.RESPONSE_SHEETS_GRIDDATA.value


def test_griddata_zero_origin_fields_may_be_omitted_only_at_zero():
    window = _window(row_start=0, column_start=0)
    explicit = parse_griddata_envelope(_grid_envelope(window, values=[]), window=window)
    assert (explicit.start_row, explicit.start_column) == (0, 0)

    payload = _grid_envelope(window, values=[{"formattedValue": "origin"}])
    data = payload["sheets"][0]["data"][0]
    del data["startRow"]
    del data["startColumn"]

    parsed = parse_griddata_envelope(payload, window=window)

    assert (parsed.start_row, parsed.start_column, parsed.returned_cells) == (0, 0, 1)

    for row_start, column_start, omitted_key in (
        (0, 7, "startRow"),
        (9, 0, "startColumn"),
    ):
        window = _window(row_start=row_start, column_start=column_start)
        payload = _grid_envelope(window, values=[])
        del payload["sheets"][0]["data"][0][omitted_key]
        parsed = parse_griddata_envelope(payload, window=window)
        assert (parsed.start_row, parsed.start_column) == (row_start, column_start)

    for row_start, column_start, omitted_key in (
        (9, 7, "startRow"),
        (9, 7, "startColumn"),
    ):
        window = _window(row_start=row_start, column_start=column_start)
        payload = _grid_envelope(window, values=[])
        del payload["sheets"][0]["data"][0][omitted_key]
        with pytest.raises(ContentSafeError) as caught:
            parse_griddata_envelope(payload, window=window)
        assert caught.value.code == "RESPONSE_VALIDATION"
        assert caught.value.operation == ContentErrorOperation.RESPONSE_SHEETS_GRIDDATA.value


@pytest.mark.parametrize(
    "axis, value",
    [
        ("startRow", None),
        ("startRow", True),
        ("startRow", "0"),
        ("startRow", 0.0),
        ("startRow", -1),
        ("startColumn", None),
        ("startColumn", False),
        ("startColumn", "0"),
        ("startColumn", 0.0),
        ("startColumn", -1),
    ],
)
def test_griddata_present_origin_fields_remain_strictly_typed(axis: str, value: object):
    window = _window(row_start=0, column_start=0)
    payload = _grid_envelope(window, values=[])
    payload["sheets"][0]["data"][0][axis] = value

    with pytest.raises(ContentSafeError) as caught:
        parse_griddata_envelope(payload, window=window)
    assert caught.value.code == "RESPONSE_VALIDATION"
    assert caught.value.operation == ContentErrorOperation.RESPONSE_SHEETS_GRIDDATA.value


def test_formula_and_hyperlink_are_inert_payload_data():
    window = _window()
    payload = _grid_envelope(
        window,
        values=[
            {
                "userEnteredValue": {"formulaValue": '=IMPORTXML("https://outside.invalid", "//x")'},
                "formattedValue": "stored display",
                "hyperlink": "https://outside.invalid/path",
            }
        ],
    )
    result = parse_griddata_envelope(payload, window=window)
    assert result.returned_cells == 1
    assert "outside.invalid" not in repr(result)
    assert NEVER_EXECUTE_FILE_CONTENT is True


def test_spreadsheet_id_and_request_families_reject_untrusted_request_data():
    for invalid_id in ("", "https://attacker.invalid/sheet", "../files", "bad\nvalue", "x" * 257):
        with pytest.raises(ContentSafeError):
            build_workbook_metadata_request(invalid_id)
    with pytest.raises(ContentSafeError):
        build_griddata_window_request("valid_id", "'Main'!A1:A1")
    with pytest.raises(ContentSafeError):
        _operation_for_request(build_workbook_metadata_request("valid_id"))


def test_sheets_executor_rejects_non_sheets_request_and_redirects_without_following():
    calls: list[httpx.Request] = []

    def redirect_handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(302, headers={"Location": "https://attacker.invalid/"})

    with httpx.Client(transport=httpx.MockTransport(redirect_handler)) as client:
        port, context = _authorized_port(client, ContentOperation.SHEETS_WORKBOOK_METADATA)
        with pytest.raises(ContentSafeError) as caught:
            port(context, object())  # type: ignore[arg-type]
        assert caught.value.code == "READ_ONLY_OPERATION_FORBIDDEN"
        with pytest.raises(ContentSafeError) as redirect_error:
            port(
                context,
                build_workbook_metadata_request("valid_id"),
            )
    assert redirect_error.value.code == "RESPONSE_VALIDATION"
    assert len(calls) == 1
    assert "attacker.invalid" not in str(redirect_error.value)
    assert "synthetic-secret" not in str(redirect_error.value)


def test_authorized_sheets_port_requires_matching_sealed_operation_before_token():
    requests: list[httpx.Request] = []
    token_calls: list[object] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _json_response({"sheets": []})

    mismatched = _OperationAuthority(
        profile_handle=None,  # type: ignore[arg-type]
        subject_handle=None,  # type: ignore[arg-type]
        operation=ContentOperation.FILE_CONTENT_READ,
        approved_scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
        admin_mode_authorized=False,
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        port = _build_google_sheets_request_port(
            client=client,
            require_context=lambda _: mismatched,
            token_provider=lambda *args: token_calls.append(args) or "must-not-be-used",
        )
        with pytest.raises(ContentSafeError) as caught:
            port(object(), build_workbook_metadata_request("valid_id"))  # type: ignore[arg-type]
    assert caught.value.code == "READ_ONLY_OPERATION_FORBIDDEN"
    assert token_calls == []
    assert requests == []


def test_sheets_close_failure_does_not_escape_or_mask_safe_http_error():
    stream = _FailClose()

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(302, stream=stream)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        port, context = _authorized_port(client, ContentOperation.SHEETS_WORKBOOK_METADATA)
        with pytest.raises(ContentSafeError) as caught:
            port(
                context,
                build_workbook_metadata_request("valid_id"),
            )
    assert caught.value.code == "RESPONSE_VALIDATION"
    assert "private-stream-close-sentinel" not in str(caught.value)


def test_sheets_response_body_cap_is_streamed_before_json_decode(monkeypatch):
    stream = _Chunks(total=4 * 1024 * 1024, byte=b"S")

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=stream)

    monkeypatch.setattr(
        "google_workspace_admin.content.google_sheets_adapter._decode_sheets_json",
        lambda _: pytest.fail("oversized body must be rejected before JSON materialization"),
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        port, context = _authorized_port(client, ContentOperation.SHEETS_WORKBOOK_METADATA)
        with pytest.raises(ContentSafeError) as caught:
            port(
                context,
                build_workbook_metadata_request("valid_id"),
            )
    assert caught.value.code == "TOO_LARGE"
    assert stream.yielded < stream.total
    assert stream.yielded <= MAX_SHEETS_RESPONSE_BYTES + 64 * 1024
    assert stream.closed is True
    assert "S" * 32 not in str(caught.value)
    assert "synthetic-secret" not in str(caught.value)
    assert "sheets.googleapis.com" not in str(caught.value)


def test_sheets_response_content_length_cap_stops_before_body_iteration():
    stream = _FailIfRead()

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Length": str(MAX_SHEETS_RESPONSE_BYTES + 1)},
            stream=stream,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        port, context = _authorized_port(client, ContentOperation.SHEETS_WORKBOOK_METADATA)
        with pytest.raises(ContentSafeError) as caught:
            port(
                context,
                build_workbook_metadata_request("valid_id"),
            )
    assert caught.value.code == "TOO_LARGE"
    assert stream.iterated is False


def test_sheets_decoded_response_cap_rejects_compressed_expansion():
    raw = gzip.compress(b"x" * (MAX_SHEETS_RESPONSE_BYTES + 1))

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={
                "Content-Length": str(len(raw)),
                "Content-Encoding": "gzip",
            },
            stream=_Payload(raw),
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        port, context = _authorized_port(client, ContentOperation.SHEETS_WORKBOOK_METADATA)
        with pytest.raises(ContentSafeError) as caught:
            port(
                context,
                build_workbook_metadata_request("valid_id"),
            )
    assert caught.value.code == "TOO_LARGE"


@pytest.mark.parametrize(
    ("body", "expected_code"),
    [
        (b"not-json-sensitive-body", "RESPONSE_VALIDATION"),
        (b'{"sheets":[],"sheets":[]}', "RESPONSE_VALIDATION"),
        (b"[]", "RESPONSE_VALIDATION"),
    ],
)
def test_malformed_sheets_json_fails_closed_without_payload_leakage(body: bytes, expected_code: str):
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=_Payload(body))

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        port, context = _authorized_port(client, ContentOperation.SHEETS_WORKBOOK_METADATA)
        with pytest.raises(ContentSafeError) as caught:
            port(
                context,
                build_workbook_metadata_request("valid_id"),
            )
    assert caught.value.code == expected_code
    assert caught.value.operation == ContentErrorOperation.RESPONSE_SHEETS_GET.value
    assert "not-json-sensitive-body" not in str(caught.value)
    assert "synthetic-secret" not in str(caught.value)


def test_capability_is_private_and_uses_existing_drive_readonly_profile():
    for operation in (
        ContentOperation.SHEETS_WORKBOOK_METADATA,
        ContentOperation.SHEETS_GRIDDATA_WINDOW,
    ):
        rule = capability_rule(operation)
        contract = get_operation_contract(operation)
        assert rule.capability is ContentCapability.GOOGLE_SHEETS_CONTENT
        assert rule.scope_profile is ApprovedScopeProfile.DRIVE_DISCOVERY
        assert rule.subject_capability is SubjectCapability.DRIVE
        assert rule.admin_capability is AdminCapability.NONE
        assert contract.method == "GET"
        assert contract.endpoint_template == f"{SHEETS_API_ROOT}/{{spreadsheet_id}}"
        assert contract.scope_profile is ApprovedScopeProfile.DRIVE_DISCOVERY
    assert scopes_for(ApprovedScopeProfile.DRIVE_DISCOVERY) == (
        "https://www.googleapis.com/auth/drive.readonly",
    )
    assert "spreadsheets.readonly" not in scopes_for(ApprovedScopeProfile.DRIVE_DISCOVERY)


def test_sheet_mime_routes_to_bounded_public_reader(monkeypatch):
    assert route_mime_type(SHEET_MIME) is ContentClass.GOOGLE_SHEET
    assert fixed_reader_dispatch(ContentClass.GOOGLE_SHEET) is ReaderDispatch.GOOGLE_SHEETS
    sheet_id = "synthetic-sheet-id"
    modified = "2026-09-21T00:00:00.000Z"
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.host == "www.googleapis.com":
            return _json_response(
                {
                    "id": sheet_id,
                    "mimeType": SPREADSHEET_MIME,
                    "modifiedTime": modified,
                    "trashed": False,
                }
            )
        query = parse_qs(request.url.query.decode())
        if "ranges" not in query:
            return _json_response(
                {"sheets": [{"properties": _properties(rows=1, columns=1)}]}
            )
        return _json_response(
            {
                "sheets": [
                    {
                        "properties": {"sheetId": 10, "index": 0, "sheetType": "GRID"},
                        "data": [
                            {
                                "startRow": 0,
                                "startColumn": 0,
                                "rowData": [{"values": [{"formattedValue": "safe cell"}]}],
                            }
                        ],
                    }
                ]
            }
        )

    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        monkeypatch.setattr(server, "_get_content_runtime", lambda: runtime)
        monkeypatch.setattr(
            server,
            "_content_identity",
            lambda: ("drive-discovery", "analyst@cevalente.com.br"),
        )
        response = server.workspace_file_content_read(sheet_id, SPREADSHEET_MIME, modified)
    assert response["processing_status"] == "PROCESSED", (
        response["safe_error_code"],
        response["failure_stage"],
        [(request.method, request.url.host, request.url.path, request.url.query) for request in calls],
    )
    assert response["chunks"][0]["text"] == "safe cell"
    assert response["chunks"][0]["file_ref"].startswith("gdrv_v1_")
    assert sheet_id not in repr(response)
    assert response["chunks"][0]["provenance"] == {
        "sheet_ordinal": 0,
        "a1": "A1",
        "component": "CELL_DISPLAY",
    }
    assert len(captured) == len(calls) == 4
    assert [request.method for request in calls] == ["GET"] * 4
    assert [request.url.host for request in calls] == [
        "www.googleapis.com",
        "sheets.googleapis.com",
        "sheets.googleapis.com",
        "www.googleapis.com",
    ]
    assert "ranges" not in parse_qs(calls[1].url.query.decode())
    assert "ranges" in parse_qs(calls[2].url.query.decode())


def test_missing_public_file_ref_key_fails_closed_before_google_requests(monkeypatch):
    file_id = "synthetic-sheet-id"
    modified = "2026-09-21T00:00:00.000Z"
    handler, _calls = _mock_sheets_handler(file_id=file_id, sheets=(_properties(),))
    with content_runtime_harness(
        monkeypatch,
        handler,
        public_file_ref_provider=None,
    ) as (runtime, captured):
        _enable_public_runtime(monkeypatch, runtime)
        response = _public_sheet_call(runtime, file_id, modified)

    assert response["processing_status"] == "EXTRACTION_FAILED"
    assert response["safe_error_code"] == "CONTENT_NOT_SUPPORTED"
    assert captured == []


def test_pseudonymous_reference_is_not_accepted_as_sheets_read_input(monkeypatch):
    file_id = TEST_PUBLIC_FILE_REF
    modified = "2026-09-21T00:00:00.000Z"
    handler, _calls = _mock_sheets_handler(file_id=file_id, sheets=(_properties(),))
    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _enable_public_runtime(monkeypatch, runtime)
        response = _public_sheet_call(runtime, file_id, modified)

    assert response["processing_status"] == "EXTRACTION_FAILED"
    assert response["safe_error_code"] == "LOCAL_VALIDATION"
    assert captured == []


def _column_index(letters: str) -> int:
    value = 0
    for character in letters:
        value = value * 26 + ord(character) - ord("A") + 1
    return value - 1


def _window_from_request(request: httpx.Request) -> tuple[str, int, int, int]:
    query = parse_qs(request.url.query.decode())
    range_text = query["ranges"][0]
    title, coordinates = range_text.rsplit("!", 1)
    match = re.fullmatch(r"([A-Z]+)([0-9]+):([A-Z]+)([0-9]+)", coordinates)
    assert match is not None
    start_column = _column_index(match.group(1))
    row = int(match.group(2)) - 1
    end_column = _column_index(match.group(3))
    return title.strip("'").replace("''", "'"), row, start_column, end_column - start_column + 1


def _drive_payload(
    file_id: str,
    modified: str = "2026-09-21T00:00:00.000Z",
    *,
    mime_type: str = SPREADSHEET_MIME,
    trashed: bool = False,
    size: int | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": file_id,
        "mimeType": mime_type,
        "modifiedTime": modified,
        "trashed": trashed,
    }
    if size is not None:
        payload["size"] = size
    return payload


def _metadata_payload(*sheets: dict[str, object]) -> dict[str, object]:
    return {"sheets": [{"properties": sheet} for sheet in sheets]}


def _grid_response(
    *,
    sheet_id: int,
    index: int,
    row: int,
    column: int,
    cells: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "sheets": [
            {
                "properties": {"sheetId": sheet_id, "index": index, "sheetType": "GRID"},
                "data": [
                    {
                        "startRow": row,
                        "startColumn": column,
                        "rowData": [{"values": cells}],
                    }
                ],
            }
        ]
    }


def _mock_sheets_handler(
    *,
    file_id: str,
    sheets: tuple[dict[str, object], ...],
    cell_factory=None,
    drive_responses: tuple[dict[str, object] | int, ...] | None = None,
):
    calls: list[httpx.Request] = []
    drive_count = 0
    by_title = {sheet["title"]: sheet for sheet in sheets}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal drive_count
        calls.append(request)
        if request.url.host == "www.googleapis.com":
            drive_count += 1
            response = None if drive_responses is None else drive_responses[min(drive_count - 1, len(drive_responses) - 1)]
            if type(response) is int:
                return httpx.Response(response)
            return _json_response(response or _drive_payload(file_id))
        query = parse_qs(request.url.query.decode())
        if "ranges" not in query:
            return _json_response({"sheets": [{"properties": sheet} for sheet in sheets]})
        title, row, column, width = _window_from_request(request)
        sheet = by_title[title]
        if cell_factory is None:
            cells: list[dict[str, object]] = []
        else:
            cells = cell_factory(sheet, row, column, width, len(calls))
        return _json_response(
            _grid_response(
                sheet_id=sheet["sheetId"],
                index=sheet["index"],
                row=row,
                column=column,
                cells=cells,
            )
        )

    return handler, calls


def _public_sheet_call(runtime, file_id: str, modified: str, token: str | None = None):
    return server.workspace_file_content_read(
        file_id,
        SPREADSHEET_MIME,
        modified,
        continuation_token=token,
    )


def _enable_public_runtime(monkeypatch, runtime) -> None:
    monkeypatch.setattr(server, "_get_content_runtime", lambda: runtime)
    monkeypatch.setattr(
        server,
        "_content_identity",
        lambda: ("drive-discovery", "analyst@cevalente.com.br"),
    )


def test_end_to_end_worst_case_call_budget_and_zero_chunk_continuation(monkeypatch):
    file_id = "synthetic-sheet-id"
    modified = "2026-09-21T00:00:00.000Z"
    sheet = _properties(rows=1, columns=10_000)
    handler, calls = _mock_sheets_handler(file_id=file_id, sheets=(sheet,))
    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _enable_public_runtime(monkeypatch, runtime)
        first = _public_sheet_call(runtime, file_id, modified)
        assert first["processing_status"] == "PARTIALLY_PROCESSED"
        assert first["chunks"] == []
        token = first["continuation_token"]
        assert isinstance(token, str) and len(token) <= 4096
        assert file_id not in token and "Main" not in token
        assert len(calls) == len(captured) == 11
        assert sum("ranges" in parse_qs(request.url.query.decode()) for request in calls) == MAX_SHEETS_GRIDDATA_REQUESTS_PER_INVOCATION
        requested = 0
        for request in calls:
            query = parse_qs(request.url.query.decode())
            if "ranges" in query:
                _, _, _, width = _window_from_request(request)
                requested += width
        assert requested == MAX_SHEETS_GRIDDATA_CELLS_PER_INVOCATION == 8000
        assert all(request.method == "GET" for request in calls)
        second = _public_sheet_call(runtime, file_id, modified, token)
    assert second["processing_status"] == "EMPTY"
    assert second["chunks"] == []
    assert second["continuation_token"] is None
    assert len(calls) == 16


def test_public_chain_retains_prior_chunks_through_empty_terminal_page(monkeypatch):
    file_id = "synthetic-sheet-id"
    modified = "2026-09-21T00:00:00.000Z"
    sheet = _properties(rows=3, columns=8000)

    def cells(_sheet, row, column, _width, _call):
        return [{"formattedValue": "first-page-only"}] if (row, column) == (0, 0) else []

    handler, calls = _mock_sheets_handler(
        file_id=file_id,
        sheets=(sheet,),
        cell_factory=cells,
    )
    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _enable_public_runtime(monkeypatch, runtime)
        pages = []
        aggregate = []
        consumed_tokens = set()
        token = None
        for _ in range(4):
            page = _public_sheet_call(runtime, file_id, modified, token)
            pages.append(page)
            assert page["processing_status"] in {"PARTIALLY_PROCESSED", "PROCESSED", "EMPTY"}
            assert page["chunk_count"] == page["result_count"] == len(page["chunks"])
            aggregate.extend(page["chunks"])
            token = page["continuation_token"]
            if token is None:
                break
            assert token not in consumed_tokens
            consumed_tokens.add(token)
        else:
            pytest.fail("synthetic continuation chain did not terminate")

        call_count = len(calls)
        with pytest.raises(ContentSafeError):
            _public_sheet_call(runtime, file_id, modified, pages[0]["continuation_token"])
        assert len(calls) == call_count

    assert [page["processing_status"] for page in pages] == [
        "PARTIALLY_PROCESSED", "PARTIALLY_PROCESSED", "EMPTY"
    ]
    assert [page["chunk_count"] for page in pages] == [1, 0, 0]
    assert [page["continuation_token"] is not None for page in pages] == [True, True, False]
    assert len(consumed_tokens) == 2
    assert [(chunk["text"], chunk["provenance"]["a1"]) for chunk in aggregate] == [
        ("first-page-only", "A1")
    ]
    assert pages[-1]["chunks"] == []
    assert len(calls) == len(captured) == 33


def test_row_major_hidden_sheet_order_and_sparse_requested_cell_accounting(monkeypatch):
    file_id = "synthetic-sheet-id"
    modified = "2026-09-21T00:00:00.000Z"
    second_sheet = _properties(sheet_id=20, index=1, title="Hidden", hidden=True, rows=1, columns=2)
    first_sheet = _properties(sheet_id=10, index=0, title="First", rows=2, columns=2)

    def cells(sheet, row, column, width, _call):
        prefix = "first" if sheet["title"] == "First" else "hidden"
        return [
            {"formattedValue": f"{prefix}-{row}-{column + offset}"}
            for offset in range(width)
        ]

    handler, calls = _mock_sheets_handler(
        file_id=file_id,
        sheets=(second_sheet, first_sheet),
        cell_factory=cells,
    )
    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _enable_public_runtime(monkeypatch, runtime)
        response = _public_sheet_call(runtime, file_id, modified)
    assert response["processing_status"] == "PROCESSED"
    assert [chunk["text"] for chunk in response["chunks"]] == [
        "first-0-0", "first-0-1", "first-1-0", "first-1-1", "hidden-0-0", "hidden-0-1"
    ]
    assert [chunk["provenance"]["sheet_ordinal"] for chunk in response["chunks"]] == [0, 0, 0, 0, 1, 1]
    ranges = [parse_qs(request.url.query.decode())["ranges"][0] for request in calls if "ranges" in parse_qs(request.url.query.decode())]
    assert ranges == ["'First'!A1:B1", "'First'!A2:B2", "'Hidden'!A1:B1"]
    assert len(captured) == 6


def test_content_in_hidden_row_and_column_is_not_filtered(monkeypatch):
    file_id = "synthetic-sheet-id"
    modified = "2026-09-21T00:00:00.000Z"
    sheet = _properties(rows=2, columns=2)

    def cells(_sheet, row, _column, _width, _call):
        if row == 1:
            return [{}, {"formattedValue": "hidden row and column value"}]
        return [{}, {}]

    handler, calls = _mock_sheets_handler(
        file_id=file_id,
        sheets=(sheet,),
        cell_factory=cells,
    )
    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _enable_public_runtime(monkeypatch, runtime)
        response = _public_sheet_call(runtime, file_id, modified)
    assert response["processing_status"] == "PROCESSED"
    assert [chunk["text"] for chunk in response["chunks"]] == ["hidden row and column value"]
    assert response["chunks"][0]["provenance"]["a1"] == "B2"
    assert len(calls) == len(captured) == 5


def test_component_continuation_resumes_exactly_at_rich_text_run(monkeypatch):
    file_id = "synthetic-sheet-id"
    modified = "2026-09-21T00:00:00.000Z"
    sheet = _properties(rows=1, columns=1)
    run_count = 65
    cell = {
        "userEnteredValue": {"stringValue": "x" * 100},
        "formattedValue": "display",
        "textFormatRuns": [
            {"startIndex": index, "format": {"link": {"uri": f"https://synthetic.invalid/{index}"}}}
            for index in range(1, run_count + 1)
        ],
    }
    handler, calls = _mock_sheets_handler(
        file_id=file_id,
        sheets=(sheet,),
        cell_factory=lambda *_: [cell],
    )
    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _enable_public_runtime(monkeypatch, runtime)
        first = _public_sheet_call(runtime, file_id, modified)
        second = _public_sheet_call(runtime, file_id, modified, first["continuation_token"])
    first_texts = [chunk["text"] for chunk in first["chunks"]]
    second_texts = [chunk["text"] for chunk in second["chunks"]]
    assert first["processing_status"] == "PARTIALLY_PROCESSED"
    assert len(first_texts) == 64
    assert second["processing_status"] == "PROCESSED"
    assert len(second_texts) == 2
    assert second["continuation_token"] is None
    assert second["chunk_count"] == len(second["chunks"])
    assert first_texts[0] == "display"
    assert second_texts == ["https://synthetic.invalid/64", "https://synthetic.invalid/65"]
    all_run_ordinals = [
        chunk["provenance"].get("rich_text_run_ordinal")
        for chunk in first["chunks"] + second["chunks"]
        if chunk["provenance"]["component"] == "CELL_RICH_TEXT_LINK"
    ]
    assert all_run_ordinals == list(range(run_count))
    assert len(calls) == len(captured) == 8
    call_count = len(calls)
    with pytest.raises(ContentSafeError):
        _public_sheet_call(runtime, file_id, modified, first["continuation_token"])
    assert len(calls) == call_count


def test_extracted_byte_budget_resumes_without_duplicate_or_omitted_cells(monkeypatch):
    file_id = "synthetic-sheet-id"
    modified = "2026-09-21T00:00:00.000Z"
    sheet = _properties(rows=1, columns=2)
    handler, calls = _mock_sheets_handler(
        file_id=file_id,
        sheets=(sheet,),
        cell_factory=lambda _sheet, _row, column, width, _call: [
            {"formattedValue": ("ab", "cd")[column + offset]}
            for offset in range(width)
        ],
    )
    monkeypatch.setattr(
        google_sheets_reader,
        "DEFAULT_CONTENT_READING_BUDGETS",
        replace(DEFAULT_CONTENT_READING_BUDGETS, max_extracted_content_bytes=3),
    )
    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _enable_public_runtime(monkeypatch, runtime)
        first = _public_sheet_call(runtime, file_id, modified)
        second = _public_sheet_call(runtime, file_id, modified, first["continuation_token"])
    assert first["processing_status"] == "PARTIALLY_PROCESSED"
    assert [chunk["text"] for chunk in first["chunks"]] == ["ab"]
    assert second["processing_status"] == "PROCESSED"
    assert [chunk["text"] for chunk in second["chunks"]] == ["cd"]
    assert len(calls) == len(captured) == 8


def test_component_budget_resumes_between_display_formula_and_note(monkeypatch):
    file_id = "synthetic-sheet-id"
    modified = "2026-09-21T00:00:00.000Z"
    sheet = _properties(rows=1, columns=1)
    cell = {
        "userEnteredValue": {"formulaValue": "=SUM(A1:A2)"},
        "formattedValue": "100",
        "note": "cell note",
        "hyperlink": "https://synthetic.invalid/cell",
    }
    handler, calls = _mock_sheets_handler(
        file_id=file_id,
        sheets=(sheet,),
        cell_factory=lambda *_: [cell],
    )
    monkeypatch.setattr(
        google_sheets_reader,
        "DEFAULT_CONTENT_READING_BUDGETS",
        replace(DEFAULT_CONTENT_READING_BUDGETS, max_chunks_per_invocation=1),
    )
    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _enable_public_runtime(monkeypatch, runtime)
        first = _public_sheet_call(runtime, file_id, modified)
        results = [first]
        while results[-1]["continuation_token"] is not None:
            results.append(
                _public_sheet_call(
                    runtime,
                    file_id,
                    modified,
                    results[-1]["continuation_token"],
                )
            )
    all_components = [
        (chunk["text"], chunk["provenance"]["component"])
        for result in results
        for chunk in result["chunks"]
    ]
    assert first["processing_status"] == "PARTIALLY_PROCESSED"
    assert [result["processing_status"] for result in results] == [
        "PARTIALLY_PROCESSED",
        "PARTIALLY_PROCESSED",
        "PARTIALLY_PROCESSED",
        "PROCESSED",
    ]
    assert all_components == [
        ("100", "CELL_DISPLAY"),
        ("=SUM(A1:A2)", "CELL_FORMULA"),
        ("cell note", "CELL_NOTE"),
        ("https://synthetic.invalid/cell", "CELL_HYPERLINK"),
    ]
    assert len(calls) == len(captured) == 16


def test_utf8_byte_budget_counts_encoded_bytes_across_continuation(monkeypatch):
    file_id = "synthetic-sheet-id"
    modified = "2026-09-21T00:00:00.000Z"
    sheet = _properties(rows=1, columns=2)
    handler, calls = _mock_sheets_handler(
        file_id=file_id,
        sheets=(sheet,),
        cell_factory=lambda _sheet, _row, column, width, _call: [
            {"formattedValue": value}
            for value in ("é", "x")[column : column + width]
        ],
    )
    monkeypatch.setattr(
        google_sheets_reader,
        "DEFAULT_CONTENT_READING_BUDGETS",
        replace(DEFAULT_CONTENT_READING_BUDGETS, max_extracted_content_bytes=2),
    )
    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _enable_public_runtime(monkeypatch, runtime)
        first = _public_sheet_call(runtime, file_id, modified)
        second = _public_sheet_call(runtime, file_id, modified, first["continuation_token"])
    assert first["processing_status"] == "PARTIALLY_PROCESSED"
    assert [chunk["text"] for chunk in first["chunks"]] == ["é"]
    assert second["processing_status"] == "PROCESSED"
    assert [chunk["text"] for chunk in second["chunks"]] == ["x"]
    assert len(calls) == len(captured) == 8


def test_single_component_over_256_kib_fails_safely_without_oversized_chunk(monkeypatch):
    file_id = "synthetic-sheet-id"
    modified = "2026-09-21T00:00:00.000Z"
    sheet = _properties(rows=1, columns=1)
    huge_value = "x" * (256 * 1024 + 1)
    handler, calls = _mock_sheets_handler(
        file_id=file_id,
        sheets=(sheet,),
        cell_factory=lambda *_: [{"formattedValue": huge_value}],
    )
    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _enable_public_runtime(monkeypatch, runtime)
        response = _public_sheet_call(runtime, file_id, modified)
    assert response["processing_status"] == "TOO_LARGE"
    assert response["chunks"] == []
    assert huge_value not in repr(response)
    assert len(calls) == len(captured) == 3


@pytest.mark.parametrize(
    ("columns", "expected_grid_calls", "expected_status"),
    [
        (0, 0, "EMPTY"),
        (1, 1, "EMPTY"),
        (999, 1, "EMPTY"),
        (1000, 1, "EMPTY"),
        (1001, 2, "EMPTY"),
        (7000, 7, "EMPTY"),
        (7999, 8, "EMPTY"),
        (8000, 8, "EMPTY"),
        (8001, 8, "PARTIALLY_PROCESSED"),
    ],
)
def test_window_boundaries_are_one_row_and_never_over_budget(
    monkeypatch,
    columns,
    expected_grid_calls,
    expected_status,
):
    file_id = "synthetic-sheet-id"
    modified = "2026-09-21T00:00:00.000Z"
    sheet = _properties(rows=1, columns=columns)
    handler, calls = _mock_sheets_handler(file_id=file_id, sheets=(sheet,))
    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _enable_public_runtime(monkeypatch, runtime)
        response = _public_sheet_call(runtime, file_id, modified)
    grid_requests = [request for request in calls if "ranges" in parse_qs(request.url.query.decode())]
    widths = [_window_from_request(request)[3] for request in grid_requests]
    assert response["processing_status"] == expected_status
    if expected_status == "EMPTY":
        assert response["chunk_count"] == 0
        assert response["chunks"] == []
        assert response["continuation_token"] is None
    else:
        assert response["continuation_token"] is not None
    assert len(grid_requests) == expected_grid_calls
    assert all(1 <= width <= MAX_SHEETS_REQUEST_WINDOW_CELLS for width in widths)
    assert sum(widths) <= MAX_SHEETS_GRIDDATA_CELLS_PER_INVOCATION
    assert len(calls) == len(captured) == expected_grid_calls + 3


def test_unsupported_sheet_types_are_explicit_gaps_without_grid_requests(monkeypatch):
    file_id = "synthetic-sheet-id"
    modified = "2026-09-21T00:00:00.000Z"
    grid = _properties(sheet_id=10, index=0, title="Grid", rows=1, columns=1)
    obj = _properties(sheet_id=20, index=1, title="Drawing", sheet_type="OBJECT")
    data_source = _properties(sheet_id=30, index=2, title="Source", sheet_type="DATA_SOURCE")

    def cells(_sheet, _row, _column, width, _call):
        return [{"formattedValue": "covered grid"}] if width else []

    handler, calls = _mock_sheets_handler(
        file_id=file_id,
        sheets=(grid, obj, data_source),
        cell_factory=cells,
    )
    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _enable_public_runtime(monkeypatch, runtime)
        response = _public_sheet_call(runtime, file_id, modified)
    assert response["processing_status"] == "PARTIALLY_PROCESSED"
    assert [chunk["text"] for chunk in response["chunks"]] == ["covered grid"]
    assert len([request for request in calls if "ranges" in parse_qs(request.url.query.decode())]) == 1
    assert len(captured) == len(calls) == 4


def test_structural_failure_after_a_window_releases_no_buffered_chunks(monkeypatch):
    file_id = "synthetic-sheet-id"
    modified = "2026-09-21T00:00:00.000Z"
    sheet = _properties(rows=2, columns=1)
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.host == "www.googleapis.com":
            return _json_response(_drive_payload(file_id))
        query = parse_qs(request.url.query.decode())
        if "ranges" not in query:
            return _json_response({"sheets": [{"properties": sheet}]})
        _title, row, column, _width = _window_from_request(request)
        if row == 0:
            return _json_response(_grid_response(sheet_id=10, index=0, row=row, column=column, cells=[{"formattedValue": "buffered secret"}]))
        return _json_response({"sheets": "malformed"})

    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _enable_public_runtime(monkeypatch, runtime)
        response = _public_sheet_call(runtime, file_id, modified)
    assert response["processing_status"] == "EXTRACTION_FAILED"
    assert response["chunks"] == []
    assert "buffered secret" not in repr(response)
    assert len(calls) == len(captured) == 4


def test_invalid_and_wrong_file_continuations_fail_before_network(monkeypatch):
    file_id = "synthetic-sheet-id"
    modified = "2026-09-21T00:00:00.000Z"
    sheet = _properties(rows=1, columns=10_000)
    handler, calls = _mock_sheets_handler(file_id=file_id, sheets=(sheet,))
    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _enable_public_runtime(monkeypatch, runtime)
        first = _public_sheet_call(runtime, file_id, modified)
        call_count = len(calls)
        for token, requested_id in (
            (first["continuation_token"] + "x", file_id),
            (first["continuation_token"], "other-synthetic-file"),
        ):
            with pytest.raises(ContentSafeError):
                _public_sheet_call(runtime, requested_id, modified, token)
            assert len(calls) == call_count
        resumed = _public_sheet_call(runtime, file_id, modified, first["continuation_token"])
        assert resumed["processing_status"] == "EMPTY"
        resumed_call_count = len(calls)
        with pytest.raises(ContentSafeError):
            _public_sheet_call(runtime, file_id, modified, first["continuation_token"])
        assert len(calls) == resumed_call_count
    assert call_count == 11
    assert len(captured) == len(calls) == 16


def test_postflight_change_discards_current_invocation_chunks_and_does_not_retry(monkeypatch):
    file_id = "synthetic-sheet-id"
    modified = "2026-09-21T00:00:00.000Z"
    later = "2026-09-21T00:01:00.000Z"
    sheet = _properties(rows=1, columns=1)
    handler, calls = _mock_sheets_handler(
        file_id=file_id,
        sheets=(sheet,),
        cell_factory=lambda *_: [{"formattedValue": "sensitive synthetic value"}],
        drive_responses=(_drive_payload(file_id, modified), _drive_payload(file_id, later)),
    )
    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _enable_public_runtime(monkeypatch, runtime)
        response = _public_sheet_call(runtime, file_id, modified)
    assert response["processing_status"] == "CHANGED_DURING_AUDIT"
    assert response["chunks"] == []
    assert response["continuation_token"] is None
    assert len(calls) == len(captured) == 4


def test_postflight_transport_failure_discards_chunks(monkeypatch):
    file_id = "synthetic-sheet-id"
    modified = "2026-09-21T00:00:00.000Z"
    sheet = _properties(rows=1, columns=1)
    handler, calls = _mock_sheets_handler(
        file_id=file_id,
        sheets=(sheet,),
        cell_factory=lambda *_: [{"formattedValue": "sensitive synthetic value"}],
        drive_responses=(_drive_payload(file_id, modified), 503),
    )
    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _enable_public_runtime(monkeypatch, runtime)
        response = _public_sheet_call(runtime, file_id, modified)
    assert response["processing_status"] == "TRANSIENT_UPSTREAM"
    assert response["chunks"] == []
    assert response["continuation_token"] is None
    assert not (
        response["continuation_token"] is None
        and response["processing_status"] in {"PROCESSED", "EMPTY"}
    )
    assert len(calls) == len(captured) == 4


def test_preflight_mismatch_blocks_sheets_requests(monkeypatch):
    file_id = "synthetic-sheet-id"
    modified = "2026-09-21T00:00:00.000Z"
    sheet = _properties(rows=1, columns=1)
    handler, calls = _mock_sheets_handler(
        file_id=file_id,
        sheets=(sheet,),
        drive_responses=(_drive_payload(file_id, "2026-09-21T00:01:00.000Z"),),
    )
    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _enable_public_runtime(monkeypatch, runtime)
        response = _public_sheet_call(runtime, file_id, modified)
    assert response["processing_status"] == "CHANGED_DURING_AUDIT"
    assert response["chunks"] == []
    assert len(calls) == len(captured) == 1
    assert calls[0].url.host == "www.googleapis.com"


@pytest.mark.parametrize(
    "preflight",
    [
        _drive_payload("synthetic-sheet-id", mime_type="text/plain"),
        _drive_payload("synthetic-sheet-id", trashed=True),
    ],
)
def test_preflight_mime_or_trashed_mismatch_blocks_sheets_reads(monkeypatch, preflight):
    file_id = "synthetic-sheet-id"
    modified = "2026-09-21T00:00:00.000Z"
    sheet = _properties(rows=1, columns=1)
    handler, calls = _mock_sheets_handler(
        file_id=file_id,
        sheets=(sheet,),
        drive_responses=(preflight,),
    )
    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _enable_public_runtime(monkeypatch, runtime)
        response = _public_sheet_call(runtime, file_id, modified)
    assert response["processing_status"] == "CHANGED_DURING_AUDIT"
    assert response["chunks"] == []
    assert len(calls) == len(captured) == 1


@pytest.mark.parametrize(
    "postflight",
    [
        _drive_payload("synthetic-sheet-id", mime_type="text/plain"),
        _drive_payload("synthetic-sheet-id", trashed=True),
    ],
)
def test_postflight_mime_or_trashed_mismatch_releases_no_chunks(monkeypatch, postflight):
    file_id = "synthetic-sheet-id"
    modified = "2026-09-21T00:00:00.000Z"
    sheet = _properties(rows=1, columns=1)
    handler, calls = _mock_sheets_handler(
        file_id=file_id,
        sheets=(sheet,),
        cell_factory=lambda *_: [{"formattedValue": "buffered sensitive value"}],
        drive_responses=(_drive_payload(file_id, modified), postflight),
    )
    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _enable_public_runtime(monkeypatch, runtime)
        response = _public_sheet_call(runtime, file_id, modified)
    assert response["processing_status"] == "CHANGED_DURING_AUDIT"
    assert response["chunks"] == []
    assert response["continuation_token"] is None
    assert "buffered sensitive value" not in repr(response)
    assert len(calls) == len(captured) == 4


def test_native_sheets_does_not_require_or_compare_drive_size(monkeypatch):
    file_id = "synthetic-sheet-id"
    modified = "2026-09-21T00:00:00.000Z"
    sheet = _properties(rows=1, columns=1)
    handler, calls = _mock_sheets_handler(
        file_id=file_id,
        sheets=(sheet,),
        cell_factory=lambda *_: [{"formattedValue": "safe"}],
        drive_responses=(
            _drive_payload(file_id, modified, size=123),
            _drive_payload(file_id, modified, size=456),
        ),
    )
    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _enable_public_runtime(monkeypatch, runtime)
        response = _public_sheet_call(runtime, file_id, modified)
    assert response["processing_status"] == "PROCESSED"
    assert response["chunks"][0]["text"] == "safe"
    drive_query = parse_qs(calls[0].url.query.decode())
    assert "size" not in drive_query["fields"][0]
    assert len(calls) == len(captured) == 4


def test_smart_chip_gap_persists_across_continuation(monkeypatch):
    file_id = "synthetic-sheet-id"
    modified = "2026-09-21T00:00:00.000Z"
    sheet = _properties(rows=1, columns=9000)

    def cells(_sheet, _row, column, _width, _call):
        if column == 0:
            return [{
                "userEnteredValue": {"stringValue": "x"},
                "formattedValue": "ordinary",
                "chipRuns": [{"startIndex": 0, "chip": {"personProperties": {"email": "person@synthetic.invalid"}}}],
            }]
        return []

    handler, calls = _mock_sheets_handler(file_id=file_id, sheets=(sheet,), cell_factory=cells)
    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _enable_public_runtime(monkeypatch, runtime)
        first = _public_sheet_call(runtime, file_id, modified)
        second = _public_sheet_call(runtime, file_id, modified, first["continuation_token"])
    assert first["processing_status"] == "PARTIALLY_PROCESSED"
    assert len(first["chunks"]) == 1
    assert second["processing_status"] == "PARTIALLY_PROCESSED"
    assert second["continuation_token"] is None
    serialized = repr((first, second))
    assert "person@synthetic.invalid" not in serialized
    assert len(calls) == len(captured) == 15


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("sheetId", 99),
        ("index", 1),
        ("title", "Renamed"),
        ("sheetType", "OBJECT"),
        ("rowCount", 2),
        ("columnCount", 9_001),
        ("hidden", True),
    ],
)
def test_metadata_fingerprint_mismatch_rejects_resume_before_griddata(monkeypatch, field, value):
    file_id = "synthetic-sheet-id"
    modified = "2026-09-21T00:00:00.000Z"
    first_sheet = _properties(rows=1, columns=9000)
    second_sheet = dict(first_sheet)
    if field in {"rowCount", "columnCount"}:
        dimensions = dict(first_sheet["gridProperties"])
        dimensions[field] = value
        second_sheet["gridProperties"] = dimensions
    elif field == "sheetType" and value == "OBJECT":
        second_sheet["sheetType"] = value
        second_sheet.pop("gridProperties")
    else:
        second_sheet[field] = value
    metadata_count = 0
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal metadata_count
        calls.append(request)
        if request.url.host == "www.googleapis.com":
            return _json_response(_drive_payload(file_id, modified))
        query = parse_qs(request.url.query.decode())
        if "ranges" not in query:
            metadata_count += 1
            sheet = first_sheet if metadata_count == 1 else second_sheet
            return _json_response({"sheets": [{"properties": sheet}]})
        title, row, column, _width = _window_from_request(request)
        sheet = first_sheet if title == "Main" else second_sheet
        return _json_response(
            _grid_response(
                sheet_id=sheet["sheetId"],
                index=sheet["index"],
                row=row,
                column=column,
                cells=[],
            )
        )

    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _enable_public_runtime(monkeypatch, runtime)
        first = _public_sheet_call(runtime, file_id, modified)
        second = _public_sheet_call(runtime, file_id, modified, first["continuation_token"])
    assert first["processing_status"] == "PARTIALLY_PROCESSED"
    assert second["processing_status"] == "CHANGED_DURING_AUDIT"
    assert second["chunks"] == []
    assert sum("ranges" in parse_qs(request.url.query.decode()) for request in calls) == 8
    assert len(calls) == len(captured) == 13


def test_absolute_coverage_cap_persists_and_narrows_last_request(monkeypatch):
    file_id = "synthetic-sheet-id"
    modified = "2026-09-21T00:00:00.000Z"
    sheet = _properties(rows=5_000_001, columns=1)
    handler, calls = _mock_sheets_handler(file_id=file_id, sheets=(sheet,))
    manager = DocsContinuationManager(key=b"sheets-reader-test-key-material-000000")
    original_manager = __import__("google_workspace_admin.content.bootstrap", fromlist=["DocsContinuationManager"]).DocsContinuationManager
    import google_workspace_admin.content.bootstrap as bootstrap_module
    monkeypatch.setattr(bootstrap_module, "DocsContinuationManager", lambda: manager)
    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _enable_public_runtime(monkeypatch, runtime)
        fingerprint = ((10, 0, "Main", "GRID", 5_000_001, 1, False),)
        state = SheetsContinuationState(
            snapshot=InventorySnapshot(file_id, SPREADSHEET_MIME, modified),
            reader_version=google_workspace_reader_version(),
            metadata_fingerprint=fingerprint,
            sheet_ordinal=0,
            sheet_id=10,
            row=4_999_999,
            column=0,
            component=None,
            rich_text_run_ordinal=None,
            rich_text_start_utf16=None,
            logical_cells_completed=4_999_999,
        )
        token = manager.issue_sheets(state)
        response = _public_sheet_call(runtime, file_id, modified, token)
        # A new caller token cannot reset the server-side logical progress.
        with pytest.raises(ContentSafeError):
            _public_sheet_call(runtime, file_id, modified, token)
    assert response["processing_status"] == "PARTIALLY_PROCESSED"
    assert response["continuation_token"] is None
    grid_requests = [request for request in calls if "ranges" in parse_qs(request.url.query.decode())]
    assert len(grid_requests) == 1
    assert _window_from_request(grid_requests[0])[1:] == (4_999_999, 0, 1)
    assert len(captured) == len(calls) == 4
    assert original_manager is DocsContinuationManager


def test_reader_issued_continuation_preserves_absolute_file_progress(monkeypatch):
    file_id = "synthetic-sheet-id"
    modified = "2026-09-21T00:00:00.000Z"
    sheet = _properties(rows=1, columns=5)
    handler, calls = _mock_sheets_handler(file_id=file_id, sheets=(sheet,))
    monkeypatch.setattr(
        google_sheets_reader,
        "DEFAULT_CONTENT_READING_BUDGETS",
        replace(DEFAULT_CONTENT_READING_BUDGETS, max_sheets_cells_per_file=3),
    )
    monkeypatch.setattr(google_sheets_reader, "MAX_SHEETS_GRIDDATA_CELLS_PER_INVOCATION", 2)
    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _enable_public_runtime(monkeypatch, runtime)
        first = _public_sheet_call(runtime, file_id, modified)
        second = _public_sheet_call(runtime, file_id, modified, first["continuation_token"])
        calls_after_second = len(calls)
        with pytest.raises(ContentSafeError):
            _public_sheet_call(runtime, file_id, modified, first["continuation_token"])
        assert len(calls) == calls_after_second
    first_windows = [
        _window_from_request(request)[3]
        for request in calls[:]
        if "ranges" in parse_qs(request.url.query.decode())
    ]
    assert first["processing_status"] == "PARTIALLY_PROCESSED"
    assert first["continuation_token"] is not None
    assert second["processing_status"] == "PARTIALLY_PROCESSED"
    assert second["partial_reason"] == "RESOURCE_LIMIT"
    assert second["continuation_token"] is None
    assert first_windows == [2, 1]
    assert len(calls) == len(captured) == 8


def google_workspace_reader_version() -> int:
    from google_workspace_admin.content.google_sheets_reader import GOOGLE_SHEETS_READER_VERSION

    return GOOGLE_SHEETS_READER_VERSION


def _valid_sheets_continuation_state(
    file_id: str = "synthetic-sheet-id",
    modified: str = "2026-09-21T00:00:00.000Z",
) -> SheetsContinuationState:
    return SheetsContinuationState(
        snapshot=InventorySnapshot(file_id, SPREADSHEET_MIME, modified),
        reader_version=google_workspace_reader_version(),
        metadata_fingerprint=((10, 0, "Main", "GRID", 1, 2, False),),
        sheet_ordinal=0,
        sheet_id=10,
        row=0,
        column=1,
        component=None,
        rich_text_run_ordinal=None,
        rich_text_start_utf16=None,
        logical_cells_completed=1,
    )


def test_sheets_continuation_is_atomically_one_use_and_operation_bound():
    manager = DocsContinuationManager(key=b"sheets-reader-test-key-material-000000")
    state = _valid_sheets_continuation_state()
    token = manager.issue_sheets(state)
    start = Barrier(3)

    def resolve_once():
        start.wait()
        try:
            return manager.resolve_sheets(
                token,
                snapshot=state.snapshot,
                reader_version=state.reader_version,
            )
        except ContentSafeError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        calls = [pool.submit(resolve_once) for _ in range(2)]
        start.wait()
        resolved = [call.result() for call in calls]
    assert sum(value is state for value in resolved) == 1
    with pytest.raises(ContentSafeError):
        manager.resolve_sheets(
            token,
            snapshot=state.snapshot,
            reader_version=state.reader_version,
        )


def test_non_ascii_sheets_continuation_handles_fail_closed_before_hmac_encoding():
    manager = DocsContinuationManager(key=b"sheets-reader-test-key-material-000000")
    state = _valid_sheets_continuation_state()
    token = manager.issue_sheets(state)
    _, _, expiry_text, supplied_mac = token.split(".")

    for malformed_handle in ("é", "漢", "😀"):
        malformed_token = f"v1.{malformed_handle}.{expiry_text}.{supplied_mac}"
        with pytest.raises(ContentSafeError) as caught:
            manager.resolve_sheets(
                malformed_token,
                snapshot=state.snapshot,
                reader_version=state.reader_version,
            )
        assert caught.value.code == "LOCAL_VALIDATION"
        assert caught.value.operation == ContentErrorOperation.READING_CONTINUATION.value


def test_expired_and_wrong_operation_sheets_tokens_fail_before_network(monkeypatch):
    file_id = "synthetic-sheet-id"
    modified = "2026-09-21T00:00:00.000Z"
    now = [1_000.0]
    manager = DocsContinuationManager(
        clock=lambda: now[0],
        key=b"sheets-reader-test-key-material-000000",
    )
    import google_workspace_admin.content.bootstrap as bootstrap_module

    monkeypatch.setattr(bootstrap_module, "DocsContinuationManager", lambda: manager)
    sheet = _properties(rows=1, columns=9_000)
    handler, calls = _mock_sheets_handler(file_id=file_id, sheets=(sheet,))
    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _enable_public_runtime(monkeypatch, runtime)
        first = _public_sheet_call(runtime, file_id, modified)
        token = first["continuation_token"]
        call_count = len(calls)
        with pytest.raises(ContentSafeError):
            server.workspace_file_content_read(
                file_id,
                "application/vnd.google-apps.document",
                modified,
                continuation_token=token,
            )
        assert len(calls) == call_count
        now[0] += 901
        with pytest.raises(ContentSafeError):
            _public_sheet_call(runtime, file_id, modified, token)
        assert len(calls) == call_count
    assert len(captured) == call_count == 11


def test_continuation_token_excludes_sheet_cursor_and_sensitive_component_values(monkeypatch):
    file_id = "private-spreadsheet-id-sentinel"
    modified = "2026-09-21T00:00:00.000Z"
    title = "Private sheet title sentinel"
    sheet = _properties(sheet_id=987654321, title=title, rows=1, columns=9_000)
    private_values = (
        "private-display-sentinel",
        '=HYPERLINK("https://private-formula.invalid/secret", "x")',
        "private-note-sentinel",
        "https://private-cell-link.invalid/secret",
        "https://private-rich-link.invalid/secret",
        "person-private@synthetic.invalid",
        "https://private-chip-link.invalid/secret",
    )
    formula_cell = {
        "userEnteredValue": {"formulaValue": private_values[1]},
        "formattedValue": private_values[0],
        "note": private_values[2],
        "hyperlink": private_values[3],
    }
    rich_cell = {
        "userEnteredValue": {"stringValue": "x" * 100},
        "formattedValue": "private-second-cell-display",
        "textFormatRuns": [
            {
                "startIndex": index,
                "format": {"link": {"uri": private_values[4] + f"/{index}"}},
            }
            for index in range(62)
        ],
        "chipRuns": [
            {"startIndex": 0, "chip": {"personProperties": {"email": private_values[5]}}},
            {"startIndex": 1, "chip": {"richLinkProperties": {"uri": private_values[6]}}},
        ],
    }
    # Rich-text offsets must be inside the source string; chip payloads are
    # inspected only for their closed type and never retained in the cursor.
    handler, calls = _mock_sheets_handler(
        file_id=file_id,
        sheets=(sheet,),
        cell_factory=lambda _sheet, _row, column, _width, _call: (
            [formula_cell, rich_cell] if column == 0 else []
        ),
    )
    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _enable_public_runtime(monkeypatch, runtime)
        first = _public_sheet_call(runtime, file_id, modified)
    token = first["continuation_token"]
    assert first["processing_status"] == "PARTIALLY_PROCESSED"
    assert isinstance(token, str) and len(token) <= 4096
    assert re.fullmatch(r"v1\.[A-Za-z0-9_-]{32}\.\d{1,12}\.[A-Za-z0-9_-]{43}", token)
    assert len(calls) == len(captured) == 4
    for value in (file_id, str(sheet["sheetId"]), title, *private_values, "private-second-cell-display"):
        assert value not in token


def test_cross_cell_components_remain_independent_through_public_reader(monkeypatch):
    file_id = "synthetic-sheet-id"
    modified = "2026-09-21T00:00:00.000Z"
    sheet = _properties(rows=1, columns=2)
    handler, _calls = _mock_sheets_handler(
        file_id=file_id,
        sheets=(sheet,),
        cell_factory=lambda _sheet, _row, column, width, _call: [
            {"formattedValue": value}
            for value in ("secret", "token")[column : column + width]
        ],
    )
    with content_runtime_harness(monkeypatch, handler) as (runtime, _captured):
        _enable_public_runtime(monkeypatch, runtime)
        response = _public_sheet_call(runtime, file_id, modified)
    assert response["processing_status"] == "PROCESSED"
    assert [chunk["text"] for chunk in response["chunks"]] == ["secret", "token"]
    assert "secrettoken" not in repr(response)


def test_non_sheets_native_mime_keeps_existing_unsupported_route(monkeypatch):
    monkeypatch.setattr(
        server,
        "_get_content_runtime",
        lambda: pytest.fail("unsupported MIME must not create the content runtime"),
    )
    response = server.workspace_file_content_read(
        "synthetic-pdf-id",
        "application/pdf",
        "2026-09-21T00:00:00.000Z",
    )
    assert response["processing_status"] == "NATIVE_TYPE_UNSUPPORTED"
    assert response["content_class"] == "PDF"
    assert response["chunks"] == []


def test_sheets_continuation_bounds_and_shared_lifecycle_remain_closed():
    assert DocsContinuationManager()._ttl_seconds == 900
    assert DocsContinuationManager()._max_states == 1000
    with pytest.raises(ContentSafeError):
        SheetsContinuationState(
            snapshot=InventorySnapshot("synthetic-sheet-id", SPREADSHEET_MIME, "2026-09-21T00:00:00.000Z"),
            reader_version=google_workspace_reader_version(),
            metadata_fingerprint=((10, 0, "Main", "GRID", 5_000_001, 1, False),),
            sheet_ordinal=0,
            sheet_id=10,
            row=0,
            column=0,
            component=None,
            rich_text_run_ordinal=None,
            rich_text_start_utf16=None,
            logical_cells_completed=5_000_001,
        )


def test_sheets_field_masks_are_closed_and_contain_only_selected_families():
    assert SHEETS_WORKBOOK_METADATA_FIELDS == (
        "sheets(properties(sheetId,index,title,hidden,sheetType,gridProperties(rowCount,columnCount)))"
    )
    assert SHEETS_GRIDDATA_FIELDS == (
        "sheets(properties(sheetId,index,sheetType),data(startRow,startColumn,"
        "rowData(values(userEnteredValue,effectiveValue(errorValue(type)),formattedValue,"
        "note,hyperlink,textFormatRuns(startIndex,format(link(uri))),"
        "chipRuns(startIndex,chip(personProperties(email),richLinkProperties(uri)))))))"
    )
    for mask in (SHEETS_WORKBOOK_METADATA_FIELDS, SHEETS_GRIDDATA_FIELDS):
        assert "owners" not in mask
        assert "permissions" not in mask
        assert "developerMetadata" not in mask


def test_cell_components_have_fixed_order_independent_units_and_component_provenance():
    window = _window(title="Private sheet title")
    result = _extract_cells(
        window,
        [
            {
                "userEnteredValue": {"formulaValue": '=IMPORTXML("https://example.invalid", "//x")'},
                "formattedValue": "100",
                "note": "100",
                "hyperlink": "https://example.invalid/cell",
            },
            {
                "userEnteredValue": {"stringValue": "A😀B"},
                "formattedValue": "A😀B",
                "textFormatRuns": [
                    {"startIndex": 0, "format": {"link": {"uri": "https://example.invalid/first"}}},
                    {"startIndex": 1, "format": {}},
                    {"startIndex": 3, "format": {"link": {"uri": "https://example.invalid/second"}}},
                ],
            },
        ],
    )

    units = result.units
    assert [unit.provenance.component for unit in units] == [
        SheetsContentComponent.CELL_DISPLAY,
        SheetsContentComponent.CELL_FORMULA,
        SheetsContentComponent.CELL_NOTE,
        SheetsContentComponent.CELL_HYPERLINK,
        SheetsContentComponent.CELL_DISPLAY,
        SheetsContentComponent.CELL_RICH_TEXT_LINK,
        SheetsContentComponent.CELL_RICH_TEXT_LINK,
    ]
    assert [unit.payload.text for unit in units] == [
        "100",
        '=IMPORTXML("https://example.invalid", "//x")',
        "100",
        "https://example.invalid/cell",
        "A😀B",
        "https://example.invalid/first",
        "https://example.invalid/second",
    ]
    assert units[0].payload.text == units[2].payload.text
    assert units[0].provenance.row == units[0].provenance.column == 0
    assert units[0].provenance.range_a1 == "A1"
    assert units[0].provenance.sheet_index == 0
    assert units[0].provenance.sheet_title == "Private sheet title"
    assert units[0].provenance.sheet_id == "10"
    assert units[5].provenance.rich_text_run_ordinal == 0
    assert units[5].provenance.rich_text_start_utf16 == 0
    assert units[5].provenance.rich_text_end_utf16 == 1
    assert units[6].provenance.rich_text_run_ordinal == 2
    assert units[6].provenance.rich_text_start_utf16 == 3
    assert units[6].provenance.rich_text_end_utf16 == 4
    assert result.coverage_gaps == ()


@pytest.mark.parametrize(
    "display",
    [
        "  abc  ",
        "00123",
        "10,50%",
        "R$ 1.234,56",
        "01/09/2026",
        "true",
        "line 1\nline 2",
        "\tvalue\t",
        "   \t\n",
        "雪😀",
    ],
)
def test_display_values_preserve_sheets_formatting_and_whitespace(display: str):
    result = _extract_cells(_window(), [{"formattedValue": display}])
    assert len(result.units) == 1
    assert result.units[0].payload.text == display
    assert result.units[0].provenance.component is SheetsContentComponent.CELL_DISPLAY


def test_empty_components_are_omitted_and_rich_links_do_not_require_cell_hyperlink():
    result = _extract_cells(
        _window(column_count=3),
        [
            {
                "userEnteredValue": {"stringValue": "x"},
                "formattedValue": "",
                "note": "",
                "hyperlink": "",
                "textFormatRuns": [
                    {"startIndex": 0, "format": {"link": {"uri": ""}}},
                ],
            },
            {"userEnteredValue": {"formulaValue": ""}},
            {
                "userEnteredValue": {"stringValue": "ab"},
                "formattedValue": "ab",
                "textFormatRuns": [
                    {"startIndex": 0, "format": {"link": {"uri": "https://example.invalid/a"}}},
                    {"startIndex": 1, "format": {"link": {"uri": "https://example.invalid/b"}}},
                ],
            },
        ],
    )
    assert [unit.payload.text for unit in result.units] == [
        "ab",
        "https://example.invalid/a",
        "https://example.invalid/b",
    ]
    assert [unit.provenance.component for unit in result.units] == [
        SheetsContentComponent.CELL_DISPLAY,
        SheetsContentComponent.CELL_RICH_TEXT_LINK,
        SheetsContentComponent.CELL_RICH_TEXT_LINK,
    ]


def test_identical_cell_and_rich_text_link_targets_remain_distinct_components():
    uri = "https://example.invalid/shared"
    result = _extract_cells(
        _window(),
        [
            {
                "userEnteredValue": {"stringValue": "linked"},
                "formattedValue": "shared display",
                "hyperlink": uri,
                "textFormatRuns": [
                    {"startIndex": 0, "format": {"link": {"uri": uri}}},
                ],
            }
        ],
    )
    assert [unit.payload.text for unit in result.units] == ["shared display", uri, uri]
    assert [unit.provenance.component for unit in result.units] == [
        SheetsContentComponent.CELL_DISPLAY,
        SheetsContentComponent.CELL_HYPERLINK,
        SheetsContentComponent.CELL_RICH_TEXT_LINK,
    ]


def test_sparse_cells_use_griddata_origin_without_shifting_or_synthesizing():
    window = _window(row_start=4, column_start=25, column_count=4)
    result = _extract_cells(window, [{}, {"formattedValue": "kept"}, {}])
    assert len(result.units) == 1
    assert result.units[0].payload.text == "kept"
    assert result.units[0].provenance.row == 4
    assert result.units[0].provenance.column == 26
    assert result.units[0].provenance.range_a1 == "AA5"
    assert cell_to_a1(4, 25) == "Z5"


def test_hidden_sheet_content_is_not_filtered_by_extraction():
    sheet = _metadata_sheet(hidden=True, title="Hidden")
    window = SheetsGridWindow(sheet, 2, 1, 3, 2)
    result = _extract_cells(window, [{"formattedValue": "still audited"}])
    assert sheet.hidden is True
    assert [unit.payload.text for unit in result.units] == ["still audited"]
    assert result.units[0].provenance.range_a1 == "D3"


def test_note_whitespace_and_multiline_content_are_preserved_as_a_separate_unit():
    note = "\t note line 1  \nline 2\r\n"
    result = _extract_cells(
        _window(),
        [{"formattedValue": "display", "note": note}],
    )
    assert [unit.payload.text for unit in result.units] == ["display", note]
    assert result.units[1].provenance.component is SheetsContentComponent.CELL_NOTE


def test_merged_spill_and_pivot_data_are_never_expanded_or_attributed_to_anchor():
    result = _extract_cells(
        _window(column_count=4),
        [
            {"formattedValue": "merged anchor", "userEnteredValue": {"formulaValue": "=SUM(A1:A2)"}},
            {},
            {"formattedValue": "spill result", "userEnteredValue": {"stringValue": "spill result"}},
            {"formattedValue": "pivot result"},
        ],
    )
    assert [(unit.payload.text, unit.provenance.range_a1) for unit in result.units] == [
        ("merged anchor", "A1"),
        ("=SUM(A1:A2)", "A1"),
        ("spill result", "C1"),
        ("pivot result", "D1"),
    ]
    assert sum(
        unit.provenance.component is SheetsContentComponent.CELL_FORMULA
        for unit in result.units
    ) == 1


def test_known_calculation_error_is_a_displayed_cell_not_a_malformed_workbook():
    result = _extract_cells(
        _window(),
        [
            {
                "userEnteredValue": {"formulaValue": "=NA()"},
                "effectiveValue": {"errorValue": {"type": "N_A"}},
                "formattedValue": "#N/A",
            }
        ],
    )
    assert [unit.payload.text for unit in result.units] == ["#N/A", "=NA()"]
    assert [unit.provenance.component for unit in result.units] == [
        SheetsContentComponent.CELL_DISPLAY,
        SheetsContentComponent.CELL_FORMULA,
    ]


def test_cross_cell_text_is_never_concatenated():
    result = _extract_cells(
        _window(),
        [{"formattedValue": "secret"}, {"formattedValue": "token"}],
    )
    assert [unit.payload.text for unit in result.units] == ["secret", "token"]
    assert [unit.provenance.range_a1 for unit in result.units] == ["A1", "B1"]
    assert all(unit.payload.text != "secrettoken" for unit in result.units)


def test_utf16_helpers_and_runs_handle_supplementary_plane_offsets():
    assert len("A😀B") == 3
    assert utf16_code_unit_length("A😀B") == 4
    result = _extract_cells(
        _window(),
        [
            {
                "userEnteredValue": {"stringValue": "A😀B"},
                "textFormatRuns": [
                    {"startIndex": 0},
                    {"startIndex": 3, "format": {"link": {"uri": "https://example.invalid/after-emoji"}}},
                ],
            }
        ],
    )
    link = result.units[0]
    assert link.payload.text == "https://example.invalid/after-emoji"
    assert link.provenance.rich_text_start_utf16 == 3
    assert link.provenance.rich_text_end_utf16 == 4


def test_real_e1_shape_omits_first_start_index_and_extracts_two_distinct_links():
    left = "https://example.com/gsheets-validation-v1/left"
    right = "https://example.com/gsheets-validation-v1/right"
    result = _extract_cells(
        _window(),
        [
            {
                "userEnteredValue": {"stringValue": "LEFT RIGHT"},
                "formattedValue": "LEFT RIGHT",
                "textFormatRuns": [
                    {"format": {"link": {"uri": left}}},
                    {"startIndex": 4, "format": {}},
                    {"startIndex": 5, "format": {"link": {"uri": right}}},
                ],
            }
        ],
    )

    assert [unit.payload.text for unit in result.units] == ["LEFT RIGHT", left, right]
    assert [unit.provenance.component for unit in result.units] == [
        SheetsContentComponent.CELL_DISPLAY,
        SheetsContentComponent.CELL_RICH_TEXT_LINK,
        SheetsContentComponent.CELL_RICH_TEXT_LINK,
    ]
    assert [
        (unit.provenance.rich_text_start_utf16, unit.provenance.rich_text_end_utf16)
        for unit in result.units[1:]
    ] == [(0, 4), (5, 10)]
    assert " " not in [unit.payload.text for unit in result.units[1:]]


def test_text_format_run_first_start_index_omission_defaults_to_zero():
    window = _window()
    payload = _grid_envelope(
        window,
        values=[
            {
                "userEnteredValue": {"stringValue": "ab"},
                "textFormatRuns": [{"format": {}}],
            }
        ],
    )

    parsed = parse_griddata_envelope(payload, window=window)

    assert parsed.cells[0].text_format_runs[0].start_index == 0


def test_text_format_run_explicit_first_zero_matches_omitted_default():
    window = _window()
    omitted = parse_griddata_envelope(
        _grid_envelope(
            window,
            values=[
                {
                    "userEnteredValue": {"stringValue": "ab"},
                    "textFormatRuns": [{"format": {}}],
                }
            ],
        ),
        window=window,
    )
    explicit = parse_griddata_envelope(
        _grid_envelope(
            window,
            values=[
                {
                    "userEnteredValue": {"stringValue": "ab"},
                    "textFormatRuns": [{"startIndex": 0, "format": {}}],
                }
            ],
        ),
        window=window,
    )

    assert omitted.cells[0].text_format_runs == explicit.cells[0].text_format_runs


@pytest.mark.parametrize(
    "runs",
    [
        [{"startIndex": 0, "format": {}}, {"format": {}}],
        [{"format": {}}, {"format": {}}],
    ],
)
def test_text_format_run_later_start_index_omission_fails_closed(runs):
    window = _window()
    with pytest.raises(ContentSafeError) as caught:
        parse_griddata_envelope(
            _grid_envelope(
                window,
                values=[
                    {
                        "userEnteredValue": {"stringValue": "ab"},
                        "textFormatRuns": runs,
                    }
                ],
            ),
            window=window,
        )
    assert caught.value.code == "RESPONSE_VALIDATION"


@pytest.mark.parametrize("invalid", [None, True, False, "0", 0.0, -1])
def test_text_format_run_present_invalid_start_index_types_remain_rejected(invalid):
    window = _window()
    with pytest.raises(ContentSafeError) as caught:
        parse_griddata_envelope(
            _grid_envelope(
                window,
                values=[
                    {
                        "userEnteredValue": {"stringValue": "ab"},
                        "textFormatRuns": [{"startIndex": invalid, "format": {}}],
                    }
                ],
            ),
            window=window,
        )
    assert caught.value.code == "RESPONSE_VALIDATION"


def test_text_format_run_explicit_nonzero_first_index_preserves_existing_behavior():
    window = _window()
    result = _extract_cells(
        window,
        [
            {
                "userEnteredValue": {"stringValue": "ab"},
                "textFormatRuns": [
                    {"startIndex": 1, "format": {"link": {"uri": "https://example.invalid/b"}}}
                ],
            }
        ],
    )

    assert result.units[0].payload.text == "https://example.invalid/b"
    assert result.units[0].provenance.rich_text_start_utf16 == 1
    assert result.units[0].provenance.rich_text_end_utf16 == 2


def test_text_format_run_omitted_first_index_preserves_utf16_offsets():
    window = _window()
    result = _extract_cells(
        window,
        [
            {
                "userEnteredValue": {"stringValue": "A😀B𐐷C"},
                "textFormatRuns": [
                    {},
                    {"startIndex": 6, "format": {"link": {"uri": "https://example.invalid/c"}}},
                ],
            }
        ],
    )

    assert result.units[0].payload.text == "https://example.invalid/c"
    assert result.units[0].provenance.rich_text_start_utf16 == 6
    assert result.units[0].provenance.rich_text_end_utf16 == 7


@pytest.mark.parametrize(
    "cell",
    [
        {"formattedValue": []},
        {"formattedValue": "bad\ud800"},
        {"userEnteredValue": {"numberValue": True}},
        {"userEnteredValue": {"boolValue": 1}},
        {"userEnteredValue": {"stringValue": "a", "formulaValue": "=1"}},
        {"userEnteredValue": {"unknownValue": "do not stringify"}},
        {"effectiveValue": {"errorValue": {"type": []}}},
        {"textFormatRuns": {}},
        {"textFormatRuns": [{"startIndex": True}]},
        {"textFormatRuns": [{"startIndex": -1}]},
        {"userEnteredValue": {"stringValue": "A😀B"}, "textFormatRuns": [{"startIndex": 2}]},
        {"userEnteredValue": {"stringValue": "ab"}, "textFormatRuns": [{"startIndex": 1}, {"startIndex": 0}]},
        {"userEnteredValue": {"stringValue": "ab"}, "textFormatRuns": [{"startIndex": 0}, {"startIndex": 0}]},
        {"userEnteredValue": {"stringValue": "a"}, "textFormatRuns": [{"startIndex": 1}]},
        {"userEnteredValue": {"stringValue": "a"}, "textFormatRuns": [{"startIndex": 0, "format": {"link": {"uri": []}}}]},
        {"userEnteredValue": {"stringValue": "a"}, "textFormatRuns": [{"startIndex": 0, "format": {"link": {}}}]},
        {"note": "bad\x00control"},
    ],
)
def test_malformed_cell_unions_and_rich_text_fail_closed(cell: dict[str, object]):
    with pytest.raises(ContentSafeError) as caught:
        parse_griddata_envelope(_grid_envelope(_window(), values=[cell]), window=_window())
    assert caught.value.code == "RESPONSE_VALIDATION"
    assert caught.value.operation == ContentErrorOperation.RESPONSE_SHEETS_GRIDDATA.value
    assert "do not stringify" not in str(caught.value)
    assert "bad" not in str(caught.value)


def test_smart_chip_runs_detect_coverage_gap_without_retaining_sensitive_values():
    window = _window()
    payload = _grid_envelope(
        window,
        values=[
            {
                "userEnteredValue": {"stringValue": "plain"},
                "chipRuns": [{"startIndex": 0}],
            },
            {
                "userEnteredValue": {"stringValue": "@person"},
                "formattedValue": "Person",
                "chipRuns": [
                    {
                        "startIndex": 0,
                        "chip": {"personProperties": {"email": "synthetic.person@example.invalid"}},
                    }
                ],
            },
        ],
    )
    parsed = parse_griddata_envelope(payload, window=window)
    assert parsed.coverage_gaps == (SheetsCoverageGap.SMART_CHIP,)
    assert [cell.has_unsupported_smart_chip for cell in parsed.cells] == [False, True]
    assert "synthetic.person@example.invalid" not in repr(parsed)
    extracted = extract_griddata_content(parsed, window=window, file_ref=TEST_PUBLIC_FILE_REF)
    assert extracted.coverage_gaps == (SheetsCoverageGap.SMART_CHIP,)
    assert [unit.payload.text for unit in extracted.units] == ["Person"]
    assert "synthetic.person@example.invalid" not in repr(extracted)
    assert not hasattr(parsed.cells[1], "user_entered_string")


def test_plain_chip_runs_do_not_create_smart_chip_coverage_gap():
    window = _window()
    parsed = parse_griddata_envelope(
        _grid_envelope(
            window,
            values=[
                {
                    "userEnteredValue": {"stringValue": "plain text"},
                    "chipRuns": [{"startIndex": 0}],
                }
            ],
        ),
        window=window,
    )
    assert parsed.coverage_gaps == ()
    assert parsed.cells[0].has_unsupported_smart_chip is False


def test_smart_chip_first_run_uses_documented_default_zero_index():
    window = _window()
    parsed = parse_griddata_envelope(
        _grid_envelope(
            window,
            values=[
                {
                    "userEnteredValue": {"stringValue": "@person"},
                    "chipRuns": [
                        {"chip": {"personProperties": {"email": "synthetic@example.invalid"}}},
                    ],
                }
            ],
        ),
        window=window,
    )
    assert parsed.coverage_gaps == (SheetsCoverageGap.SMART_CHIP,)
    assert "synthetic@example.invalid" not in repr(parsed)


def test_smart_chip_rich_link_is_detected_but_uri_is_not_retained():
    window = _window()
    payload = _grid_envelope(
        window,
        values=[
            {
                "userEnteredValue": {"stringValue": "@file"},
                "chipRuns": [
                    {
                        "startIndex": 0,
                        "chip": {"richLinkProperties": {"uri": "https://private.example.invalid/file"}},
                    }
                ],
            }
        ],
    )
    parsed = parse_griddata_envelope(payload, window=window)
    assert parsed.coverage_gaps == (SheetsCoverageGap.SMART_CHIP,)
    assert "private.example.invalid" not in repr(parsed)
    assert extract_griddata_content(
        parsed,
        window=window,
        file_ref=TEST_PUBLIC_FILE_REF,
    ).units == ()


@pytest.mark.parametrize(
    "chip_runs",
    [
        [{"startIndex": True, "chip": {"personProperties": {"email": "person@example.invalid"}}}],
        [{"startIndex": 3, "chip": {"personProperties": {"email": "person@example.invalid"}}}],
        [
            {
                "startIndex": 0,
                "chip": {
                    "personProperties": {"email": "person@example.invalid"},
                    "richLinkProperties": {"uri": "https://example.invalid"},
                },
            }
        ],
        [{"startIndex": 0, "chip": {"personProperties": {"email": []}}}],
        [{"startIndex": 0, "chip": {"richLinkProperties": {"uri": "https://bad\ud800"}}}],
    ],
)
def test_malformed_smart_chip_runs_fail_closed_without_sensitive_error_text(chip_runs):
    window = _window()
    with pytest.raises(ContentSafeError) as caught:
        parse_griddata_envelope(
            _grid_envelope(
                window,
                values=[
                    {
                        "userEnteredValue": {"stringValue": "abc"},
                        "chipRuns": chip_runs,
                    }
                ],
            ),
            window=window,
        )
    assert caught.value.code == "RESPONSE_VALIDATION"
    assert caught.value.operation == ContentErrorOperation.RESPONSE_SHEETS_GRIDDATA.value
    assert "person@example.invalid" not in str(caught.value)
    assert "example.invalid" not in str(caught.value)


def test_internal_sheet_provenance_is_not_accepted_by_docs_public_serializer():
    from google_workspace_admin.content.provenance import SheetsProvenance

    result = _extract_cells(_window(title="private title"), [{"formattedValue": "private cell"}])
    provenance = result.units[0].provenance
    assert type(provenance) is SheetsProvenance
    assert provenance.sheet_title == "private title"
    assert provenance.sheet_id == "10"
    assert "private title" not in repr(provenance)
    assert "10" not in repr(provenance)
    with pytest.raises(ContentSafeError) as caught:
        server._serialize_docs_provenance(provenance)
    assert "private title" not in str(caught.value)
    assert "private cell" not in str(caught.value)
    assert "10" not in str(caught.value)


def _rich_a1_range(column_start: int, *, row: int = 0, column_count: int = 1, title: str = "Synthetic grid"):
    return _SheetsA1Range(title, row, column_start, column_count)


def _rich_payload(
    ranges: tuple[_SheetsA1Range, ...],
    *,
    spreadsheet_id: str = "synthetic_file_id",
    data_order: tuple[int, ...] | None = None,
    cells_by_range: tuple[list[dict[str, object]], ...] | None = None,
) -> dict[str, object]:
    ranges = tuple(ranges)
    order = tuple(range(len(ranges))) if data_order is None else data_order
    cells = cells_by_range or tuple([{"formattedValue": f"slot-{i}"}] for i in range(len(ranges)))
    blocks: list[dict[str, object]] = []
    for index in order:
        a1_range = ranges[index]
        block: dict[str, object] = {}
        if a1_range.row != 0:
            block["startRow"] = a1_range.row
        if a1_range.column_start != 0:
            block["startColumn"] = a1_range.column_start
        block["rowData"] = [{"values": cells[index]}]
        blocks.append(block)
    return {
        "spreadsheetId": spreadsheet_id,
        "properties": {"locale": "synthetic_LOCALE", "timeZone": "Synthetic/Zone"},
        "sheets": [
            {
                "properties": _properties(
                    sheet_id=77,
                    index=0,
                    title="Synthetic grid",
                    rows=20,
                    columns=40,
                ),
                "data": blocks,
            }
        ],
    }


def _rich_port_authority():
    context = object()
    authority = _OperationAuthority(
        profile_handle=None,  # type: ignore[arg-type]
        subject_handle=None,  # type: ignore[arg-type]
        operation=ContentOperation.SHEETS_GRIDDATA_WINDOW,
        approved_scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
        admin_mode_authorized=False,
    )

    def require_context(candidate: object) -> object:
        if candidate is not context:
            raise ContentSafeError(
                code="READ_ONLY_OPERATION_FORBIDDEN",
                operation=ContentErrorOperation.AUTH_CONTEXT_PROVENANCE,
            )
        return authority

    def token_provider(candidate: object, profile: ApprovedScopeProfile) -> str:
        assert candidate is context
        assert profile is ApprovedScopeProfile.DRIVE_DISCOVERY
        return "synthetic-private-token"

    return context, require_context, token_provider


def _drive_metadata_port_authority():
    context = object()
    authority = _OperationAuthority(
        profile_handle=None,  # type: ignore[arg-type]
        subject_handle=None,  # type: ignore[arg-type]
        operation=ContentOperation.SHEETS_WORKBOOK_METADATA,
        approved_scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
        admin_mode_authorized=False,
    )

    def require_context(candidate: object) -> object:
        if candidate is not context:
            raise ContentSafeError(
                code="READ_ONLY_OPERATION_FORBIDDEN",
                operation=ContentErrorOperation.AUTH_CONTEXT_PROVENANCE,
            )
        return authority

    def token_provider(candidate: object, profile: ApprovedScopeProfile) -> str:
        assert candidate is context
        assert profile is ApprovedScopeProfile.DRIVE_DISCOVERY
        return "synthetic-private-token"

    return context, require_context, token_provider


def test_private_rich_request_has_closed_get_fields_and_three_repeated_ranges():
    ranges = (
        _rich_a1_range(4),
        _rich_a1_range(0),
        _rich_a1_range(2),
    )
    request = _build_rich_cell_data_request("synthetic_file_id", ranges)
    assert type(request) is _RichCellDataRequest
    assert tuple(name for name in request.__dataclass_fields__) == ("spreadsheet_id", "ranges")
    assert _request_params(request) == (
        ("ranges", "'Synthetic grid'!E1:E1"),
        ("ranges", "'Synthetic grid'!A1:A1"),
        ("ranges", "'Synthetic grid'!C1:C1"),
        ("fields", _RICH_GRIDDATA_FIELDS),
        ("includeGridData", True),
    )
    for selector in (
        "spreadsheetId",
        "properties(locale,timeZone)",
        "sheetId,title,index,hidden,sheetType",
        "gridProperties(rowCount,columnCount)",
        "data(startRow,startColumn",
        "userEnteredValue",
        "effectiveValue",
        "formattedValue",
        "numberFormat(type,pattern)",
    ):
        assert selector in _RICH_GRIDDATA_FIELDS
    assert "host" not in request.__dataclass_fields__
    assert "method" not in request.__dataclass_fields__
    assert "headers" not in request.__dataclass_fields__
    assert "body" not in request.__dataclass_fields__

    sent: list[httpx.Request] = []

    def handler(http_request: httpx.Request) -> httpx.Response:
        sent.append(http_request)
        return _json_response(
            _rich_payload(ranges, data_order=(1, 2, 0))
        )

    with httpx.Client(transport=httpx.MockTransport(handler), timeout=30.0) as client:
        context, require_context, token_provider = _rich_port_authority()
        port = google_sheets_reader._build_google_sheets_rich_read_port(
            client=client,
            require_context=require_context,
            token_provider=token_provider,
        )
        result = port(context, "synthetic_file_id", ranges)

    assert len(sent) == 1
    request_sent = sent[0]
    assert request_sent.method == "GET"
    assert request_sent.url.scheme == "https"
    assert request_sent.url.host == "sheets.googleapis.com"
    assert request_sent.url.path == "/v4/spreadsheets/synthetic_file_id"
    assert request_sent.content == b""
    query = parse_qs(request_sent.url.query.decode())
    assert query["ranges"] == [
        "'Synthetic grid'!E1:E1",
        "'Synthetic grid'!A1:A1",
        "'Synthetic grid'!C1:C1",
    ]
    assert query["fields"] == [_RICH_GRIDDATA_FIELDS]
    assert query["includeGridData"] == ["true"]
    assert "synthetic-private-token" not in repr(result)
    assert [item.window.column_start for item in result.ranges] == [4, 0, 2]


@pytest.mark.parametrize(
    "ranges",
    [
        (),
        (_rich_a1_range(0),) * 4,
        ("'Synthetic grid'!A1:A1",),
    ],
)
def test_private_rich_request_rejects_empty_oversized_or_untyped_ranges(ranges):
    with pytest.raises(ContentSafeError):
        _build_rich_cell_data_request("synthetic_file_id", ranges)


def test_private_rich_request_allows_one_and_three_ranges_and_rejects_invalid_coordinates():
    assert len(_build_rich_cell_data_request("synthetic_file_id", (_rich_a1_range(0),)).ranges) == 1
    assert len(
        _build_rich_cell_data_request(
            "synthetic_file_id",
            (_rich_a1_range(0), _rich_a1_range(2), _rich_a1_range(4)),
        ).ranges
    ) == 3
    with pytest.raises(ContentSafeError):
        _build_rich_cell_data_request("https://attacker.invalid/sheet", (_rich_a1_range(0),))
    for args in (
        ("Synthetic grid", True, 0, 1),
        ("Synthetic grid", 0, -1, 1),
        ("Synthetic grid", 0, 0, 0),
        ("Synthetic grid", 0, 0, MAX_SHEETS_REQUEST_WINDOW_CELLS + 1),
    ):
        with pytest.raises(ContentSafeError):
            _SheetsA1Range(*args)
    with pytest.raises(ContentSafeError):
        _build_rich_cell_data_request("synthetic_file_id", [_rich_a1_range(0)])


def test_rich_grid_mapping_is_response_order_independent_and_reuses_parser(monkeypatch):
    ranges = (_rich_a1_range(4), _rich_a1_range(0))
    values = (
        [{"formattedValue": "right", "effectiveValue": {"numberValue": 2}}],
        [{"formattedValue": "left", "effectiveValue": {"numberValue": 1}}],
    )
    original_parser = google_sheets_reader.parse_griddata_envelope
    parser_calls: list[dict[str, object]] = []

    def spy_parser(payload, *, window):
        parser_calls.append(payload)
        cells = payload["sheets"][0]["data"][0].get("rowData", [{"values": []}])[0].get("values", [])
        for cell in cells:
            assert "userEnteredFormat" not in cell
            assert "effectiveValue" not in cell
        return original_parser(payload, window=window)

    monkeypatch.setattr(google_sheets_reader, "parse_griddata_envelope", spy_parser)
    request = _build_rich_cell_data_request("synthetic_file_id", ranges)
    normal = google_sheets_reader._parse_rich_sheets_response(
        _rich_payload(ranges, data_order=(0, 1), cells_by_range=values),
        request,
    )
    reversed_result = google_sheets_reader._parse_rich_sheets_response(
        _rich_payload(ranges, data_order=(1, 0), cells_by_range=values),
        request,
    )
    summary = lambda result: tuple(
        (
            item.sheet.sheet_id,
            item.sheet.index,
            item.envelope.start_row,
            item.envelope.start_column,
            tuple(cell.cell_data["formattedValue"] for cell in item.raw_cells),
        )
        for item in result.ranges
    )
    assert summary(normal) == summary(reversed_result)
    assert [item.envelope.start_column for item in normal.ranges] == [4, 0]
    assert len(parser_calls) == 4
    assert all(item.envelope.returned_cells == 1 for item in normal.ranges)


def test_private_rich_response_retains_regional_metadata_effective_values_and_number_format():
    ranges = (_rich_a1_range(1, column_count=3),)
    format_number = {"numberFormat": {"type": "NUMBER", "pattern": "#,##0.0"}}
    format_percent = {"numberFormat": {"type": "PERCENT", "pattern": "0.0%"}}
    values = (
        [
            {
                "userEnteredValue": {"numberValue": 1234.5},
                "effectiveValue": {"numberValue": 1234.5},
                "formattedValue": "synthetic-number-display",
                "userEnteredFormat": format_number,
            },
            {
                "userEnteredValue": {"numberValue": 0.125},
                "effectiveValue": {"numberValue": 0.125},
                "formattedValue": "synthetic-percent-display",
                "userEnteredFormat": format_percent,
            },
            {
                "effectiveValue": {"stringValue": "derived spill value"},
                "formattedValue": "derived spill display",
            },
        ],
    )
    result = google_sheets_reader._parse_rich_sheets_response(
        _rich_payload(ranges, cells_by_range=values),
        _build_rich_cell_data_request("synthetic_file_id", ranges),
    )
    assert result.locale == "synthetic_LOCALE"
    assert result.time_zone == "Synthetic/Zone"
    assert result.ranges[0].envelope.cells[0].formatted_value == "synthetic-number-display"
    assert result.ranges[0].envelope.cells[1].formatted_value == "synthetic-percent-display"
    raw = [cell.cell_data for cell in result.ranges[0].raw_cells]
    assert raw[0]["effectiveValue"] == {"numberValue": 1234.5}
    assert raw[1]["effectiveValue"] == {"numberValue": 0.125}
    assert raw[2]["effectiveValue"] == {"stringValue": "derived spill value"}
    assert raw[0]["userEnteredFormat"] == format_number
    assert raw[1]["userEnteredFormat"] == format_percent
    with pytest.raises(TypeError):
        raw[0]["userEnteredFormat"]["numberFormat"] = {}  # type: ignore[index]


def test_trailing_omitted_cell_data_is_not_padded_or_classified_as_authored_absence():
    requested = _rich_a1_range(10, column_count=2)
    result = google_sheets_reader._parse_rich_sheets_response(
        _rich_payload(
            (requested,),
            cells_by_range=(
                [
                    {
                        "userEnteredValue": {"numberValue": 7},
                        "effectiveValue": {"numberValue": 7},
                        "formattedValue": "synthetic observed cell",
                    }
                ],
            ),
        ),
        _build_rich_cell_data_request("synthetic_file_id", (requested,)),
    )
    observation = result.ranges[0]
    explicit = google_sheets_reader._lookup_explicit_raw_cell_data(
        observation,
        row=0,
        column=10,
    )
    omitted = google_sheets_reader._lookup_explicit_raw_cell_data(
        observation,
        row=0,
        column=11,
    )
    assert observation.envelope.returned_cells == 1
    assert len(observation.raw_cells) == 1
    assert explicit.state is google_sheets_reader._CellDataLookupState.EXPLICIT
    assert explicit.cell_data is not None
    assert omitted.state is google_sheets_reader._CellDataLookupState.NOT_ESTABLISHED
    assert omitted.cell_data is None


def test_existing_griddata_parser_contract_still_rejects_rich_cell_fields():
    window = _window(column_count=1)
    for cell in (
        {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "0.0"}}},
        {"effectiveValue": {"numberValue": 12.5}},
    ):
        with pytest.raises(ContentSafeError):
            parse_griddata_envelope(_grid_envelope(window, values=[cell]), window=window)


def test_private_rich_read_port_failure_sends_once_without_retry():
    sent: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        raise httpx.ConnectError("synthetic transient failure", request=request)

    with httpx.Client(transport=httpx.MockTransport(handler), timeout=30.0) as client:
        context, require_context, token_provider = _rich_port_authority()
        port = google_sheets_reader._build_google_sheets_rich_read_port(
            client=client,
            require_context=require_context,
            token_provider=token_provider,
        )
        with pytest.raises(ContentSafeError) as caught:
            port(context, "synthetic_file_id", (_rich_a1_range(0),))
    assert caught.value.code == "TRANSIENT_UPSTREAM"
    assert len(sent) == 1
    assert "synthetic transient failure" not in str(caught.value)
    assert "synthetic-private-token" not in str(caught.value)


def test_private_rich_read_reuses_raw_and_decoded_body_caps():
    stream = _FailIfRead()

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Length": str(MAX_SHEETS_RESPONSE_BYTES + 1)},
            stream=stream,
        )

    with httpx.Client(transport=httpx.MockTransport(handler), timeout=30.0) as client:
        context, require_context, token_provider = _rich_port_authority()
        port = google_sheets_reader._build_google_sheets_rich_read_port(
            client=client,
            require_context=require_context,
            token_provider=token_provider,
        )
        with pytest.raises(ContentSafeError) as caught:
            port(context, "synthetic_file_id", (_rich_a1_range(0),))
    assert caught.value.code == "TOO_LARGE"
    assert stream.iterated is False


def test_private_runtime_seam_uses_existing_keyless_profile_and_one_sheet_send(monkeypatch):
    a1_range = _rich_a1_range(0)
    payload = _rich_payload((a1_range,), spreadsheet_id="runtime_spreadsheet")

    def handler(_: httpx.Request) -> httpx.Response:
        return _json_response(payload)

    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        result = runtime._read_sheets_rich(
            profile_id="drive-discovery",
            user_key="analyst@cevalente.com.br",
            spreadsheet_id="runtime_spreadsheet",
            ranges=(a1_range,),
        )
        with pytest.raises(ContentSafeError):
            runtime._read_sheets_rich(
                profile_id="drive-discovery",
                user_key="unregistered@example.invalid",
                spreadsheet_id="runtime_spreadsheet",
                ranges=(a1_range,),
            )
        assert len(captured) == 1
    assert len(captured) == 1
    assert captured[0].method == "GET"
    assert captured[0].url.host == "sheets.googleapis.com"
    assert result.spreadsheet_id == "runtime_spreadsheet"


def test_private_drive_metadata_port_is_one_fixed_bounded_get(monkeypatch):
    sent: list[httpx.Request] = []
    bounded_calls: list[tuple[int, int]] = []
    original_bounded_read = google_docs_adapter.read_bounded_response_body

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        payload = _drive_payload("synthetic_file_id")
        payload["webViewLink"] = "must-not-escape-the-private-parser"
        return _json_response(payload)

    def bounded_read(response: httpx.Response, *, raw_cap: int, decoded_cap: int):
        bounded_calls.append((raw_cap, decoded_cap))
        return original_bounded_read(
            response,
            raw_cap=raw_cap,
            decoded_cap=decoded_cap,
        )

    monkeypatch.setattr(google_docs_adapter, "read_bounded_response_body", bounded_read)
    context, require_context, token_provider = _drive_metadata_port_authority()
    with httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False) as client:
        port = google_docs_adapter._build_google_drive_file_metadata_read_port(
            client=client,
            require_context=require_context,
            token_provider=token_provider,
        )
        result = port(context, "synthetic_file_id")

    assert type(result) is DriveFileMetadata
    assert result.file_id == "synthetic_file_id"
    assert result.mime_type == SPREADSHEET_MIME
    assert result.modified_time == "2026-09-21T00:00:00.000Z"
    assert result.trashed is False
    assert set(result.__dataclass_fields__) == {
        "file_id",
        "mime_type",
        "modified_time",
        "trashed",
    }
    assert "must-not-escape-the-private-parser" not in repr(result)
    assert len(sent) == 1
    request = sent[0]
    assert request.method == "GET"
    assert request.url.scheme == "https"
    assert request.url.host == "www.googleapis.com"
    assert request.url.path == "/drive/v3/files/synthetic_file_id"
    query = parse_qs(request.url.query.decode("ascii"))
    assert query == {
        "fields": [DRIVE_FILE_METADATA_FIELDS],
        "supportsAllDrives": ["true"],
    }
    assert request.headers["authorization"] == "Bearer synthetic-private-token"
    assert bounded_calls == [(64 * 1024, 64 * 1024)]
    assert tuple(inspect.signature(port).parameters) == ("context", "file_id")


@pytest.mark.parametrize(
    "untrusted_id",
    ["https://attacker.invalid/file", "../outside", "folder/file", ""],
)
def test_private_drive_metadata_port_rejects_url_and_path_injection(untrusted_id):
    sent: list[httpx.Request] = []
    context, require_context, token_provider = _drive_metadata_port_authority()
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: sent.append(request) or _json_response(_drive_payload(untrusted_id))
        )
    ) as client:
        port = google_docs_adapter._build_google_drive_file_metadata_read_port(
            client=client,
            require_context=require_context,
            token_provider=token_provider,
        )
        with pytest.raises(ContentSafeError):
            port(context, untrusted_id)
        with pytest.raises(TypeError):
            port(context, "synthetic_file_id", method="POST")  # type: ignore[call-arg]
        with pytest.raises(TypeError):
            port(context, "synthetic_file_id", url="https://attacker.invalid")  # type: ignore[call-arg]
        with pytest.raises(TypeError):
            port(context, "synthetic_file_id", headers={"Authorization": "Bearer caller"})  # type: ignore[call-arg]
    assert sent == []


@pytest.mark.parametrize(
    "payload",
    [
        {"id": "different_file", "mimeType": SPREADSHEET_MIME, "modifiedTime": "t", "trashed": False},
        {"id": "synthetic_file_id", "mimeType": SPREADSHEET_MIME, "trashed": False},
        {"id": "synthetic_file_id", "mimeType": SPREADSHEET_MIME, "modifiedTime": "t", "trashed": "false"},
    ],
)
def test_private_drive_metadata_port_fails_closed_on_malformed_metadata(payload):
    context, require_context, token_provider = _drive_metadata_port_authority()
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: _json_response(payload))
    ) as client:
        port = google_docs_adapter._build_google_drive_file_metadata_read_port(
            client=client,
            require_context=require_context,
            token_provider=token_provider,
        )
        result = port(context, "synthetic_file_id")
    assert type(result) is _DriveFileMetadataReadFailure
    assert result.kind == "response_validation"


def test_private_drive_metadata_port_rejects_duplicate_json_keys():
    raw = (
        b'{"id":"synthetic_file_id","id":"synthetic_file_id",'
        b'"mimeType":"application/vnd.google-apps.spreadsheet",'
        b'"modifiedTime":"2026-09-21T00:00:00.000Z","trashed":false}'
    )
    context, require_context, token_provider = _drive_metadata_port_authority()
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                headers={"Content-Length": str(len(raw))},
                stream=_Payload(raw),
            )
        )
    ) as client:
        port = google_docs_adapter._build_google_drive_file_metadata_read_port(
            client=client,
            require_context=require_context,
            token_provider=token_provider,
        )
        result = port(context, "synthetic_file_id")
    assert type(result) is _DriveFileMetadataReadFailure
    assert result.kind == "json"


def test_private_drive_metadata_port_bounds_body_before_json_parse():
    stream = _FailIfRead()
    context, require_context, token_provider = _drive_metadata_port_authority()
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                headers={"Content-Length": str(64 * 1024 + 1)},
                stream=stream,
            )
        )
    ) as client:
        port = google_docs_adapter._build_google_drive_file_metadata_read_port(
            client=client,
            require_context=require_context,
            token_provider=token_provider,
        )
        result = port(context, "synthetic_file_id")
    assert type(result) is _DriveFileMetadataReadFailure
    assert result.kind == "too_large"
    assert stream.iterated is False


def test_private_drive_metadata_port_does_not_retry_transient_failure():
    sent: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        raise httpx.ConnectError("synthetic transport failure", request=request)

    context, require_context, token_provider = _drive_metadata_port_authority()
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        port = google_docs_adapter._build_google_drive_file_metadata_read_port(
            client=client,
            require_context=require_context,
            token_provider=token_provider,
        )
        result = port(context, "synthetic_file_id")
    assert type(result) is _DriveFileMetadataReadFailure
    assert result.kind == "transport"
    assert len(sent) == 1
    assert not any("write" in operation.value.casefold() for operation in ContentOperation)


def test_private_runtime_composes_drive_sheets_drive_without_public_dispatch(monkeypatch):
    spreadsheet_id = "synthetic_spreadsheet"
    a1_range = _rich_a1_range(0)
    rich_payload = _rich_payload((a1_range,), spreadsheet_id=spreadsheet_id)

    def forbidden_public_dispatch(*args, **kwargs):
        del args, kwargs
        raise AssertionError("private composition must not enter public MCP dispatch")

    monkeypatch.setattr(ContentRuntime, "execute", forbidden_public_dispatch)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "www.googleapis.com":
            return _json_response(_drive_payload(spreadsheet_id))
        assert request.url.host == "sheets.googleapis.com"
        return _json_response(rich_payload)

    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        preflight = runtime._read_drive_file_metadata(
            profile_id="drive-discovery",
            user_key="analyst@cevalente.com.br",
            file_id=spreadsheet_id,
        )
        rich = runtime._read_sheets_rich(
            profile_id="drive-discovery",
            user_key="analyst@cevalente.com.br",
            spreadsheet_id=spreadsheet_id,
            ranges=(a1_range,),
        )
        postflight = runtime._read_drive_file_metadata(
            profile_id="drive-discovery",
            user_key="analyst@cevalente.com.br",
            file_id=spreadsheet_id,
        )

    assert type(preflight) is DriveFileMetadata
    assert type(postflight) is DriveFileMetadata
    assert preflight == postflight
    assert rich.spreadsheet_id == spreadsheet_id
    assert len(captured) == 3
    assert [request.url.host for request in captured] == [
        "www.googleapis.com",
        "sheets.googleapis.com",
        "www.googleapis.com",
    ]
    assert all(request.method == "GET" for request in captured)
    assert sum(request.url.host == "sheets.googleapis.com" for request in captured) == 1
    assert sum(request.url.host == "www.googleapis.com" for request in captured) == 2
    assert tuple(inspect.signature(ContentRuntime._read_drive_file_metadata).parameters) == (
        "self",
        "profile_id",
        "user_key",
        "file_id",
    )
