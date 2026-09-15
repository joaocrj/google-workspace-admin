"""Test-only bootstrap wiring for the sealed Content runtime."""

from __future__ import annotations

from contextlib import contextmanager

import httpx

from google_workspace_admin.content import bootstrap
from google_workspace_admin.content.auth.capabilities import AdminCapability
from google_workspace_admin.content.auth.registry import ProvisionedContentProfile
from google_workspace_admin.content.auth.scopes import ApprovedScopeProfile
from google_workspace_admin.content.auth.subject import (
    SubjectResolutionSource,
    WorkspaceSubject,
)
from google_workspace_admin.content.transport import RetryPolicy


def provisioned_profile(
    *,
    profile_id: str = "drive-discovery",
    scope: ApprovedScopeProfile = ApprovedScopeProfile.DRIVE_DISCOVERY,
    admin: bool = False,
) -> ProvisionedContentProfile:
    return ProvisionedContentProfile(
        profile_id=profile_id,
        service_account="content-research@example.iam.gserviceaccount.com",
        customer_id="customer-1",
        allowed_domain="cevalente.com.br",
        administrative_auditor="suporte.ti@cevalente.com.br",
        approved_scope_profile=scope,
        admin_capability=(
            AdminCapability.SHARED_DRIVE_DISCOVERY if admin else AdminCapability.NONE
        ),
    )


def workspace_subject(*, mailbox_ready: bool = True) -> WorkspaceSubject:
    return WorkspaceSubject(
        primary_email="analyst@cevalente.com.br",
        user_id="user-1",
        customer_id="customer-1",
        domain="cevalente.com.br",
        suspended=False,
        archived=False,
        mailbox_ready=mailbox_ready,
        resolution_source=SubjectResolutionSource.PRIMARY_EMAIL,
    )


@contextmanager
def content_runtime_harness(
    monkeypatch,
    handler,
    *,
    profiles: tuple[ProvisionedContentProfile, ...] | None = None,
    subjects: dict[str, WorkspaceSubject] | None = None,
    retry_policy: RetryPolicy | None = None,
    sleeper=None,
):
    captured: list[httpx.Request] = []

    def capturing_handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return handler(request)

    configured_profiles = profiles or (
        provisioned_profile(),
        provisioned_profile(
            profile_id="drive-metadata",
            scope=ApprovedScopeProfile.DRIVE_METADATA,
        ),
    )
    subject_map = subjects or {"analyst@cevalente.com.br": workspace_subject()}

    def lookup(user_key: str) -> WorkspaceSubject | None:
        return subject_map.get(user_key.casefold())

    monkeypatch.setattr(bootstrap, "_load_provisioned_profiles", lambda: configured_profiles)
    monkeypatch.setattr(bootstrap, "_build_subject_lookup", lambda: lookup)
    monkeypatch.setattr(
        bootstrap,
        "_build_http_client",
        lambda: httpx.Client(
            transport=httpx.MockTransport(capturing_handler),
            follow_redirects=False,
            timeout=30.0,
        ),
    )
    monkeypatch.setattr(
        bootstrap,
        "_build_retry_policy",
        lambda: retry_policy or RetryPolicy(),
    )
    if sleeper is not None:
        monkeypatch.setattr(bootstrap, "_build_sleeper", lambda: sleeper)

    runtime = bootstrap.create_content_runtime()
    try:
        yield runtime, captured
    finally:
        runtime.close()
