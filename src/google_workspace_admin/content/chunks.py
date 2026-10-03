"""Typed bounded normalized content chunks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import TypeAlias

from google_workspace_admin.content.budgets import MAX_STRUCTURED_CHUNK_BYTES, MAX_TEXT_CHUNK_BYTES
from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError
from google_workspace_admin.content.public_file_ref import is_public_file_ref
from google_workspace_admin.content.provenance import (
    DocsProvenance,
    ExcelProvenance,
    PdfProvenance,
    PowerPointProvenance,
    Provenance,
    SheetsProvenance,
    SlidesProvenance,
    TextProvenance,
    WordProvenance,
    validate_provenance,
)
from google_workspace_admin.content.routing import ContentClass


MAX_FILE_REFERENCE_LENGTH = 256
MAX_SEQUENCE = 1_000_000
MAX_SCALAR_STRING_BYTES = MAX_STRUCTURED_CHUNK_BYTES
MAX_SCALAR_INTEGER = 9_223_372_036_854_775_807


class ContentKind(str, Enum):
    TEXT = "TEXT"
    CELLS = "CELLS"
    RECORDS = "RECORDS"
    STRUCTURED = "STRUCTURED"


def _safe_text(value: object, *, maximum_bytes: int) -> str:
    if type(value) is not str:
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_CHUNK)
    try:
        encoded = value.encode("utf-8")
    except UnicodeError:
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_CHUNK) from None
    if len(encoded) > maximum_bytes:
        raise ContentSafeError(code="CONTEXT_LIMIT_EXCEEDED", operation=ContentErrorOperation.READING_CHUNK)
    return value


@dataclass(frozen=True, slots=True)
class TextPayload:
    text: str

    def __post_init__(self) -> None:
        if type(self) is not TextPayload:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_CHUNK)
        _safe_text(self.text, maximum_bytes=MAX_TEXT_CHUNK_BYTES)


@dataclass(frozen=True, slots=True)
class ScalarValue:
    value: str | int | float | bool | None

    def __post_init__(self) -> None:
        if type(self) is not ScalarValue:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_CHUNK)
        if self.value is not None:
            if type(self.value) is str:
                _safe_text(self.value, maximum_bytes=MAX_SCALAR_STRING_BYTES)
            elif type(self.value) is float and not math.isfinite(self.value):
                raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_CHUNK)
            elif type(self.value) is int and abs(self.value) > MAX_SCALAR_INTEGER:
                raise ContentSafeError(code="CONTEXT_LIMIT_EXCEEDED", operation=ContentErrorOperation.READING_CHUNK)
            elif type(self.value) not in (str, int, float, bool):
                raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_CHUNK)


def _tuple_of(value: object, item_type: type) -> tuple:
    if type(value) not in (tuple, list):
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_CHUNK)
    items = tuple(value)
    if any(type(item) is not item_type for item in items):
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_CHUNK)
    return items


def _payload_bytes(values: tuple[ScalarValue, ...]) -> int:
    total = len(values) * 8
    for value in values:
        scalar = value.value
        if isinstance(scalar, str):
            total += len(scalar.encode("utf-8"))
        else:
            total += 16
    return total


@dataclass(frozen=True, slots=True)
class CellsPayload:
    cells: tuple[ScalarValue, ...]

    def __post_init__(self) -> None:
        if type(self) is not CellsPayload:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_CHUNK)
        cells = _tuple_of(self.cells, ScalarValue)
        if _payload_bytes(cells) > MAX_STRUCTURED_CHUNK_BYTES:
            raise ContentSafeError(code="CONTEXT_LIMIT_EXCEEDED", operation=ContentErrorOperation.READING_CHUNK)
        object.__setattr__(self, "cells", cells)


@dataclass(frozen=True, slots=True)
class RecordPayload:
    values: tuple[ScalarValue, ...]

    def __post_init__(self) -> None:
        if type(self) is not RecordPayload:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_CHUNK)
        values = _tuple_of(self.values, ScalarValue)
        if _payload_bytes(values) > MAX_STRUCTURED_CHUNK_BYTES:
            raise ContentSafeError(code="CONTEXT_LIMIT_EXCEEDED", operation=ContentErrorOperation.READING_CHUNK)
        object.__setattr__(self, "values", values)


@dataclass(frozen=True, slots=True)
class RecordsPayload:
    records: tuple[RecordPayload, ...]

    def __post_init__(self) -> None:
        if type(self) is not RecordsPayload:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_CHUNK)
        records = _tuple_of(self.records, RecordPayload)
        if len(records) * 8 + sum(_payload_bytes(record.values) for record in records) > MAX_STRUCTURED_CHUNK_BYTES:
            raise ContentSafeError(code="CONTEXT_LIMIT_EXCEEDED", operation=ContentErrorOperation.READING_CHUNK)
        object.__setattr__(self, "records", records)


@dataclass(frozen=True, slots=True)
class StructuredField:
    key: str
    value: ScalarValue

    def __post_init__(self) -> None:
        if type(self) is not StructuredField:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_CHUNK)
        if not self.key:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_CHUNK)
        _safe_text(self.key, maximum_bytes=256)
        if any(ord(character) < 32 or 0x7F <= ord(character) <= 0x9F for character in self.key):
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_CHUNK)
        if type(self.value) is not ScalarValue:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_CHUNK)


@dataclass(frozen=True, slots=True)
class StructuredPayload:
    fields: tuple[StructuredField, ...]

    def __post_init__(self) -> None:
        if type(self) is not StructuredPayload:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_CHUNK)
        fields = _tuple_of(self.fields, StructuredField)
        total = len(fields) * 8 + sum(len(field.key.encode("utf-8")) + _payload_bytes((field.value,)) for field in fields)
        if total > MAX_STRUCTURED_CHUNK_BYTES:
            raise ContentSafeError(code="CONTEXT_LIMIT_EXCEEDED", operation=ContentErrorOperation.READING_CHUNK)
        object.__setattr__(self, "fields", fields)


ContentPayload: TypeAlias = TextPayload | CellsPayload | RecordsPayload | StructuredPayload


def _opaque_token(value: object) -> str | None:
    if value is None:
        return None
    if type(value) is not str or not value or len(value) > 4096 or any(character.isspace() or ord(character) < 32 or 0x7F <= ord(character) <= 0x9F for character in value):
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_CHUNK)
    return value


@dataclass(frozen=True, slots=True)
class ContentChunk:
    file_ref: str
    content_class: ContentClass
    sequence: int
    content_kind: ContentKind
    payload: ContentPayload
    provenance: Provenance
    truncated: bool = False
    continuation: str | None = None

    def __post_init__(self) -> None:
        if (
            type(self.file_ref) is not str
            or len(self.file_ref) > MAX_FILE_REFERENCE_LENGTH
            or not is_public_file_ref(self.file_ref)
        ):
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_CHUNK)
        if type(self.content_class) is not ContentClass:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_CHUNK)
        if isinstance(self.sequence, bool) or type(self.sequence) is not int or self.sequence < 0 or self.sequence > MAX_SEQUENCE:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_CHUNK)
        if type(self.content_kind) is not ContentKind or type(self.payload) not in (TextPayload, CellsPayload, RecordsPayload, StructuredPayload):
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_CHUNK)
        expected = {
            ContentKind.TEXT: TextPayload,
            ContentKind.CELLS: CellsPayload,
            ContentKind.RECORDS: RecordsPayload,
            ContentKind.STRUCTURED: StructuredPayload,
        }[self.content_kind]
        if type(self.payload) is not expected:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_CHUNK)
        provenance = validate_provenance(self.provenance)
        expected_provenance = {
            ContentClass.GOOGLE_DOC: DocsProvenance,
            ContentClass.GOOGLE_SHEET: SheetsProvenance,
            ContentClass.GOOGLE_SLIDE: SlidesProvenance,
            ContentClass.PDF: PdfProvenance,
            ContentClass.MICROSOFT_WORD: WordProvenance,
            ContentClass.MICROSOFT_EXCEL: ExcelProvenance,
            ContentClass.MICROSOFT_POWERPOINT: PowerPointProvenance,
            ContentClass.TEXT: TextProvenance,
            ContentClass.CSV: TextProvenance,
            ContentClass.JSON: TextProvenance,
            ContentClass.XML: TextProvenance,
        }.get(self.content_class)
        if expected_provenance is not None and type(provenance) is not expected_provenance:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_CHUNK)
        if type(self.truncated) is not bool:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_CHUNK)
        token = _opaque_token(self.continuation)
        if token is not None and not self.truncated:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_CHUNK)
        object.__setattr__(self, "continuation", token)
