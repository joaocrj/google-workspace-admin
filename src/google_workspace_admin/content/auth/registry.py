"""Startup-only profile provisioning for the sealed Content runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from google_workspace_admin.content.auth.capabilities import AdminCapability
from google_workspace_admin.content.auth.handles import RegisteredProfileHandle
from google_workspace_admin.content.auth.profile import ContentAuthProfile
from google_workspace_admin.content.auth.scopes import ApprovedScopeProfile
from google_workspace_admin.content.errors import ContentSafeError


@dataclass(frozen=True, slots=True)
class ProvisionedContentProfile:
    """Trusted startup data; never an operation or MCP invocation model."""

    profile_id: str
    service_account: str
    customer_id: str
    allowed_domain: str
    administrative_auditor: str
    approved_scope_profile: ApprovedScopeProfile
    admin_capability: AdminCapability = AdminCapability.NONE

    def build(self) -> ContentAuthProfile:
        return ContentAuthProfile(
            profile_id=self.profile_id,
            service_account=self.service_account,
            customer_id=self.customer_id,
            allowed_domain=self.allowed_domain,
            administrative_auditor=self.administrative_auditor,
            approved_scope_profile=self.approved_scope_profile,
            admin_capability=self.admin_capability,
        )


class _ProfileRegistry(Protocol):
    @property
    def profile_ids(self) -> tuple[str, ...]: ...

    def select(self, profile_id: object) -> RegisteredProfileHandle: ...
