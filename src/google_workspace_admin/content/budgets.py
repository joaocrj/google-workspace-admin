"""Immutable, finite budgets shared by future Content readers."""

from __future__ import annotations

from dataclasses import dataclass

from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError


MIB = 1024 * 1024
MAX_DOWNLOAD_BYTES = 32 * MIB
MAX_EXPORT_BYTES = 8 * MIB
MAX_PARSER_INPUT_BYTES = 32 * MIB
MAX_EXTRACTED_CONTENT_BYTES = 2 * MIB
MAX_TEXT_CHUNK_BYTES = 256 * 1024
MAX_STRUCTURED_CHUNK_BYTES = MIB
MAX_DECOMPRESSED_ARCHIVE_BYTES = 64 * MIB
MAX_ARCHIVE_MEMBERS = 10_000
MAX_PARSER_CHUNK_TIMEOUT_SECONDS = 300
MAX_PARSER_FILE_TIMEOUT_SECONDS = 600


def _positive(value: object, maximum: int) -> int:
    if isinstance(value, bool) or type(value) is not int or value < 1 or value > maximum:
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_BUDGET)
    return value


@dataclass(frozen=True, slots=True)
class ContentReadingBudgets:
    """Finite policy constants; none are MCP parameters."""

    max_download_bytes: int = MAX_DOWNLOAD_BYTES
    max_export_bytes: int = MAX_EXPORT_BYTES
    max_parser_input_bytes: int = MAX_PARSER_INPUT_BYTES
    max_extracted_content_bytes: int = MAX_EXTRACTED_CONTENT_BYTES
    max_text_chunk_bytes: int = MAX_TEXT_CHUNK_BYTES
    max_structured_chunk_bytes: int = MAX_STRUCTURED_CHUNK_BYTES
    max_decompressed_archive_bytes: int = MAX_DECOMPRESSED_ARCHIVE_BYTES
    max_archive_members: int = MAX_ARCHIVE_MEMBERS
    parser_chunk_timeout_seconds: int = 15
    parser_file_timeout_seconds: int = 30
    max_docs_structural_elements: int = 50_000
    max_docs_tables: int = 2_000
    max_docs_text_runs: int = 100_000
    max_sheets_cells_per_chunk: int = 100_000
    max_sheets_cells_per_file: int = 5_000_000
    max_sheets_tabs: int = 200
    max_slides: int = 500
    max_slides_elements_per_slide: int = 5_000
    max_pdf_pages: int = 200
    max_word_paragraphs: int = 100_000
    max_excel_cells: int = 1_000_000
    max_powerpoint_slides: int = 500
    max_text_lines_or_records: int = 1_000_000
    max_json_xml_depth: int = 100

    def __post_init__(self) -> None:
        if type(self) is not ContentReadingBudgets:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_BUDGET)
        for field_name, maximum in (
            ("max_download_bytes", MAX_DOWNLOAD_BYTES),
            ("max_export_bytes", MAX_EXPORT_BYTES),
            ("max_parser_input_bytes", MAX_PARSER_INPUT_BYTES),
            ("max_extracted_content_bytes", MAX_EXTRACTED_CONTENT_BYTES),
            ("max_text_chunk_bytes", MAX_TEXT_CHUNK_BYTES),
            ("max_structured_chunk_bytes", MAX_STRUCTURED_CHUNK_BYTES),
            ("max_decompressed_archive_bytes", MAX_DECOMPRESSED_ARCHIVE_BYTES),
            ("max_archive_members", MAX_ARCHIVE_MEMBERS),
            ("parser_chunk_timeout_seconds", MAX_PARSER_CHUNK_TIMEOUT_SECONDS),
            ("parser_file_timeout_seconds", MAX_PARSER_FILE_TIMEOUT_SECONDS),
            ("max_docs_structural_elements", 50_000),
            ("max_docs_tables", 2_000),
            ("max_docs_text_runs", 100_000),
            ("max_sheets_cells_per_chunk", 100_000),
            ("max_sheets_cells_per_file", 5_000_000),
            ("max_sheets_tabs", 200),
            ("max_slides", 500),
            ("max_slides_elements_per_slide", 5_000),
            ("max_pdf_pages", 200),
            ("max_word_paragraphs", 100_000),
            ("max_excel_cells", 1_000_000),
            ("max_powerpoint_slides", 500),
            ("max_text_lines_or_records", 1_000_000),
            ("max_json_xml_depth", 100),
        ):
            _positive(getattr(self, field_name), maximum)
        if self.max_parser_input_bytes < self.max_text_chunk_bytes:
            raise ContentSafeError(code="CONTEXT_LIMIT_EXCEEDED", operation=ContentErrorOperation.READING_BUDGET)
        if self.max_parser_input_bytes < self.max_structured_chunk_bytes:
            raise ContentSafeError(code="CONTEXT_LIMIT_EXCEEDED", operation=ContentErrorOperation.READING_BUDGET)
        if self.max_extracted_content_bytes > self.max_parser_input_bytes:
            raise ContentSafeError(code="CONTEXT_LIMIT_EXCEEDED", operation=ContentErrorOperation.READING_BUDGET)
        if self.parser_file_timeout_seconds < self.parser_chunk_timeout_seconds:
            raise ContentSafeError(code="CONTEXT_LIMIT_EXCEEDED", operation=ContentErrorOperation.READING_BUDGET)


DEFAULT_CONTENT_READING_BUDGETS = ContentReadingBudgets()
