"""Minimal, content-free evidence references with generated identifiers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import re

from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError


class EvidenceSourceType(str, Enum):
    DRIVE = "drive"
    GMAIL = "gmail"


_RESOURCE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$")
_LOCATOR_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/#=\-]{0,255}$")


def _required_reference(
    value: object,
    pattern: re.Pattern[str],
) -> str:
    if not isinstance(value, str):
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.EVIDENCE)
    normalized = value.strip()
    if not pattern.fullmatch(normalized):
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.EVIDENCE)
    return normalized


def evidence_id_for(
    source_type: EvidenceSourceType,
    resource_id: str,
    locator: str,
) -> str:
    if not isinstance(source_type, EvidenceSourceType):
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.EVIDENCE,
        )
    safe_resource_id = _required_reference(
        resource_id,
        _RESOURCE_PATTERN,
    )
    safe_locator = _required_reference(
        locator,
        _LOCATOR_PATTERN,
    )
    material = "\0".join((source_type.value, safe_resource_id, safe_locator))
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return f"ev_{digest}"


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    source_type: EvidenceSourceType
    resource_id: str
    locator: str
    evidence_id: str = field(init=False)
    truncated: bool = False
    redacted: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.source_type, EvidenceSourceType):
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.EVIDENCE,
            )
        resource_id = _required_reference(
            self.resource_id,
            _RESOURCE_PATTERN,
        )
        locator = _required_reference(
            self.locator,
            _LOCATOR_PATTERN,
        )
        if not isinstance(self.truncated, bool) or not isinstance(
            self.redacted,
            bool,
        ):
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.EVIDENCE,
            )
        object.__setattr__(self, "resource_id", resource_id)
        object.__setattr__(self, "locator", locator)
        object.__setattr__(
            self,
            "evidence_id",
            evidence_id_for(self.source_type, resource_id, locator),
        )
