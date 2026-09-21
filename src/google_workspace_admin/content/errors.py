"""Safe errors for the future Content Read boundary."""

from __future__ import annotations

from enum import Enum

from google_workspace_admin.http_errors import SafeOperationError


class ContentErrorOperation(str, Enum):
    UNKNOWN = "content.unknown"
    AUTH_PROFILE_VALIDATION = "content.auth.profile_validation"
    AUTH_PROFILE_PROVISIONING = "content.auth.profile_provisioning"
    AUTH_PROFILE_LOOKUP = "content.auth.profile_lookup"
    AUTH_PROFILE_PROVENANCE = "content.auth.profile_provenance"
    AUTH_PROFILE_SUBJECT = "content.auth.profile_subject"
    AUTH_CONTEXT_PROVENANCE = "content.auth.context_provenance"
    AUTH_BROKER = "content.auth.broker"
    SUBJECT_VALIDATION = "content.subject.validation"
    SUBJECT_RESOLUTION = "content.subject.resolution"
    SUBJECT_PROVENANCE = "content.subject.provenance"
    SUBJECT_MAILBOX = "content.subject.mailbox"
    SCOPE_REGISTRY = "content.scope.registry"
    CAPABILITY_MATRIX = "content.capability.matrix"
    AUTH_CACHE = "content.auth.cache"
    OPERATION_RESOLUTION = "content.operation.resolution"
    OPERATION_NORMALIZATION = "content.operation.normalization"
    DRIVE_LIST = "drive.list"
    DRIVE_GET = "drive.get"
    DRIVE_FILES_LIST = "drive.files.list"
    DRIVE_FILE_METADATA_GET = "drive.files.get.metadata"
    DOCS_GET = "docs.documents.get"
    FILE_CONTENT_READ = "content.file.read"
    DRIVE_FILTER = "content.drive.filter"
    PAGINATION = "content.pagination"
    CONTEXT_LIMIT = "content.context_limit"
    RETRY_POLICY = "content.retry"
    TRANSPORT = "content.transport"
    RESPONSE_DRIVE_LIST = "content.response.drive_list"
    RESPONSE_DRIVE_GET = "content.response.drive_get"
    RESPONSE_DRIVE_FILES_LIST = "content.response.drive_files_list"
    RESPONSE_DRIVE_FILE_METADATA = "content.response.drive_file_metadata"
    RESPONSE_DOCS_GET = "content.response.docs_get"
    EVIDENCE = "content.evidence"
    AUDIT = "content.audit"
    BOOTSTRAP = "content.bootstrap"
    RUNTIME = "content.runtime"
    READING_ROUTER = "content.reading.router"
    READING_BUDGET = "content.reading.budget"
    READING_CHUNK = "content.reading.chunk"
    READING_PROVENANCE = "content.reading.provenance"
    READING_OUTCOME = "content.reading.outcome"
    READING_READER = "content.reading.reader"
    READING_SNAPSHOT = "content.reading.snapshot"
    READING_PREFLIGHT = "content.reading.preflight"
    READING_SAFETY = "content.reading.safety"
    READING_CONTINUATION = "content.reading.continuation"


class FailureStage(str, Enum):
    """Closed, non-content-derived location of a content-read failure."""

    PREFLIGHT_FETCH = "PREFLIGHT_FETCH"
    PREFLIGHT_VALIDATION = "PREFLIGHT_VALIDATION"
    DOCS_REQUEST = "DOCS_REQUEST"
    DOCS_RESPONSE_TRANSPORT = "DOCS_RESPONSE_TRANSPORT"
    DOCS_JSON_PARSE = "DOCS_JSON_PARSE"
    DOCS_SCHEMA_PARSE = "DOCS_SCHEMA_PARSE"
    DOCS_STRUCTURAL_EXTRACTION = "DOCS_STRUCTURAL_EXTRACTION"
    PROVENANCE_BUILD = "PROVENANCE_BUILD"
    POSTFLIGHT_FETCH = "POSTFLIGHT_FETCH"
    POSTFLIGHT_VALIDATION = "POSTFLIGHT_VALIDATION"


class StructuralFailureKind(str, Enum):
    """Closed causal boundary inside Docs structural extraction."""

    TAB_TRAVERSAL = "TAB_TRAVERSAL"
    BODY_STRUCTURAL_ELEMENT = "BODY_STRUCTURAL_ELEMENT"
    PARAGRAPH_STRUCTURE = "PARAGRAPH_STRUCTURE"
    PARAGRAPH_ELEMENT_INDEX = "PARAGRAPH_ELEMENT_INDEX"
    TABLE_STRUCTURE = "TABLE_STRUCTURE"
    TABLE_CELL_STRUCTURE = "TABLE_CELL_STRUCTURE"
    TABLE_OF_CONTENTS_STRUCTURE = "TABLE_OF_CONTENTS_STRUCTURE"
    HEADER_STRUCTURE = "HEADER_STRUCTURE"
    FOOTER_STRUCTURE = "FOOTER_STRUCTURE"
    FOOTNOTE_STRUCTURE = "FOOTNOTE_STRUCTURE"
    OTHER_STRUCTURAL_VALIDATION = "OTHER_STRUCTURAL_VALIDATION"


class ParagraphFailureKind(str, Enum):
    """Closed causal boundary inside paragraph structural extraction."""

    PARAGRAPH_OBJECT = "PARAGRAPH_OBJECT"
    PARAGRAPH_STYLE = "PARAGRAPH_STYLE"
    NAMED_STYLE = "NAMED_STYLE"
    BULLET_STRUCTURE = "BULLET_STRUCTURE"
    ELEMENTS_CONTAINER = "ELEMENTS_CONTAINER"
    ELEMENT_STRUCTURE = "ELEMENT_STRUCTURE"
    POSITIONED_OBJECTS = "POSITIONED_OBJECTS"
    PARAGRAPH_LIMIT = "PARAGRAPH_LIMIT"


class ContentSafeError(SafeOperationError):
    """Content error without raw Google bodies, headers, or credentials."""

    def __init__(
        self,
        *,
        code: str,
        operation: ContentErrorOperation,
        http_status: int | None = None,
        category: str | None = None,
        failure_stage: FailureStage | None = None,
        structural_failure_kind: StructuralFailureKind | None = None,
        paragraph_failure_kind: ParagraphFailureKind | None = None,
    ) -> None:
        if failure_stage is not None and type(failure_stage) is not FailureStage:
            raise TypeError("failure_stage must be a FailureStage")
        if (
            structural_failure_kind is not None
            and type(structural_failure_kind) is not StructuralFailureKind
        ):
            raise TypeError("structural_failure_kind must be a StructuralFailureKind")
        if (
            structural_failure_kind is not None
            and failure_stage is not FailureStage.DOCS_STRUCTURAL_EXTRACTION
        ):
            raise ValueError(
                "structural_failure_kind requires DOCS_STRUCTURAL_EXTRACTION"
            )
        if (
            paragraph_failure_kind is not None
            and type(paragraph_failure_kind) is not ParagraphFailureKind
        ):
            raise TypeError("paragraph_failure_kind must be a ParagraphFailureKind")
        if paragraph_failure_kind is not None and (
            failure_stage is not FailureStage.DOCS_STRUCTURAL_EXTRACTION
            or structural_failure_kind is not StructuralFailureKind.PARAGRAPH_STRUCTURE
        ):
            raise ValueError(
                "paragraph_failure_kind requires PARAGRAPH_STRUCTURE extraction"
            )
        self.category = category
        self.failure_stage = failure_stage
        self.structural_failure_kind = structural_failure_kind
        self.paragraph_failure_kind = paragraph_failure_kind
        safe_operation = (
            operation.value
            if type(operation) is ContentErrorOperation
            else ContentErrorOperation.UNKNOWN.value
        )
        super().__init__(
            code=code,
            layer="content",
            operation=safe_operation,
            http_status=http_status,
        )
