"""Immutable Content Research authorization profile."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re

from google_workspace_admin.content.auth.capabilities import AdminCapability
from google_workspace_admin.content.auth.scopes import (
    ApprovedScopeProfile,
    scopes_for,
)
from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError


class ReadonlyCapabilityProfile(str, Enum):
    """Closed capability label; no write capability is represented."""

    CONTENT_READ_ONLY = "content_read_only"


CONTENT_ALLOWED_DOMAIN = "cevalente.com.br"
CONTENT_ADMINISTRATIVE_AUDITOR = "suporte.ti@cevalente.com.br"


_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_CUSTOMER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_SERVICE_ACCOUNT_PATTERN = re.compile(
    r"^[^@\s]+@[^@\s]+\.iam\.gserviceaccount\.com$"
)


def _require_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.AUTH_PROFILE_VALIDATION,
        )

    normalized = value.strip()
    if any(ord(character) < 32 for character in normalized):
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.AUTH_PROFILE_VALIDATION,
        )
    return normalized


@dataclass(frozen=True, slots=True)
class ContentAuthProfile:
    """Fixed identity and policy context for future Content reads."""

    profile_id: str
    service_account: str
    customer_id: str
    allowed_domain: str
    administrative_auditor: str
    approved_scope_profile: ApprovedScopeProfile
    readonly_capability_profile: str = (
        ReadonlyCapabilityProfile.CONTENT_READ_ONLY
    )
    admin_capability: AdminCapability = AdminCapability.NONE

    def __post_init__(self) -> None:
        profile_id = _require_text(self.profile_id, "profile_id")
        if not _IDENTIFIER_PATTERN.fullmatch(profile_id):
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.AUTH_PROFILE_VALIDATION,
            )

        service_account = _require_text(
            self.service_account,
            "service_account",
        )
        customer_id = _require_text(self.customer_id, "customer_id")
        allowed_domain = _require_text(
            self.allowed_domain,
            "allowed_domain",
        ).lower()
        auditor = _require_text(
            self.administrative_auditor,
            "administrative_auditor",
        ).lower()

        if not _SERVICE_ACCOUNT_PATTERN.fullmatch(service_account):
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.AUTH_PROFILE_VALIDATION,
            )
        if not _CUSTOMER_PATTERN.fullmatch(customer_id):
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.AUTH_PROFILE_VALIDATION,
            )
        if "@" not in auditor or auditor.rsplit("@", 1)[1] != allowed_domain:
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.AUTH_PROFILE_VALIDATION,
            )
        if allowed_domain != CONTENT_ALLOWED_DOMAIN:
            raise ContentSafeError(
                code="MAILBOX_NOT_ALLOWED",
                operation=ContentErrorOperation.AUTH_PROFILE_VALIDATION,
            )
        if auditor != CONTENT_ADMINISTRATIVE_AUDITOR:
            raise ContentSafeError(
                code="TARGET_SUBJECT_INVALID",
                operation=ContentErrorOperation.AUTH_PROFILE_VALIDATION,
            )
        if not isinstance(
            self.approved_scope_profile,
            ApprovedScopeProfile,
        ):
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.AUTH_PROFILE_VALIDATION,
            )
        if not isinstance(
            self.readonly_capability_profile,
            ReadonlyCapabilityProfile,
        ) or self.readonly_capability_profile is not ReadonlyCapabilityProfile.CONTENT_READ_ONLY:
            raise ContentSafeError(
                code="READ_ONLY_OPERATION_FORBIDDEN",
                operation=ContentErrorOperation.AUTH_PROFILE_VALIDATION,
            )
        if not isinstance(self.admin_capability, AdminCapability):
            raise ContentSafeError(
                code="READ_ONLY_OPERATION_FORBIDDEN",
                operation=ContentErrorOperation.AUTH_PROFILE_VALIDATION,
            )

        # Resolve once during validation so an invalid profile cannot be held
        # by a future token broker.  The value is intentionally not stored as
        # a mutable list.
        scopes_for(self.approved_scope_profile)

        object.__setattr__(self, "profile_id", profile_id)
        object.__setattr__(self, "service_account", service_account)
        object.__setattr__(self, "customer_id", customer_id)
        object.__setattr__(self, "allowed_domain", allowed_domain)
        object.__setattr__(self, "administrative_auditor", auditor)

    @property
    def approved_scopes(self) -> tuple[str, ...]:
        return scopes_for(self.approved_scope_profile)
