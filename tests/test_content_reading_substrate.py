from dataclasses import FrozenInstanceError
import ast
from pathlib import Path

import pytest

from google_workspace_admin.content import (
    BoundedReadResult,
    CellsPayload,
    ContentChunk,
    ContentClass,
    ContentKind,
    ContentReader,
    ContentReadingBudgets,
    CoverageLedger,
    DEFAULT_CONTENT_READING_BUDGETS,
    DEFAULT_UNTRUSTED_CONTENT_POLICY,
    DocsProvenance,
    FailureStage,
    DownloadPreflight,
    ExcelProvenance,
    InventorySnapshot,
    NEVER_EXECUTE_FILE_CONTENT,
    PdfProvenance,
    PowerPointProvenance,
    ProcessingOutcome,
    ProcessingStatus,
    ParagraphFailureKind,
    RecordPayload,
    RecordsPayload,
    SafeContentErrorCode,
    ScalarValue,
    SheetsProvenance,
    SlidesProvenance,
    StructuredField,
    StructuredPayload,
    StructuralFailureKind,
    TextPayload,
    TextProvenance,
    validate_coverage_complete,
    WordProvenance,
    classify_budget_exhaustion,
    fixed_reader_dispatch,
    route_mime_type,
    validate_reader_continuation,
)
from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError

TEST_PUBLIC_FILE_REF = "gdrv_v1_" + "A" * 43


def test_structural_failure_kind_is_closed_and_complete():
    assert tuple(StructuralFailureKind) == (
        StructuralFailureKind.TAB_TRAVERSAL,
        StructuralFailureKind.BODY_STRUCTURAL_ELEMENT,
        StructuralFailureKind.PARAGRAPH_STRUCTURE,
        StructuralFailureKind.PARAGRAPH_ELEMENT_INDEX,
        StructuralFailureKind.TABLE_STRUCTURE,
        StructuralFailureKind.TABLE_CELL_STRUCTURE,
        StructuralFailureKind.TABLE_OF_CONTENTS_STRUCTURE,
        StructuralFailureKind.HEADER_STRUCTURE,
        StructuralFailureKind.FOOTER_STRUCTURE,
        StructuralFailureKind.FOOTNOTE_STRUCTURE,
        StructuralFailureKind.OTHER_STRUCTURAL_VALIDATION,
    )


def test_paragraph_failure_kind_is_closed_and_complete():
    assert tuple(ParagraphFailureKind) == (
        ParagraphFailureKind.PARAGRAPH_OBJECT,
        ParagraphFailureKind.PARAGRAPH_STYLE,
        ParagraphFailureKind.NAMED_STYLE,
        ParagraphFailureKind.BULLET_STRUCTURE,
        ParagraphFailureKind.ELEMENTS_CONTAINER,
        ParagraphFailureKind.ELEMENT_STRUCTURE,
        ParagraphFailureKind.POSITIONED_OBJECTS,
        ParagraphFailureKind.PARAGRAPH_LIMIT,
    )


@pytest.mark.parametrize(
    ("stage", "structural_kind"),
    [
        (FailureStage.DOCS_REQUEST, None),
        (FailureStage.DOCS_RESPONSE_TRANSPORT, None),
        (FailureStage.DOCS_JSON_PARSE, None),
        (FailureStage.DOCS_SCHEMA_PARSE, None),
        (FailureStage.PROVENANCE_BUILD, None),
        (FailureStage.DOCS_STRUCTURAL_EXTRACTION, StructuralFailureKind.TABLE_STRUCTURE),
        (FailureStage.DOCS_STRUCTURAL_EXTRACTION, StructuralFailureKind.PARAGRAPH_ELEMENT_INDEX),
    ],
)
def test_paragraph_failure_kind_is_null_outside_known_paragraph_boundary(stage, structural_kind):
    outcome = ProcessingOutcome(
        ProcessingStatus.EXTRACTION_FAILED,
        ContentClass.GOOGLE_DOC,
        safe_error_code=SafeContentErrorCode.RESPONSE_VALIDATION,
        failure_stage=stage,
        structural_failure_kind=structural_kind,
    )
    assert outcome.paragraph_failure_kind is None


@pytest.mark.parametrize(
    ("mime", "expected"),
    [
        ("application/vnd.google-apps.document", ContentClass.GOOGLE_DOC),
        ("application/vnd.google-apps.spreadsheet", ContentClass.GOOGLE_SHEET),
        ("application/vnd.google-apps.presentation", ContentClass.GOOGLE_SLIDE),
        ("application/vnd.google-apps.folder", ContentClass.GOOGLE_FOLDER),
        ("application/pdf", ContentClass.PDF),
        ("application/msword", ContentClass.MICROSOFT_WORD),
        ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", ContentClass.MICROSOFT_WORD),
        ("application/vnd.ms-excel", ContentClass.MICROSOFT_EXCEL),
        ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ContentClass.MICROSOFT_EXCEL),
        ("application/vnd.ms-powerpoint", ContentClass.MICROSOFT_POWERPOINT),
        ("application/vnd.openxmlformats-officedocument.presentationml.presentation", ContentClass.MICROSOFT_POWERPOINT),
        ("text/plain", ContentClass.TEXT),
        ("text/csv", ContentClass.CSV),
        ("application/json", ContentClass.JSON),
        ("application/xml", ContentClass.XML),
        ("application/zip", ContentClass.ARCHIVE),
        ("image/png", ContentClass.IMAGE),
        ("audio/mpeg", ContentClass.AUDIO),
        ("video/mp4", ContentClass.VIDEO),
        ("application/octet-stream", ContentClass.OTHER_BINARY),
    ],
)
def test_mime_router_is_closed_and_allowlisted(mime, expected):
    assert route_mime_type(mime) is expected


def test_mime_router_is_case_insensitive_but_extension_is_irrelevant():
    assert route_mime_type("TEXT/PLAIN") is ContentClass.TEXT
    assert route_mime_type("application/octet-stream") is ContentClass.OTHER_BINARY
    assert route_mime_type("application/x-unknown") is ContentClass.UNKNOWN
    assert route_mime_type("image/x-unknown") is ContentClass.UNKNOWN


@pytest.mark.parametrize("value", [None, True, 1, "", " ", "text/plain\n", "a" * 257])
def test_mime_router_rejects_malformed_mime(value):
    with pytest.raises(ContentSafeError):
        route_mime_type(value)


def test_defaults_are_exact_and_immutable():
    assert DEFAULT_CONTENT_READING_BUDGETS.max_download_bytes == 32 * 1024 * 1024
    assert DEFAULT_CONTENT_READING_BUDGETS.max_export_bytes == 8 * 1024 * 1024
    assert DEFAULT_CONTENT_READING_BUDGETS.max_parser_input_bytes == 32 * 1024 * 1024
    assert DEFAULT_CONTENT_READING_BUDGETS.max_extracted_content_bytes == 2 * 1024 * 1024
    assert DEFAULT_CONTENT_READING_BUDGETS.max_text_chunk_bytes == 256 * 1024
    assert DEFAULT_CONTENT_READING_BUDGETS.max_structured_chunk_bytes == 1024 * 1024
    assert DEFAULT_CONTENT_READING_BUDGETS.max_decompressed_archive_bytes == 64 * 1024 * 1024
    assert DEFAULT_CONTENT_READING_BUDGETS.max_archive_members == 10_000
    assert DEFAULT_CONTENT_READING_BUDGETS.parser_chunk_timeout_seconds == 15
    assert DEFAULT_CONTENT_READING_BUDGETS.parser_file_timeout_seconds == 30
    with pytest.raises(FrozenInstanceError):
        DEFAULT_CONTENT_READING_BUDGETS.max_download_bytes = 1  # type: ignore[misc]


@pytest.mark.parametrize(
    "field",
    [
        "max_download_bytes",
        "max_export_bytes",
        "max_parser_input_bytes",
        "max_extracted_content_bytes",
        "max_text_chunk_bytes",
        "max_structured_chunk_bytes",
        "max_decompressed_archive_bytes",
        "max_archive_members",
        "parser_chunk_timeout_seconds",
        "parser_file_timeout_seconds",
        "max_docs_structural_elements",
        "max_docs_tables",
        "max_docs_text_runs",
        "max_docs_tabs",
        "max_docs_tab_depth",
        "max_docs_structural_depth",
        "max_chunks_per_invocation",
        "max_sheets_cells_per_chunk",
        "max_sheets_cells_per_file",
        "max_sheets_tabs",
        "max_slides",
        "max_slides_elements_per_slide",
        "max_pdf_pages",
        "max_word_paragraphs",
        "max_excel_cells",
        "max_powerpoint_slides",
        "max_text_lines_or_records",
        "max_json_xml_depth",
    ],
)
def test_budget_fields_are_strictly_positive_and_bounded(field):
    for value in (True, 0, -1, 1.0, "1"):
        with pytest.raises(ContentSafeError):
            ContentReadingBudgets(**{field: value})


def test_budget_cross_limits_are_fail_closed():
    with pytest.raises(ContentSafeError):
        ContentReadingBudgets(max_parser_input_bytes=1)
    with pytest.raises(ContentSafeError):
        ContentReadingBudgets(max_extracted_content_bytes=2 * 1024 * 1024, max_parser_input_bytes=2 * 1024 * 1024 - 1)


def test_first_budget_exhaustion_can_be_partial_with_opaque_continuation():
    assert classify_budget_exhaustion(safe_continuation_possible=True, absolute_limit_exceeded=False) is ProcessingStatus.PARTIALLY_PROCESSED
    assert classify_budget_exhaustion(safe_continuation_possible=False, absolute_limit_exceeded=False) is ProcessingStatus.TOO_LARGE
    assert classify_budget_exhaustion(safe_continuation_possible=True, absolute_limit_exceeded=True) is ProcessingStatus.TOO_LARGE
    with pytest.raises(ContentSafeError):
        classify_budget_exhaustion(safe_continuation_possible=1, absolute_limit_exceeded=False)  # type: ignore[arg-type]


def test_typed_payloads_reject_arbitrary_objects_and_bound_bytes():
    assert TextPayload("ok").text == "ok"
    with pytest.raises(ContentSafeError):
        TextPayload("x" * (256 * 1024 + 1))
    with pytest.raises(ContentSafeError):
        ScalarValue(10**100)
    with pytest.raises(ContentSafeError):
        CellsPayload([{"cell": "value"}])  # type: ignore[list-item]
    assert RecordsPayload((RecordPayload((ScalarValue("v"),)),)).records[0].values[0].value == "v"
    assert StructuredPayload((StructuredField("kind", ScalarValue("value")),)).fields[0].key == "kind"


def test_content_chunk_validates_kind_payload_provenance_sequence_and_token():
    chunk = ContentChunk(
        file_ref=TEST_PUBLIC_FILE_REF,
        content_class=ContentClass.TEXT,
        sequence=0,
        content_kind=ContentKind.TEXT,
        payload=TextPayload("hello"),
        provenance=TextProvenance(line=1),
        continuation="opaque-token",
        truncated=True,
    )
    assert chunk.sequence == 0 and chunk.continuation == "opaque-token"
    assert chunk.file_ref == TEST_PUBLIC_FILE_REF
    with pytest.raises(ContentSafeError):
        ContentChunk(
            file_ref="raw-drive-id",
            content_class=ContentClass.TEXT,
            sequence=0,
            content_kind=ContentKind.TEXT,
            payload=TextPayload("hello"),
            provenance=TextProvenance(line=1),
        )
    with pytest.raises(ContentSafeError):
        ContentChunk(
            file_ref=TEST_PUBLIC_FILE_REF,
            content_class=ContentClass.TEXT,
            sequence=True,  # type: ignore[arg-type]
            content_kind=ContentKind.TEXT,
            payload=TextPayload("hello"),
            provenance=TextProvenance(line=1),
        )
    with pytest.raises(ContentSafeError):
        ContentChunk(
            file_ref="https://attacker.invalid/file",
            content_class=ContentClass.TEXT,
            sequence=0,
            content_kind=ContentKind.TEXT,
            payload=TextPayload("hello"),
            provenance=TextProvenance(line=1),
        )
    with pytest.raises(ContentSafeError):
        ContentChunk(
            file_ref="../attacker",
            content_class=ContentClass.TEXT,
            sequence=0,
            content_kind=ContentKind.TEXT,
            payload=TextPayload("hello"),
            provenance=TextProvenance(line=1),
        )
    with pytest.raises(ContentSafeError):
        ContentChunk(
            file_ref=TEST_PUBLIC_FILE_REF,
            content_class=ContentClass.TEXT,
            sequence=0,
            content_kind=ContentKind.TEXT,
            payload=TextPayload("hello"),
            provenance=TextProvenance(line=1),
            continuation="bad token",
        )
    with pytest.raises(ContentSafeError):
        ContentChunk(
            file_ref=TEST_PUBLIC_FILE_REF,
            content_class=ContentClass.TEXT,
            sequence=0,
            content_kind=ContentKind.TEXT,
            payload=TextPayload("hello"),
            provenance=TextProvenance(line=1),
            continuation="opaque",
            truncated=False,
        )
    with pytest.raises(ContentSafeError):
        ContentChunk(
            file_ref=TEST_PUBLIC_FILE_REF,
            content_class=ContentClass.PDF,
            sequence=0,
            content_kind=ContentKind.TEXT,
            payload=TextPayload("hello"),
            provenance=TextProvenance(line=1),
        )
    with pytest.raises(ContentSafeError):
        ContentChunk(
            file_ref=TEST_PUBLIC_FILE_REF,
            content_class=ContentClass.TEXT,
            sequence=0,
            content_kind=ContentKind.TEXT,
            payload={"raw": "response"},  # type: ignore[arg-type]
            provenance=TextProvenance(line=1),
        )


@pytest.mark.parametrize(
    "provenance",
    [
        DocsProvenance("tab-1", "body:0", 0),
        SheetsProvenance("sheet-1", "A1:B2", 1, 1),
        SlidesProvenance("slide-1", "element-1"),
        PdfProvenance(1),
        WordProvenance(section=0, paragraph=1),
        ExcelProvenance("sheet-1", "A1", 1, 1),
        PowerPointProvenance(1, "element-1"),
        TextProvenance(line=1, byte_offset=0),
    ],
)
def test_provenance_variants_are_location_only(provenance):
    assert provenance is not None


@pytest.mark.parametrize(
    "factory",
    [
        lambda: DocsProvenance("", "body"),
        lambda: SheetsProvenance("sheet", "A1", row=1),
        lambda: PdfProvenance(0),
        lambda: WordProvenance(),
        lambda: TextProvenance(),
        lambda: SlidesProvenance("slide\n", "element"),
        lambda: DocsProvenance("https://attacker.invalid", "body"),
    ],
)
def test_invalid_provenance_combinations_fail_closed(factory):
    with pytest.raises(ContentSafeError):
        factory()


def test_processing_outcomes_are_terminal_and_unambiguous():
    processed = ProcessingOutcome(
        ProcessingStatus.PROCESSED,
        ContentClass.TEXT,
        chunk_count=1,
        result_count=1,
    )
    empty = ProcessingOutcome(ProcessingStatus.EMPTY, ContentClass.TEXT)
    partial = ProcessingOutcome(
        ProcessingStatus.PARTIALLY_PROCESSED,
        ContentClass.TEXT,
        chunk_count=1,
        result_count=1,
        truncated=True,
        partial_reason="BUDGET_EXHAUSTED",
        continuation="opaque",
    )
    assert processed.is_success and empty.is_success and partial.is_partial
    assert processed.paragraph_failure_kind is None
    assert empty.paragraph_failure_kind is None
    assert partial.paragraph_failure_kind is None
    terminal_partial = ProcessingOutcome(
        ProcessingStatus.PARTIALLY_PROCESSED,
        ContentClass.GOOGLE_DOC,
        partial_reason="UNSUPPORTED_KNOWN_COVERAGE_GAP",
    )
    assert terminal_partial.is_partial and terminal_partial.continuation is None
    with pytest.raises(ContentSafeError):
        ProcessingOutcome(ProcessingStatus.READING, ContentClass.TEXT)  # type: ignore[arg-type]
    with pytest.raises(ContentSafeError):
        ProcessingOutcome(ProcessingStatus.PROCESSED, ContentClass.TEXT, chunk_count=1, continuation="more")
    with pytest.raises(ContentSafeError):
        ProcessingOutcome(ProcessingStatus.EMPTY, ContentClass.TEXT, result_count=1)
    with pytest.raises(ContentSafeError):
        ProcessingOutcome(
            ProcessingStatus.PARTIALLY_PROCESSED,
            ContentClass.TEXT,
            chunk_count=1,
            result_count=1,
            truncated=True,
            partial_reason="BUDGET_EXHAUSTED",
        )
    assert ProcessingOutcome(ProcessingStatus.ACCESS_DENIED, ContentClass.TEXT).is_failure
    denied = ProcessingOutcome(
        ProcessingStatus.ACCESS_DENIED,
        ContentClass.TEXT,
        safe_error_code=SafeContentErrorCode.ACCESS_DENIED,
    )
    assert denied.is_failure and not denied.is_success
    staged_failure = ProcessingOutcome(
        ProcessingStatus.EXTRACTION_FAILED,
        ContentClass.GOOGLE_DOC,
        safe_error_code=SafeContentErrorCode.RESPONSE_VALIDATION,
        failure_stage=FailureStage.DOCS_JSON_PARSE,
    )
    assert staged_failure.failure_stage is FailureStage.DOCS_JSON_PARSE
    assert staged_failure.structural_failure_kind is None
    structural_failure = ProcessingOutcome(
        ProcessingStatus.EXTRACTION_FAILED,
        ContentClass.GOOGLE_DOC,
        safe_error_code=SafeContentErrorCode.RESPONSE_VALIDATION,
        failure_stage=FailureStage.DOCS_STRUCTURAL_EXTRACTION,
        structural_failure_kind=StructuralFailureKind.TABLE_STRUCTURE,
    )
    assert structural_failure.structural_failure_kind is StructuralFailureKind.TABLE_STRUCTURE
    paragraph_failure = ProcessingOutcome(
        ProcessingStatus.EXTRACTION_FAILED,
        ContentClass.GOOGLE_DOC,
        safe_error_code=SafeContentErrorCode.RESPONSE_VALIDATION,
        failure_stage=FailureStage.DOCS_STRUCTURAL_EXTRACTION,
        structural_failure_kind=StructuralFailureKind.PARAGRAPH_STRUCTURE,
        paragraph_failure_kind=ParagraphFailureKind.PARAGRAPH_STYLE,
    )
    assert paragraph_failure.paragraph_failure_kind is ParagraphFailureKind.PARAGRAPH_STYLE
    with pytest.raises(ContentSafeError):
        ProcessingOutcome(
            ProcessingStatus.EXTRACTION_FAILED,
            ContentClass.GOOGLE_DOC,
            safe_error_code=SafeContentErrorCode.RESPONSE_VALIDATION,
            failure_stage="DOCS_JSON_PARSE",  # type: ignore[arg-type]
        )
    with pytest.raises(ContentSafeError):
        ProcessingOutcome(
            ProcessingStatus.PROCESSED,
            ContentClass.TEXT,
            chunk_count=1,
            failure_stage=FailureStage.DOCS_JSON_PARSE,
        )
    for stage, kind in (
        (FailureStage.DOCS_STRUCTURAL_EXTRACTION, None),
        (FailureStage.DOCS_REQUEST, StructuralFailureKind.PARAGRAPH_STRUCTURE),
        (FailureStage.PROVENANCE_BUILD, StructuralFailureKind.TABLE_CELL_STRUCTURE),
    ):
        with pytest.raises(ContentSafeError):
            ProcessingOutcome(
                ProcessingStatus.EXTRACTION_FAILED,
                ContentClass.GOOGLE_DOC,
                safe_error_code=SafeContentErrorCode.RESPONSE_VALIDATION,
                failure_stage=stage,
                structural_failure_kind=kind,
            )

    for kwargs in (
        {
            "processing_status": ProcessingStatus.PROCESSED,
            "content_class": ContentClass.GOOGLE_DOC,
            "chunk_count": 1,
            "paragraph_failure_kind": ParagraphFailureKind.PARAGRAPH_STYLE,
        },
        {
            "processing_status": ProcessingStatus.EXTRACTION_FAILED,
            "content_class": ContentClass.GOOGLE_DOC,
            "safe_error_code": SafeContentErrorCode.RESPONSE_VALIDATION,
            "failure_stage": FailureStage.DOCS_REQUEST,
            "paragraph_failure_kind": ParagraphFailureKind.PARAGRAPH_OBJECT,
        },
        {
            "processing_status": ProcessingStatus.EXTRACTION_FAILED,
            "content_class": ContentClass.GOOGLE_DOC,
            "safe_error_code": SafeContentErrorCode.RESPONSE_VALIDATION,
            "failure_stage": FailureStage.PROVENANCE_BUILD,
            "paragraph_failure_kind": ParagraphFailureKind.ELEMENT_STRUCTURE,
        },
        {
            "processing_status": ProcessingStatus.EXTRACTION_FAILED,
            "content_class": ContentClass.GOOGLE_DOC,
            "safe_error_code": SafeContentErrorCode.RESPONSE_VALIDATION,
            "failure_stage": FailureStage.DOCS_STRUCTURAL_EXTRACTION,
            "structural_failure_kind": StructuralFailureKind.TABLE_STRUCTURE,
            "paragraph_failure_kind": ParagraphFailureKind.BULLET_STRUCTURE,
        },
        {
            "processing_status": ProcessingStatus.EXTRACTION_FAILED,
            "content_class": ContentClass.GOOGLE_DOC,
            "safe_error_code": SafeContentErrorCode.RESPONSE_VALIDATION,
            "failure_stage": FailureStage.DOCS_STRUCTURAL_EXTRACTION,
            "structural_failure_kind": StructuralFailureKind.PARAGRAPH_ELEMENT_INDEX,
            "paragraph_failure_kind": ParagraphFailureKind.ELEMENTS_CONTAINER,
        },
        {
            "processing_status": ProcessingStatus.EXTRACTION_FAILED,
            "content_class": ContentClass.GOOGLE_DOC,
            "safe_error_code": SafeContentErrorCode.RESPONSE_VALIDATION,
            "failure_stage": FailureStage.DOCS_STRUCTURAL_EXTRACTION,
            "structural_failure_kind": StructuralFailureKind.PARAGRAPH_STRUCTURE,
        },
    ):
        with pytest.raises(ContentSafeError):
            ProcessingOutcome(**kwargs)
    with pytest.raises(TypeError):
        ContentSafeError(
            code="RESPONSE_VALIDATION",
            operation=ContentErrorOperation.RESPONSE_DOCS_GET,
            failure_stage=FailureStage.DOCS_STRUCTURAL_EXTRACTION,
            structural_failure_kind="TABLE_STRUCTURE",  # type: ignore[arg-type]
        )
    with pytest.raises(TypeError):
        ContentSafeError(
            code="RESPONSE_VALIDATION",
            operation=ContentErrorOperation.RESPONSE_DOCS_GET,
            failure_stage=FailureStage.DOCS_STRUCTURAL_EXTRACTION,
            structural_failure_kind=StructuralFailureKind.PARAGRAPH_STRUCTURE,
            paragraph_failure_kind="PARAGRAPH_STYLE",  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError):
        ContentSafeError(
            code="RESPONSE_VALIDATION",
            operation=ContentErrorOperation.RESPONSE_DOCS_GET,
            failure_stage=FailureStage.DOCS_REQUEST,
            paragraph_failure_kind=ParagraphFailureKind.PARAGRAPH_OBJECT,
        )


@pytest.mark.parametrize(
    "status",
    [
        ProcessingStatus.TOO_LARGE,
        ProcessingStatus.ACCESS_DENIED,
        ProcessingStatus.NOT_FOUND,
        ProcessingStatus.CHANGED_DURING_AUDIT,
        ProcessingStatus.EXTRACTION_FAILED,
        ProcessingStatus.TRANSIENT_UPSTREAM,
    ],
)
def test_pre_rv_remediation_terminal_failures_forbid_counts_and_resume_state(status):
    assert ProcessingOutcome(status, ContentClass.TEXT).is_failure
    for kwargs in (
        {"chunk_count": 1},
        {"result_count": 1},
        {"continuation": "opaque"},
        {"truncated": True},
    ):
        with pytest.raises(ContentSafeError):
            ProcessingOutcome(status, ContentClass.TEXT, **kwargs)


def test_pre_rv_remediation_bounded_failure_forbids_chunks_even_with_zero_counts():
    chunk = ContentChunk(
        file_ref=TEST_PUBLIC_FILE_REF,
        content_class=ContentClass.TEXT,
        sequence=0,
        content_kind=ContentKind.TEXT,
        payload=TextPayload("data"),
        provenance=TextProvenance(line=1),
    )
    with pytest.raises(ContentSafeError):
        BoundedReadResult(
            (chunk,),
            ProcessingOutcome(
                ProcessingStatus.EXTRACTION_FAILED,
                ContentClass.TEXT,
                safe_error_code=SafeContentErrorCode.RESPONSE_VALIDATION,
            ),
        )
    with pytest.raises(ContentSafeError):
        BoundedReadResult(
            (),
            ProcessingOutcome(
                ProcessingStatus.EXTRACTION_FAILED,
                ContentClass.GOOGLE_DOC,
                safe_error_code=SafeContentErrorCode.RESPONSE_VALIDATION,
            ),
            (DocsProvenance("tab-1", "BODY", block_role="SECTION_BREAK"),),
        )


def test_processing_status_sets_are_closed_and_disjoint():
    from google_workspace_admin.content import (
        FAILURE_STATUSES,
        NON_TERMINAL_STATUSES,
        PARTIAL_STATUSES,
        SUCCESS_STATUSES,
        TERMINAL_STATUSES,
    )

    assert NON_TERMINAL_STATUSES.isdisjoint(TERMINAL_STATUSES)
    assert SUCCESS_STATUSES.isdisjoint(PARTIAL_STATUSES)
    assert FAILURE_STATUSES.isdisjoint(SUCCESS_STATUSES | PARTIAL_STATUSES)
    assert NON_TERMINAL_STATUSES | TERMINAL_STATUSES == set(ProcessingStatus)
    assert SUCCESS_STATUSES | PARTIAL_STATUSES | FAILURE_STATUSES == TERMINAL_STATUSES


def test_coverage_ledger_enforces_exactly_one_terminal_outcome_per_file():
    outcome = ProcessingOutcome(ProcessingStatus.EMPTY, ContentClass.TEXT)
    ledger = CoverageLedger().record("file-1", outcome)
    assert ledger.total_inventoried == 1 and ledger.analyzed == 1 and ledger.failures == 0
    validate_coverage_complete(["file-1"], ledger)
    with pytest.raises(ContentSafeError):
        ledger.record("file-1", outcome)
    with pytest.raises(ContentSafeError):
        validate_coverage_complete(["file-1", "file-2"], ledger)
    with pytest.raises(ContentSafeError):
        CoverageLedger((ledger.records[0], ledger.records[0]))


def test_bounded_read_result_matches_outcome_and_chunks():
    chunk = ContentChunk(
        file_ref=TEST_PUBLIC_FILE_REF,
        content_class=ContentClass.TEXT,
        sequence=0,
        content_kind=ContentKind.TEXT,
        payload=TextPayload("hello"),
        provenance=TextProvenance(line=1),
    )
    result = BoundedReadResult(
        (chunk,),
        ProcessingOutcome(ProcessingStatus.PROCESSED, ContentClass.TEXT, chunk_count=1, result_count=1),
    )
    assert result.chunks == (chunk,)
    with pytest.raises(ContentSafeError):
        BoundedReadResult((chunk,), ProcessingOutcome(ProcessingStatus.EMPTY, ContentClass.TEXT))
    with pytest.raises(ContentSafeError):
        BoundedReadResult(
            (
                ContentChunk(
                    file_ref=TEST_PUBLIC_FILE_REF,
                    content_class=ContentClass.TEXT,
                    sequence=0,
                    content_kind=ContentKind.TEXT,
                    payload=TextPayload("hello"),
                    provenance=TextProvenance(line=1),
                    truncated=True,
                ),
            ),
            ProcessingOutcome(ProcessingStatus.PROCESSED, ContentClass.TEXT, chunk_count=1, result_count=1),
        )
    partial_chunk = ContentChunk(
        file_ref=TEST_PUBLIC_FILE_REF,
        content_class=ContentClass.TEXT,
        sequence=0,
        content_kind=ContentKind.TEXT,
        payload=TextPayload("hello"),
        provenance=TextProvenance(line=1),
        truncated=True,
        continuation="opaque",
    )
    partial_outcome = ProcessingOutcome(
        ProcessingStatus.PARTIALLY_PROCESSED,
        ContentClass.TEXT,
        chunk_count=1,
        result_count=1,
        truncated=True,
        partial_reason="BUDGET_EXHAUSTED",
        continuation="opaque",
    )
    assert BoundedReadResult((partial_chunk,), partial_outcome).outcome.is_partial
    terminal_partial = BoundedReadResult(
        (),
        ProcessingOutcome(
            ProcessingStatus.PARTIALLY_PROCESSED,
            ContentClass.GOOGLE_DOC,
            partial_reason="UNSUPPORTED_KNOWN_COVERAGE_GAP",
        ),
    )
    assert terminal_partial.outcome.continuation is None
    with pytest.raises(ContentSafeError):
        BoundedReadResult(
            (partial_chunk,),
            ProcessingOutcome(
                ProcessingStatus.PARTIALLY_PROCESSED,
                ContentClass.TEXT,
                chunk_count=1,
                result_count=1,
                truncated=True,
                partial_reason="BUDGET_EXHAUSTED",
                continuation="other",
            ),
        )


def test_inventory_snapshot_and_preflight_are_internal_and_validated():
    snapshot = InventorySnapshot("File-1", "text/plain", "2026-09-16T00:00:00Z", 12)
    assert snapshot.file_id == "File-1" and snapshot.expected_mime_type == "text/plain"
    assert snapshot.same_version(InventorySnapshot("File-1", "text/plain", "2026-09-16T00:00:00Z", 12))
    assert not snapshot.same_version(InventorySnapshot("File-1", "text/plain", "2026-09-17T00:00:00Z", 12))
    with pytest.raises(ContentSafeError):
        InventorySnapshot("https://attacker.invalid/file", "text/plain")
    with pytest.raises(ContentSafeError):
        InventorySnapshot("../../attacker", "text/plain")
    with pytest.raises(ContentSafeError):
        InventorySnapshot("file-1", "text/plain", modified_time=" ")
    with pytest.raises(ContentSafeError):
        InventorySnapshot("file-1", "text/plain", size=-1)
    assert DownloadPreflight(True).decision.value == "ALLOWED"
    with pytest.raises(ContentSafeError) as error:
        DownloadPreflight(False).require_allowed()
    assert error.value.code == "DOWNLOAD_NOT_ALLOWED"


def test_fixed_dispatch_cannot_be_overridden_by_content():
    assert fixed_reader_dispatch(ContentClass.TEXT).value == "TEXT"
    assert fixed_reader_dispatch(ContentClass.ARCHIVE).value == "NONE"
    with pytest.raises(ContentSafeError):
        fixed_reader_dispatch("TEXT")  # type: ignore[arg-type]
    policy = DEFAULT_UNTRUSTED_CONTENT_POLICY
    assert NEVER_EXECUTE_FILE_CONTENT is True
    assert all(value is False for value in (getattr(policy, field.name) for field in policy.__dataclass_fields__.values()))


def test_reader_protocol_has_only_closed_arguments():
    annotations = ContentReader.read.__annotations__
    assert "snapshot" in annotations and "budgets" in annotations
    assert "url" not in annotations and "host" not in annotations and "scope" not in annotations
    assert validate_reader_continuation(None) is None
    assert validate_reader_continuation("opaque") == "opaque"
    with pytest.raises(ContentSafeError):
        validate_reader_continuation("bad token")


def test_substrate_contains_no_active_content_execution_or_network_primitives():
    substrate_root = Path(__file__).parents[1] / "src" / "google_workspace_admin" / "content"
    substrate = tuple(
        substrate_root / name
        for name in (
            "routing.py",
            "budgets.py",
            "chunks.py",
            "coverage.py",
            "inventory.py",
            "outcomes.py",
            "provenance.py",
            "readers.py",
            "safety.py",
        )
    )
    forbidden_imports = {"subprocess", "requests", "httpx", "urllib.request"}
    forbidden_calls = {"eval", "exec", "system", "popen", "run", "check_call", "check_output"}
    for path in substrate:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(alias.name not in forbidden_imports for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                assert (node.module or "") not in forbidden_imports
            elif isinstance(node, ast.Call):
                name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
                assert name not in forbidden_calls
