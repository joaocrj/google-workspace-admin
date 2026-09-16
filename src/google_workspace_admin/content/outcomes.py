"""Closed processing outcomes and budget-exhaustion semantics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError
from google_workspace_admin.content.routing import ContentClass


class ProcessingStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    ROUTED = "ROUTED"
    READING = "READING"
    NORMALIZING = "NORMALIZING"
    PROCESSED = "PROCESSED"
    EMPTY = "EMPTY"
    PARTIALLY_PROCESSED = "PARTIALLY_PROCESSED"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    NATIVE_TYPE_UNSUPPORTED = "NATIVE_TYPE_UNSUPPORTED"
    TOO_LARGE = "TOO_LARGE"
    ENCRYPTED = "ENCRYPTED"
    CORRUPTED = "CORRUPTED"
    ACCESS_DENIED = "ACCESS_DENIED"
    NOT_FOUND = "NOT_FOUND"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    DOWNLOAD_NOT_ALLOWED = "DOWNLOAD_NOT_ALLOWED"
    EXPORT_NOT_SUPPORTED = "EXPORT_NOT_SUPPORTED"
    SKIPPED_BY_POLICY = "SKIPPED_BY_POLICY"
    CHANGED_DURING_AUDIT = "CHANGED_DURING_AUDIT"
    TRANSIENT_UPSTREAM = "TRANSIENT_UPSTREAM"


NON_TERMINAL_STATUSES = frozenset(
    {
        ProcessingStatus.DISCOVERED,
        ProcessingStatus.ROUTED,
        ProcessingStatus.READING,
        ProcessingStatus.NORMALIZING,
    }
)
SUCCESS_STATUSES = frozenset({ProcessingStatus.PROCESSED, ProcessingStatus.EMPTY})
PARTIAL_STATUSES = frozenset({ProcessingStatus.PARTIALLY_PROCESSED})
FAILURE_STATUSES = frozenset(set(ProcessingStatus) - NON_TERMINAL_STATUSES - SUCCESS_STATUSES - PARTIAL_STATUSES)
TERMINAL_STATUSES = frozenset(set(ProcessingStatus) - NON_TERMINAL_STATUSES)


class SafeContentErrorCode(str, Enum):
    LOCAL_VALIDATION = "LOCAL_VALIDATION"
    CONTENT_NOT_SUPPORTED = "CONTENT_NOT_SUPPORTED"
    ACCESS_DENIED = "ACCESS_DENIED"
    NOT_FOUND = "NOT_FOUND"
    TOO_LARGE = "TOO_LARGE"
    ENCRYPTED = "ENCRYPTED"
    DOWNLOAD_NOT_ALLOWED = "DOWNLOAD_NOT_ALLOWED"
    DOWNLOAD_FAILED = "DOWNLOAD_FAILED"
    EXPORT_NOT_SUPPORTED = "EXPORT_NOT_SUPPORTED"
    EXPORT_FAILED = "EXPORT_FAILED"
    PARSE_FAILED = "PARSE_FAILED"
    RESPONSE_VALIDATION = "RESPONSE_VALIDATION"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    TRANSIENT_UPSTREAM = "TRANSIENT_UPSTREAM"
    CHANGED_DURING_AUDIT = "CHANGED_DURING_AUDIT"


MAX_OUTCOME_COUNT = 500
MAX_REASON_LENGTH = 256
MAX_CONTINUATION_LENGTH = 4096


def _count(value: object) -> int:
    if isinstance(value, bool) or type(value) is not int or value < 0 or value > MAX_OUTCOME_COUNT:
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_OUTCOME)
    return value


def _token(value: object) -> str | None:
    if value is None:
        return None
    if type(value) is not str or not value or len(value) > MAX_CONTINUATION_LENGTH or any(character.isspace() or ord(character) < 32 or 0x7F <= ord(character) <= 0x9F for character in value):
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_OUTCOME)
    return value


def _reason(value: object, *, required: bool) -> str | None:
    if value is None and not required:
        return None
    if type(value) is not str or not value or len(value) > MAX_REASON_LENGTH or any(ord(character) < 32 or 0x7F <= ord(character) <= 0x9F for character in value):
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_OUTCOME)
    return value


@dataclass(frozen=True, slots=True)
class ProcessingOutcome:
    processing_status: ProcessingStatus
    content_class: ContentClass
    chunk_count: int = 0
    result_count: int = 0
    truncated: bool = False
    partial_reason: str | None = None
    continuation: str | None = None
    safe_error_code: SafeContentErrorCode | None = None

    def __post_init__(self) -> None:
        if type(self.processing_status) is not ProcessingStatus or self.processing_status in NON_TERMINAL_STATUSES:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_OUTCOME)
        if type(self.content_class) is not ContentClass:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_OUTCOME)
        _count(self.chunk_count)
        _count(self.result_count)
        if type(self.truncated) is not bool:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_OUTCOME)
        token = _token(self.continuation)
        if self.safe_error_code is not None and type(self.safe_error_code) is not SafeContentErrorCode:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_OUTCOME)

        status = self.processing_status
        if status is ProcessingStatus.PROCESSED:
            if self.chunk_count < 1 or self.truncated or self.partial_reason is not None or token is not None or self.safe_error_code is not None:
                raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_OUTCOME)
            _reason(self.partial_reason, required=False)
        elif status is ProcessingStatus.EMPTY:
            if self.chunk_count != 0 or self.result_count != 0 or self.truncated or self.partial_reason is not None or token is not None or self.safe_error_code is not None:
                raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_OUTCOME)
        elif status is ProcessingStatus.PARTIALLY_PROCESSED:
            if self.chunk_count < 1 or not self.truncated or token is None:
                raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_OUTCOME)
            _reason(self.partial_reason, required=True)
        else:
            if self.truncated or self.partial_reason is not None or token is not None:
                raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_OUTCOME)

        object.__setattr__(self, "continuation", token)

    @property
    def is_terminal(self) -> bool:
        return self.processing_status in TERMINAL_STATUSES

    @property
    def is_success(self) -> bool:
        return self.processing_status in SUCCESS_STATUSES

    @property
    def is_partial(self) -> bool:
        return self.processing_status in PARTIAL_STATUSES

    @property
    def is_failure(self) -> bool:
        return self.processing_status in FAILURE_STATUSES


def classify_budget_exhaustion(*, safe_continuation_possible: bool, absolute_limit_exceeded: bool) -> ProcessingStatus:
    """Choose partial continuation versus terminal ``TOO_LARGE``.

    A first bounded operation reaching its chunk budget is not automatically a
    terminal failure.  It becomes partial when a safe opaque continuation can
    resume the remaining work; an impossible continuation or absolute limit is
    terminal ``TOO_LARGE``.
    """

    if type(safe_continuation_possible) is not bool or type(absolute_limit_exceeded) is not bool:
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_BUDGET)
    if absolute_limit_exceeded:
        return ProcessingStatus.TOO_LARGE
    return ProcessingStatus.PARTIALLY_PROCESSED if safe_continuation_possible else ProcessingStatus.TOO_LARGE
