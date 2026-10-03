"""Bounded Sheets traversal, continuation, and Drive snapshot verification."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from enum import Enum
from types import MappingProxyType

import httpx

from google_workspace_admin.content.auth.handles import (
    AuthorizedOperationContext,
    _OperationAuthority,
)
from google_workspace_admin.content.auth.scopes import ApprovedScopeProfile
from google_workspace_admin.content.budgets import (
    DEFAULT_CONTENT_READING_BUDGETS,
    MAX_SHEETS_GRIDDATA_CELLS_PER_INVOCATION,
    MAX_SHEETS_GRIDDATA_REQUESTS_PER_INVOCATION,
    MAX_SHEETS_REQUEST_WINDOW_CELLS,
)
from google_workspace_admin.content.chunks import ContentChunk, TextPayload
from google_workspace_admin.content.continuation import (
    DocsContinuationManager,
    SheetsContinuationState,
)
from google_workspace_admin.content.errors import (
    ContentErrorOperation,
    ContentSafeError,
    FailureStage,
)
from google_workspace_admin.content.google_docs import (
    DriveFileMetadata,
    _DriveFileMetadataReadFailure,
)
from google_workspace_admin.content.google_sheets import (
    GOOGLE_SHEET_MIME_TYPE,
    SheetHandling,
    SheetMetadata,
    SheetType,
    SheetsCoverageGap,
    SheetsGridWindow,
    GridDataEnvelope,
    WorkbookMetadata,
    _SheetsA1Range,
    _grid_origin,
    extract_griddata_content,
    parse_griddata_envelope,
    parse_workbook_metadata,
)
from google_workspace_admin.content.google_sheets_adapter import (
    _RichCellDataRequest,
    _build_google_sheets_request_port,
    _build_rich_cell_data_request,
    build_griddata_window_request,
    build_workbook_metadata_request,
)
from google_workspace_admin.content.inventory import InventorySnapshot
from google_workspace_admin.content.operations import (
    ContentOperation,
    _NormalizedOperationRequest,
)
from google_workspace_admin.content.outcomes import (
    ProcessingOutcome,
    ProcessingStatus,
    SafeContentErrorCode,
)
from google_workspace_admin.content.provenance import SheetsContentComponent, SheetsProvenance
from google_workspace_admin.content.readers import BoundedReadResult
from google_workspace_admin.content.routing import ContentClass


GOOGLE_SHEETS_READER_VERSION = 1
_COMPONENT_ORDER = {
    SheetsContentComponent.CELL_DISPLAY: 0,
    SheetsContentComponent.CELL_FORMULA: 1,
    SheetsContentComponent.CELL_NOTE: 2,
    SheetsContentComponent.CELL_HYPERLINK: 3,
    SheetsContentComponent.CELL_RICH_TEXT_LINK: 4,
}


class _CellDataLookupState(str, Enum):
    EXPLICIT = "EXPLICIT"
    NOT_ESTABLISHED = "NOT_ESTABLISHED"


@dataclass(frozen=True, slots=True)
class _MappedRawCellData:
    row: int
    column: int
    cell_data: Mapping[str, object] = field(repr=False)


@dataclass(frozen=True, slots=True)
class _RichGridBlockObservation:
    requested_range: _SheetsA1Range
    sheet: SheetMetadata
    window: SheetsGridWindow
    envelope: GridDataEnvelope
    raw_cells: tuple[_MappedRawCellData, ...] = field(repr=False)


@dataclass(frozen=True, slots=True)
class _CellDataLookup:
    state: _CellDataLookupState
    cell_data: Mapping[str, object] | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class _RichSheetsReadResult:
    spreadsheet_id: str = field(repr=False)
    locale: str | None
    time_zone: str | None
    metadata: WorkbookMetadata
    ranges: tuple[_RichGridBlockObservation, ...] = field(repr=False)


def _rich_response_error() -> ContentSafeError:
    return ContentSafeError(
        code="RESPONSE_VALIDATION",
        operation=ContentErrorOperation.RESPONSE_SHEETS_GET,
    )


def _rich_mapping(value: object) -> Mapping[str, object]:
    if type(value) is not dict:
        raise _rich_response_error()
    return value


def _freeze_json(value: object) -> object:
    if type(value) is dict:
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if type(value) is list:
        return tuple(_freeze_json(item) for item in value)
    return value


def _project_rich_griddata_for_parser(data: Mapping[str, object]) -> dict[str, object]:
    """Drop only rich fields the production GridData DTO deliberately rejects."""

    projected: dict[str, object] = {
        key: data[key] for key in ("startRow", "startColumn") if key in data
    }
    if "rowData" not in data:
        return projected
    raw_rows = data["rowData"]
    if type(raw_rows) is not list:
        projected["rowData"] = raw_rows
        return projected
    rows: list[object] = []
    for raw_row in raw_rows:
        if type(raw_row) is not dict:
            rows.append(raw_row)
            continue
        row: dict[str, object] = {
            key: value for key, value in raw_row.items() if key != "values"
        }
        if "values" in raw_row:
            raw_values = raw_row["values"]
            if type(raw_values) is not list:
                row["values"] = raw_values
            else:
                values: list[object] = []
                for raw_cell in raw_values:
                    if type(raw_cell) is not dict:
                        values.append(raw_cell)
                        continue
                    # effectiveValue is a richer union in this response. It is
                    # retained in raw_cells below; the existing DTO does not
                    # consume it and must not be broadened for this port.
                    values.append(
                        {
                            key: value
                            for key, value in raw_cell.items()
                            if key not in {"effectiveValue", "userEnteredFormat"}
                        }
                    )
                row["values"] = values
        rows.append(row)
    projected["rowData"] = rows
    return projected


def _lookup_explicit_raw_cell_data(
    observation: _RichGridBlockObservation,
    *,
    row: object,
    column: object,
) -> _CellDataLookup:
    """Lookup only a requested coordinate; an omitted CellData is not absence."""

    if (
        type(observation) is not _RichGridBlockObservation
        or type(row) is not int
        or type(column) is not int
    ):
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.SHEETS_GRIDDATA_WINDOW,
        )
    if row != observation.requested_range.row or not (
        observation.requested_range.column_start
        <= column
        < observation.requested_range.column_start + observation.requested_range.column_count
    ):
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.SHEETS_GRIDDATA_WINDOW,
        )
    for raw_cell in observation.raw_cells:
        if raw_cell.row == row and raw_cell.column == column:
            return _CellDataLookup(_CellDataLookupState.EXPLICIT, raw_cell.cell_data)
    return _CellDataLookup(_CellDataLookupState.NOT_ESTABLISHED)


def _parse_rich_sheets_response(
    payload: Mapping[str, object],
    request: _RichCellDataRequest,
) -> _RichSheetsReadResult:
    """Route GridData by sheet identity and explicit origin, then reuse parsers."""

    if type(request) is not _RichCellDataRequest:
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.SHEETS_GRIDDATA_WINDOW,
        )
    if payload.get("spreadsheetId") != request.spreadsheet_id:
        raise _rich_response_error()
    raw_properties = payload.get("properties", {})
    properties = _rich_mapping(raw_properties)
    locale = properties.get("locale")
    time_zone = properties.get("timeZone")
    if (locale is not None and type(locale) is not str) or (
        time_zone is not None and type(time_zone) is not str
    ):
        raise _rich_response_error()

    metadata = parse_workbook_metadata(payload)
    raw_sheets = payload.get("sheets")
    if type(raw_sheets) is not list:
        raise _rich_response_error()
    metadata_by_id = {sheet.sheet_id: sheet for sheet in metadata.sheets}
    requested: dict[tuple[int, int, int], tuple[_SheetsA1Range, SheetMetadata, SheetsGridWindow]] = {}
    requested_in_order: list[tuple[int, int, int]] = []
    for a1_range in request.ranges:
        matches = [sheet for sheet in metadata.sheets if sheet.title == a1_range.sheet_title]
        if len(matches) != 1 or matches[0].sheet_type is not SheetType.GRID:
            raise _rich_response_error()
        sheet = matches[0]
        window = SheetsGridWindow(
            sheet,
            a1_range.row,
            1,
            a1_range.column_start,
            a1_range.column_count,
        )
        key = (sheet.sheet_id, a1_range.row, a1_range.column_start)
        if key in requested:
            raise _rich_response_error()
        requested[key] = (a1_range, sheet, window)
        requested_in_order.append(key)

    raw_blocks: dict[tuple[int, int, int], Mapping[str, object]] = {}
    for raw_sheet in raw_sheets:
        sheet_object = _rich_mapping(raw_sheet)
        sheet_properties = _rich_mapping(sheet_object.get("properties"))
        sheet_id = sheet_properties.get("sheetId")
        if type(sheet_id) is not int or sheet_id not in metadata_by_id:
            raise _rich_response_error()
        sheet = metadata_by_id[sheet_id]
        raw_data = sheet_object.get("data", [])
        if type(raw_data) is not list:
            raise _rich_response_error()
        for raw_block in raw_data:
            block = _rich_mapping(raw_block)
            origin_row = _grid_origin(block, "startRow", 0)
            origin_column = _grid_origin(block, "startColumn", 0)
            key = (sheet.sheet_id, origin_row, origin_column)
            if key not in requested or key in raw_blocks:
                raise _rich_response_error()
            raw_blocks[key] = block
    if set(raw_blocks) != set(requested):
        raise _rich_response_error()

    observations: list[_RichGridBlockObservation] = []
    for key in requested_in_order:
        a1_range, sheet, window = requested[key]
        raw_block = raw_blocks[key]
        compatibility_payload = {
            "sheets": [
                {
                    "properties": {
                        "sheetId": sheet.sheet_id,
                        "index": sheet.index,
                        "sheetType": sheet.sheet_type.value,
                    },
                    "data": [_project_rich_griddata_for_parser(raw_block)],
                }
            ]
        }
        envelope = parse_griddata_envelope(compatibility_payload, window=window)
        raw_rows = raw_block.get("rowData", [])
        if type(raw_rows) is not list:
            raise _rich_response_error()
        raw_cells: list[Mapping[str, object]] = []
        for raw_row in raw_rows:
            row = _rich_mapping(raw_row)
            raw_values = row.get("values", [])
            if type(raw_values) is not list:
                raise _rich_response_error()
            raw_cells.extend(_rich_mapping(raw_cell) for raw_cell in raw_values)
        if len(raw_cells) != len(envelope.cells):
            raise _rich_response_error()
        mapped = tuple(
            _MappedRawCellData(
                row=cell.row,
                column=cell.column,
                cell_data=_freeze_json(raw_cell),
            )
            for cell, raw_cell in zip(envelope.cells, raw_cells, strict=True)
        )
        observations.append(
            _RichGridBlockObservation(
                requested_range=a1_range,
                sheet=sheet,
                window=window,
                envelope=envelope,
                raw_cells=mapped,
            )
        )
    return _RichSheetsReadResult(
        spreadsheet_id=request.spreadsheet_id,
        locale=locale,
        time_zone=time_zone,
        metadata=metadata,
        ranges=tuple(observations),
    )


def _build_google_sheets_rich_read_port(
    *,
    client: httpx.Client,
    require_context: Callable[[object], object],
    token_provider: Callable[[object, ApprovedScopeProfile], str],
) -> Callable[[AuthorizedOperationContext, object, object], _RichSheetsReadResult]:
    """Construct the private one-GET rich Sheets observation capability."""

    sheets_request = _build_google_sheets_request_port(
        client=client,
        require_context=require_context,
        token_provider=token_provider,
    )

    def read(
        context: AuthorizedOperationContext,
        spreadsheet_id: object,
        ranges: object,
    ) -> _RichSheetsReadResult:
        request = _build_rich_cell_data_request(spreadsheet_id, ranges)
        payload = sheets_request(context, request)
        return _parse_rich_sheets_response(payload, request)

    return read


@dataclass(frozen=True, slots=True)
class _DriveFailure:
    status: int | None = None
    kind: str = "transport"


@dataclass(frozen=True, slots=True)
class _Cursor:
    sheet_ordinal: int
    sheet: SheetMetadata
    row: int
    column: int
    component: SheetsContentComponent | None = None
    rich_text_run_ordinal: int | None = None
    rich_text_start_utf16: int | None = None


class _ResumeMismatch(Exception):
    pass


def _api_failure(error: ContentSafeError, *, stage: FailureStage | None = None) -> BoundedReadResult:
    mapping = {
        "ACCESS_DENIED": (ProcessingStatus.ACCESS_DENIED, SafeContentErrorCode.ACCESS_DENIED),
        "NOT_FOUND": (ProcessingStatus.NOT_FOUND, SafeContentErrorCode.NOT_FOUND),
        "QUOTA_EXCEEDED": (ProcessingStatus.TRANSIENT_UPSTREAM, SafeContentErrorCode.QUOTA_EXCEEDED),
        "TRANSIENT_UPSTREAM": (ProcessingStatus.TRANSIENT_UPSTREAM, SafeContentErrorCode.TRANSIENT_UPSTREAM),
        "TOO_LARGE": (ProcessingStatus.TOO_LARGE, SafeContentErrorCode.TOO_LARGE),
    }
    status, code = mapping.get(
        error.code,
        (ProcessingStatus.EXTRACTION_FAILED, SafeContentErrorCode.RESPONSE_VALIDATION),
    )
    return _failure(status, code, stage=stage)


def _failure(
    status: ProcessingStatus,
    code: SafeContentErrorCode,
    *,
    stage: FailureStage | None = None,
) -> BoundedReadResult:
    kwargs = {} if stage is None else {"failure_stage": stage}
    return BoundedReadResult(
        (),
        ProcessingOutcome(
            status,
            ContentClass.GOOGLE_SHEET,
            safe_error_code=code,
            **kwargs,
        ),
    )


def _partial_without_token(
    chunks: tuple[ContentChunk, ...],
    *,
    reason: str,
) -> BoundedReadResult:
    return BoundedReadResult(
        chunks,
        ProcessingOutcome(
            ProcessingStatus.PARTIALLY_PROCESSED,
            ContentClass.GOOGLE_SHEET,
            chunk_count=len(chunks),
            result_count=len(chunks),
            partial_reason=reason,
        ),
    )


def _metadata_fingerprint(metadata: WorkbookMetadata) -> tuple[tuple[int, int, str, str, int | None, int | None, bool], ...]:
    return tuple(
        (
            sheet.sheet_id,
            sheet.index,
            sheet.title,
            sheet.sheet_type.value,
            sheet.row_count,
            sheet.column_count,
            sheet.hidden,
        )
        for sheet in metadata.sheets
    )


def _first_cursor(metadata: WorkbookMetadata, start_ordinal: int = 0) -> _Cursor | None:
    for ordinal in range(start_ordinal, len(metadata.sheets)):
        sheet = metadata.sheets[ordinal]
        if (
            sheet.handling is SheetHandling.GRIDDATA_ELIGIBLE
            and sheet.row_count
            and sheet.column_count
        ):
            return _Cursor(ordinal, sheet, 0, 0)
    return None


def _advance_cursor(metadata: WorkbookMetadata, cursor: _Cursor) -> _Cursor | None:
    sheet = cursor.sheet
    assert sheet.row_count is not None and sheet.column_count is not None
    column = cursor.column + 1
    row = cursor.row
    if column < sheet.column_count:
        return _Cursor(cursor.sheet_ordinal, sheet, row, column)
    column = 0
    row += 1
    if row < sheet.row_count:
        return _Cursor(cursor.sheet_ordinal, sheet, row, column)
    return _first_cursor(metadata, cursor.sheet_ordinal + 1)


def _unit_position(chunk: ContentChunk) -> tuple[int, int, int]:
    provenance = chunk.provenance
    if type(provenance) is not SheetsProvenance or provenance.component is None:
        raise ContentSafeError(
            code="RESPONSE_VALIDATION",
            operation=ContentErrorOperation.RESPONSE_SHEETS_GRIDDATA,
        )
    component_order = _COMPONENT_ORDER[provenance.component]
    run_ordinal = -1 if provenance.rich_text_run_ordinal is None else provenance.rich_text_run_ordinal
    run_start = -1 if provenance.rich_text_start_utf16 is None else provenance.rich_text_start_utf16
    return component_order, run_ordinal, run_start


def _state_cursor(state: SheetsContinuationState, metadata: WorkbookMetadata) -> _Cursor:
    if state.sheet_ordinal >= len(metadata.sheets):
        raise _ResumeMismatch
    sheet = metadata.sheets[state.sheet_ordinal]
    if sheet.sheet_id != state.sheet_id or sheet.handling is not SheetHandling.GRIDDATA_ELIGIBLE:
        raise _ResumeMismatch
    return _Cursor(
        state.sheet_ordinal,
        sheet,
        state.row,
        state.column,
        state.component,
        state.rich_text_run_ordinal,
        state.rich_text_start_utf16,
    )


def _next_component_state(
    *,
    snapshot: InventorySnapshot,
    fingerprint: tuple[tuple[int, int, str, str, int | None, int | None, bool], ...],
    cursor: _Cursor,
    logical_cells_completed: int,
    coverage_gaps: set[SheetsCoverageGap],
) -> SheetsContinuationState:
    ordered_gaps = tuple(gap for gap in SheetsCoverageGap if gap in coverage_gaps)
    return SheetsContinuationState(
        snapshot=snapshot,
        reader_version=GOOGLE_SHEETS_READER_VERSION,
        metadata_fingerprint=fingerprint,
        sheet_ordinal=cursor.sheet_ordinal,
        sheet_id=cursor.sheet.sheet_id,
        row=cursor.row,
        column=cursor.column,
        component=cursor.component,
        rich_text_run_ordinal=cursor.rich_text_run_ordinal,
        rich_text_start_utf16=cursor.rich_text_start_utf16,
        logical_cells_completed=logical_cells_completed,
        coverage_gaps=ordered_gaps,
    )


def _drive_failure_result(failure: _DriveFailure, *, preflight: bool) -> BoundedReadResult:
    if failure.kind == "response_validation":
        return _failure(
            ProcessingStatus.EXTRACTION_FAILED,
            SafeContentErrorCode.RESPONSE_VALIDATION,
            stage=(
                FailureStage.PREFLIGHT_VALIDATION
                if preflight
                else FailureStage.POSTFLIGHT_VALIDATION
            ),
        )
    if failure.status in {401, 403}:
        status, code = ProcessingStatus.ACCESS_DENIED, SafeContentErrorCode.ACCESS_DENIED
    elif failure.status == 404:
        status, code = ProcessingStatus.NOT_FOUND, SafeContentErrorCode.NOT_FOUND
    elif failure.status == 429:
        status, code = ProcessingStatus.TRANSIENT_UPSTREAM, SafeContentErrorCode.QUOTA_EXCEEDED
    elif failure.status in {408, 425} or failure.status is not None and failure.status >= 500 or failure.kind in {"timeout", "transport"}:
        status, code = ProcessingStatus.TRANSIENT_UPSTREAM, SafeContentErrorCode.TRANSIENT_UPSTREAM
    elif failure.kind == "too_large":
        status, code = ProcessingStatus.TOO_LARGE, SafeContentErrorCode.TOO_LARGE
    else:
        status, code = ProcessingStatus.EXTRACTION_FAILED, SafeContentErrorCode.RESPONSE_VALIDATION
    stage = FailureStage.PREFLIGHT_FETCH if preflight else FailureStage.POSTFLIGHT_FETCH
    return _failure(status, code, stage=stage)


def _build_google_sheets_read_port(
    *,
    client: httpx.Client,
    require_context: Callable[[object], object],
    token_provider: Callable[[object, ApprovedScopeProfile], str],
    continuation_manager: DocsContinuationManager,
    public_file_ref_provider: Callable[[str], str] | None = None,
    drive_file_metadata_read: Callable[
        [AuthorizedOperationContext, object], DriveFileMetadata | _DriveFileMetadataReadFailure
    ],
) -> Callable[
    [AuthorizedOperationContext, _NormalizedOperationRequest, Callable[[], AuthorizedOperationContext]],
    BoundedReadResult,
]:
    """Build the internal Sheets reader. It accepts no caller-provided ranges or ops."""

    sheets_request = _build_google_sheets_request_port(
        client=client,
        require_context=require_context,
        token_provider=token_provider,
    )
    if not callable(drive_file_metadata_read):
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.TRANSPORT,
        )

    def drive_metadata(
        context: AuthorizedOperationContext,
        snapshot: InventorySnapshot,
    ) -> DriveFileMetadata | _DriveFailure:
        result = drive_file_metadata_read(context, snapshot.file_id)
        if type(result) is DriveFileMetadata:
            return result
        if type(result) is _DriveFileMetadataReadFailure:
            return _DriveFailure(status=result.status, kind=result.kind)
        return _DriveFailure(kind="response_malformed")

    def read(
        context: AuthorizedOperationContext,
        request: _NormalizedOperationRequest,
        authorize_griddata: Callable[[], AuthorizedOperationContext],
    ) -> BoundedReadResult:
        incoming_token = request.continuation_token
        continuation_state: SheetsContinuationState | None = None
        snapshot: InventorySnapshot | None = None
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
            or authority.operation is not ContentOperation.SHEETS_WORKBOOK_METADATA
            or request.operation is not ContentOperation.SHEETS_WORKBOOK_METADATA
            or request.file_id is None
            or request.expected_mime_type != GOOGLE_SHEET_MIME_TYPE
            or request.modified_time is None
            or not callable(authorize_griddata)
        ):
            raise ContentSafeError(
                code="READ_ONLY_OPERATION_FORBIDDEN",
                operation=ContentErrorOperation.SHEETS_WORKBOOK_METADATA,
            )
        snapshot = InventorySnapshot(
            request.file_id,
            request.expected_mime_type,
            request.modified_time,
        )
        if public_file_ref_provider is None:
            return _failure(
                ProcessingStatus.EXTRACTION_FAILED,
                SafeContentErrorCode.CONTENT_NOT_SUPPORTED,
            )
        try:
            public_file_ref = public_file_ref_provider(snapshot.file_id)
        except ContentSafeError:
            return _failure(
                ProcessingStatus.EXTRACTION_FAILED,
                SafeContentErrorCode.LOCAL_VALIDATION,
            )
        except Exception:
            return _failure(
                ProcessingStatus.EXTRACTION_FAILED,
                SafeContentErrorCode.LOCAL_VALIDATION,
            )
        if incoming_token is not None:
            continuation_state = continuation_manager.resolve_sheets(
                incoming_token,
                snapshot=snapshot,
                reader_version=GOOGLE_SHEETS_READER_VERSION,
            )

        preflight_raw = drive_metadata(context, snapshot)
        if type(preflight_raw) is _DriveFailure:
            return _drive_failure_result(preflight_raw, preflight=True)
        preflight = preflight_raw
        if (
            preflight.trashed
            or preflight.mime_type != GOOGLE_SHEET_MIME_TYPE
            or preflight.mime_type != snapshot.expected_mime_type
            or preflight.modified_time != snapshot.modified_time
        ):
            _discard_incoming(continuation_manager, incoming_token)
            return _failure(
                ProcessingStatus.CHANGED_DURING_AUDIT,
                SafeContentErrorCode.CHANGED_DURING_AUDIT,
                stage=FailureStage.PREFLIGHT_VALIDATION,
            )

        try:
            metadata_raw = sheets_request(
                context,
                build_workbook_metadata_request(snapshot.file_id),
            )
            metadata = parse_workbook_metadata(metadata_raw)
        except ContentSafeError as error:
            _discard_incoming(continuation_manager, incoming_token)
            if error.code == "TOO_LARGE":
                return _partial_without_token((), reason="RESOURCE_LIMIT")
            return _api_failure(error)
        except Exception:
            _discard_incoming(continuation_manager, incoming_token)
            return _failure(
                ProcessingStatus.EXTRACTION_FAILED,
                SafeContentErrorCode.RESPONSE_VALIDATION,
            )

        fingerprint = _metadata_fingerprint(metadata)
        if continuation_state is not None and continuation_state.metadata_fingerprint != fingerprint:
            _discard_incoming(continuation_manager, incoming_token)
            return _failure(
                ProcessingStatus.CHANGED_DURING_AUDIT,
                SafeContentErrorCode.CHANGED_DURING_AUDIT,
                stage=FailureStage.PREFLIGHT_VALIDATION,
            )

        coverage_gaps: set[SheetsCoverageGap] = set()
        for sheet in metadata.sheets:
            if sheet.handling is SheetHandling.OBJECT_COVERAGE_GAP:
                coverage_gaps.add(SheetsCoverageGap.OBJECT_SHEET)
            elif sheet.handling is SheetHandling.DATA_SOURCE_COVERAGE_GAP:
                coverage_gaps.add(SheetsCoverageGap.DATA_SOURCE_SHEET)
        if continuation_state is not None:
            coverage_gaps.update(continuation_state.coverage_gaps)

        cursor = (
            _state_cursor(continuation_state, metadata)
            if continuation_state is not None
            else _first_cursor(metadata)
        )
        logical_cells_completed = (
            0 if continuation_state is None else continuation_state.logical_cells_completed
        )
        chunks: list[ContentChunk] = []
        extracted_bytes = 0
        requested_cells = 0
        grid_requests = 0
        stop_for_invocation_budget = False
        stop_for_file_limit = False
        resume_target_pending = continuation_state is not None and continuation_state.component is not None
        resume_mismatch = False
        grid_context: AuthorizedOperationContext | None = None

        budgets = DEFAULT_CONTENT_READING_BUDGETS
        while cursor is not None:
            remaining_file_cells = budgets.max_sheets_cells_per_file - logical_cells_completed
            if remaining_file_cells <= 0:
                stop_for_file_limit = True
                break
            if (
                grid_requests >= MAX_SHEETS_GRIDDATA_REQUESTS_PER_INVOCATION
                or requested_cells >= MAX_SHEETS_GRIDDATA_CELLS_PER_INVOCATION
            ):
                stop_for_invocation_budget = True
                break

            assert cursor.sheet.column_count is not None
            remaining_row_cells = cursor.sheet.column_count - cursor.column
            width = min(
                remaining_row_cells,
                MAX_SHEETS_REQUEST_WINDOW_CELLS,
                MAX_SHEETS_GRIDDATA_CELLS_PER_INVOCATION - requested_cells,
                remaining_file_cells,
            )
            if width < 1:
                stop_for_file_limit = remaining_file_cells < 1
                stop_for_invocation_budget = not stop_for_file_limit
                break
            window = SheetsGridWindow(
                cursor.sheet,
                cursor.row,
                1,
                cursor.column,
                width,
            )
            requested_cells += width
            grid_requests += 1
            try:
                if grid_context is None:
                    grid_context = authorize_griddata()
                grid_raw = sheets_request(
                    grid_context,
                    build_griddata_window_request(snapshot.file_id, window),
                )
                envelope = parse_griddata_envelope(grid_raw, window=window)
                extraction = extract_griddata_content(
                    envelope,
                    window=window,
                    file_ref=public_file_ref,
                )
            except ContentSafeError as error:
                _discard_incoming(continuation_manager, incoming_token)
                return _api_failure(error)
            except Exception:
                _discard_incoming(continuation_manager, incoming_token)
                return _failure(
                    ProcessingStatus.EXTRACTION_FAILED,
                    SafeContentErrorCode.RESPONSE_VALIDATION,
                )
            coverage_gaps.update(extraction.coverage_gaps)
            by_coordinate: dict[tuple[int, int], list[ContentChunk]] = {}
            for unit in extraction.units:
                provenance = unit.provenance
                if type(provenance) is not SheetsProvenance or provenance.row is None or provenance.column is None:
                    _discard_incoming(continuation_manager, incoming_token)
                    return _failure(
                        ProcessingStatus.EXTRACTION_FAILED,
                        SafeContentErrorCode.RESPONSE_VALIDATION,
                    )
                by_coordinate.setdefault((provenance.row, provenance.column), []).append(unit)

            window_cursor = cursor
            window_start_row = cursor.row
            window_start_column = cursor.column
            for column_offset in range(width):
                coordinate = (window_start_row, window_start_column + column_offset)
                cell_units = by_coordinate.get(coordinate, [])
                if resume_target_pending and continuation_state is not None:
                    assert continuation_state.component is not None
                    target = (
                        _COMPONENT_ORDER[continuation_state.component],
                        -1 if continuation_state.rich_text_run_ordinal is None else continuation_state.rich_text_run_ordinal,
                        -1 if continuation_state.rich_text_start_utf16 is None else continuation_state.rich_text_start_utf16,
                    )
                    positions = [_unit_position(unit) for unit in cell_units]
                    if target not in positions:
                        resume_mismatch = True
                        break
                    cell_units = [unit for unit, position in zip(cell_units, positions) if position >= target]
                    resume_target_pending = False

                for unit in cell_units:
                    text = unit.payload.text if type(unit.payload) is TextPayload else None
                    if text is None:
                        _discard_incoming(continuation_manager, incoming_token)
                        return _failure(
                            ProcessingStatus.EXTRACTION_FAILED,
                            SafeContentErrorCode.RESPONSE_VALIDATION,
                        )
                    size_bytes = len(text.encode("utf-8", "strict"))
                    if (
                        len(chunks) >= budgets.max_chunks_per_invocation
                        or extracted_bytes + size_bytes > budgets.max_extracted_content_bytes
                    ):
                        provenance = unit.provenance
                        assert type(provenance) is SheetsProvenance and provenance.component is not None
                        cursor = _Cursor(
                            window_cursor.sheet_ordinal,
                            window_cursor.sheet,
                            coordinate[0],
                            coordinate[1],
                            provenance.component,
                            provenance.rich_text_run_ordinal,
                            provenance.rich_text_start_utf16,
                        )
                        stop_for_invocation_budget = True
                        break
                    chunks.append(replace(unit, sequence=len(chunks)))
                    extracted_bytes += size_bytes
                if stop_for_invocation_budget or resume_mismatch:
                    break
                logical_cells_completed += 1
                window_cursor = _advance_cursor(metadata, window_cursor)
                cursor = window_cursor
            if resume_mismatch or stop_for_invocation_budget:
                break
            if logical_cells_completed >= budgets.max_sheets_cells_per_file and cursor is not None:
                stop_for_file_limit = True
                break

        if resume_mismatch:
            # Verify the Drive snapshot once more, but never release buffered units.
            postflight_raw = drive_metadata(context, snapshot)
            _discard_incoming(continuation_manager, incoming_token)
            if type(postflight_raw) is _DriveFailure:
                return _drive_failure_result(postflight_raw, preflight=False)
            postflight = postflight_raw
            if postflight != preflight or postflight.trashed:
                return _failure(
                    ProcessingStatus.CHANGED_DURING_AUDIT,
                    SafeContentErrorCode.CHANGED_DURING_AUDIT,
                    stage=FailureStage.POSTFLIGHT_VALIDATION,
                )
            return _failure(
                ProcessingStatus.CHANGED_DURING_AUDIT,
                SafeContentErrorCode.CHANGED_DURING_AUDIT,
            )

        postflight_raw = drive_metadata(context, snapshot)
        if type(postflight_raw) is _DriveFailure:
            _discard_incoming(continuation_manager, incoming_token)
            return _drive_failure_result(postflight_raw, preflight=False)
        postflight = postflight_raw
        if postflight != preflight or postflight.trashed:
            _discard_incoming(continuation_manager, incoming_token)
            return _failure(
                ProcessingStatus.CHANGED_DURING_AUDIT,
                SafeContentErrorCode.CHANGED_DURING_AUDIT,
                stage=FailureStage.POSTFLIGHT_VALIDATION,
            )

        if cursor is not None and stop_for_file_limit:
            if incoming_token is not None:
                _discard_incoming(continuation_manager, incoming_token)
            return _partial_without_token(tuple(chunks), reason="RESOURCE_LIMIT")

        if cursor is not None and stop_for_invocation_budget:
            try:
                state = _next_component_state(
                    snapshot=snapshot,
                    fingerprint=fingerprint,
                    cursor=cursor,
                    logical_cells_completed=logical_cells_completed,
                    coverage_gaps=coverage_gaps,
                )
                token = continuation_manager.issue_sheets(state)
            except ContentSafeError as error:
                _discard_incoming(continuation_manager, incoming_token)
                if error.code == "CONTEXT_LIMIT_EXCEEDED":
                    return _partial_without_token(tuple(chunks), reason="RESOURCE_LIMIT")
                return _failure(
                    ProcessingStatus.EXTRACTION_FAILED,
                    SafeContentErrorCode.RESPONSE_VALIDATION,
                )
            final_chunks = tuple(
                replace(chunk, truncated=(index == len(chunks) - 1), continuation=(token if index == len(chunks) - 1 else None))
                for index, chunk in enumerate(chunks)
            )
            return BoundedReadResult(
                final_chunks,
                ProcessingOutcome(
                    ProcessingStatus.PARTIALLY_PROCESSED,
                    ContentClass.GOOGLE_SHEET,
                    chunk_count=len(final_chunks),
                    result_count=len(final_chunks),
                    truncated=True,
                    partial_reason="INVOCATION_BUDGET",
                    continuation=token,
                ),
            )

        if incoming_token is not None:
            _discard_incoming(continuation_manager, incoming_token)
        final = tuple(chunks)
        if coverage_gaps:
            return _partial_without_token(final, reason="COVERAGE_GAP")
        if not final:
            return BoundedReadResult(
                (),
                ProcessingOutcome(ProcessingStatus.EMPTY, ContentClass.GOOGLE_SHEET),
            )
        return BoundedReadResult(
            final,
            ProcessingOutcome(
                ProcessingStatus.PROCESSED,
                ContentClass.GOOGLE_SHEET,
                chunk_count=len(final),
                result_count=len(final),
            ),
        )

    return read


def _discard_incoming(manager: DocsContinuationManager, token: str | None) -> None:
    if token is None:
        return
    try:
        manager.discard_sheets(token)
    except ContentSafeError:
        pass
