"""Non-secret, externally configured Content identity boundaries.

Only installation identifiers are read from the environment.  OAuth scopes,
operation capabilities, administrative privileges and HTTP destinations stay
closed in the Content source code.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import os
import re

from google_workspace_admin.content.auth.profile import (
    CONTENT_ADMINISTRATIVE_AUDITOR,
    CONTENT_ALLOWED_DOMAIN,
)
from google_workspace_admin.content.auth.registry import ProvisionedContentProfile
from google_workspace_admin.content.auth.scopes import ApprovedScopeProfile
from google_workspace_admin.content.auth.subject import (
    SubjectResolutionSource,
    WorkspaceSubject,
)
from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError


CONTENT_DISCOVERY_PROFILE_ID = "drive-discovery"

CONTENT_PROJECT_ID_ENV = "GOOGLE_WORKSPACE_CONTENT_PROJECT_ID"
CONTENT_SERVICE_ACCOUNT_ENV = "GOOGLE_WORKSPACE_CONTENT_SERVICE_ACCOUNT"
CONTENT_SUBJECT_ENV = "GOOGLE_WORKSPACE_CONTENT_SUBJECT"
CONTENT_CUSTOMER_ID_ENV = "GOOGLE_WORKSPACE_CONTENT_CUSTOMER_ID"
CONTENT_DOMAIN_ENV = "GOOGLE_WORKSPACE_CONTENT_DOMAIN"

CONTENT_REQUIRED_ENV_VARS = (
    CONTENT_PROJECT_ID_ENV,
    CONTENT_SERVICE_ACCOUNT_ENV,
    CONTENT_SUBJECT_ENV,
    CONTENT_CUSTOMER_ID_ENV,
    CONTENT_DOMAIN_ENV,
)

_PROJECT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]{4,29}$")
_SERVICE_ACCOUNT_PATTERN = re.compile(
    r"^[^@\s]+@[^@\s]+\.iam\.gserviceaccount\.com$"
)
_CUSTOMER_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _configuration_failure(
    code: str = "LOCAL_VALIDATION",
) -> ContentSafeError:
    return ContentSafeError(
        code=code,
        operation=ContentErrorOperation.BOOTSTRAP,
    )


def _required_environment_value(
    environment: Mapping[str, str],
    name: str,
) -> str:
    value = environment.get(name)
    if not isinstance(value, str) or not value.strip():
        raise _configuration_failure("CONTENT_NOT_SUPPORTED")
    normalized = value.strip()
    if any(
        character.isspace()
        or ord(character) < 32
        or 0x7F <= ord(character) <= 0x9F
        for character in normalized
    ):
        raise _configuration_failure()
    return normalized


@dataclass(frozen=True, slots=True)
class ContentConfig:
    """Trusted startup configuration containing identifiers only."""

    project_id: str
    service_account: str
    subject: str
    customer_id: str
    domain: str

    def __post_init__(self) -> None:
        project_id = _required_text(self.project_id)
        service_account = _required_text(self.service_account)
        subject = _required_text(self.subject).casefold()
        customer_id = _required_text(self.customer_id)
        domain = _required_text(self.domain).casefold()

        if not _PROJECT_ID_PATTERN.fullmatch(project_id):
            raise _configuration_failure()
        if not _SERVICE_ACCOUNT_PATTERN.fullmatch(service_account):
            raise _configuration_failure()
        if not _CUSTOMER_ID_PATTERN.fullmatch(customer_id):
            raise _configuration_failure()
        if customer_id.casefold() == "my_customer":
            raise _configuration_failure()
        if domain != CONTENT_ALLOWED_DOMAIN:
            raise _configuration_failure("MAILBOX_NOT_ALLOWED")
        if not _EMAIL_PATTERN.fullmatch(subject):
            raise _configuration_failure("TARGET_SUBJECT_INVALID")
        if subject.rsplit("@", 1)[1].casefold() != domain:
            raise _configuration_failure("MAILBOX_NOT_ALLOWED")

        object.__setattr__(self, "project_id", project_id)
        object.__setattr__(self, "service_account", service_account)
        object.__setattr__(self, "subject", subject)
        object.__setattr__(self, "customer_id", customer_id)
        object.__setattr__(self, "domain", domain)

    def __repr__(self) -> str:
        return "<ContentConfig identifiers-only redacted>"

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> "ContentConfig":
        """Parse configuration lazily, without touching credentials."""

        source = os.environ if environment is None else environment
        return cls(
            project_id=_required_environment_value(source, CONTENT_PROJECT_ID_ENV),
            service_account=_required_environment_value(
                source,
                CONTENT_SERVICE_ACCOUNT_ENV,
            ),
            subject=_required_environment_value(source, CONTENT_SUBJECT_ENV),
            customer_id=_required_environment_value(
                source,
                CONTENT_CUSTOMER_ID_ENV,
            ),
            domain=_required_environment_value(source, CONTENT_DOMAIN_ENV),
        )

    def to_provisioned_profile(self) -> ProvisionedContentProfile:
        """Create the only ordinary discovery profile supported here."""

        return ProvisionedContentProfile(
            profile_id=CONTENT_DISCOVERY_PROFILE_ID,
            service_account=self.service_account,
            customer_id=self.customer_id,
            allowed_domain=self.domain,
            administrative_auditor=CONTENT_ADMINISTRATIVE_AUDITOR,
            approved_scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
        )

    def fixed_subject(self) -> WorkspaceSubject:
        """Build the fixed configured subject without a Directory lookup.

        Drive discovery needs only a delegated primary email.  The foundation
        value object's user_id is retained as the same opaque configured
        identifier; no user ID lookup or Directory API call is performed.
        """

        return WorkspaceSubject(
            primary_email=self.subject,
            user_id=self.subject,
            customer_id=self.customer_id,
            domain=self.domain,
            suspended=False,
            archived=False,
            mailbox_ready=False,
            resolution_source=SubjectResolutionSource.PRIMARY_EMAIL,
        )


def load_content_config() -> ContentConfig:
    """Load installation configuration only when Content is used."""

    return ContentConfig.from_environment()


def discovery_request_identity() -> tuple[str, str]:
    """Return the fixed MCP-to-Content identity, or fail closed."""

    config = load_content_config()
    return CONTENT_DISCOVERY_PROFILE_ID, config.subject


def _required_text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _configuration_failure()
    normalized = value.strip()
    if any(
        character.isspace()
        or ord(character) < 32
        or 0x7F <= ord(character) <= 0x9F
        for character in normalized
    ):
        raise _configuration_failure()
    return normalized
