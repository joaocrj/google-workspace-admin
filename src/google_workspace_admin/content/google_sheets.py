"""Strict metadata and bounded-window contracts for native Google Sheets."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping

from google_workspace_admin.content.budgets import (
    DEFAULT_CONTENT_READING_BUDGETS,
    MAX_SHEETS_REQUEST_WINDOW_CELLS,
    MAX_SHEETS_RESPONSE_BYTES,
    MAX_TEXT_CHUNK_BYTES,
)
from google_workspace_admin.content.chunks import ContentChunk, ContentKind, TextPayload
from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError
from google_workspace_admin.content.provenance import (
    SheetsContentComponent,
    SheetsProvenance,
)
from google_workspace_admin.content.routing import ContentClass


_MAX_API_INT = 2_147_483_647
_SHEETS_METADATA_ERROR = ContentErrorOperation.RESPONSE_SHEETS_METADATA
_SHEETS_GRIDDATA_ERROR = ContentErrorOperation.RESPONSE_SHEETS_GRIDDATA


class SheetType(str, Enum):
    GRID = "GRID"
    OBJECT = "OBJECT"
    DATA_SOURCE = "DATA_SOURCE"


class SheetHandling(str, Enum):
    GRIDDATA_ELIGIBLE = "GRIDDATA_ELIGIBLE"
    OBJECT_COVERAGE_GAP = "OBJECT_COVERAGE_GAP"
    DATA_SOURCE_COVERAGE_GAP = "DATA_SOURCE_COVERAGE_GAP"


class SheetsCoverageGap(str, Enum):
    SMART_CHIP = "SMART_CHIP"
    OBJECT_SHEET = "OBJECT_SHEET"
    DATA_SOURCE_SHEET = "DATA_SOURCE_SHEET"


GOOGLE_SHEET_MIME_TYPE = "application/vnd.google-apps.spreadsheet"


@dataclass(frozen=True, slots=True)
class SheetMetadata:
    sheet_id: int
    index: int
    title: str
    hidden: bool
    sheet_type: SheetType
    row_count: int | None
    column_count: int | None

    def __post_init__(self) -> None:
        if type(self) is not SheetMetadata:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.RESPONSE_SHEETS_METADATA)
        _api_int(self.sheet_id, _SHEETS_METADATA_ERROR)
        _api_int(self.index, _SHEETS_METADATA_ERROR)
        _title(self.title, _SHEETS_METADATA_ERROR)
        if type(self.hidden) is not bool or type(self.sheet_type) is not SheetType:
            raise ContentSafeError(code="RESPONSE_VALIDATION", operation=_SHEETS_METADATA_ERROR)
        if self.sheet_type is SheetType.GRID:
            _api_int(self.row_count, _SHEETS_METADATA_ERROR)
            _api_int(self.column_count, _SHEETS_METADATA_ERROR)
        else:
            if self.row_count is not None:
                _api_int(self.row_count, _SHEETS_METADATA_ERROR)
            if self.column_count is not None:
                _api_int(self.column_count, _SHEETS_METADATA_ERROR)

    @property
    def handling(self) -> SheetHandling:
        if self.sheet_type is SheetType.GRID:
            return SheetHandling.GRIDDATA_ELIGIBLE
        if self.sheet_type is SheetType.OBJECT:
            return SheetHandling.OBJECT_COVERAGE_GAP
        return SheetHandling.DATA_SOURCE_COVERAGE_GAP


@dataclass(frozen=True, slots=True)
class WorkbookMetadata:
    sheets: tuple[SheetMetadata, ...]

    def __post_init__(self) -> None:
        if type(self) is not WorkbookMetadata or type(self.sheets) is not tuple:
            raise ContentSafeError(code="RESPONSE_VALIDATION", operation=_SHEETS_METADATA_ERROR)
        if len(self.sheets) > DEFAULT_CONTENT_READING_BUDGETS.max_sheets_tabs:
            raise ContentSafeError(code="TOO_LARGE", operation=_SHEETS_METADATA_ERROR)
        if any(type(sheet) is not SheetMetadata for sheet in self.sheets):
            raise ContentSafeError(code="RESPONSE_VALIDATION", operation=_SHEETS_METADATA_ERROR)
        if tuple(sorted(self.sheets, key=lambda sheet: sheet.index)) != self.sheets:
            raise ContentSafeError(code="RESPONSE_VALIDATION", operation=_SHEETS_METADATA_ERROR)
        if len({sheet.sheet_id for sheet in self.sheets}) != len(self.sheets) or len(
            {sheet.index for sheet in self.sheets}
        ) != len(self.sheets):
            raise ContentSafeError(code="RESPONSE_VALIDATION", operation=_SHEETS_METADATA_ERROR)


@dataclass(frozen=True, slots=True)
class SheetsGridWindow:
    """One row by a bounded column interval, resolved from workbook metadata."""

    sheet: SheetMetadata
    row_start: int
    row_count: int
    column_start: int
    column_count: int

    def __post_init__(self) -> None:
        if type(self) is not SheetsGridWindow or type(self.sheet) is not SheetMetadata:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.SHEETS_GRIDDATA_WINDOW)
        if self.sheet.handling is not SheetHandling.GRIDDATA_ELIGIBLE:
            raise ContentSafeError(code="CONTENT_NOT_SUPPORTED", operation=ContentErrorOperation.SHEETS_GRIDDATA_WINDOW)
        row_start = _api_int(self.row_start, ContentErrorOperation.SHEETS_GRIDDATA_WINDOW)
        row_count = _api_int(self.row_count, ContentErrorOperation.SHEETS_GRIDDATA_WINDOW)
        column_start = _api_int(self.column_start, ContentErrorOperation.SHEETS_GRIDDATA_WINDOW)
        column_count = _api_int(self.column_count, ContentErrorOperation.SHEETS_GRIDDATA_WINDOW)
        if row_count != 1 or not 1 <= column_count <= MAX_SHEETS_REQUEST_WINDOW_CELLS:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.SHEETS_GRIDDATA_WINDOW)
        if self.sheet.row_count is None or self.sheet.column_count is None:
            raise ContentSafeError(code="RESPONSE_VALIDATION", operation=_SHEETS_METADATA_ERROR)
        if row_start >= self.sheet.row_count or column_start >= self.sheet.column_count:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.SHEETS_GRIDDATA_WINDOW)
        if row_count > self.sheet.row_count - row_start:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.SHEETS_GRIDDATA_WINDOW)
        if column_count > self.sheet.column_count - column_start:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.SHEETS_GRIDDATA_WINDOW)
        if row_count * column_count > MAX_SHEETS_REQUEST_WINDOW_CELLS:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.SHEETS_GRIDDATA_WINDOW)


@dataclass(frozen=True, slots=True)
class _SheetsA1Range:
    """A private, typed single-row range; callers never provide A1/URL text."""

    sheet_title: str
    row: int
    column_start: int
    column_count: int

    def __post_init__(self) -> None:
        if type(self) is not _SheetsA1Range:
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.SHEETS_GRIDDATA_WINDOW,
            )
        _title(self.sheet_title, ContentErrorOperation.SHEETS_GRIDDATA_WINDOW)
        row = _api_int(self.row, ContentErrorOperation.SHEETS_GRIDDATA_WINDOW)
        column_start = _api_int(self.column_start, ContentErrorOperation.SHEETS_GRIDDATA_WINDOW)
        column_count = _api_int(self.column_count, ContentErrorOperation.SHEETS_GRIDDATA_WINDOW)
        if (
            row >= _MAX_API_INT
            or not 1 <= column_count <= MAX_SHEETS_REQUEST_WINDOW_CELLS
            or column_count - 1 > _MAX_API_INT - column_start
        ):
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.SHEETS_GRIDDATA_WINDOW,
            )


@dataclass(frozen=True, slots=True)
class GridDataEnvelope:
    sheet_id: int
    sheet_index: int
    start_row: int
    start_column: int
    returned_rows: int
    returned_cells: int
    cells: tuple["SheetsGridCell", ...] = field(default=(), repr=False)
    coverage_gaps: tuple[SheetsCoverageGap, ...] = ()

    def __post_init__(self) -> None:
        for value in (
            self.sheet_id,
            self.sheet_index,
            self.start_row,
            self.start_column,
            self.returned_rows,
            self.returned_cells,
        ):
            _api_int(value, _SHEETS_GRIDDATA_ERROR)
        if (
            self.returned_rows > 1
            or self.returned_cells > MAX_SHEETS_REQUEST_WINDOW_CELLS
            or (self.returned_rows == 0 and self.returned_cells != 0)
            or type(self.cells) is not tuple
            or len(self.cells) != self.returned_cells
            or any(type(cell) is not SheetsGridCell for cell in self.cells)
            or type(self.coverage_gaps) is not tuple
            or any(type(gap) is not SheetsCoverageGap for gap in self.coverage_gaps)
            or len(set(self.coverage_gaps)) != len(self.coverage_gaps)
        ):
            raise _invalid(_SHEETS_GRIDDATA_ERROR)
        expected_gaps = (
            (SheetsCoverageGap.SMART_CHIP,)
            if any(cell.has_unsupported_smart_chip for cell in self.cells)
            else ()
        )
        if self.coverage_gaps != expected_gaps:
            raise _invalid(_SHEETS_GRIDDATA_ERROR)


@dataclass(frozen=True, slots=True)
class SheetsTextFormatRun:
    ordinal: int
    start_index: int
    end_index: int
    link_uri: str | None = field(repr=False)

    def __post_init__(self) -> None:
        for value in (self.ordinal, self.start_index, self.end_index):
            _api_int(value, _SHEETS_GRIDDATA_ERROR)
        if self.end_index <= self.start_index or (
            self.link_uri is not None and type(self.link_uri) is not str
        ):
            raise _invalid(_SHEETS_GRIDDATA_ERROR)


@dataclass(frozen=True, slots=True)
class SheetsGridCell:
    row: int
    column: int
    formula_value: str | None = field(default=None, repr=False)
    formatted_value: str | None = field(default=None, repr=False)
    note: str | None = field(default=None, repr=False)
    hyperlink: str | None = field(default=None, repr=False)
    text_format_runs: tuple[SheetsTextFormatRun, ...] = field(default=(), repr=False)
    has_unsupported_smart_chip: bool = False

    def __post_init__(self) -> None:
        _api_int(self.row, _SHEETS_GRIDDATA_ERROR)
        _api_int(self.column, _SHEETS_GRIDDATA_ERROR)
        for value in (
            self.formula_value,
            self.formatted_value,
            self.note,
            self.hyperlink,
        ):
            if value is not None and type(value) is not str:
                raise _invalid(_SHEETS_GRIDDATA_ERROR)
        if type(self.text_format_runs) is not tuple or any(
            type(run) is not SheetsTextFormatRun for run in self.text_format_runs
        ):
            raise _invalid(_SHEETS_GRIDDATA_ERROR)
        if type(self.has_unsupported_smart_chip) is not bool:
            raise _invalid(_SHEETS_GRIDDATA_ERROR)
        for value in (self.formula_value, self.formatted_value, self.note, self.hyperlink):
            if value is not None:
                _cell_text(value, allow_empty=True, maximum_bytes=MAX_SHEETS_RESPONSE_BYTES)
        previous_start = -1
        for ordinal, run in enumerate(self.text_format_runs):
            if run.ordinal != ordinal or run.start_index <= previous_start:
                raise _invalid(_SHEETS_GRIDDATA_ERROR)
            previous_start = run.start_index
            if run.link_uri is not None:
                _cell_text(run.link_uri, allow_empty=True, maximum_bytes=MAX_TEXT_CHUNK_BYTES)


@dataclass(frozen=True, slots=True)
class SheetsGridExtraction:
    """Independent cell-component content units from one validated window."""

    units: tuple[ContentChunk, ...] = field(repr=False)
    coverage_gaps: tuple[SheetsCoverageGap, ...]

    def __post_init__(self) -> None:
        if type(self.units) is not tuple or any(type(unit) is not ContentChunk for unit in self.units):
            raise _invalid(_SHEETS_GRIDDATA_ERROR)
        if type(self.coverage_gaps) is not tuple or any(
            type(gap) is not SheetsCoverageGap for gap in self.coverage_gaps
        ) or len(set(self.coverage_gaps)) != len(self.coverage_gaps):
            raise _invalid(_SHEETS_GRIDDATA_ERROR)


def _invalid(operation: ContentErrorOperation) -> ContentSafeError:
    return ContentSafeError(code="RESPONSE_VALIDATION", operation=operation)


def _api_int(
    value: object,
    operation: ContentErrorOperation,
) -> int:
    if type(value) is not int or value < 0 or value > _MAX_API_INT:
        raise ContentSafeError(code="RESPONSE_VALIDATION", operation=operation)
    return value


def _title(value: object, operation: ContentErrorOperation) -> str:
    if type(value) is not str or not value or len(value) > 100:
        raise ContentSafeError(code="RESPONSE_VALIDATION", operation=operation)
    try:
        value.encode("utf-8", "strict")
    except UnicodeEncodeError:
        raise ContentSafeError(code="RESPONSE_VALIDATION", operation=operation) from None
    if any(ord(character) < 32 or 0x7F <= ord(character) <= 0x9F for character in value):
        raise ContentSafeError(code="RESPONSE_VALIDATION", operation=operation)
    return value


def _mapping(value: object, operation: ContentErrorOperation) -> Mapping[str, object]:
    if type(value) is not dict:
        raise _invalid(operation)
    return value


def _closed_mapping(
    value: object,
    *,
    allowed: frozenset[str],
    operation: ContentErrorOperation,
) -> Mapping[str, object]:
    mapping = _mapping(value, operation)
    if set(mapping) - allowed:
        raise _invalid(operation)
    return mapping


def _cell_text(
    value: object,
    *,
    allow_empty: bool,
    maximum_bytes: int,
) -> str:
    """Validate source text without changing any whitespace or formatting."""

    if type(value) is not str:
        raise _invalid(_SHEETS_GRIDDATA_ERROR)
    if not allow_empty and not value:
        raise _invalid(_SHEETS_GRIDDATA_ERROR)
    try:
        encoded = value.encode("utf-8", "strict")
    except UnicodeEncodeError:
        raise _invalid(_SHEETS_GRIDDATA_ERROR) from None
    if len(encoded) > maximum_bytes:
        raise ContentSafeError(code="TOO_LARGE", operation=_SHEETS_GRIDDATA_ERROR)
    for character in value:
        code_point = ord(character)
        if (code_point < 32 and character not in "\t\r\n") or 0x7F <= code_point <= 0x9F:
            raise _invalid(_SHEETS_GRIDDATA_ERROR)
    return value


def utf16_code_unit_length(value: str) -> int:
    if type(value) is not str:
        raise _invalid(_SHEETS_GRIDDATA_ERROR)
    try:
        return len(value.encode("utf-16-le", "strict")) // 2
    except UnicodeEncodeError:
        raise _invalid(_SHEETS_GRIDDATA_ERROR) from None


def _utf16_run_extent(value: str) -> tuple[int, frozenset[int]]:
    if type(value) is not str:
        raise _invalid(_SHEETS_GRIDDATA_ERROR)
    offsets: set[int] = set()
    position = 0
    try:
        for character in value:
            offsets.add(position)
            position += len(character.encode("utf-16-le", "strict")) // 2
    except UnicodeEncodeError:
        raise _invalid(_SHEETS_GRIDDATA_ERROR) from None
    offsets.add(position)
    return position, frozenset(offsets)


def _validate_effective_value(value: object) -> None:
    if value is None:
        raise _invalid(_SHEETS_GRIDDATA_ERROR)
    effective = _closed_mapping(
        value,
        allowed=frozenset({"errorValue"}),
        operation=_SHEETS_GRIDDATA_ERROR,
    )
    if not effective:
        return
    error_value = _closed_mapping(
        effective.get("errorValue"),
        allowed=frozenset({"type"}),
        operation=_SHEETS_GRIDDATA_ERROR,
    )
    error_type = error_value.get("type")
    if type(error_type) is not str or error_type not in {
        "ERROR",
        "NULL_VALUE",
        "DIVIDE_BY_ZERO",
        "VALUE",
        "REF",
        "NAME",
        "NUM",
        "N_A",
        "LOADING",
    }:
        raise _invalid(_SHEETS_GRIDDATA_ERROR)


def _parse_user_entered_value(value: object) -> tuple[str | None, str | None]:
    if value is None:
        raise _invalid(_SHEETS_GRIDDATA_ERROR)
    entered = _mapping(value, _SHEETS_GRIDDATA_ERROR)
    if len(entered) != 1:
        raise _invalid(_SHEETS_GRIDDATA_ERROR)
    branch, raw_value = next(iter(entered.items()))
    if branch == "stringValue":
        return (
            _cell_text(
                raw_value,
                allow_empty=True,
                maximum_bytes=MAX_SHEETS_RESPONSE_BYTES,
            ),
            None,
        )
    if branch == "formulaValue":
        return (
            None,
            _cell_text(
                raw_value,
                allow_empty=True,
                maximum_bytes=MAX_TEXT_CHUNK_BYTES,
            ),
        )
    if branch == "numberValue":
        if type(raw_value) not in (int, float) or (
            type(raw_value) is float and not math.isfinite(raw_value)
        ):
            raise _invalid(_SHEETS_GRIDDATA_ERROR)
        return None, None
    if branch == "boolValue":
        if type(raw_value) is not bool:
            raise _invalid(_SHEETS_GRIDDATA_ERROR)
        return None, None
    raise _invalid(_SHEETS_GRIDDATA_ERROR)


def _parse_text_format_runs(
    value: object,
    *,
    source_text: str | None,
) -> tuple[SheetsTextFormatRun, ...]:
    if value is None:
        raise _invalid(_SHEETS_GRIDDATA_ERROR)
    if type(value) is not list:
        raise _invalid(_SHEETS_GRIDDATA_ERROR)
    if value and source_text is None:
        raise _invalid(_SHEETS_GRIDDATA_ERROR)
    extent, valid_offsets = (0, frozenset()) if source_text is None else _utf16_run_extent(source_text)
    parsed: list[tuple[int, str | None]] = []
    previous_start = -1
    for ordinal, raw_run in enumerate(value):
        run = _closed_mapping(
            raw_run,
            allowed=frozenset({"startIndex", "format"}),
            operation=_SHEETS_GRIDDATA_ERROR,
        )
        if "startIndex" in run:
            start_index = _api_int(run["startIndex"], _SHEETS_GRIDDATA_ERROR)
        elif ordinal == 0:
            # Sheets omits the default UTF-16 zero offset on the first run.
            start_index = 0
        else:
            raise _invalid(_SHEETS_GRIDDATA_ERROR)
        if (
            start_index >= extent
            or start_index not in valid_offsets
            or start_index <= previous_start
        ):
            raise _invalid(_SHEETS_GRIDDATA_ERROR)
        previous_start = start_index
        link_uri: str | None = None
        if "format" in run:
            text_format = _closed_mapping(
                run["format"],
                allowed=frozenset({"link"}),
                operation=_SHEETS_GRIDDATA_ERROR,
            )
            if "link" in text_format:
                link = _closed_mapping(
                    text_format["link"],
                    allowed=frozenset({"uri"}),
                    operation=_SHEETS_GRIDDATA_ERROR,
                )
                link_uri = _cell_text(
                    link.get("uri"),
                    allow_empty=True,
                    maximum_bytes=MAX_TEXT_CHUNK_BYTES,
                )
        parsed.append((start_index, link_uri))

    return tuple(
        SheetsTextFormatRun(
            ordinal=ordinal,
            start_index=start_index,
            end_index=parsed[ordinal + 1][0] if ordinal + 1 < len(parsed) else extent,
            link_uri=link_uri,
        )
        for ordinal, (start_index, link_uri) in enumerate(parsed)
    )


def _parse_chip_runs(value: object, *, source_text: str | None) -> bool:
    if value is None or type(value) is not list:
        raise _invalid(_SHEETS_GRIDDATA_ERROR)
    if value and source_text is None:
        raise _invalid(_SHEETS_GRIDDATA_ERROR)
    extent, valid_offsets = (0, frozenset()) if source_text is None else _utf16_run_extent(source_text)
    previous_start = -1
    has_chip = False
    for ordinal, raw_run in enumerate(value):
        run = _closed_mapping(
            raw_run,
            allowed=frozenset({"startIndex", "chip"}),
            operation=_SHEETS_GRIDDATA_ERROR,
        )
        # The official chips guide omits the first run's default-zero index.
        start_index = _api_int(
            run.get("startIndex", 0 if ordinal == 0 else None),
            _SHEETS_GRIDDATA_ERROR,
        )
        if (
            start_index >= extent
            or start_index not in valid_offsets
            or start_index <= previous_start
        ):
            raise _invalid(_SHEETS_GRIDDATA_ERROR)
        previous_start = start_index
        if "chip" not in run:
            continue

        chip = _mapping(run["chip"], _SHEETS_GRIDDATA_ERROR)
        branches = set(chip)
        if len(branches) != 1 or not branches <= {"personProperties", "richLinkProperties"}:
            raise _invalid(_SHEETS_GRIDDATA_ERROR)
        branch = next(iter(branches))
        identifying_field = "email" if branch == "personProperties" else "uri"
        properties = _closed_mapping(
            chip[branch],
            allowed=frozenset({identifying_field}),
            operation=_SHEETS_GRIDDATA_ERROR,
        )
        identifier = properties.get(identifying_field)
        if type(identifier) is not str or not identifier:
            raise _invalid(_SHEETS_GRIDDATA_ERROR)
        try:
            identifier.encode("utf-8", "strict")
        except UnicodeEncodeError:
            raise _invalid(_SHEETS_GRIDDATA_ERROR) from None
        if any(ord(character) < 32 or 0x7F <= ord(character) <= 0x9F for character in identifier):
            raise _invalid(_SHEETS_GRIDDATA_ERROR)
        # Keep only the safe coverage signal; never retain email or URI.
        has_chip = True
    return has_chip


def _parse_grid_cell(
    value: object,
    *,
    row: int,
    column: int,
) -> SheetsGridCell:
    cell = _closed_mapping(
        value,
        allowed=frozenset(
            {
                "userEnteredValue",
                "effectiveValue",
                "formattedValue",
                "note",
                "hyperlink",
                "textFormatRuns",
                "chipRuns",
            }
        ),
        operation=_SHEETS_GRIDDATA_ERROR,
    )
    source_text: str | None = None
    formula: str | None = None
    if "userEnteredValue" in cell:
        source_text, formula = _parse_user_entered_value(cell["userEnteredValue"])
    if "effectiveValue" in cell:
        _validate_effective_value(cell["effectiveValue"])

    formatted = (
        _cell_text(
            cell["formattedValue"],
            allow_empty=True,
            maximum_bytes=MAX_TEXT_CHUNK_BYTES,
        )
        if "formattedValue" in cell
        else None
    )
    note = (
        _cell_text(
            cell["note"],
            allow_empty=True,
            maximum_bytes=MAX_TEXT_CHUNK_BYTES,
        )
        if "note" in cell
        else None
    )
    hyperlink = (
        _cell_text(
            cell["hyperlink"],
            allow_empty=True,
            maximum_bytes=MAX_TEXT_CHUNK_BYTES,
        )
        if "hyperlink" in cell
        else None
    )
    text_runs = (
        _parse_text_format_runs(cell["textFormatRuns"], source_text=source_text)
        if "textFormatRuns" in cell
        else ()
    )
    has_chip = (
        _parse_chip_runs(cell["chipRuns"], source_text=source_text)
        if "chipRuns" in cell
        else False
    )
    return SheetsGridCell(
        row=row,
        column=column,
        formula_value=formula,
        formatted_value=formatted,
        note=note,
        hyperlink=hyperlink,
        text_format_runs=text_runs,
        has_unsupported_smart_chip=has_chip,
    )


def _parse_optional_grid_dimensions(
    properties: Mapping[str, object],
    *,
    required: bool,
) -> tuple[int | None, int | None]:
    grid = properties.get("gridProperties")
    if grid is None:
        if required:
            raise _invalid(_SHEETS_METADATA_ERROR)
        return None, None
    grid_properties = _mapping(grid, _SHEETS_METADATA_ERROR)
    rows = grid_properties.get("rowCount")
    columns = grid_properties.get("columnCount")
    if required and ("rowCount" not in grid_properties or "columnCount" not in grid_properties):
        raise _invalid(_SHEETS_METADATA_ERROR)
    if rows is not None:
        rows = _api_int(rows, _SHEETS_METADATA_ERROR)
    if columns is not None:
        columns = _api_int(columns, _SHEETS_METADATA_ERROR)
    return rows, columns


def parse_workbook_metadata(payload: object) -> WorkbookMetadata:
    """Validate the masked workbook metadata and preserve API sheet order."""

    workbook = _mapping(payload, _SHEETS_METADATA_ERROR)
    raw_sheets = workbook.get("sheets")
    if type(raw_sheets) is not list:
        raise _invalid(_SHEETS_METADATA_ERROR)
    if len(raw_sheets) > DEFAULT_CONTENT_READING_BUDGETS.max_sheets_tabs:
        raise ContentSafeError(code="TOO_LARGE", operation=_SHEETS_METADATA_ERROR)

    sheets: list[SheetMetadata] = []
    seen_ids: set[int] = set()
    seen_indexes: set[int] = set()
    for raw_sheet in raw_sheets:
        sheet = _mapping(raw_sheet, _SHEETS_METADATA_ERROR)
        properties = _mapping(sheet.get("properties"), _SHEETS_METADATA_ERROR)
        sheet_id = _api_int(properties.get("sheetId"), _SHEETS_METADATA_ERROR)
        index = _api_int(properties.get("index"), _SHEETS_METADATA_ERROR)
        title = _title(properties.get("title"), _SHEETS_METADATA_ERROR)
        hidden = properties.get("hidden", False)
        if type(hidden) is not bool:
            raise _invalid(_SHEETS_METADATA_ERROR)
        raw_type = properties.get("sheetType")
        if type(raw_type) is not str:
            raise _invalid(_SHEETS_METADATA_ERROR)
        try:
            sheet_type = SheetType(raw_type)
        except ValueError:
            raise _invalid(_SHEETS_METADATA_ERROR) from None
        row_count, column_count = _parse_optional_grid_dimensions(
            properties,
            required=sheet_type is SheetType.GRID,
        )
        if sheet_type is SheetType.GRID and (row_count is None or column_count is None):
            raise _invalid(_SHEETS_METADATA_ERROR)
        if sheet_id in seen_ids or index in seen_indexes:
            raise _invalid(_SHEETS_METADATA_ERROR)
        seen_ids.add(sheet_id)
        seen_indexes.add(index)
        sheets.append(
            SheetMetadata(
                sheet_id=sheet_id,
                index=index,
                title=title,
                hidden=hidden,
                sheet_type=sheet_type,
                row_count=row_count,
                column_count=column_count,
            )
        )

    sheets.sort(key=lambda item: item.index)
    return WorkbookMetadata(tuple(sheets))


def zero_based_column_to_a1(column_index: int) -> str:
    """Convert one zero-based column index into canonical A1 letters."""

    remaining = _api_int(column_index, ContentErrorOperation.SHEETS_GRIDDATA_WINDOW)
    letters: list[str] = []
    while True:
        remaining, remainder = divmod(remaining, 26)
        letters.append(chr(ord("A") + remainder))
        if remaining == 0:
            break
        remaining -= 1
    return "".join(reversed(letters))


def cell_to_a1(row_index: int, column_index: int) -> str:
    """Return a title-free A1 coordinate from zero-based typed indexes."""

    row = _api_int(row_index, ContentErrorOperation.SHEETS_GRIDDATA_WINDOW)
    column = _api_int(column_index, ContentErrorOperation.SHEETS_GRIDDATA_WINDOW)
    if row >= _MAX_API_INT:
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.SHEETS_GRIDDATA_WINDOW)
    return f"{zero_based_column_to_a1(column)}{row + 1}"


def window_to_a1_range(window: SheetsGridWindow) -> str:
    """Generate a quoted, escaped single-row A1 range from typed coordinates."""

    if type(window) is not SheetsGridWindow:
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.SHEETS_GRIDDATA_WINDOW)
    return _sheets_a1_range_to_a1_range(
        _SheetsA1Range(
            window.sheet.title,
            window.row_start,
            window.column_start,
            window.column_count,
        )
    )


def _sheets_a1_range_to_a1_range(a1_range: _SheetsA1Range) -> str:
    """Format only the internal typed coordinate model using one A1 path."""

    if type(a1_range) is not _SheetsA1Range:
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.SHEETS_GRIDDATA_WINDOW,
        )
    escaped_title = a1_range.sheet_title.replace("'", "''")
    start_column = zero_based_column_to_a1(a1_range.column_start)
    end_column = zero_based_column_to_a1(a1_range.column_start + a1_range.column_count - 1)
    row_number = a1_range.row + 1
    return f"'{escaped_title}'!{start_column}{row_number}:{end_column}{row_number}"


def _grid_origin(
    data: Mapping[str, object],
    key: str,
    expected: int,
) -> int:
    """Read an optional GridData origin without weakening strict validation.

    Google omits zero-valued startRow/startColumn fields for responses whose
    requested origin is zero.  An omitted field therefore has one narrow
    meaning: the semantic value is zero.  Nonzero origins still require an
    explicit, typed value and every present value must remain bounded and exact.
    """

    if key not in data:
        if expected == 0:
            return 0
        raise _invalid(_SHEETS_GRIDDATA_ERROR)
    return _api_int(data[key], _SHEETS_GRIDDATA_ERROR)


def parse_griddata_envelope(
    payload: object,
    *,
    window: SheetsGridWindow,
) -> GridDataEnvelope:
    """Validate a bounded window and retain only typed, inert cell components."""

    if type(window) is not SheetsGridWindow:
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.SHEETS_GRIDDATA_WINDOW)
    workbook = _closed_mapping(
        payload,
        allowed=frozenset({"sheets"}),
        operation=_SHEETS_GRIDDATA_ERROR,
    )
    raw_sheets = workbook.get("sheets")
    if type(raw_sheets) is not list or len(raw_sheets) != 1:
        raise _invalid(_SHEETS_GRIDDATA_ERROR)
    sheet = _closed_mapping(
        raw_sheets[0],
        allowed=frozenset({"properties", "data"}),
        operation=_SHEETS_GRIDDATA_ERROR,
    )
    properties = _closed_mapping(
        sheet.get("properties"),
        allowed=frozenset({"sheetId", "index", "sheetType"}),
        operation=_SHEETS_GRIDDATA_ERROR,
    )
    sheet_id = _api_int(properties.get("sheetId"), _SHEETS_GRIDDATA_ERROR)
    sheet_index = _api_int(properties.get("index"), _SHEETS_GRIDDATA_ERROR)
    if sheet_id != window.sheet.sheet_id or sheet_index != window.sheet.index:
        raise _invalid(_SHEETS_GRIDDATA_ERROR)
    if properties.get("sheetType") != SheetType.GRID.value:
        raise _invalid(_SHEETS_GRIDDATA_ERROR)

    raw_data = sheet.get("data")
    if type(raw_data) is not list or len(raw_data) > 1:
        raise _invalid(_SHEETS_GRIDDATA_ERROR)
    if not raw_data:
        return GridDataEnvelope(
            sheet_id=sheet_id,
            sheet_index=sheet_index,
            start_row=window.row_start,
            start_column=window.column_start,
            returned_rows=0,
            returned_cells=0,
        )

    data = _closed_mapping(
        raw_data[0],
        allowed=frozenset({"startRow", "startColumn", "rowData"}),
        operation=_SHEETS_GRIDDATA_ERROR,
    )
    start_row = _grid_origin(data, "startRow", window.row_start)
    start_column = _grid_origin(data, "startColumn", window.column_start)
    if start_row != window.row_start or start_column != window.column_start:
        raise _invalid(_SHEETS_GRIDDATA_ERROR)
    row_data = data.get("rowData", [])
    if type(row_data) is not list or len(row_data) > window.row_count:
        raise _invalid(_SHEETS_GRIDDATA_ERROR)

    returned_cells = 0
    cells: list[SheetsGridCell] = []
    for row_offset, raw_row in enumerate(row_data):
        row = _closed_mapping(
            raw_row,
            allowed=frozenset({"values"}),
            operation=_SHEETS_GRIDDATA_ERROR,
        )
        values = row.get("values", [])
        if type(values) is not list or len(values) > window.column_count:
            raise _invalid(_SHEETS_GRIDDATA_ERROR)
        returned_cells += len(values)
        absolute_row = _api_int(start_row + row_offset, _SHEETS_GRIDDATA_ERROR)
        if window.sheet.row_count is None or absolute_row >= window.sheet.row_count:
            raise _invalid(_SHEETS_GRIDDATA_ERROR)
        for column_offset, value in enumerate(values):
            absolute_column = _api_int(start_column + column_offset, _SHEETS_GRIDDATA_ERROR)
            if window.sheet.column_count is None or absolute_column >= window.sheet.column_count:
                raise _invalid(_SHEETS_GRIDDATA_ERROR)
            cells.append(
                _parse_grid_cell(
                    value,
                    row=absolute_row,
                    column=absolute_column,
                )
            )
    if returned_cells > MAX_SHEETS_REQUEST_WINDOW_CELLS:
        raise _invalid(_SHEETS_GRIDDATA_ERROR)
    return GridDataEnvelope(
        sheet_id=sheet_id,
        sheet_index=sheet_index,
        start_row=start_row,
        start_column=start_column,
        returned_rows=len(row_data),
        returned_cells=returned_cells,
        cells=tuple(cells),
        coverage_gaps=(
            (SheetsCoverageGap.SMART_CHIP,)
            if any(cell.has_unsupported_smart_chip for cell in cells)
            else ()
        ),
    )


def extract_griddata_content(
    envelope: GridDataEnvelope,
    *,
    window: SheetsGridWindow,
    file_ref: str,
) -> SheetsGridExtraction:
    """Create one independent text chunk per nonempty cell component."""

    if type(envelope) is not GridDataEnvelope or type(window) is not SheetsGridWindow:
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.SHEETS_GRIDDATA_WINDOW)
    if (
        _api_int(envelope.sheet_id, _SHEETS_GRIDDATA_ERROR) != window.sheet.sheet_id
        or _api_int(envelope.sheet_index, _SHEETS_GRIDDATA_ERROR) != window.sheet.index
        or _api_int(envelope.start_row, _SHEETS_GRIDDATA_ERROR) != window.row_start
        or _api_int(envelope.start_column, _SHEETS_GRIDDATA_ERROR) != window.column_start
        or _api_int(envelope.returned_rows, _SHEETS_GRIDDATA_ERROR) > window.row_count
        or _api_int(envelope.returned_cells, _SHEETS_GRIDDATA_ERROR)
        > window.row_count * window.column_count
        or type(envelope.cells) is not tuple
        or len(envelope.cells) != envelope.returned_cells
    ):
        raise _invalid(_SHEETS_GRIDDATA_ERROR)

    units: list[ContentChunk] = []
    previous_coordinate: tuple[int, int] | None = None
    for cell in envelope.cells:
        if type(cell) is not SheetsGridCell:
            raise _invalid(_SHEETS_GRIDDATA_ERROR)
        coordinate = (cell.row, cell.column)
        if (
            not window.row_start <= cell.row < window.row_start + window.row_count
            or not window.column_start <= cell.column < window.column_start + window.column_count
            or (previous_coordinate is not None and coordinate <= previous_coordinate)
        ):
            raise _invalid(_SHEETS_GRIDDATA_ERROR)
        previous_coordinate = coordinate

        components: list[
            tuple[SheetsContentComponent, str | None, SheetsTextFormatRun | None]
        ] = [
            (SheetsContentComponent.CELL_DISPLAY, cell.formatted_value, None),
            (SheetsContentComponent.CELL_FORMULA, cell.formula_value, None),
            (SheetsContentComponent.CELL_NOTE, cell.note, None),
            (SheetsContentComponent.CELL_HYPERLINK, cell.hyperlink, None),
        ]
        components.extend(
            (SheetsContentComponent.CELL_RICH_TEXT_LINK, run.link_uri, run)
            for run in cell.text_format_runs
        )
        for component, text, run in components:
            if text is None or text == "":
                continue
            text = _cell_text(
                text,
                allow_empty=False,
                maximum_bytes=MAX_TEXT_CHUNK_BYTES,
            )
            if len(units) >= 1_000_000:
                raise ContentSafeError(code="TOO_LARGE", operation=_SHEETS_GRIDDATA_ERROR)
            try:
                provenance = SheetsProvenance(
                    sheet_id=str(window.sheet.sheet_id),
                    range_a1=cell_to_a1(cell.row, cell.column),
                    row=cell.row,
                    column=cell.column,
                    sheet_index=window.sheet.index,
                    sheet_title=window.sheet.title,
                    component=component,
                    rich_text_run_ordinal=None if run is None else run.ordinal,
                    rich_text_start_utf16=None if run is None else run.start_index,
                    rich_text_end_utf16=None if run is None else run.end_index,
                )
                units.append(
                    ContentChunk(
                        file_ref=file_ref,
                        content_class=ContentClass.GOOGLE_SHEET,
                        sequence=len(units),
                        content_kind=ContentKind.TEXT,
                        payload=TextPayload(text),
                        provenance=provenance,
                    )
                )
            except ContentSafeError:
                raise ContentSafeError(
                    code="RESPONSE_VALIDATION",
                    operation=_SHEETS_GRIDDATA_ERROR,
                ) from None

    gaps = tuple(
        gap
        for gap in SheetsCoverageGap
        if gap in envelope.coverage_gaps
    )
    if any(type(gap) is not SheetsCoverageGap for gap in envelope.coverage_gaps):
        raise _invalid(_SHEETS_GRIDDATA_ERROR)
    return SheetsGridExtraction(tuple(units), gaps)
