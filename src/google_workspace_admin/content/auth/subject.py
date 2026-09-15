"""Validated Workspace subject value object."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
import unicodedata

from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError


class SubjectResolutionSource(str, Enum):
    PRIMARY_EMAIL = "primary_email"
    ALIAS = "alias"
    USER_ID = "user_id"


_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _required_text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContentSafeError(code="TARGET_SUBJECT_INVALID", operation=ContentErrorOperation.SUBJECT_VALIDATION)
    normalized = unicodedata.normalize("NFKC", value).strip()
    if any(character.isspace() or ord(character) < 32 for character in normalized):
        raise ContentSafeError(code="TARGET_SUBJECT_INVALID", operation=ContentErrorOperation.SUBJECT_VALIDATION)
    return normalized


@dataclass(frozen=True, slots=True)
class WorkspaceSubject:
    """Identity returned only after a future Directory resolution policy."""

    primary_email: str
    user_id: str
    customer_id: str
    domain: str
    suspended: bool
    archived: bool
    mailbox_ready: bool
    resolution_source: SubjectResolutionSource

    def __post_init__(self) -> None:
        email = _required_text(self.primary_email).casefold()
        user_id = _required_text(self.user_id)
        customer_id = _required_text(self.customer_id)
        domain = _required_text(self.domain).casefold()

        if not _EMAIL_PATTERN.fullmatch(email):
            raise ContentSafeError(
                code="TARGET_SUBJECT_INVALID",
                operation=ContentErrorOperation.SUBJECT_VALIDATION,
            )
        if email.rsplit("@", 1)[1] != domain:
            raise ContentSafeError(
                code="TARGET_SUBJECT_INVALID",
                operation=ContentErrorOperation.SUBJECT_VALIDATION,
            )
        for value, field in (
            (self.suspended, "suspended"),
            (self.archived, "archived"),
            (self.mailbox_ready, "mailbox_ready"),
        ):
            if not isinstance(value, bool):
                raise ContentSafeError(
                    code="TARGET_SUBJECT_INVALID",
                    operation=ContentErrorOperation.SUBJECT_VALIDATION,
                )
        if not isinstance(self.resolution_source, SubjectResolutionSource):
            raise ContentSafeError(
                code="TARGET_SUBJECT_INVALID",
                operation=ContentErrorOperation.SUBJECT_VALIDATION,
            )

        object.__setattr__(self, "primary_email", email)
        object.__setattr__(self, "user_id", user_id)
        object.__setattr__(self, "customer_id", customer_id)
        object.__setattr__(self, "domain", domain)
