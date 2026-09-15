import ast
import copy
import inspect
from pathlib import Path

import pytest

from content_runtime_harness import content_runtime_harness, provisioned_profile, workspace_subject
from google_workspace_admin.content import bootstrap
from google_workspace_admin.content.auth import broker as broker_module
from google_workspace_admin.content.auth import registry as registry_module
from google_workspace_admin.content.auth import resolver as resolver_module
from google_workspace_admin.content.auth.capabilities import SubjectCapability
from google_workspace_admin.content.auth.handles import (
    AuthorizedOperationContext,
    AuthorizedSubjectHandle,
    RegisteredProfileHandle,
)
from google_workspace_admin.content.auth.profile import ContentAuthProfile
from google_workspace_admin.content.auth.scopes import ApprovedScopeProfile
from google_workspace_admin.content.auth.subject import SubjectResolutionSource, WorkspaceSubject
from google_workspace_admin.content.errors import ContentSafeError
from google_workspace_admin.content.operations import DriveListRequest
from google_workspace_admin.content.policy import validate_subject_for_capability
from google_workspace_admin.content.runtime import ContentRuntime


@pytest.mark.parametrize(
    "handle_type",
    [RegisteredProfileHandle, AuthorizedSubjectHandle, AuthorizedOperationContext],
)
def test_object_new_forged_handles_are_inert(handle_type):
    forged = object.__new__(handle_type)
    assert "opaque" in repr(forged)
    with pytest.raises(TypeError):
        copy.copy(forged)
    with pytest.raises(TypeError):
        copy.deepcopy(forged)


def test_handles_have_no_operational_issuer_api():
    for module in (registry_module, resolver_module, broker_module):
        assert not any(
            hasattr(module, name)
            for name in (
                "_build_profile_registry",
                "_build_subject_resolver",
                "_build_content_auth_broker",
            )
        )


def test_manual_profile_and_subject_objects_are_not_authorities():
    profile = ContentAuthProfile(
        profile_id="drive-discovery",
        service_account="content-research@example.iam.gserviceaccount.com",
        customer_id="customer-1",
        allowed_domain="cevalente.com.br",
        administrative_auditor="suporte.ti@cevalente.com.br",
        approved_scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
    )
    subject = workspace_subject()
    assert profile.profile_id == "drive-discovery"
    assert subject.primary_email == "analyst@cevalente.com.br"
    with pytest.raises(TypeError):
        DriveListRequest(
            profile_id="drive-discovery",
            user_key="analyst@cevalente.com.br",
            profile=profile,  # type: ignore[call-arg]
        )
    with pytest.raises(TypeError):
        DriveListRequest(
            profile_id="drive-discovery",
            user_key="analyst@cevalente.com.br",
            subject=subject,  # type: ignore[call-arg]
        )


def test_runtime_accepts_only_registered_profile_id(monkeypatch):
    with content_runtime_harness(
        monkeypatch,
        lambda request: __import__("httpx").Response(200, request=request, json={"drives": []}),
    ) as (runtime, captured):
        with pytest.raises(ContentSafeError):
            runtime.execute(DriveListRequest("synthetic-profile", "analyst@cevalente.com.br"))
    assert captured == []


@pytest.mark.parametrize(
    "subject",
    [
        workspace_subject(mailbox_ready=False),
        WorkspaceSubject(
            primary_email="analyst@cevalente.com.br",
            user_id="user-1",
            customer_id="customer-1",
            domain="cevalente.com.br",
            suspended=True,
            archived=False,
            mailbox_ready=True,
            resolution_source=SubjectResolutionSource.PRIMARY_EMAIL,
        ),
        WorkspaceSubject(
            primary_email="analyst@cevalente.com.br",
            user_id="user-1",
            customer_id="customer-1",
            domain="cevalente.com.br",
            suspended=False,
            archived=True,
            mailbox_ready=True,
            resolution_source=SubjectResolutionSource.PRIMARY_EMAIL,
        ),
        WorkspaceSubject(
            primary_email="analyst@cevalente.com.br",
            user_id="user-1",
            customer_id="other",
            domain="cevalente.com.br",
            suspended=False,
            archived=False,
            mailbox_ready=True,
            resolution_source=SubjectResolutionSource.PRIMARY_EMAIL,
        ),
    ],
)
def test_invalid_subject_states_are_rejected_by_policy(subject):
    from google_workspace_admin.content.auth.profile import ContentAuthProfile

    profile = ContentAuthProfile(
        profile_id="drive-discovery",
        service_account="content-research@example.iam.gserviceaccount.com",
        customer_id="customer-1",
        allowed_domain="cevalente.com.br",
        administrative_auditor="suporte.ti@cevalente.com.br",
        approved_scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
    )
    if subject.mailbox_ready is False:
        assert validate_subject_for_capability(subject, profile, SubjectCapability.DRIVE) is subject
        return
    with pytest.raises(ContentSafeError):
        validate_subject_for_capability(subject, profile, SubjectCapability.DRIVE)


def test_mailbox_not_ready_is_rejected_for_gmail_capability():
    profile = ContentAuthProfile(
        profile_id="gmail-content",
        service_account="content-research@example.iam.gserviceaccount.com",
        customer_id="customer-1",
        allowed_domain="cevalente.com.br",
        administrative_auditor="suporte.ti@cevalente.com.br",
        approved_scope_profile=ApprovedScopeProfile.GMAIL_CONTENT,
    )
    with pytest.raises(ContentSafeError) as error:
        validate_subject_for_capability(
            workspace_subject(mailbox_ready=False), profile, SubjectCapability.GMAIL
        )
    assert error.value.code == "MAILBOX_NOT_ALLOWED"


def test_not_found_lookup_cannot_create_subject_authority(monkeypatch):
    with content_runtime_harness(
        monkeypatch,
        lambda request: __import__("httpx").Response(200, request=request, json={"drives": []}),
        subjects={},
    ) as (runtime, captured):
        with pytest.raises(ContentSafeError):
            runtime.execute(DriveListRequest("drive-discovery", "missing@cevalente.com.br"))
    assert captured == []


def test_production_bootstrap_has_no_injection_parameters():
    assert tuple(inspect.signature(bootstrap.create_content_runtime).parameters) == ()
    with pytest.raises(ContentSafeError):
        bootstrap.create_content_runtime()
    for name in ("profile", "client", "resolver", "broker", "transport", "executor"):
        with pytest.raises(TypeError):
            bootstrap.create_content_runtime(**{name: object()})  # type: ignore[call-arg]


def test_runtime_is_concrete_and_not_a_subclass_injection_point():
    with pytest.raises(TypeError):
        class MaliciousRuntime(ContentRuntime):
            pass

    assert not hasattr(ContentRuntime, "set_client")
    assert not hasattr(ContentRuntime, "attach_client")
    assert not hasattr(ContentRuntime, "_bind_content_runtime")


def test_fabricated_runtime_fails_closed():
    forged = object.__new__(ContentRuntime)
    with pytest.raises(ContentSafeError):
        forged.execute(DriveListRequest("drive-discovery", "analyst@cevalente.com.br"))


def test_closed_runtime_cannot_execute_after_close(monkeypatch):
    import httpx

    with content_runtime_harness(
        monkeypatch,
        lambda request: httpx.Response(200, request=request, json={"drives": []}),
    ) as (runtime, _):
        runtime.close()
        with pytest.raises(ContentSafeError):
            runtime.execute(DriveListRequest("drive-discovery", "analyst@cevalente.com.br"))


def test_supported_requests_cannot_carry_authority_components():
    for field, value in (
        ("broker", object()),
        ("resolver", object()),
        ("adapter", object()),
        ("client", object()),
        ("authority", object()),
    ):
        with pytest.raises(TypeError):
            DriveListRequest(
                "drive-discovery",
                "analyst@cevalente.com.br",
                **{field: value},  # type: ignore[arg-type]
            )


def test_profile_registry_and_subject_resolver_are_not_public_builders():
    assert not hasattr(bootstrap, "_build_profile_registry")
    assert not hasattr(bootstrap, "_build_subject_resolver")
    assert not hasattr(bootstrap, "_build_content_auth_broker")


def test_content_production_has_no_direct_generic_dwd_import():
    root = Path(__file__).parents[1] / "src" / "google_workspace_admin" / "content"
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert node.module != "google_workspace_admin.auth.dwd"
                if node.module == "google_workspace_admin.auth":
                    assert all(alias.name != "dwd" for alias in node.names)
            if isinstance(node, ast.Import):
                assert all(
                    alias.name not in {
                        "google_workspace_admin.auth",
                        "google_workspace_admin.auth.dwd",
                    }
                    for alias in node.names
                )


def test_auth_package_does_not_export_operational_components():
    import google_workspace_admin.content.auth as auth_package

    for name in (
        "ContentAuthBroker",
        "ContentProfileRegistry",
        "StaticSubjectResolver",
        "RegisteredProfileHandle",
        "AuthorizedSubjectHandle",
        "AuthorizedOperationContext",
    ):
        assert name not in auth_package.__all__
        assert not hasattr(auth_package, name)
