"""Closed MIME routing for future Content readers.

This module deliberately contains no parser registry and no caller-provided
mapping.  MIME is the only routing input; unknown values fail closed.
"""

from __future__ import annotations

from enum import Enum
from types import MappingProxyType
from typing import Final

from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError


class ContentClass(str, Enum):
    GOOGLE_DOC = "GOOGLE_DOC"
    GOOGLE_SHEET = "GOOGLE_SHEET"
    GOOGLE_SLIDE = "GOOGLE_SLIDE"
    GOOGLE_FOLDER = "GOOGLE_FOLDER"
    PDF = "PDF"
    MICROSOFT_WORD = "MICROSOFT_WORD"
    MICROSOFT_EXCEL = "MICROSOFT_EXCEL"
    MICROSOFT_POWERPOINT = "MICROSOFT_POWERPOINT"
    TEXT = "TEXT"
    CSV = "CSV"
    JSON = "JSON"
    XML = "XML"
    ARCHIVE = "ARCHIVE"
    IMAGE = "IMAGE"
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"
    OTHER_BINARY = "OTHER_BINARY"
    UNKNOWN = "UNKNOWN"


MAX_MIME_LENGTH: Final[int] = 256


def _is_control(value: str) -> bool:
    return any(ord(character) < 32 or 0x7F <= ord(character) <= 0x9F for character in value)


_EXACT_MIME_CLASSES = MappingProxyType(
    {
        "application/vnd.google-apps.document": ContentClass.GOOGLE_DOC,
        "application/vnd.google-apps.spreadsheet": ContentClass.GOOGLE_SHEET,
        "application/vnd.google-apps.presentation": ContentClass.GOOGLE_SLIDE,
        "application/vnd.google-apps.folder": ContentClass.GOOGLE_FOLDER,
        "application/pdf": ContentClass.PDF,
        "application/msword": ContentClass.MICROSOFT_WORD,
        "application/vnd.ms-word": ContentClass.MICROSOFT_WORD,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ContentClass.MICROSOFT_WORD,
        "application/vnd.ms-excel": ContentClass.MICROSOFT_EXCEL,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ContentClass.MICROSOFT_EXCEL,
        "application/vnd.ms-powerpoint": ContentClass.MICROSOFT_POWERPOINT,
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": ContentClass.MICROSOFT_POWERPOINT,
        "text/plain": ContentClass.TEXT,
        "text/csv": ContentClass.CSV,
        "application/csv": ContentClass.CSV,
        "application/json": ContentClass.JSON,
        "text/json": ContentClass.JSON,
        "application/xml": ContentClass.XML,
        "text/xml": ContentClass.XML,
        "application/zip": ContentClass.ARCHIVE,
        "application/x-7z-compressed": ContentClass.ARCHIVE,
        "application/x-rar-compressed": ContentClass.ARCHIVE,
        "application/gzip": ContentClass.ARCHIVE,
        "application/x-gzip": ContentClass.ARCHIVE,
        "application/x-tar": ContentClass.ARCHIVE,
        "application/x-bzip2": ContentClass.ARCHIVE,
        "image/png": ContentClass.IMAGE,
        "image/jpeg": ContentClass.IMAGE,
        "image/tiff": ContentClass.IMAGE,
        "image/gif": ContentClass.IMAGE,
        "audio/mpeg": ContentClass.AUDIO,
        "audio/wav": ContentClass.AUDIO,
        "audio/ogg": ContentClass.AUDIO,
        "video/mp4": ContentClass.VIDEO,
        "video/quicktime": ContentClass.VIDEO,
        "video/webm": ContentClass.VIDEO,
        "application/octet-stream": ContentClass.OTHER_BINARY,
    }
)


def validate_mime_type(value: object) -> str:
    """Validate a MIME value without interpreting filename extensions."""

    if type(value) is not str:
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_ROUTER)
    if _is_control(value):
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_ROUTER)
    normalized = value.strip().lower()
    if not normalized or len(normalized) > MAX_MIME_LENGTH or _is_control(normalized):
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_ROUTER)
    if any(character.isspace() for character in normalized):
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_ROUTER)
    return normalized


def route_mime_type(value: object) -> ContentClass:
    """Return the closed class for an allowlisted MIME value.

    Media types are listed explicitly; an unlisted subtype becomes ``UNKNOWN``
    and is handled fail-closed.
    """

    mime_type = validate_mime_type(value)
    exact = _EXACT_MIME_CLASSES.get(mime_type)
    if exact is not None:
        return exact
    return ContentClass.UNKNOWN


def allowlisted_mime_types() -> tuple[str, ...]:
    """Return a stable copy of exact MIME values accepted by the router."""

    return tuple(sorted(_EXACT_MIME_CLASSES))
