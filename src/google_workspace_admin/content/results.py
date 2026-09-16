"""Typed, allowlisted results for the future Shared Drive operations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict

from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError
from google_workspace_admin.content.limits import GLOBAL_CONTENT_CEILING, validate_positive_int


def _text(value: object, operation: ContentErrorOperation) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContentSafeError(code="RESPONSE_VALIDATION", operation=operation)
    return value.strip()


def _optional_text(value: object, operation: ContentErrorOperation) -> str | None:
    return None if value is None else _text(value, operation)


def _next_page_token(
    payload: Mapping[str, object], operation: ContentErrorOperation
) -> str | None:
    value = payload.get("nextPageToken")
    return None if value is None else _text(value, operation)


def _opaque_next_page_token(
    payload: Mapping[str, object], operation: ContentErrorOperation
) -> str | None:
    value = payload.get("nextPageToken")
    if value is None:
        return None
    if type(value) is not str or not value or any(
        character.isspace()
        or ord(character) < 32
        or 0x7F <= ord(character) <= 0x9F
        for character in value
    ):
        raise ContentSafeError(code="RESPONSE_VALIDATION", operation=operation)
    return value


@dataclass(frozen=True, slots=True)
class DriveSummary:
    drive_id: str
    name: str


@dataclass(frozen=True, slots=True)
class DriveListPage:
    items: tuple[DriveSummary, ...]
    next_page_token: str | None
    truncated: bool


@dataclass(frozen=True, slots=True)
class DriveGetResult:
    drive: DriveSummary


@dataclass(frozen=True, slots=True)
class DriveFileSummary:
    file_id: str
    name: str
    mime_type: str
    parents: tuple[str, ...]
    modified_time: str | None
    size: int | None
    trashed: bool


@dataclass(frozen=True, slots=True)
class DriveFileListPage:
    items: tuple[DriveFileSummary, ...]
    next_page_token: str | None
    truncated: bool


class DriveFileInventoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    file_id: str
    name: str
    mime_type: str
    modified_time: str | None
    size: int | None
    parents: list[str]


class DriveFileInventoryPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    files: list[DriveFileInventoryItem]
    next_page_token: str | None


def _mapping(value: object, operation: ContentErrorOperation) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ContentSafeError(code="RESPONSE_VALIDATION", operation=operation)
    return value


def _drive_summary(value: object, operation: ContentErrorOperation) -> DriveSummary:
    item = _mapping(value, operation)
    return DriveSummary(
        drive_id=_text(item.get("id"), operation),
        name=_text(item.get("name"), operation),
    )


def _bounded_items(
    payload: Mapping[str, object],
    field: str,
    operation: ContentErrorOperation,
    max_items: int,
) -> list[object]:
    validate_positive_int(
        max_items,
        name=ContentErrorOperation.PAGINATION,
        maximum=GLOBAL_CONTENT_CEILING,
    )
    raw_items = payload.get(field, [])
    if not isinstance(raw_items, list):
        raise ContentSafeError(code="RESPONSE_VALIDATION", operation=operation)
    if len(raw_items) > max_items:
        raise ContentSafeError(code="CONTEXT_LIMIT_EXCEEDED", operation=operation)
    return raw_items


def parse_drive_list(payload: Mapping[str, object], *, max_items: int) -> DriveListPage:
    operation = ContentErrorOperation.RESPONSE_DRIVE_LIST
    body = _mapping(payload, operation)
    items = tuple(
        _drive_summary(item, operation)
        for item in _bounded_items(body, "drives", operation, max_items)
    )
    token = _next_page_token(body, operation)
    return DriveListPage(items=items, next_page_token=token, truncated=token is not None)


def parse_drive_get(payload: Mapping[str, object]) -> DriveGetResult:
    operation = ContentErrorOperation.RESPONSE_DRIVE_GET
    return DriveGetResult(drive=_drive_summary(payload, operation))


def _drive_file(value: object) -> DriveFileSummary:
    operation = ContentErrorOperation.RESPONSE_DRIVE_FILES_LIST
    item = _mapping(value, operation)
    raw_parents = item.get("parents", [])
    if not isinstance(raw_parents, list) or any(
        not isinstance(parent, str)
        or not parent
        or any(
            character.isspace()
            or ord(character) < 32
            or 0x7F <= ord(character) <= 0x9F
            for character in parent
        )
        for parent in raw_parents
    ):
        raise ContentSafeError(code="RESPONSE_VALIDATION", operation=operation)
    if "trashed" not in item or item["trashed"] is not False:
        raise ContentSafeError(code="RESPONSE_VALIDATION", operation=operation)
    raw_size = item.get("size")
    size: int | None = None
    if raw_size is not None:
        if (
            not isinstance(raw_size, str)
            or not raw_size
            or not raw_size.isascii()
            or not raw_size.isdigit()
        ):
            raise ContentSafeError(code="RESPONSE_VALIDATION", operation=operation)
        size = int(raw_size)
        if size > 9_223_372_036_854_775_807:
            raise ContentSafeError(code="RESPONSE_VALIDATION", operation=operation)
    return DriveFileSummary(
        file_id=_text(item.get("id"), operation),
        name=_text(item.get("name"), operation),
        mime_type=_text(item.get("mimeType"), operation),
        parents=tuple(raw_parents),
        modified_time=_optional_text(item.get("modifiedTime"), operation),
        size=size,
        trashed=False,
    )


def parse_drive_files_list(
    payload: Mapping[str, object], *, max_items: int
) -> DriveFileListPage:
    operation = ContentErrorOperation.RESPONSE_DRIVE_FILES_LIST
    body = _mapping(payload, operation)
    items = tuple(
        _drive_file(item)
        for item in _bounded_items(body, "files", operation, max_items)
    )
    token = _opaque_next_page_token(body, operation)
    return DriveFileListPage(items=items, next_page_token=token, truncated=token is not None)
