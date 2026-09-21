"""Typed, location-only provenance variants for normalized content."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError


MAX_LOCATION_LENGTH = 256
MAX_INDEX = 50_000_000
MAX_PATH_DEPTH = 64


def _location(value: object) -> str:
    if type(value) is not str or not value or len(value) > MAX_LOCATION_LENGTH:
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_PROVENANCE)
    folded = value.casefold()
    if (
        any(ord(character) < 32 or 0x7F <= ord(character) <= 0x9F for character in value)
        or "://" in value
        or folded.startswith(("http:", "https:", "www.", "drive.google.com/", "www.googleapis.com/"))
    ):
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_PROVENANCE)
    return value


def _index(value: object, *, optional: bool = False) -> int | None:
    if value is None and optional:
        return None
    if isinstance(value, bool) or type(value) is not int or value < 0 or value > MAX_INDEX:
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_PROVENANCE)
    return value


def _location_optional(value: object) -> str | None:
    return None if value is None else _location(value)


def _location_path(value: object) -> tuple[str, ...]:
    if type(value) not in (tuple, list) or len(value) > MAX_PATH_DEPTH:
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_PROVENANCE)
    result = tuple(_location(item) for item in value)
    return result


def _index_path(value: object) -> tuple[int, ...]:
    if type(value) not in (tuple, list) or len(value) > MAX_PATH_DEPTH:
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_PROVENANCE)
    return tuple(_index(item) for item in value)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class DocsProvenance:
    tab_id: str
    structural_segment: str
    text_run_index: int | None = None
    tab_path: tuple[str, ...] = ()
    structural_path: tuple[int, ...] = ()
    segment_id: str | None = None
    start_index: int | None = None
    end_index: int | None = None
    paragraph_index: int | None = None
    table_index: int | None = None
    row: int | None = None
    column: int | None = None
    sub_offset_utf16: int | None = None
    block_role: str | None = None
    list_id: str | None = None
    list_nesting_level: int | None = None
    object_id: str | None = None
    section_index: int | None = None

    def __post_init__(self) -> None:
        if type(self) is not DocsProvenance:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_PROVENANCE)
        _location(self.tab_id)
        _location(self.structural_segment)
        _index(self.text_run_index, optional=True)
        object.__setattr__(self, "tab_path", _location_path(self.tab_path))
        object.__setattr__(self, "structural_path", _index_path(self.structural_path))
        for field_name in ("segment_id", "block_role", "list_id", "object_id"):
            object.__setattr__(self, field_name, _location_optional(getattr(self, field_name)))
        for field_name in (
            "start_index",
            "end_index",
            "paragraph_index",
            "table_index",
            "row",
            "column",
            "sub_offset_utf16",
            "list_nesting_level",
            "section_index",
        ):
            _index(getattr(self, field_name), optional=True)
        if (self.start_index is None) != (self.end_index is None):
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_PROVENANCE)
        if self.start_index is not None and self.end_index is not None and self.end_index < self.start_index:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_PROVENANCE)


@dataclass(frozen=True, slots=True)
class SheetsProvenance:
    sheet_id: str
    range_a1: str
    row: int | None = None
    column: int | None = None

    def __post_init__(self) -> None:
        if type(self) is not SheetsProvenance:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_PROVENANCE)
        _location(self.sheet_id)
        _location(self.range_a1)
        row = _index(self.row, optional=True)
        column = _index(self.column, optional=True)
        if (row is None) != (column is None):
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_PROVENANCE)


@dataclass(frozen=True, slots=True)
class SlidesProvenance:
    slide_id: str
    element_id: str

    def __post_init__(self) -> None:
        if type(self) is not SlidesProvenance:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_PROVENANCE)
        _location(self.slide_id)
        _location(self.element_id)


@dataclass(frozen=True, slots=True)
class PdfProvenance:
    page: int

    def __post_init__(self) -> None:
        if type(self) is not PdfProvenance:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_PROVENANCE)
        page = _index(self.page)
        if page == 0:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_PROVENANCE)


@dataclass(frozen=True, slots=True)
class WordProvenance:
    section: int | None = None
    paragraph: int | None = None
    table: int | None = None

    def __post_init__(self) -> None:
        if type(self) is not WordProvenance:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_PROVENANCE)
        values = (_index(self.section, optional=True), _index(self.paragraph, optional=True), _index(self.table, optional=True))
        if all(value is None for value in values):
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_PROVENANCE)


@dataclass(frozen=True, slots=True)
class ExcelProvenance:
    sheet_id: str
    range_a1: str
    row: int | None = None
    column: int | None = None

    def __post_init__(self) -> None:
        if type(self) is not ExcelProvenance:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_PROVENANCE)
        _location(self.sheet_id)
        _location(self.range_a1)
        row = _index(self.row, optional=True)
        column = _index(self.column, optional=True)
        if (row is None) != (column is None):
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_PROVENANCE)


@dataclass(frozen=True, slots=True)
class PowerPointProvenance:
    slide: int
    element_id: str

    def __post_init__(self) -> None:
        if type(self) is not PowerPointProvenance:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_PROVENANCE)
        slide = _index(self.slide)
        if slide == 0:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_PROVENANCE)
        _location(self.element_id)


@dataclass(frozen=True, slots=True)
class TextProvenance:
    line: int | None = None
    record: int | None = None
    byte_offset: int | None = None

    def __post_init__(self) -> None:
        if type(self) is not TextProvenance:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_PROVENANCE)
        values = (
            _index(self.line, optional=True),
            _index(self.record, optional=True),
            _index(self.byte_offset, optional=True),
        )
        if all(value is None for value in values):
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_PROVENANCE)


Provenance: TypeAlias = (
    DocsProvenance
    | SheetsProvenance
    | SlidesProvenance
    | PdfProvenance
    | WordProvenance
    | ExcelProvenance
    | PowerPointProvenance
    | TextProvenance
)


PROVENANCE_TYPES = (
    DocsProvenance,
    SheetsProvenance,
    SlidesProvenance,
    PdfProvenance,
    WordProvenance,
    ExcelProvenance,
    PowerPointProvenance,
    TextProvenance,
)


def validate_provenance(value: object) -> Provenance:
    if type(value) not in PROVENANCE_TYPES:
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_PROVENANCE)
    return value
