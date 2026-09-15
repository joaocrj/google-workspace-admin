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
    DRIVE_FILTER = "content.drive.filter"
    PAGINATION = "content.pagination"
    CONTEXT_LIMIT = "content.context_limit"
    RETRY_POLICY = "content.retry"
    TRANSPORT = "content.transport"
    RESPONSE_DRIVE_LIST = "content.response.drive_list"
    RESPONSE_DRIVE_GET = "content.response.drive_get"
    RESPONSE_DRIVE_FILES_LIST = "content.response.drive_files_list"
    EVIDENCE = "content.evidence"
    AUDIT = "content.audit"
    BOOTSTRAP = "content.bootstrap"
    RUNTIME = "content.runtime"


class ContentSafeError(SafeOperationError):
    """Content error without raw Google bodies, headers, or credentials."""

    def __init__(
        self,
        *,
        code: str,
        operation: ContentErrorOperation,
        http_status: int | None = None,
        category: str | None = None,
    ) -> None:
        self.category = category
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
