"""Validated internal inventory snapshots and download preflight policy."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError
from google_workspace_admin.content.routing import MAX_MIME_LENGTH, validate_mime_type


MAX_FILE_ID_LENGTH = 256
MAX_MODIFIED_TIME_LENGTH = 128
MAX_INT64 = 9_223_372_036_854_775_807


def _opaque(value: object, *, maximum: int) -> str:
    if type(value) is not str:
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_SNAPSHOT)
    folded = value.casefold()
    if (
        not value
        or len(value) > maximum
        or any(character.isspace() or ord(character) < 32 or 0x7F <= ord(character) <= 0x9F for character in value)
        or "://" in value
        or any(character in value for character in ("/", "\\", "?", "#"))
        or folded.startswith(("http:", "https:", "drive.google.com/", "www.googleapis.com/"))
    ):
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_SNAPSHOT)
    return value


@dataclass(frozen=True, slots=True)
class InventorySnapshot:
    file_id: str
    expected_mime_type: str
    modified_time: str | None = None
    size: int | None = None

    def __post_init__(self) -> None:
        if type(self) is not InventorySnapshot:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_SNAPSHOT)
        _opaque(self.file_id, maximum=MAX_FILE_ID_LENGTH)
        mime_type = validate_mime_type(self.expected_mime_type)
        if len(mime_type) > MAX_MIME_LENGTH:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_SNAPSHOT)
        if self.modified_time is not None:
            if type(self.modified_time) is not str or not self.modified_time or len(self.modified_time) > MAX_MODIFIED_TIME_LENGTH or any(character.isspace() or ord(character) < 32 or 0x7F <= ord(character) <= 0x9F for character in self.modified_time):
                raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_SNAPSHOT)
        if self.size is not None and (isinstance(self.size, bool) or type(self.size) is not int or self.size < 0 or self.size > MAX_INT64):
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_SNAPSHOT)
        object.__setattr__(self, "expected_mime_type", mime_type)

    def same_version(self, other: object) -> bool:
        """Compare immutable inventory identity/version data for TOCTOU checks."""

        if type(other) is not InventorySnapshot:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_SNAPSHOT)
        return (
            self.file_id,
            self.expected_mime_type,
            self.modified_time,
            self.size,
        ) == (
            other.file_id,
            other.expected_mime_type,
            other.modified_time,
            other.size,
        )


class DownloadPreflightDecision(str, Enum):
    ALLOWED = "ALLOWED"
    NOT_ALLOWED = "NOT_ALLOWED"


@dataclass(frozen=True, slots=True)
class DownloadPreflight:
    """Internal result of a future bounded ``capabilities.canDownload`` check."""

    can_download: bool

    def __post_init__(self) -> None:
        if type(self) is not DownloadPreflight:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_PREFLIGHT)
        if type(self.can_download) is not bool:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_PREFLIGHT)

    @property
    def decision(self) -> DownloadPreflightDecision:
        return DownloadPreflightDecision.ALLOWED if self.can_download else DownloadPreflightDecision.NOT_ALLOWED

    def require_allowed(self) -> None:
        if not self.can_download:
            raise ContentSafeError(code="DOWNLOAD_NOT_ALLOWED", operation=ContentErrorOperation.READING_PREFLIGHT)
