"""Sealed, read-only local foundation for future Workspace Content tools.

No MCP tool or Google authentication is registered here.  Operational access
is limited to a startup-assembled :class:`ContentRuntime` and closed requests.
"""

from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError
from google_workspace_admin.content.operations import (
    DriveFilesListRequest,
    DriveGetRequest,
    DriveListRequest,
)
from google_workspace_admin.content.results import (
    DriveFileInventoryItem,
    DriveFileInventoryPage,
    DriveFileListPage,
    DriveFileSummary,
    DriveGetResult,
    DriveListPage,
    DriveSummary,
)
from google_workspace_admin.content.runtime import ContentRuntime
from google_workspace_admin.content.budgets import (
    DEFAULT_CONTENT_READING_BUDGETS,
    ContentReadingBudgets,
)
from google_workspace_admin.content.coverage import (
    CoverageLedger,
    CoverageRecord,
    validate_coverage_complete,
)
from google_workspace_admin.content.chunks import (
    CellsPayload,
    ContentChunk,
    ContentKind,
    RecordPayload,
    RecordsPayload,
    ScalarValue,
    StructuredField,
    StructuredPayload,
    TextPayload,
)
from google_workspace_admin.content.inventory import (
    DownloadPreflight,
    DownloadPreflightDecision,
    InventorySnapshot,
)
from google_workspace_admin.content.outcomes import (
    FAILURE_STATUSES,
    NON_TERMINAL_STATUSES,
    PARTIAL_STATUSES,
    SUCCESS_STATUSES,
    TERMINAL_STATUSES,
    ProcessingOutcome,
    ProcessingStatus,
    SafeContentErrorCode,
    classify_budget_exhaustion,
)
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
)
from google_workspace_admin.content.readers import (
    BoundedReadResult,
    ContentReader,
    validate_reader_continuation,
)
from google_workspace_admin.content.routing import (
    ContentClass,
    allowlisted_mime_types,
    route_mime_type,
    validate_mime_type,
)
from google_workspace_admin.content.safety import (
    DEFAULT_UNTRUSTED_CONTENT_POLICY,
    NEVER_EXECUTE_FILE_CONTENT,
    ReaderDispatch,
    UntrustedContentPolicy,
    fixed_reader_dispatch,
)

__all__ = [
    "ContentErrorOperation",
    "ContentRuntime",
    "DriveFileListPage",
    "DriveFileInventoryItem",
    "DriveFileInventoryPage",
    "DriveFileSummary",
    "DriveFilesListRequest",
    "DriveGetRequest",
    "DriveGetResult",
    "DriveListPage",
    "DriveListRequest",
    "DriveSummary",
    "ContentSafeError",
    "ContentClass",
    "route_mime_type",
    "validate_mime_type",
    "allowlisted_mime_types",
    "ContentReadingBudgets",
    "DEFAULT_CONTENT_READING_BUDGETS",
    "CoverageRecord",
    "CoverageLedger",
    "validate_coverage_complete",
    "ContentKind",
    "ContentChunk",
    "TextPayload",
    "CellsPayload",
    "RecordPayload",
    "RecordsPayload",
    "ScalarValue",
    "StructuredField",
    "StructuredPayload",
    "Provenance",
    "DocsProvenance",
    "SheetsProvenance",
    "SlidesProvenance",
    "PdfProvenance",
    "WordProvenance",
    "ExcelProvenance",
    "PowerPointProvenance",
    "TextProvenance",
    "InventorySnapshot",
    "DownloadPreflight",
    "DownloadPreflightDecision",
    "ProcessingStatus",
    "ProcessingOutcome",
    "SafeContentErrorCode",
    "classify_budget_exhaustion",
    "NON_TERMINAL_STATUSES",
    "SUCCESS_STATUSES",
    "PARTIAL_STATUSES",
    "FAILURE_STATUSES",
    "TERMINAL_STATUSES",
    "BoundedReadResult",
    "ContentReader",
    "validate_reader_continuation",
    "UntrustedContentPolicy",
    "DEFAULT_UNTRUSTED_CONTENT_POLICY",
    "NEVER_EXECUTE_FILE_CONTENT",
    "ReaderDispatch",
    "fixed_reader_dispatch",
]
