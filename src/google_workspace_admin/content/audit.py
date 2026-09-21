"""Sanitized audit-event value objects; no persistence is provided."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import hashlib
import hmac
import re
from typing import Protocol, runtime_checkable

from google_workspace_admin.content.auth.scopes import ApprovedScopeProfile
from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError, FailureStage
from google_workspace_admin.content.limits import GLOBAL_CONTENT_CEILING
from google_workspace_admin.content.outcomes import ProcessingStatus
from google_workspace_admin.content.routing import ContentClass
from google_workspace_admin.http_errors import SAFE_ERROR_CODES


_PROFILE_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_PSEUDONYM_PATTERN = re.compile(r"^target_[0-9a-f]{64}$")


@runtime_checkable
class AuditKeyProvider(Protocol):
    """Internal secret provider; the key is never part of an audit event."""

    def get_key(self) -> bytes:
        """Return the deployment-scoped HMAC key."""


class AuditTargetKind(str, Enum):
    DRIVE = "drive"
    MAILBOX = "mailbox"
    DOMAIN = "domain"
    FILE = "file"


class AuditExtent(str, Enum):
    SINGLE_RESOURCE = "single_resource"
    SINGLE_PAGE = "single_page"
    BOUNDED_OPERATION = "bounded_operation"


class ContentAuditOperation(str, Enum):
    DRIVE_LIST = "drive.list"
    DRIVE_GET = "drive.get"
    DRIVE_FILES_LIST = "drive.files.list"
    FILE_CONTENT_READ = "content.file.read"


class ContentAuditReader(str, Enum):
    GOOGLE_DOCS = "google_docs"


@dataclass(frozen=True, slots=True)
class AuditScopeSummary:
    """Closed audit scope metadata; no query or target text is accepted."""

    operation: ContentAuditOperation
    scope_profile: ApprovedScopeProfile
    target_kind: AuditTargetKind
    extent: AuditExtent

    def __post_init__(self) -> None:
        if type(self.operation) is not ContentAuditOperation:
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.AUDIT,
            )
        if not isinstance(self.scope_profile, ApprovedScopeProfile):
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.AUDIT,
            )
        if not isinstance(self.target_kind, AuditTargetKind):
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.AUDIT,
            )
        if not isinstance(self.extent, AuditExtent):
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.AUDIT,
            )


def pseudonymize_target(
    target: str,
    *,
    key_provider: AuditKeyProvider,
) -> str:
    if not isinstance(target, str) or not target.strip():
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.AUDIT,
        )
    if not isinstance(key_provider, AuditKeyProvider):
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.AUDIT,
        )
    key = key_provider.get_key()
    if not isinstance(key, bytes) or not key:
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.AUDIT,
        )
    digest = hmac.new(
        key,
        target.strip().casefold().encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"target_{digest}"


@dataclass(frozen=True, slots=True)
class AuditEvent:
    timestamp: datetime
    operation: ContentAuditOperation
    auditor_profile_id: str
    target_pseudonym: str | None
    scope_summary: AuditScopeSummary
    result_count: int | None
    success: bool
    safe_error_code: str | None = None
    content_class: ContentClass | None = None
    reader: ContentAuditReader | None = None
    processing_status: ProcessingStatus | None = None
    failure_stage: FailureStage | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.timestamp, datetime) or self.timestamp.tzinfo is None:
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.AUDIT,
            )
        if type(self.operation) is not ContentAuditOperation:
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.AUDIT,
            )
        if not isinstance(self.auditor_profile_id, str) or not _PROFILE_PATTERN.fullmatch(
            self.auditor_profile_id
        ):
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.AUDIT,
            )
        if self.target_pseudonym is not None and not _PSEUDONYM_PATTERN.fullmatch(
            self.target_pseudonym
        ):
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.AUDIT,
            )
        if type(self.scope_summary) is not AuditScopeSummary:
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.AUDIT,
            )
        if self.result_count is not None and (
            isinstance(self.result_count, bool)
            or not isinstance(self.result_count, int)
            or self.result_count < 0
            or self.result_count > GLOBAL_CONTENT_CEILING
        ):
            raise ContentSafeError(
                code="CONTEXT_LIMIT_EXCEEDED",
                operation=ContentErrorOperation.AUDIT,
            )
        if not isinstance(self.success, bool):
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.AUDIT,
            )
        if self.safe_error_code is not None and self.safe_error_code not in SAFE_ERROR_CODES:
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.AUDIT,
            )
        if self.failure_stage is not None and type(self.failure_stage) is not FailureStage:
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.AUDIT,
            )
        docs_event = self.operation is ContentAuditOperation.FILE_CONTENT_READ
        if docs_event:
            if (
                self.content_class is not ContentClass.GOOGLE_DOC
                or self.reader is not ContentAuditReader.GOOGLE_DOCS
                or not isinstance(self.processing_status, ProcessingStatus)
            ):
                raise ContentSafeError(
                    code="LOCAL_VALIDATION",
                    operation=ContentErrorOperation.AUDIT,
                )
            if self.processing_status in {
                ProcessingStatus.PROCESSED,
                ProcessingStatus.EMPTY,
                ProcessingStatus.PARTIALLY_PROCESSED,
            } and self.failure_stage is not None:
                raise ContentSafeError(
                    code="LOCAL_VALIDATION",
                    operation=ContentErrorOperation.AUDIT,
                )
        elif any(
            value is not None
            for value in (self.content_class, self.reader, self.processing_status, self.failure_stage)
        ):
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.AUDIT,
            )
