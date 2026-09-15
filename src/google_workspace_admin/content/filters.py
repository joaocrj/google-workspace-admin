"""Structured Drive filters with an unconditional trashed=false predicate."""

from __future__ import annotations

from dataclasses import dataclass
import re

from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError


_FILTER_TEXT = re.compile(r"^[^\x00-\x1f\x7f]{1,256}$")


def _filter_text(value: object) -> str:
    if not isinstance(value, str):
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.DRIVE_FILTER)
    normalized = value.strip()
    if not normalized or not _FILTER_TEXT.fullmatch(normalized):
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.DRIVE_FILTER)
    return normalized


def _quote_query_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


@dataclass(frozen=True, slots=True)
class DriveFilesFilter:
    """Only structured predicates are accepted; q is never caller-supplied."""

    parent_id: str | None = None
    mime_type: str | None = None
    name_contains: str | None = None
    modified_time_after: str | None = None

    def __post_init__(self) -> None:
        for value, name in (
            (self.parent_id, "parent_id"),
            (self.mime_type, "mime_type"),
            (self.name_contains, "name_contains"),
            (self.modified_time_after, "modified_time_after"),
        ):
            if value is not None:
                object.__setattr__(
                    self,
                    name,
                    _filter_text(value),
                )

    def to_query(self) -> str:
        clauses = ["trashed = false"]
        if self.parent_id is not None:
            clauses.append(
                f"'{_quote_query_value(self.parent_id)}' in parents"
            )
        if self.mime_type is not None:
            clauses.append(
                f"mimeType = '{_quote_query_value(self.mime_type)}'"
            )
        if self.name_contains is not None:
            clauses.append(
                f"name contains '{_quote_query_value(self.name_contains)}'"
            )
        if self.modified_time_after is not None:
            clauses.append(
                "modifiedTime > "
                f"'{_quote_query_value(self.modified_time_after)}'"
            )
        return " and ".join(clauses)
