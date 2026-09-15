"""Non-authority value contracts for future Content authentication.

Issuer handles, registries, resolvers and brokers are intentionally not
exported.  The existing keyless DWD implementation remains unchanged.
"""

from google_workspace_admin.content.auth.capabilities import (
    AdminCapability,
    ContentCapability,
    SubjectCapability,
)
from google_workspace_admin.content.auth.profile import (
    CONTENT_ADMINISTRATIVE_AUDITOR,
    CONTENT_ALLOWED_DOMAIN,
    ContentAuthProfile,
    ReadonlyCapabilityProfile,
)
from google_workspace_admin.content.auth.scopes import (
    ApprovedScopeProfile,
    all_approved_scopes,
    scopes_for,
)
from google_workspace_admin.content.auth.subject import (
    SubjectResolutionSource,
    WorkspaceSubject,
)

__all__ = [
    "AdminCapability",
    "ApprovedScopeProfile",
    "CONTENT_ADMINISTRATIVE_AUDITOR",
    "CONTENT_ALLOWED_DOMAIN",
    "ContentAuthProfile",
    "ContentCapability",
    "ReadonlyCapabilityProfile",
    "SubjectCapability",
    "SubjectResolutionSource",
    "WorkspaceSubject",
    "all_approved_scopes",
    "scopes_for",
]
