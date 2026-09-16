"""Non-executable-content and fixed dispatch policies."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError
from google_workspace_admin.content.routing import ContentClass


@dataclass(frozen=True, slots=True)
class UntrustedContentPolicy:
    execute_file_content: bool = False
    execute_macros: bool = False
    execute_javascript: bool = False
    execute_formulas: bool = False
    follow_hyperlinks: bool = False
    resolve_external_entities: bool = False
    network_fetch: bool = False
    shell_commands: bool = False
    dynamic_imports: bool = False

    def __post_init__(self) -> None:
        if type(self) is not UntrustedContentPolicy:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_SAFETY)
        if any(
            type(getattr(self, field_name)) is not bool
            for field_name in self.__dataclass_fields__
        ) or any(
            getattr(self, field_name) for field_name in self.__dataclass_fields__
        ):
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_SAFETY)


NEVER_EXECUTE_FILE_CONTENT = True
DEFAULT_UNTRUSTED_CONTENT_POLICY = UntrustedContentPolicy()


class ReaderDispatch(str, Enum):
    GOOGLE_DOCS = "GOOGLE_DOCS"
    GOOGLE_SHEETS = "GOOGLE_SHEETS"
    GOOGLE_SLIDES = "GOOGLE_SLIDES"
    PDF = "PDF"
    MICROSOFT_WORD = "MICROSOFT_WORD"
    MICROSOFT_EXCEL = "MICROSOFT_EXCEL"
    MICROSOFT_POWERPOINT = "MICROSOFT_POWERPOINT"
    TEXT = "TEXT"
    CSV = "CSV"
    JSON = "JSON"
    XML = "XML"
    NONE = "NONE"


_FIXED_DISPATCH = MappingProxyType(
    {
        ContentClass.GOOGLE_DOC: ReaderDispatch.GOOGLE_DOCS,
        ContentClass.GOOGLE_SHEET: ReaderDispatch.GOOGLE_SHEETS,
        ContentClass.GOOGLE_SLIDE: ReaderDispatch.GOOGLE_SLIDES,
        ContentClass.PDF: ReaderDispatch.PDF,
        ContentClass.MICROSOFT_WORD: ReaderDispatch.MICROSOFT_WORD,
        ContentClass.MICROSOFT_EXCEL: ReaderDispatch.MICROSOFT_EXCEL,
        ContentClass.MICROSOFT_POWERPOINT: ReaderDispatch.MICROSOFT_POWERPOINT,
        ContentClass.TEXT: ReaderDispatch.TEXT,
        ContentClass.CSV: ReaderDispatch.CSV,
        ContentClass.JSON: ReaderDispatch.JSON,
        ContentClass.XML: ReaderDispatch.XML,
    }
)


def fixed_reader_dispatch(content_class: object) -> ReaderDispatch:
    if type(content_class) is not ContentClass:
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_SAFETY)
    return _FIXED_DISPATCH.get(content_class, ReaderDispatch.NONE)
