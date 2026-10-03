"""Validated Google Docs DTO extraction and deterministic local chunking."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, replace
from typing import Iterator, Literal

from google_workspace_admin.content.budgets import ContentReadingBudgets
from google_workspace_admin.content.chunks import ContentChunk, ContentKind, TextPayload
from google_workspace_admin.content.continuation import (
    DocsContinuationManager,
    DocsContinuationState,
)
from google_workspace_admin.content.errors import (
    ContentErrorOperation,
    ContentSafeError,
    FailureStage,
    ParagraphFailureKind,
    StructuralFailureKind,
)
from google_workspace_admin.content.inventory import InventorySnapshot
from google_workspace_admin.content.outcomes import (
    ProcessingOutcome,
    ProcessingStatus,
    SafeContentErrorCode,
)
from google_workspace_admin.content.provenance import DocsProvenance
from google_workspace_admin.content.readers import BoundedReadResult, MAX_STRUCTURAL_LOCATIONS
from google_workspace_admin.content.routing import ContentClass


GOOGLE_DOC_MIME_TYPE = "application/vnd.google-apps.document"
GOOGLE_DOCS_READER_VERSION = 1
DOCS_RESPONSE_FIELDS = "documentId,revisionId,suggestionsViewMode,tabs"


# Private, opt-in scaffolding for value-free structural response diagnostics.
# It is intentionally not part of any result, audit, logger, or MCP schema.
_PARAGRAPH_ELEMENT_UNION_MEMBERS = (
    "textRun",
    "autoText",
    "pageBreak",
    "columnBreak",
    "footnoteReference",
    "horizontalRule",
    "equation",
    "inlineObjectElement",
    "person",
    "richLink",
    "dateElement",
)
_PARAGRAPH_ELEMENT_METADATA_FIELDS = ("startIndex", "endIndex")
_ELEMENT_VALUE_TYPES = frozenset(
    {
        "ABSENT",
        "NULL",
        "MAPPING",
        "LIST",
        "STRING",
        "INTEGER",
        "BOOLEAN",
        "FLOAT",
        "OTHER_SCALAR",
    }
)
_ELEMENT_STRING_FAILURE_REASONS = frozenset(
    {
        "MAXIMUM_EXCEEDED",
        "UTF8_ENCODING_INVALID",
        "DISALLOWED_C0_OR_C1_CONTROL",
    }
)
_ElementStringFailureReason = Literal[
    "MAXIMUM_EXCEEDED",
    "UTF8_ENCODING_INVALID",
    "DISALLOWED_C0_OR_C1_CONTROL",
]
_ElementStringFailureRecorder = Callable[
    [_ElementStringFailureReason], None
]
_ELEMENT_STRUCTURE_BRANCHES = frozenset(
    {
        "UNION_SELECTION_NO_RECOGNIZED_MEMBER",
        "UNION_SELECTION_MULTIPLE_RECOGNIZED_MEMBERS",
        "TEXT_RUN_PAYLOAD_NOT_MAPPING",
        "TEXT_RUN_CONTENT_INVALID",
        "TEXT_RUN_INDEX_LENGTH_MISMATCH",
        "FOOTNOTE_REFERENCE_PAYLOAD_NOT_MAPPING",
        "FOOTNOTE_REFERENCE_NUMBER_INVALID",
        "EQUATION_PAYLOAD_NOT_MAPPING",
        "INLINE_OBJECT_PAYLOAD_NOT_MAPPING",
        "INLINE_OBJECT_ID_INVALID",
        "INLINE_OBJECT_REFERENCE_MISSING",
        "INLINE_OBJECT_DEFINITION_NOT_MAPPING",
        "INLINE_OBJECT_PROPERTIES_NOT_MAPPING",
        "INLINE_OBJECT_EMBEDDED_OBJECT_NOT_MAPPING",
        "INLINE_OBJECT_VISIBLE_FIELD_INVALID",
        "PERSON_PAYLOAD_NOT_MAPPING",
        "PERSON_PROPERTIES_NOT_MAPPING",
        "PERSON_VISIBLE_FIELD_INVALID",
        "RICH_LINK_PAYLOAD_NOT_MAPPING",
        "RICH_LINK_PROPERTIES_NOT_MAPPING",
        "RICH_LINK_TITLE_INVALID",
        "DATE_ELEMENT_PAYLOAD_NOT_MAPPING",
        "DATE_ELEMENT_PROPERTIES_NOT_MAPPING",
        "DATE_ELEMENT_DISPLAY_TEXT_INVALID",
        "GENERIC_PAYLOAD_NOT_MAPPING",
    }
)


def _closed_element_value_type(value: object, *, present: bool) -> str:
    if not present:
        return "ABSENT"
    if value is None:
        return "NULL"
    if isinstance(value, Mapping):
        return "MAPPING"
    if isinstance(value, list):
        return "LIST"
    if type(value) is str:
        return "STRING"
    if type(value) is bool:
        return "BOOLEAN"
    if type(value) is int:
        return "INTEGER"
    if type(value) is float:
        return "FLOAT"
    return "OTHER_SCALAR"


@dataclass(frozen=True, slots=True)
class _ElementStructureDiagnosticShape:
    """Content-free ParagraphElement facts retained only during a private capture."""

    element_is_mapping: bool
    start_index_type: str
    end_index_type: str
    start_index_present: bool
    end_index_present: bool
    recognized_union_members: tuple[str, ...]
    recognized_union_count: int
    unknown_present: bool
    selected_union_member: str | None
    selected_payload_type: str

    def __post_init__(self) -> None:
        if not self.element_is_mapping:
            raise TypeError("element diagnostic shape requires a mapping")
        if (
            self.start_index_type not in _ELEMENT_VALUE_TYPES
            or self.end_index_type not in _ELEMENT_VALUE_TYPES
            or self.selected_payload_type not in _ELEMENT_VALUE_TYPES
        ):
            raise TypeError("element diagnostic value type must be closed")
        if (
            type(self.recognized_union_count) is not int
            or self.recognized_union_count != len(self.recognized_union_members)
            or any(name not in _PARAGRAPH_ELEMENT_UNION_MEMBERS for name in self.recognized_union_members)
        ):
            raise TypeError("element diagnostic union members must be closed")
        if self.selected_union_member is not None and self.selected_union_member not in _PARAGRAPH_ELEMENT_UNION_MEMBERS:
            raise TypeError("element diagnostic selected member must be closed")


@dataclass(frozen=True, slots=True)
class _ElementStructureDiagnosticObservation:
    """First safe, non-content observation for a private diagnostic harness."""

    element_is_mapping: bool
    start_index_type: str
    end_index_type: str
    start_index_present: bool
    end_index_present: bool
    recognized_union_members: tuple[str, ...]
    recognized_union_count: int
    unknown_present: bool
    selected_union_member: str | None
    selected_payload_type: str
    failing_branch: str
    content_state: str | None = None
    string_failure_reason: _ElementStringFailureReason | None = None

    def __post_init__(self) -> None:
        _ElementStructureDiagnosticShape(
            element_is_mapping=self.element_is_mapping,
            start_index_type=self.start_index_type,
            end_index_type=self.end_index_type,
            start_index_present=self.start_index_present,
            end_index_present=self.end_index_present,
            recognized_union_members=self.recognized_union_members,
            recognized_union_count=self.recognized_union_count,
            unknown_present=self.unknown_present,
            selected_union_member=self.selected_union_member,
            selected_payload_type=self.selected_payload_type,
        )
        if self.failing_branch not in _ELEMENT_STRUCTURE_BRANCHES:
            raise TypeError("element diagnostic failing branch must be closed")
        if self.failing_branch == "TEXT_RUN_CONTENT_INVALID":
            if self.content_state not in _ELEMENT_VALUE_TYPES:
                raise TypeError("text run content diagnostic state must be closed")
            if self.content_state == "STRING":
                if self.string_failure_reason not in _ELEMENT_STRING_FAILURE_REASONS:
                    raise TypeError("text run string failure reason must be closed")
            elif self.string_failure_reason is not None:
                raise TypeError("string failure reason requires string content")
        elif (
            self.content_state is not None
            or self.string_failure_reason is not None
        ):
            raise TypeError("content diagnostics are limited to text run content")


class _ElementStructureDiagnosticCollector:
    """Ephemeral, first-failure-only storage for a controlled local harness."""

    def __init__(self) -> None:
        self._observation: _ElementStructureDiagnosticObservation | None = None

    @property
    def observation(self) -> _ElementStructureDiagnosticObservation | None:
        return self._observation

    def _record(self, observation: _ElementStructureDiagnosticObservation) -> None:
        if self._observation is None:
            self._observation = observation


_ELEMENT_STRUCTURE_DIAGNOSTIC_COLLECTOR: ContextVar[
    _ElementStructureDiagnosticCollector | None
] = ContextVar("element_structure_diagnostic_collector", default=None)
_ELEMENT_STRUCTURE_DIAGNOSTIC_SHAPE: ContextVar[
    _ElementStructureDiagnosticShape | None
] = ContextVar("element_structure_diagnostic_shape", default=None)


def _element_structure_diagnostic_shape(
    element: Mapping[str, object],
) -> _ElementStructureDiagnosticShape:
    recognized = tuple(
        name for name in _PARAGRAPH_ELEMENT_UNION_MEMBERS if name in element
    )
    selected = recognized[0] if len(recognized) == 1 else None
    unknown_present = any(
        name not in {*_PARAGRAPH_ELEMENT_METADATA_FIELDS, *_PARAGRAPH_ELEMENT_UNION_MEMBERS}
        for name in element
    )
    return _ElementStructureDiagnosticShape(
        element_is_mapping=True,
        start_index_type=_closed_element_value_type(
            element.get("startIndex"), present="startIndex" in element
        ),
        end_index_type=_closed_element_value_type(
            element.get("endIndex"), present="endIndex" in element
        ),
        start_index_present="startIndex" in element,
        end_index_present="endIndex" in element,
        recognized_union_members=recognized,
        recognized_union_count=len(recognized),
        unknown_present=unknown_present,
        selected_union_member=selected,
        selected_payload_type=_closed_element_value_type(
            element.get(selected), present=selected is not None
        ),
    )


@contextmanager
def _element_structure_diagnostic_collector() -> Iterator[_ElementStructureDiagnosticCollector]:
    """Install a request-local collector for a separately authorized harness."""

    collector = _ElementStructureDiagnosticCollector()
    token = _ELEMENT_STRUCTURE_DIAGNOSTIC_COLLECTOR.set(collector)
    try:
        yield collector
    finally:
        _ELEMENT_STRUCTURE_DIAGNOSTIC_COLLECTOR.reset(token)


@contextmanager
def _element_structure_diagnostic_element(
    element: Mapping[str, object],
) -> Iterator[None]:
    """Retain only safe element shape while an opt-in collector is active."""

    if _ELEMENT_STRUCTURE_DIAGNOSTIC_COLLECTOR.get() is None:
        yield
        return
    token = _ELEMENT_STRUCTURE_DIAGNOSTIC_SHAPE.set(
        _element_structure_diagnostic_shape(element)
    )
    try:
        yield
    finally:
        _ELEMENT_STRUCTURE_DIAGNOSTIC_SHAPE.reset(token)


def _record_element_structure_diagnostic(
    failing_branch: str,
    *,
    content_state: str | None = None,
    string_failure_reason: _ElementStringFailureReason | None = None,
) -> None:
    """Record one closed observation without retaining source values or keys."""

    collector = _ELEMENT_STRUCTURE_DIAGNOSTIC_COLLECTOR.get()
    shape = _ELEMENT_STRUCTURE_DIAGNOSTIC_SHAPE.get()
    if collector is None or shape is None or collector.observation is not None:
        return
    collector._record(
        _ElementStructureDiagnosticObservation(
            element_is_mapping=shape.element_is_mapping,
            start_index_type=shape.start_index_type,
            end_index_type=shape.end_index_type,
            start_index_present=shape.start_index_present,
            end_index_present=shape.end_index_present,
            recognized_union_members=shape.recognized_union_members,
            recognized_union_count=shape.recognized_union_count,
            unknown_present=shape.unknown_present,
            selected_union_member=shape.selected_union_member,
            selected_payload_type=shape.selected_payload_type,
            failing_branch=failing_branch,
            content_state=content_state,
            string_failure_reason=string_failure_reason,
        )
    )


def _element_payload_mapping(value: object, *, failing_branch: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        _record_element_structure_diagnostic(failing_branch)
    return _mapping(value)


def _response_error(
    *,
    stage: FailureStage = FailureStage.DOCS_SCHEMA_PARSE,
    structural_failure_kind: StructuralFailureKind | None = None,
    paragraph_failure_kind: ParagraphFailureKind | None = None,
) -> ContentSafeError:
    return ContentSafeError(
        code="RESPONSE_VALIDATION",
        operation=ContentErrorOperation.RESPONSE_DOCS_GET,
        failure_stage=stage,
        structural_failure_kind=structural_failure_kind,
        paragraph_failure_kind=paragraph_failure_kind,
    )


def _context_limit(
    *,
    stage: FailureStage = FailureStage.DOCS_STRUCTURAL_EXTRACTION,
    structural_failure_kind: StructuralFailureKind | None = None,
    paragraph_failure_kind: ParagraphFailureKind | None = None,
) -> ContentSafeError:
    return ContentSafeError(
        code="CONTEXT_LIMIT_EXCEEDED",
        operation=ContentErrorOperation.RESPONSE_DOCS_GET,
        failure_stage=stage,
        structural_failure_kind=structural_failure_kind,
        paragraph_failure_kind=paragraph_failure_kind,
    )


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise _response_error()
    return value


def _list(value: object) -> list[object]:
    if not isinstance(value, list):
        raise _response_error()
    return value


def _text(
    value: object,
    *,
    allow_empty: bool = False,
    maximum: int = 4096,
    string_failure_recorder: _ElementStringFailureRecorder | None = None,
    _allow_vertical_tab: bool = False,
) -> str:
    if type(value) is not str:
        raise _response_error()
    if len(value) > maximum:
        if string_failure_recorder is not None:
            string_failure_recorder("MAXIMUM_EXCEEDED")
        raise _response_error()
    if not allow_empty and not value:
        raise _response_error()
    try:
        value.encode("utf-8")
    except UnicodeError:
        if string_failure_recorder is not None:
            string_failure_recorder("UTF8_ENCODING_INVALID")
        raise _response_error() from None
    for character in value:
        code_point = ord(character)
        if (
            code_point < 32
            and character not in "\t\r\n"
            and not (_allow_vertical_tab and character == "\v")
        ) or 0x7F <= code_point <= 0x9F:
            if string_failure_recorder is not None:
                string_failure_recorder("DISALLOWED_C0_OR_C1_CONTROL")
            raise _response_error()
    return value


def _identifier(value: object) -> str:
    text = _text(value, maximum=256)
    if any(character.isspace() or character in "/\\?#" for character in text) or "://" in text:
        raise _response_error()
    return text


def _index(value: object, *, default_zero: bool = False) -> int:
    if value is None and default_zero:
        return 0
    if isinstance(value, bool) or type(value) is not int or value < 0 or value > 50_000_000:
        raise _response_error()
    return value


def _indices(value: Mapping[str, object]) -> tuple[int, int]:
    start = _index(value.get("startIndex"), default_zero=True)
    end = _index(value.get("endIndex"))
    if end < start:
        raise _response_error()
    return start, end


def _utf16_length(value: str) -> int:
    try:
        return len(value.encode("utf-16-le")) // 2
    except UnicodeError:
        raise _response_error() from None


@dataclass(frozen=True, slots=True)
class DriveFileMetadata:
    file_id: str
    mime_type: str
    modified_time: str
    trashed: bool


@dataclass(frozen=True, slots=True)
class _DriveFileMetadataReadFailure:
    """Closed, content-free failure returned by the private exact-ID port."""

    kind: Literal[
        "http",
        "timeout",
        "transport",
        "too_large",
        "json",
        "response_validation",
        "response_malformed",
        "unsupported_encoding",
    ]
    status: int | None = None

    def __post_init__(self) -> None:
        allowed_kinds = {
            "http",
            "timeout",
            "transport",
            "too_large",
            "json",
            "response_validation",
            "response_malformed",
            "unsupported_encoding",
        }
        if (
            type(self) is not _DriveFileMetadataReadFailure
            or type(self.kind) is not str
            or self.kind not in allowed_kinds
        ):
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.RESPONSE_DRIVE_FILE_METADATA,
            )
        if self.status is not None and (
            type(self.status) is not int or not 100 <= self.status <= 599
        ):
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.RESPONSE_DRIVE_FILE_METADATA,
            )


DriveFileMetadataReadResult = DriveFileMetadata | _DriveFileMetadataReadFailure


def parse_drive_file_metadata(
    payload: object,
    *,
    expected_file_id: str,
) -> DriveFileMetadata:
    body = _mapping(payload)
    file_id = _identifier(body.get("id"))
    mime_type = _text(body.get("mimeType"), maximum=256)
    modified_time = _text(body.get("modifiedTime"), maximum=128)
    trashed = body.get("trashed")
    if file_id != expected_file_id or type(trashed) is not bool:
        raise ContentSafeError(
            code="RESPONSE_VALIDATION",
            operation=ContentErrorOperation.RESPONSE_DRIVE_FILE_METADATA,
        )
    return DriveFileMetadata(file_id, mime_type, modified_time, trashed)


@dataclass(frozen=True, slots=True)
class _TextUnit:
    text: str
    provenance: DocsProvenance
    tab_ordinal: int
    index_tracks_text: bool = False


@dataclass(frozen=True, slots=True)
class DocsSectionBreak:
    provenance: DocsProvenance
    related_segment_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.provenance) is not DocsProvenance:
            raise _response_error()
        if type(self.related_segment_ids) not in (tuple, list):
            raise _response_error()
        identifiers = tuple(_identifier(value) for value in self.related_segment_ids)
        if len(identifiers) > 6:
            raise _response_error()
        object.__setattr__(self, "related_segment_ids", identifiers)


@dataclass(frozen=True, slots=True)
class ParsedGoogleDocument:
    revision_id: str | None
    units: tuple[_TextUnit, ...]
    section_breaks: tuple[DocsSectionBreak, ...]
    coverage_gaps: tuple[str, ...]


@dataclass(slots=True)
class _Counters:
    tabs: int = 0
    structural_elements: int = 0
    tables: int = 0
    text_runs: int = 0


class _Extractor:
    def __init__(self, budgets: ContentReadingBudgets) -> None:
        if type(budgets) is not ContentReadingBudgets:
            raise _response_error()
        self.budgets = budgets
        self.counters = _Counters()
        self.units: list[_TextUnit] = []
        self.section_breaks: list[DocsSectionBreak] = []
        self.gaps: set[str] = set()
        self.tab_ids: set[str] = set()
        self.tab_ordinal = 0

    def gap(self, reason: str) -> None:
        self.gaps.add(reason)

    def add_unit(
        self,
        text: object,
        *,
        provenance: DocsProvenance,
        tab_ordinal: int,
        index_tracks_text: bool = False,
    ) -> None:
        value = _text(text, allow_empty=True, maximum=32 * 1024 * 1024)
        if not value or not value.strip(" \t\r\n"):
            return
        self.units.append(_TextUnit(value, provenance, tab_ordinal, index_tracks_text))

    def _provenance(
        self,
        *,
        tab_id: str,
        tab_path: tuple[str, ...],
        segment: str,
        structural_path: tuple[int, ...],
        segment_id: str | None = None,
        start: int | None = None,
        end: int | None = None,
        paragraph_index: int | None = None,
        text_run_index: int | None = None,
        table_index: int | None = None,
        row: int | None = None,
        column: int | None = None,
        block_role: str | None = None,
        list_id: str | None = None,
        list_nesting_level: int | None = None,
        object_id: str | None = None,
        section_index: int | None = None,
    ) -> DocsProvenance:
        try:
            return DocsProvenance(
                tab_id=tab_id,
                structural_segment=segment,
                text_run_index=text_run_index,
                tab_path=tab_path,
                structural_path=structural_path,
                segment_id=segment_id,
                start_index=start,
                end_index=end,
                paragraph_index=paragraph_index,
                table_index=table_index,
                row=row,
                column=column,
                block_role=block_role,
                list_id=list_id,
                list_nesting_level=list_nesting_level,
                object_id=object_id,
                section_index=section_index,
            )
        except ContentSafeError:
            raise _response_error(stage=FailureStage.PROVENANCE_BUILD) from None

    @contextmanager
    def _structural_boundary(
        self,
        kind: StructuralFailureKind,
        *,
        paragraph_failure_kind: ParagraphFailureKind | None = None,
    ):
        """Tag only failures caused by the active structural boundary."""

        try:
            yield
        except ContentSafeError as error:
            if (
                error.failure_stage is FailureStage.PROVENANCE_BUILD
                or error.structural_failure_kind is not None
                or error.paragraph_failure_kind is not None
            ):
                raise
            raise ContentSafeError(
                code=error.code,
                operation=ContentErrorOperation.RESPONSE_DOCS_GET,
                http_status=error.http_status,
                failure_stage=FailureStage.DOCS_STRUCTURAL_EXTRACTION,
                structural_failure_kind=kind,
                paragraph_failure_kind=paragraph_failure_kind,
            ) from None

    @contextmanager
    def _paragraph_boundary(self, kind: ParagraphFailureKind):
        with self._structural_boundary(
            StructuralFailureKind.PARAGRAPH_STRUCTURE,
            paragraph_failure_kind=kind,
        ):
            yield

    def extract_tabs(self, tabs: object) -> None:
        raw_tabs = _list(tabs)
        if not raw_tabs:
            raise _response_error()
        try:
            self._tabs(raw_tabs, parent_id=None, parent_path=(), depth=0)
        except ContentSafeError as error:
            if (
                error.failure_stage is FailureStage.PROVENANCE_BUILD
                or error.structural_failure_kind is not None
            ):
                raise
            raise _response_error(
                stage=FailureStage.DOCS_STRUCTURAL_EXTRACTION,
                structural_failure_kind=StructuralFailureKind.OTHER_STRUCTURAL_VALIDATION,
            ) from None

    def _tabs(
        self,
        tabs: list[object],
        *,
        parent_id: str | None,
        parent_path: tuple[str, ...],
        depth: int,
    ) -> None:
        with self._structural_boundary(StructuralFailureKind.TAB_TRAVERSAL):
            self._tabs_impl(
                tabs,
                parent_id=parent_id,
                parent_path=parent_path,
                depth=depth,
            )

    def _tabs_impl(
        self,
        tabs: list[object],
        *,
        parent_id: str | None,
        parent_path: tuple[str, ...],
        depth: int,
    ) -> None:
        if depth > self.budgets.max_docs_tab_depth:
            raise _context_limit()
        for sibling_index, raw_tab in enumerate(tabs):
            self.counters.tabs += 1
            if self.counters.tabs > self.budgets.max_docs_tabs:
                raise _context_limit()
            tab = _mapping(raw_tab)
            properties = _mapping(tab.get("tabProperties"))
            tab_id = _identifier(properties.get("tabId"))
            if tab_id in self.tab_ids:
                raise _response_error()
            self.tab_ids.add(tab_id)
            title = _text(properties.get("title"), allow_empty=True, maximum=4096)
            index = _index(properties.get("index"), default_zero=True)
            nesting_level = _index(properties.get("nestingLevel"), default_zero=True)
            raw_parent = properties.get("parentTabId")
            actual_parent = None if raw_parent is None else _identifier(raw_parent)
            if index != sibling_index or nesting_level != depth or actual_parent != parent_id:
                raise _response_error()
            tab_path = parent_path + (tab_id,)
            ordinal = self.tab_ordinal
            self.tab_ordinal += 1
            self.add_unit(
                title,
                provenance=self._provenance(
                    tab_id=tab_id,
                    tab_path=tab_path,
                    segment="TAB_TITLE",
                    structural_path=(),
                ),
                tab_ordinal=ordinal,
            )
            self._document_tab(tab.get("documentTab"), tab_id=tab_id, tab_path=tab_path, tab_ordinal=ordinal)
            child_tabs = tab.get("childTabs", [])
            self._tabs(
                _list(child_tabs),
                parent_id=tab_id,
                parent_path=tab_path,
                depth=depth + 1,
            )

    def _document_tab(
        self,
        document_tab: object,
        *,
        tab_id: str,
        tab_path: tuple[str, ...],
        tab_ordinal: int,
    ) -> None:
        with self._structural_boundary(StructuralFailureKind.OTHER_STRUCTURAL_VALIDATION):
            self._document_tab_impl(
                _mapping(document_tab),
                tab_id=tab_id,
                tab_path=tab_path,
                tab_ordinal=tab_ordinal,
            )

    def _document_tab_impl(
        self,
        document_tab: Mapping[str, object],
        *,
        tab_id: str,
        tab_path: tuple[str, ...],
        tab_ordinal: int,
    ) -> None:
        lists = _mapping(document_tab.get("lists", {}))
        inline_objects = _mapping(document_tab.get("inlineObjects", {}))
        positioned_objects = _mapping(document_tab.get("positionedObjects", {}))
        emitted_inline: set[str] = set()
        emitted_positioned: set[str] = set()

        with self._structural_boundary(StructuralFailureKind.BODY_STRUCTURAL_ELEMENT):
            body = _mapping(document_tab.get("body"))
            self._content(
                body.get("content", []),
                failure_kind=StructuralFailureKind.BODY_STRUCTURAL_ELEMENT,
                tab_id=tab_id,
                tab_path=tab_path,
                tab_ordinal=tab_ordinal,
                segment="BODY",
                segment_id=None,
                structural_path=(),
                depth=0,
                lists=lists,
                inline_objects=inline_objects,
                positioned_objects=positioned_objects,
                emitted_inline=emitted_inline,
                emitted_positioned=emitted_positioned,
            )
        for key, segment, kind in (
            ("headers", "HEADER", StructuralFailureKind.HEADER_STRUCTURE),
            ("footers", "FOOTER", StructuralFailureKind.FOOTER_STRUCTURE),
            ("footnotes", "FOOTNOTE", StructuralFailureKind.FOOTNOTE_STRUCTURE),
        ):
            with self._structural_boundary(kind):
                collection = _mapping(document_tab.get(key, {}))
                for raw_id in sorted(collection):
                    segment_id = _identifier(raw_id)
                    resource = _mapping(collection[raw_id])
                    self._content(
                        resource.get("content", []),
                        failure_kind=kind,
                        tab_id=tab_id,
                        tab_path=tab_path,
                        tab_ordinal=tab_ordinal,
                        segment=segment,
                        segment_id=segment_id,
                        structural_path=(),
                        depth=0,
                        lists=lists,
                        inline_objects=inline_objects,
                        positioned_objects=positioned_objects,
                        emitted_inline=emitted_inline,
                        emitted_positioned=emitted_positioned,
                    )
        for object_id in sorted(inline_objects):
            if object_id not in emitted_inline:
                self._embedded_object(
                    object_id,
                    inline_objects[object_id],
                    tab_id=tab_id,
                    tab_path=tab_path,
                    tab_ordinal=tab_ordinal,
                    segment="INLINE_OBJECT",
                    structural_path=(),
                )
        for object_id in sorted(positioned_objects):
            if object_id not in emitted_positioned:
                self._embedded_object(
                    object_id,
                    positioned_objects[object_id],
                    tab_id=tab_id,
                    tab_path=tab_path,
                    tab_ordinal=tab_ordinal,
                    segment="POSITIONED_OBJECT",
                    structural_path=(),
                )

    def _content(
        self,
        raw_content: object,
        *,
        failure_kind: StructuralFailureKind,
        **kwargs: object,
    ) -> None:
        with self._structural_boundary(failure_kind):
            self._content_impl(raw_content, **kwargs)

    def _content_impl(
        self,
        raw_content: object,
        *,
        tab_id: str,
        tab_path: tuple[str, ...],
        tab_ordinal: int,
        segment: str,
        segment_id: str | None,
        structural_path: tuple[int, ...],
        depth: int,
        lists: Mapping[str, object],
        inline_objects: Mapping[str, object],
        positioned_objects: Mapping[str, object],
        emitted_inline: set[str],
        emitted_positioned: set[str],
        table_index: int | None = None,
        row: int | None = None,
        column: int | None = None,
    ) -> None:
        if depth > self.budgets.max_docs_structural_depth:
            raise _context_limit()
        for element_index, raw_element in enumerate(_list(raw_content)):
            self.counters.structural_elements += 1
            if self.counters.structural_elements > self.budgets.max_docs_structural_elements:
                raise _context_limit()
            element = _mapping(raw_element)
            start, end = _indices(element)
            path = structural_path + (element_index,)
            variants = [name for name in ("paragraph", "sectionBreak", "table", "tableOfContents") if name in element]
            unknown_variants = [
                name
                for name, value in element.items()
                if name not in {"startIndex", "endIndex", *variants} and isinstance(value, (dict, list))
            ]
            if len(variants) > 1:
                raise _response_error()
            if not variants:
                if unknown_variants:
                    self.gap("UNKNOWN_STRUCTURAL_ELEMENT")
                    continue
                raise _response_error()
            if unknown_variants:
                self.gap("UNKNOWN_STRUCTURAL_ELEMENT")
            variant = variants[0]
            if variant == "paragraph":
                self._paragraph(
                    element[variant],
                    tab_id=tab_id,
                    tab_path=tab_path,
                    tab_ordinal=tab_ordinal,
                    segment=segment,
                    segment_id=segment_id,
                    structural_path=path,
                    paragraph_index=element_index,
                    start=start,
                    end=end,
                    lists=lists,
                    inline_objects=inline_objects,
                    positioned_objects=positioned_objects,
                    emitted_inline=emitted_inline,
                    emitted_positioned=emitted_positioned,
                    table_index=table_index,
                    row=row,
                    column=column,
                )
            elif variant == "table":
                self._table(
                    element[variant],
                    tab_id=tab_id,
                    tab_path=tab_path,
                    tab_ordinal=tab_ordinal,
                    segment=segment,
                    segment_id=segment_id,
                    structural_path=path,
                    depth=depth + 1,
                    lists=lists,
                    inline_objects=inline_objects,
                    positioned_objects=positioned_objects,
                    emitted_inline=emitted_inline,
                    emitted_positioned=emitted_positioned,
                )
            elif variant == "tableOfContents":
                with self._structural_boundary(
                    StructuralFailureKind.TABLE_OF_CONTENTS_STRUCTURE
                ):
                    toc = _mapping(element[variant])
                    self._content(
                        toc.get("content", []),
                        failure_kind=StructuralFailureKind.TABLE_OF_CONTENTS_STRUCTURE,
                        tab_id=tab_id,
                        tab_path=tab_path,
                        tab_ordinal=tab_ordinal,
                        segment="TABLE_OF_CONTENTS",
                        segment_id=segment_id,
                        structural_path=path,
                        depth=depth + 1,
                        lists=lists,
                        inline_objects=inline_objects,
                        positioned_objects=positioned_objects,
                        emitted_inline=emitted_inline,
                        emitted_positioned=emitted_positioned,
                    )
            else:
                section_break = _mapping(element[variant])
                section_style = _mapping(section_break.get("sectionStyle", {}))
                related_segment_ids = tuple(
                    _identifier(section_style[field_name])
                    for field_name in (
                        "defaultHeaderId",
                        "defaultFooterId",
                        "firstPageHeaderId",
                        "firstPageFooterId",
                        "evenPageHeaderId",
                        "evenPageFooterId",
                    )
                    if section_style.get(field_name) is not None
                )
                self.section_breaks.append(
                    DocsSectionBreak(
                        provenance=self._provenance(
                            tab_id=tab_id,
                            tab_path=tab_path,
                            segment=segment,
                            segment_id=segment_id,
                            structural_path=path,
                            start=start,
                            end=end,
                            table_index=table_index,
                            row=row,
                            column=column,
                            block_role="SECTION_BREAK",
                            section_index=len(self.section_breaks),
                        ),
                        related_segment_ids=related_segment_ids,
                    )
                )

    def _paragraph(
        self,
        paragraph: object,
        **kwargs: object,
    ) -> None:
        with self._paragraph_boundary(ParagraphFailureKind.PARAGRAPH_OBJECT):
            paragraph_mapping = _mapping(paragraph)
        self._paragraph_impl(paragraph_mapping, **kwargs)

    def _paragraph_impl(
        self,
        paragraph: Mapping[str, object],
        *,
        tab_id: str,
        tab_path: tuple[str, ...],
        tab_ordinal: int,
        segment: str,
        segment_id: str | None,
        structural_path: tuple[int, ...],
        paragraph_index: int,
        start: int,
        end: int,
        lists: Mapping[str, object],
        inline_objects: Mapping[str, object],
        positioned_objects: Mapping[str, object],
        emitted_inline: set[str],
        emitted_positioned: set[str],
        table_index: int | None,
        row: int | None,
        column: int | None,
    ) -> None:
        with self._paragraph_boundary(ParagraphFailureKind.PARAGRAPH_STYLE):
            style = _mapping(paragraph.get("paragraphStyle", {}))
        with self._paragraph_boundary(ParagraphFailureKind.NAMED_STYLE):
            role_value = style.get("namedStyleType")
            block_role = None if role_value is None else _text(role_value, maximum=64)
        list_id = None
        nesting_level = None
        with self._paragraph_boundary(ParagraphFailureKind.BULLET_STRUCTURE):
            bullet_value = paragraph.get("bullet")
            if bullet_value is not None:
                bullet = _mapping(bullet_value)
                list_id = _identifier(bullet.get("listId"))
                nesting_level = _index(bullet.get("nestingLevel"), default_zero=True)
                if list_id not in lists:
                    raise _response_error()
        with self._paragraph_boundary(ParagraphFailureKind.ELEMENTS_CONTAINER):
            elements = _list(paragraph.get("elements", []))
        for run_index, raw_run in enumerate(elements):
            with self._structural_boundary(
                StructuralFailureKind.PARAGRAPH_ELEMENT_INDEX
            ):
                run = _mapping(raw_run)
                run_start, run_end = _indices(run)
                if run_start < start or run_end > end:
                    raise _response_error()
            with self._paragraph_boundary(ParagraphFailureKind.ELEMENT_STRUCTURE):
                with _element_structure_diagnostic_element(run):
                    variants = [
                        name for name in _PARAGRAPH_ELEMENT_UNION_MEMBERS if name in run
                    ]
                    unknown = [
                        name
                        for name, value in run.items()
                        if name not in {"startIndex", "endIndex", *variants}
                        and isinstance(value, (dict, list))
                    ]
                    if len(variants) != 1:
                        if not variants and unknown:
                            self.gap("UNKNOWN_TEXTUAL_ELEMENT")
                            continue
                        _record_element_structure_diagnostic(
                            "UNION_SELECTION_NO_RECOGNIZED_MEMBER"
                            if not variants
                            else "UNION_SELECTION_MULTIPLE_RECOGNIZED_MEMBERS"
                        )
                        raise _response_error()
                    if unknown:
                        self.gap("UNKNOWN_TEXTUAL_ELEMENT")
                    variant = variants[0]
                    provenance = self._provenance(
                        tab_id=tab_id,
                        tab_path=tab_path,
                        segment=segment,
                        segment_id=segment_id,
                        structural_path=structural_path + (run_index,),
                        start=run_start,
                        end=run_end,
                        paragraph_index=paragraph_index,
                        text_run_index=run_index,
                        table_index=table_index,
                        row=row,
                        column=column,
                        block_role=block_role,
                        list_id=list_id,
                        list_nesting_level=nesting_level,
                    )
                    if variant == "textRun":
                        with self._paragraph_boundary(ParagraphFailureKind.PARAGRAPH_LIMIT):
                            self.counters.text_runs += 1
                            if self.counters.text_runs > self.budgets.max_docs_text_runs:
                                raise _context_limit()
                        text_run = _element_payload_mapping(
                            run[variant],
                            failing_branch="TEXT_RUN_PAYLOAD_NOT_MAPPING",
                        )
                        content_value = text_run.get("content")

                        def record_string_failure(
                            reason: _ElementStringFailureReason,
                        ) -> None:
                            _record_element_structure_diagnostic(
                                "TEXT_RUN_CONTENT_INVALID",
                                content_state=_closed_element_value_type(
                                    content_value,
                                    present="content" in text_run,
                                ),
                                string_failure_reason=reason,
                            )

                        diagnostic_recorder = (
                            record_string_failure
                            if _ELEMENT_STRUCTURE_DIAGNOSTIC_COLLECTOR.get() is not None
                            and _ELEMENT_STRUCTURE_DIAGNOSTIC_SHAPE.get() is not None
                            else None
                        )

                        try:
                            content = _text(
                                content_value,
                                allow_empty=True,
                                maximum=32 * 1024 * 1024,
                                string_failure_recorder=diagnostic_recorder,
                                _allow_vertical_tab=True,
                            )
                        except ContentSafeError:
                            _record_element_structure_diagnostic(
                                "TEXT_RUN_CONTENT_INVALID",
                                content_state=_closed_element_value_type(
                                    content_value,
                                    present="content" in text_run,
                                ),
                            )
                            raise
                        if _utf16_length(content) != run_end - run_start:
                            _record_element_structure_diagnostic(
                                "TEXT_RUN_INDEX_LENGTH_MISMATCH"
                            )
                            raise _response_error()
                        # Source indexes above describe the original TextRun. Keep
                        # VT as one source unit while emitting safe visible text.
                        content = content.replace("\v", " ")
                        if "\ue907" in content:
                            content = content.replace("\ue907", "")
                            self.gap("NON_TEXT_PLACEHOLDER")
                        self.add_unit(
                            content,
                            provenance=provenance,
                            tab_ordinal=tab_ordinal,
                            index_tracks_text=True,
                        )
                    elif variant == "footnoteReference":
                        reference = _element_payload_mapping(
                            run[variant],
                            failing_branch="FOOTNOTE_REFERENCE_PAYLOAD_NOT_MAPPING",
                        )
                        number = reference.get("footnoteNumber")
                        if number is not None:
                            try:
                                self.add_unit(
                                    number,
                                    provenance=provenance,
                                    tab_ordinal=tab_ordinal,
                                )
                            except ContentSafeError:
                                _record_element_structure_diagnostic(
                                    "FOOTNOTE_REFERENCE_NUMBER_INVALID"
                                )
                                raise
                    elif variant == "equation":
                        _element_payload_mapping(
                            run[variant],
                            failing_branch="EQUATION_PAYLOAD_NOT_MAPPING",
                        )
                        self.gap("UNSUPPORTED_EQUATION")
                    elif variant == "inlineObjectElement":
                        inline = _element_payload_mapping(
                            run[variant],
                            failing_branch="INLINE_OBJECT_PAYLOAD_NOT_MAPPING",
                        )
                        try:
                            object_id = _identifier(inline.get("inlineObjectId"))
                        except ContentSafeError:
                            _record_element_structure_diagnostic(
                                "INLINE_OBJECT_ID_INVALID"
                            )
                            raise
                        if object_id not in inline_objects:
                            _record_element_structure_diagnostic(
                                "INLINE_OBJECT_REFERENCE_MISSING"
                            )
                            raise _response_error()
                        emitted_inline.add(object_id)
                        self._embedded_object(
                            object_id,
                            inline_objects[object_id],
                            tab_id=tab_id,
                            tab_path=tab_path,
                            tab_ordinal=tab_ordinal,
                            segment=segment,
                            structural_path=structural_path + (run_index,),
                            start=run_start,
                            end=run_end,
                            paragraph_index=paragraph_index,
                            table_index=table_index,
                            row=row,
                            column=column,
                        )
                    elif variant == "person":
                        person = _element_payload_mapping(
                            run[variant],
                            failing_branch="PERSON_PAYLOAD_NOT_MAPPING",
                        )
                        properties = _element_payload_mapping(
                            person.get("personProperties"),
                            failing_branch="PERSON_PROPERTIES_NOT_MAPPING",
                        )
                        for name in ("name", "email"):
                            if properties.get(name) is not None:
                                try:
                                    self.add_unit(
                                        properties[name],
                                        provenance=provenance,
                                        tab_ordinal=tab_ordinal,
                                    )
                                except ContentSafeError:
                                    _record_element_structure_diagnostic(
                                        "PERSON_VISIBLE_FIELD_INVALID"
                                    )
                                    raise
                    elif variant == "richLink":
                        rich_link = _element_payload_mapping(
                            run[variant],
                            failing_branch="RICH_LINK_PAYLOAD_NOT_MAPPING",
                        )
                        properties = _element_payload_mapping(
                            rich_link.get("richLinkProperties"),
                            failing_branch="RICH_LINK_PROPERTIES_NOT_MAPPING",
                        )
                        if properties.get("title") is not None:
                            try:
                                self.add_unit(
                                    properties["title"],
                                    provenance=provenance,
                                    tab_ordinal=tab_ordinal,
                                )
                            except ContentSafeError:
                                _record_element_structure_diagnostic(
                                    "RICH_LINK_TITLE_INVALID"
                                )
                                raise
                    elif variant == "dateElement":
                        date_element = _element_payload_mapping(
                            run[variant],
                            failing_branch="DATE_ELEMENT_PAYLOAD_NOT_MAPPING",
                        )
                        properties = _element_payload_mapping(
                            date_element.get("dateElementProperties"),
                            failing_branch="DATE_ELEMENT_PROPERTIES_NOT_MAPPING",
                        )
                        if properties.get("displayText") is not None:
                            try:
                                self.add_unit(
                                    properties["displayText"],
                                    provenance=provenance,
                                    tab_ordinal=tab_ordinal,
                                )
                            except ContentSafeError:
                                _record_element_structure_diagnostic(
                                    "DATE_ELEMENT_DISPLAY_TEXT_INVALID"
                                )
                                raise
                    else:
                        _element_payload_mapping(
                            run[variant],
                            failing_branch="GENERIC_PAYLOAD_NOT_MAPPING",
                        )

        with self._paragraph_boundary(ParagraphFailureKind.POSITIONED_OBJECTS):
            for raw_object_id in _list(paragraph.get("positionedObjectIds", [])):
                object_id = _identifier(raw_object_id)
                if object_id not in positioned_objects:
                    raise _response_error()
                if object_id not in emitted_positioned:
                    emitted_positioned.add(object_id)
                    self._embedded_object(
                        object_id,
                        positioned_objects[object_id],
                        tab_id=tab_id,
                        tab_path=tab_path,
                        tab_ordinal=tab_ordinal,
                        segment=segment,
                        structural_path=structural_path,
                        start=start,
                        end=end,
                        paragraph_index=paragraph_index,
                        table_index=table_index,
                        row=row,
                        column=column,
                    )

    def _table(
        self,
        table: object,
        **kwargs: object,
    ) -> None:
        with self._structural_boundary(StructuralFailureKind.TABLE_STRUCTURE):
            self._table_impl(_mapping(table), **kwargs)

    def _table_impl(
        self,
        table: Mapping[str, object],
        *,
        tab_id: str,
        tab_path: tuple[str, ...],
        tab_ordinal: int,
        segment: str,
        segment_id: str | None,
        structural_path: tuple[int, ...],
        depth: int,
        lists: Mapping[str, object],
        inline_objects: Mapping[str, object],
        positioned_objects: Mapping[str, object],
        emitted_inline: set[str],
        emitted_positioned: set[str],
    ) -> None:
        self.counters.tables += 1
        if self.counters.tables > self.budgets.max_docs_tables:
            raise _context_limit()
        table_index = self.counters.tables - 1
        for row_index, raw_row in enumerate(_list(table.get("tableRows", []))):
            row = _mapping(raw_row)
            for column_index, raw_cell in enumerate(_list(row.get("tableCells", []))):
                with self._structural_boundary(
                    StructuralFailureKind.TABLE_CELL_STRUCTURE
                ):
                    cell = _mapping(raw_cell)
                    self._content(
                        cell.get("content", []),
                        failure_kind=StructuralFailureKind.TABLE_CELL_STRUCTURE,
                        tab_id=tab_id,
                        tab_path=tab_path,
                        tab_ordinal=tab_ordinal,
                        segment=segment,
                        segment_id=segment_id,
                        structural_path=structural_path + (row_index, column_index),
                        depth=depth,
                        lists=lists,
                        inline_objects=inline_objects,
                        positioned_objects=positioned_objects,
                        emitted_inline=emitted_inline,
                        emitted_positioned=emitted_positioned,
                        table_index=table_index,
                        row=row_index,
                        column=column_index,
                    )

    def _embedded_object(
        self,
        object_id: object,
        value: object,
        *,
        tab_id: str,
        tab_path: tuple[str, ...],
        tab_ordinal: int,
        segment: str,
        structural_path: tuple[int, ...],
        start: int | None = None,
        end: int | None = None,
        paragraph_index: int | None = None,
        table_index: int | None = None,
        row: int | None = None,
        column: int | None = None,
    ) -> None:
        normalized_id = _identifier(object_id)
        object_value = _element_payload_mapping(
            value,
            failing_branch="INLINE_OBJECT_DEFINITION_NOT_MAPPING",
        )
        properties_value = object_value.get("inlineObjectProperties")
        if properties_value is None:
            properties_value = object_value.get("positionedObjectProperties")
        properties = _element_payload_mapping(
            properties_value,
            failing_branch="INLINE_OBJECT_PROPERTIES_NOT_MAPPING",
        )
        embedded = _element_payload_mapping(
            properties.get("embeddedObject"),
            failing_branch="INLINE_OBJECT_EMBEDDED_OBJECT_NOT_MAPPING",
        )
        provenance = self._provenance(
            tab_id=tab_id,
            tab_path=tab_path,
            segment=segment,
            structural_path=structural_path,
            start=start,
            end=end,
            paragraph_index=paragraph_index,
            table_index=table_index,
            row=row,
            column=column,
            object_id=normalized_id,
        )
        for name in ("title", "description"):
            if embedded.get(name) is not None:
                try:
                    self.add_unit(
                        embedded[name],
                        provenance=provenance,
                        tab_ordinal=tab_ordinal,
                    )
                except ContentSafeError:
                    _record_element_structure_diagnostic(
                        "INLINE_OBJECT_VISIBLE_FIELD_INVALID"
                    )
                    raise
        self.gap("UNSUPPORTED_VISUAL_OBJECT")


def parse_google_document(
    payload: object,
    *,
    expected_document_id: str,
    budgets: ContentReadingBudgets,
) -> ParsedGoogleDocument:
    body = _mapping(payload)
    document_id = _identifier(body.get("documentId"))
    if document_id != expected_document_id:
        raise _response_error()
    mode = _text(body.get("suggestionsViewMode"), maximum=64)
    if mode != "SUGGESTIONS_INLINE":
        raise _response_error()
    revision_value = body.get("revisionId")
    revision_id = None if revision_value is None else _text(revision_value, maximum=1024)
    extractor = _Extractor(budgets)
    extractor.extract_tabs(body.get("tabs"))
    return ParsedGoogleDocument(
        revision_id=revision_id,
        units=tuple(extractor.units),
        section_breaks=tuple(extractor.section_breaks),
        coverage_gaps=tuple(sorted(extractor.gaps)),
    )


def _prefix_characters(value: str, byte_limit: int) -> int:
    if byte_limit < 1:
        return 0
    if len(value.encode("utf-8")) <= byte_limit:
        return len(value)
    low, high = 0, len(value)
    while low < high:
        middle = (low + high + 1) // 2
        if len(value[:middle].encode("utf-8")) <= byte_limit:
            low = middle
        else:
            high = middle - 1
    return low


def _chunk_provenance(unit: _TextUnit, offset: int, text: str) -> DocsProvenance:
    base = unit.provenance
    prefix_utf16 = _utf16_length(unit.text[:offset])
    piece_utf16 = _utf16_length(text)
    if unit.index_tracks_text and base.start_index is not None:
        start = base.start_index + prefix_utf16
        end = start + piece_utf16
    else:
        start = base.start_index
        end = base.end_index
    return replace(
        base,
        start_index=start,
        end_index=end,
        sub_offset_utf16=(base.sub_offset_utf16 or 0) + prefix_utf16,
    )


def build_bounded_docs_result(
    document: ParsedGoogleDocument,
    *,
    snapshot: InventorySnapshot,
    budgets: ContentReadingBudgets,
    continuation_manager: DocsContinuationManager,
    public_file_ref: str,
    continuation_state: DocsContinuationState | None = None,
) -> BoundedReadResult:
    if type(document) is not ParsedGoogleDocument or type(snapshot) is not InventorySnapshot:
        raise _response_error()
    if len(document.section_breaks) > MAX_STRUCTURAL_LOCATIONS:
        return failure_result(
            ProcessingStatus.TOO_LARGE,
            SafeContentErrorCode.TOO_LARGE,
            FailureStage.DOCS_STRUCTURAL_EXTRACTION,
            StructuralFailureKind.OTHER_STRUCTURAL_VALIDATION,
        )
    structural_locations = (
        tuple(boundary.provenance for boundary in document.section_breaks)
        if continuation_state is None
        else ()
    )
    unit_index = 0 if continuation_state is None else continuation_state.unit_index
    character_offset = 0 if continuation_state is None else continuation_state.character_offset
    if unit_index > len(document.units):
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_CONTINUATION)
    if unit_index == len(document.units) and character_offset:
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_CONTINUATION)

    chunks: list[ContentChunk] = []
    output_bytes = 0
    current_unit = unit_index
    current_offset = character_offset
    while current_unit < len(document.units):
        unit = document.units[current_unit]
        if current_offset > len(unit.text):
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_CONTINUATION)
        if current_offset == len(unit.text):
            current_unit += 1
            current_offset = 0
            continue
        available = min(
            budgets.max_text_chunk_bytes,
            budgets.max_extracted_content_bytes - output_bytes,
        )
        if available < 1 or len(chunks) >= budgets.max_chunks_per_invocation:
            break
        count = _prefix_characters(unit.text[current_offset:], available)
        if count < 1:
            if not chunks:
                return failure_result(
                    ProcessingStatus.TOO_LARGE,
                    SafeContentErrorCode.TOO_LARGE,
                    FailureStage.DOCS_STRUCTURAL_EXTRACTION,
                    StructuralFailureKind.OTHER_STRUCTURAL_VALIDATION,
                )
            break
        piece = unit.text[current_offset : current_offset + count]
        chunks.append(
            ContentChunk(
                file_ref=public_file_ref,
                content_class=ContentClass.GOOGLE_DOC,
                sequence=len(chunks),
                content_kind=ContentKind.TEXT,
                payload=TextPayload(piece),
                provenance=_chunk_provenance(unit, current_offset, piece),
            )
        )
        output_bytes += len(piece.encode("utf-8"))
        current_offset += count
        if current_offset == len(unit.text):
            current_unit += 1
            current_offset = 0

    has_more = current_unit < len(document.units)
    if has_more:
        next_unit = document.units[current_unit]
        token = continuation_manager.issue(
            DocsContinuationState(
                snapshot=snapshot,
                reader_version=GOOGLE_DOCS_READER_VERSION,
                unit_index=current_unit,
                character_offset=current_offset,
                tab_ordinal=next_unit.tab_ordinal,
                structural_cursor=next_unit.provenance.structural_path,
                revision_id=document.revision_id,
            )
        )
        if not chunks:
            return failure_result(
                ProcessingStatus.TOO_LARGE,
                SafeContentErrorCode.TOO_LARGE,
                FailureStage.DOCS_STRUCTURAL_EXTRACTION,
                StructuralFailureKind.OTHER_STRUCTURAL_VALIDATION,
            )
        chunks[-1] = replace(chunks[-1], truncated=True, continuation=token)
        reason = "BUDGET_EXHAUSTED_WITH_COVERAGE_GAP" if document.coverage_gaps else "BUDGET_EXHAUSTED"
        return BoundedReadResult(
            tuple(chunks),
            ProcessingOutcome(
                ProcessingStatus.PARTIALLY_PROCESSED,
                ContentClass.GOOGLE_DOC,
                chunk_count=len(chunks),
                result_count=len(chunks),
                truncated=True,
                partial_reason=reason,
                continuation=token,
            ),
            structural_locations,
        )
    if document.coverage_gaps:
        return BoundedReadResult(
            tuple(chunks),
            ProcessingOutcome(
                ProcessingStatus.PARTIALLY_PROCESSED,
                ContentClass.GOOGLE_DOC,
                chunk_count=len(chunks),
                result_count=len(chunks),
                partial_reason="UNSUPPORTED_KNOWN_COVERAGE_GAP",
            ),
            structural_locations,
        )
    if not chunks:
        return BoundedReadResult(
            (),
            ProcessingOutcome(ProcessingStatus.EMPTY, ContentClass.GOOGLE_DOC),
            structural_locations,
        )
    return BoundedReadResult(
        tuple(chunks),
        ProcessingOutcome(
            ProcessingStatus.PROCESSED,
            ContentClass.GOOGLE_DOC,
            chunk_count=len(chunks),
            result_count=len(chunks),
        ),
        structural_locations,
    )


def failure_result(
    status: ProcessingStatus,
    error_code: SafeContentErrorCode,
    failure_stage: FailureStage | None = None,
    structural_failure_kind: StructuralFailureKind | None = None,
    paragraph_failure_kind: ParagraphFailureKind | None = None,
) -> BoundedReadResult:
    if (
        failure_stage is FailureStage.DOCS_STRUCTURAL_EXTRACTION
        and structural_failure_kind is None
    ):
        structural_failure_kind = StructuralFailureKind.OTHER_STRUCTURAL_VALIDATION
    return BoundedReadResult(
        (),
        ProcessingOutcome(
            status,
            ContentClass.GOOGLE_DOC,
            safe_error_code=error_code,
            failure_stage=failure_stage,
            structural_failure_kind=structural_failure_kind,
            paragraph_failure_kind=paragraph_failure_kind,
        ),
    )
