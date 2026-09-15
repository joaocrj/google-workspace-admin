"""Future Content token-cache key contract; no token storage or acquisition."""

from __future__ import annotations

from dataclasses import dataclass

from google_workspace_admin.content.auth.profile import ContentAuthProfile
from google_workspace_admin.content.auth.scopes import ApprovedScopeProfile
from google_workspace_admin.content.auth.subject import WorkspaceSubject
from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError


@dataclass(frozen=True, slots=True)
class ContentAuthCacheKey:
    profile_id: str
    customer_id: str
    service_account: str
    canonical_subject: str
    approved_scope_profile: ApprovedScopeProfile


def _build_content_cache_key(
    profile: ContentAuthProfile,
    subject: WorkspaceSubject,
) -> ContentAuthCacheKey:
    """Build from metadata already recovered by the authority kernel."""

    if type(profile) is not ContentAuthProfile:
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.AUTH_CACHE,
        )
    if type(subject) is not WorkspaceSubject:
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.AUTH_CACHE,
        )
    if subject.customer_id != profile.customer_id:
        raise ContentSafeError(
            code="TARGET_SUBJECT_INVALID",
            operation=ContentErrorOperation.AUTH_CACHE,
        )
    return ContentAuthCacheKey(
        profile_id=profile.profile_id,
        customer_id=profile.customer_id,
        service_account=profile.service_account,
        canonical_subject=subject.primary_email,
        approved_scope_profile=profile.approved_scope_profile,
    )
