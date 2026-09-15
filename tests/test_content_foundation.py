from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest
from mcp import Client

from google_workspace_admin import server
from google_workspace_admin.content.audit import (
    AuditEvent,
    AuditExtent,
    AuditScopeSummary,
    AuditTargetKind,
    ContentAuditOperation,
    pseudonymize_target,
)
from google_workspace_admin.content.auth import (
    ApprovedScopeProfile,
    ContentAuthProfile,
    SubjectCapability,
    SubjectResolutionSource,
    WorkspaceSubject,
)
from google_workspace_admin.content.auth.scopes import all_approved_scopes, scopes_for
from google_workspace_admin.content.errors import (
    ContentErrorOperation,
    ContentSafeError,
)
from google_workspace_admin.content.evidence import EvidenceReference, EvidenceSourceType
from google_workspace_admin.content.limits import (
    ABSOLUTE_CONTEXT_BYTES,
    ABSOLUTE_CONTEXT_CHARACTERS,
    ABSOLUTE_CONTEXT_CHUNKS,
    ContentLimitPolicy,
    ContextLimits,
    PaginationBounds,
    PaginationRequest,
    PaginationState,
)
from google_workspace_admin.content.operations import (
    DRIVE_FILES_LIST_PAGINATION,
    DRIVE_LIST_PAGINATION,
)
from google_workspace_admin.content.policy import (
    validate_subject_for_capability,
    validate_subject_for_profile,
)


def _profile(scope=ApprovedScopeProfile.DRIVE_DISCOVERY):
    return ContentAuthProfile(
        profile_id="content",
        service_account="content-research@example.iam.gserviceaccount.com",
        customer_id="customer-1",
        allowed_domain="CEVALENTE.COM.BR",
        administrative_auditor="SUPORTE.TI@CEVALENTE.COM.BR",
        approved_scope_profile=scope,
    )


def _subject(*, customer="customer-1", suspended=False, archived=False, mailbox=True):
    return WorkspaceSubject(
        primary_email="Analyst@CEVALENTE.COM.BR",
        user_id="user-1",
        customer_id=customer,
        domain="CEVALENTE.COM.BR",
        suspended=suspended,
        archived=archived,
        mailbox_ready=mailbox,
        resolution_source=SubjectResolutionSource.PRIMARY_EMAIL,
    )


def test_profile_is_immutable_and_readonly():
    profile = _profile()
    assert profile.allowed_domain == "cevalente.com.br"
    assert profile.administrative_auditor == "suporte.ti@cevalente.com.br"
    with pytest.raises(FrozenInstanceError):
        profile.customer_id = "other"  # type: ignore[misc]


def test_scope_registry_is_closed_and_readonly():
    scopes = all_approved_scopes()
    assert "https://www.googleapis.com/auth/drive.readonly" in scopes
    assert "https://www.googleapis.com/auth/drive.metadata.readonly" in scopes
    assert "https://www.googleapis.com/auth/gmail.modify" not in scopes
    assert scopes_for(ApprovedScopeProfile.DRIVE_DISCOVERY) == (
        "https://www.googleapis.com/auth/drive.readonly",
    )


def test_arbitrary_scope_iterable_is_rejected():
    with pytest.raises(ContentSafeError):
        scopes_for(["https://example.invalid/scope"])  # type: ignore[arg-type]
    with pytest.raises(ContentSafeError):
        ContentAuthProfile(
            profile_id="content",
            service_account="content-research@example.iam.gserviceaccount.com",
            customer_id="customer-1",
            allowed_domain="cevalente.com.br",
            administrative_auditor="suporte.ti@cevalente.com.br",
            approved_scope_profile=["https://www.googleapis.com/auth/drive"],  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("allowed_domain", "external.example"),
        ("administrative_auditor", "other@cevalente.com.br"),
        ("customer_id", ""),
        ("service_account", "attacker@example.com"),
    ],
)
def test_profile_rejects_invalid_configuration(field, value):
    values = {
        "profile_id": "content",
        "service_account": "content-research@example.iam.gserviceaccount.com",
        "customer_id": "customer-1",
        "allowed_domain": "cevalente.com.br",
        "administrative_auditor": "suporte.ti@cevalente.com.br",
        "approved_scope_profile": ApprovedScopeProfile.DRIVE_DISCOVERY,
    }
    values[field] = value
    with pytest.raises(ContentSafeError):
        ContentAuthProfile(**values)


def test_subject_is_canonical_and_domain_consistent():
    subject = _subject()
    assert subject.primary_email == "analyst@cevalente.com.br"
    assert subject.domain == "cevalente.com.br"
    with pytest.raises(ContentSafeError):
        WorkspaceSubject(
            primary_email="analyst@external.example",
            user_id="user-1",
            customer_id="customer-1",
            domain="cevalente.com.br",
            suspended=False,
            archived=False,
            mailbox_ready=True,
            resolution_source=SubjectResolutionSource.ALIAS,
        )


@pytest.mark.parametrize(
    "subject",
    [_subject(customer="other"), _subject(suspended=True), _subject(archived=True)],
)
def test_subject_policy_rejects_customer_and_status(subject):
    with pytest.raises(ContentSafeError):
        validate_subject_for_profile(subject, _profile())


def test_mailbox_readiness_is_capability_specific():
    subject = _subject(mailbox=False)
    assert validate_subject_for_capability(subject, _profile(), SubjectCapability.DRIVE) is subject
    with pytest.raises(ContentSafeError) as error:
        validate_subject_for_capability(subject, _profile(), SubjectCapability.GMAIL)
    assert error.value.code == "MAILBOX_NOT_ALLOWED"


@pytest.mark.parametrize("value", [True, 1.5, "100", 0, -1, 10**100])
def test_pagination_is_strict_and_bounded(value):
    with pytest.raises(ContentSafeError):
        PaginationRequest(page_size=value)  # type: ignore[arg-type]


def test_operation_pagination_caps_are_explicit():
    assert (
        DRIVE_LIST_PAGINATION.api_max_page_size,
        DRIVE_LIST_PAGINATION.default_page_size,
        DRIVE_LIST_PAGINATION.content_hard_cap,
        DRIVE_LIST_PAGINATION.max_items_per_invocation,
    ) == (100, 25, 100, 100)
    assert (
        DRIVE_FILES_LIST_PAGINATION.api_max_page_size,
        DRIVE_FILES_LIST_PAGINATION.default_page_size,
        DRIVE_FILES_LIST_PAGINATION.content_hard_cap,
        DRIVE_FILES_LIST_PAGINATION.max_items_per_invocation,
    ) == (1000, 100, 500, 500)
    assert PaginationRequest(page_size=500, max_items=20).effective_page_size == 20


def test_pagination_bounds_reject_conflicting_limits():
    with pytest.raises(ContentSafeError):
        PaginationBounds(100, 100, 25, 101)


def test_context_limits_have_absolute_ceilings():
    policy = ContentLimitPolicy(
        safe_defaults=ContextLimits(100, 200, 2),
        hard_caps=ContextLimits(
            ABSOLUTE_CONTEXT_BYTES,
            ABSOLUTE_CONTEXT_CHARACTERS,
            ABSOLUTE_CONTEXT_CHUNKS,
        ),
    )
    assert policy.resolve(ContextLimits(1000, 2000, 20)).max_chunks == 20
    with pytest.raises(ContentSafeError):
        ContextLimits(ABSOLUTE_CONTEXT_BYTES + 1, 1, 1)


@pytest.mark.parametrize("value", [True, 1.0, "100", 0, -1, 10**100])
def test_context_limits_reject_unbounded_values(value):
    with pytest.raises(ContentSafeError):
        ContextLimits(value, 1, 1)  # type: ignore[arg-type]


def test_security_limit_subclasses_are_rejected_at_consumption():
    class BypassBounds(PaginationBounds):
        def __post_init__(self):
            pass

    bounds = BypassBounds(10**100, 10**100, 10**100, 10**100)
    with pytest.raises(ContentSafeError):
        PaginationRequest(page_size=1, bounds=bounds)

    class BypassContext(ContextLimits):
        def __post_init__(self):
            pass

    huge = BypassContext(10**100, 10**100, 10**100)
    policy = ContentLimitPolicy(
        safe_defaults=ContextLimits(1, 1, 1),
        hard_caps=ContextLimits(
            ABSOLUTE_CONTEXT_BYTES,
            ABSOLUTE_CONTEXT_CHARACTERS,
            ABSOLUTE_CONTEXT_CHUNKS,
        ),
    )
    with pytest.raises(ContentSafeError):
        policy.resolve(huge)

    class BypassPolicy(ContentLimitPolicy):
        def __post_init__(self):
            pass

    bypass_policy = BypassPolicy(
        safe_defaults=ContextLimits(1, 1, 1),
        hard_caps=ContextLimits(
            ABSOLUTE_CONTEXT_BYTES,
            ABSOLUTE_CONTEXT_CHARACTERS,
            ABSOLUTE_CONTEXT_CHUNKS,
        ),
    )
    with pytest.raises(ContentSafeError):
        bypass_policy.resolve()


def test_pagination_state_is_explicit():
    assert PaginationState(next_page_token="next", truncated=True).truncated
    with pytest.raises(ContentSafeError):
        PaginationState(next_page_token="", truncated=False)


def test_evidence_is_reference_only_and_deterministic():
    first = EvidenceReference(EvidenceSourceType.DRIVE, "drive-file-1", "chunk:1")
    second = EvidenceReference(EvidenceSourceType.DRIVE, "drive-file-1", "chunk:1")
    assert first.evidence_id == second.evidence_id
    with pytest.raises(TypeError):
        EvidenceReference(EvidenceSourceType.DRIVE, "file-1", "chunk:1", evidence_id="caller")  # type: ignore[call-arg]


def test_audit_event_is_sanitized_and_hmac_pseudonymous():
    class KeyProvider:
        def __init__(self, key):
            self.key = key

        def get_key(self):
            return self.key

    first = pseudonymize_target("Analyst@Cevalente.com.br", key_provider=KeyProvider(b"one"))
    same = pseudonymize_target(" analyst@cevalente.com.br ", key_provider=KeyProvider(b"one"))
    different = pseudonymize_target("analyst@cevalente.com.br", key_provider=KeyProvider(b"two"))
    assert first == same and first != different
    event = AuditEvent(
        timestamp=datetime.now(timezone.utc),
        operation=ContentAuditOperation.DRIVE_FILES_LIST,
        auditor_profile_id="content-drive",
        target_pseudonym=first,
        scope_summary=AuditScopeSummary(
            operation=ContentAuditOperation.DRIVE_FILES_LIST,
            scope_profile=ApprovedScopeProfile.DRIVE_METADATA,
            target_kind=AuditTargetKind.DRIVE,
            extent=AuditExtent.SINGLE_PAGE,
        ),
        result_count=2,
        success=True,
    )
    assert "analyst@cevalente.com.br" not in repr(event)
    assert "b'one'" not in repr(event)


def test_audit_operation_is_closed_and_rejects_token_shaped_text():
    token_shaped = "eyJhbGciOiJSUzI1NiJ9.secret.signature"
    with pytest.raises(ContentSafeError):
        AuditScopeSummary(
            operation=token_shaped,  # type: ignore[arg-type]
            scope_profile=ApprovedScopeProfile.DRIVE_METADATA,
            target_kind=AuditTargetKind.DRIVE,
            extent=AuditExtent.SINGLE_PAGE,
        )

    class BypassScope(AuditScopeSummary):
        def __post_init__(self):
            pass

    with pytest.raises(ContentSafeError):
        AuditEvent(
            timestamp=datetime.now(timezone.utc),
            operation=ContentAuditOperation.DRIVE_FILES_LIST,
            auditor_profile_id="content-drive",
            target_pseudonym=None,
            scope_summary=BypassScope(
                operation=token_shaped,  # type: ignore[arg-type]
                scope_profile=ApprovedScopeProfile.DRIVE_METADATA,
                target_kind=AuditTargetKind.DRIVE,
                extent=AuditExtent.SINGLE_PAGE,
            ),
            result_count=0,
            success=True,
        )


def test_content_safe_error_operation_is_closed_and_does_not_reflect_free_text():
    token_shaped = "eyJhbGciOiJSUzI1NiJ9.secret.signature"
    error = ContentSafeError(code="LOCAL_VALIDATION", operation=token_shaped)  # type: ignore[arg-type]
    assert error.operation == "content.unknown"
    assert token_shaped not in str(error)
    known = ContentSafeError(
        code="LOCAL_VALIDATION",
        operation=ContentErrorOperation.RUNTIME,
    )
    assert known.operation == "content.runtime"


@pytest.mark.anyio
async def test_mcp_boundary_remains_exactly_twenty_tools_without_content_tools():
    async with Client(server.mcp, raise_exceptions=True) as client:
        tools = await client.list_tools()
    names = {tool.name for tool in tools.tools}
    assert len(names) == len(tools.tools) == 20
    assert not {
        "workspace_drives_list",
        "workspace_drive_get",
        "workspace_drive_files_list",
    } & names
