from threading import Event

import httpx
import pytest

from content_runtime_harness import (
    content_runtime_harness,
    provisioned_profile,
)
from google_workspace_admin.content.auth.scopes import ApprovedScopeProfile
from google_workspace_admin.content.errors import ContentSafeError
from google_workspace_admin.content.operations import (
    DRIVE_FILES_LIST_FIELDS,
    DRIVE_LIST_FIELDS,
    DriveFilesListRequest,
    DriveGetRequest,
    DriveListRequest,
    ContentOperation,
    _NormalizedOperationRequest,
)
from google_workspace_admin.content.results import (
    DriveFileListPage,
    DriveGetResult,
    DriveListPage,
)
from google_workspace_admin.content.runtime import ContentRuntime
from google_workspace_admin.content.transport import (
    MAX_ATTEMPTS,
    RetryPolicy,
    _sleep_with_cancellation,
)
from google_workspace_admin.http_errors import WorkspaceApiError


def _json(request, payload, status=200):
    return httpx.Response(status, request=request, json=payload)


def test_drive_list_uses_closed_runtime_and_typed_result(monkeypatch):
    def handler(request):
        return _json(
            request,
            {
                "drives": [{"id": "drive-1", "name": "Projetos", "permissions": ["drop"]}],
                "nextPageToken": "next",
            },
        )

    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        result = runtime.execute(
            DriveListRequest("drive-discovery", "analyst@cevalente.com.br", page_size=25, max_items=25)
        )
    assert isinstance(result, DriveListPage)
    assert result.items[0].drive_id == "drive-1"
    assert not hasattr(result.items[0], "permissions")
    assert captured[0].method == "GET"
    assert captured[0].url.params["fields"] == DRIVE_LIST_FIELDS
    assert captured[0].url.params["pageSize"] == "25"
    assert captured[0].headers["Authorization"] == "Bearer synthetic-access-token"


def test_drive_get_encodes_id_and_drops_unknown_fields(monkeypatch):
    def handler(request):
        return _json(request, {"id": "drive/1", "name": "Projetos", "owners": ["drop"]})

    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        result = runtime.execute(
            DriveGetRequest("drive-discovery", "analyst@cevalente.com.br", "drive/1")
        )
    assert isinstance(result, DriveGetResult)
    assert result.drive.drive_id == "drive/1"
    assert not hasattr(result.drive, "owners")
    assert str(captured[0].url).startswith("https://www.googleapis.com/drive/v3/drives/drive%2F1")


def test_files_list_enforces_fixed_query_and_typed_result(monkeypatch):
    def handler(request):
        return _json(
            request,
            {
                "files": [
                    {
                        "id": "file-1",
                        "name": "budget.xlsx",
                        "mimeType": "application/vnd.test",
                        "parents": ["folder-1"],
                        "modifiedTime": "2026-09-01T00:00:00Z",
                        "size": "42",
                        "trashed": False,
                        "driveId": "drive-1",
                        "capabilities": {"canEdit": True},
                    }
                ]
            },
        )

    request = DriveFilesListRequest(
        "drive-discovery",
        "analyst@cevalente.com.br",
        "drive-1",
    )
    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        result = runtime.execute(request)
    assert isinstance(result, DriveFileListPage)
    assert result.items[0].trashed is False
    params = captured[0].url.params
    assert params["corpora"] == "drive"
    assert params["driveId"] == "drive-1"
    assert params["spaces"] == "drive"
    assert params["includeItemsFromAllDrives"] == "true"
    assert params["supportsAllDrives"] == "true"
    assert params["fields"] == DRIVE_FILES_LIST_FIELDS
    assert params["q"] == "trashed = false"
    assert result.items[0].size == 42
    assert not hasattr(result.items[0], "drive_id")
    assert not hasattr(result.items[0], "capabilities")


def test_exact_request_dispatch_rejects_dict_and_duck_type(monkeypatch):
    class Duck:
        profile_id = "drive-discovery"
        user_key = "analyst@cevalente.com.br"

    with content_runtime_harness(monkeypatch, lambda request: _json(request, {"drives": []})) as (runtime, captured):
        with pytest.raises(ContentSafeError):
            runtime.execute({"operation": "drive.list"})
        with pytest.raises(ContentSafeError):
            runtime.execute(Duck())
    assert captured == []


def test_request_subclass_cannot_change_dispatch_semantics(monkeypatch):
    class MaliciousRequest(DriveListRequest):
        pass

    with content_runtime_harness(monkeypatch, lambda request: _json(request, {"drives": []})) as (runtime, captured):
        with pytest.raises(ContentSafeError):
            runtime.execute(MaliciousRequest("drive-discovery", "analyst@cevalente.com.br"))
    assert captured == []


def test_request_surface_has_no_method_host_endpoint_scope_or_fields():
    fields = DriveListRequest.__dataclass_fields__
    for forbidden in ("method", "host", "endpoint", "scope", "capability", "fields", "q"):
        assert forbidden not in fields
    with pytest.raises(TypeError):
        DriveListRequest("drive-discovery", "analyst@cevalente.com.br", fields="permissions(*)")  # type: ignore[call-arg]


def test_normalized_data_cannot_supply_http_destination_or_method():
    with pytest.raises(TypeError):
        _NormalizedOperationRequest(
            operation=ContentOperation.DRIVE_LIST,
            endpoint="https://attacker.invalid",  # type: ignore[call-arg]
            method="POST",  # type: ignore[call-arg]
        )


def test_max_items_reduces_outbound_page_size(monkeypatch):
    with content_runtime_harness(monkeypatch, lambda request: _json(request, {"drives": []})) as (runtime, captured):
        runtime.execute(
            DriveListRequest("drive-discovery", "analyst@cevalente.com.br", page_size=100, max_items=2)
        )
    assert captured[0].url.params["pageSize"] == "2"


def test_files_max_items_reduces_outbound_page_size(monkeypatch):
    with content_runtime_harness(monkeypatch, lambda request: _json(request, {"files": []})) as (runtime, captured):
        runtime.execute(
            DriveFilesListRequest(
                "drive-discovery", "analyst@cevalente.com.br", "drive-1", page_size=500, max_items=7
            )
        )
    assert captured[0].url.params["pageSize"] == "7"


def test_excessive_response_is_rejected_without_local_token(monkeypatch):
    def handler(request):
        return _json(
            request,
            {
                "drives": [
                    {"id": "one", "name": "one"},
                    {"id": "two", "name": "two"},
                    {"id": "three", "name": "three"},
                ],
                "nextPageToken": "real-token",
            },
        )

    with content_runtime_harness(monkeypatch, handler) as (runtime, _):
        with pytest.raises(ContentSafeError) as error:
            runtime.execute(
                DriveListRequest("drive-discovery", "analyst@cevalente.com.br", page_size=2, max_items=2)
            )
    assert error.value.code == "CONTEXT_LIMIT_EXCEEDED"


@pytest.mark.parametrize("trashed", [True, None, "false", 0])
def test_non_false_trashed_response_is_rejected(monkeypatch, trashed):
    def handler(request):
        return _json(
            request,
            {"files": [{"id": "f", "name": "f", "mimeType": "text/plain", "trashed": trashed}]},
        )

    with content_runtime_harness(monkeypatch, handler) as (runtime, _):
        with pytest.raises(ContentSafeError) as error:
            runtime.execute(DriveFilesListRequest("drive-discovery", "analyst@cevalente.com.br", "drive-1"))
    assert error.value.code == "RESPONSE_VALIDATION"


def test_missing_trashed_response_is_rejected(monkeypatch):
    def handler(request):
        return _json(request, {"files": [{"id": "f", "name": "f", "mimeType": "text/plain"}]})

    with content_runtime_harness(monkeypatch, handler) as (runtime, _):
        with pytest.raises(ContentSafeError):
            runtime.execute(DriveFilesListRequest("drive-discovery", "analyst@cevalente.com.br", "drive-1"))


def test_false_trashed_response_is_accepted(monkeypatch):
    def handler(request):
        return _json(
            request,
            {"files": [{"id": "f", "name": "f", "mimeType": "text/plain", "trashed": False}]},
        )

    with content_runtime_harness(monkeypatch, handler) as (runtime, _):
        result = runtime.execute(DriveFilesListRequest("drive-discovery", "analyst@cevalente.com.br", "drive-1"))
    assert result.items[0].trashed is False


def test_runtime_exposes_no_component_or_client_replacement_api(monkeypatch):
    with content_runtime_harness(monkeypatch, lambda request: _json(request, {"drives": []})) as (runtime, _):
        assert isinstance(runtime, ContentRuntime)
        assert not hasattr(runtime, "__dict__")
        for name in (
            "set_client",
            "attach_client",
            "_attach_internal_client",
            "_for_test",
            "set_broker",
            "set_resolver",
            "set_registry",
            "transport",
            "client",
            "broker",
            "resolver",
            "registry",
        ):
            assert not hasattr(runtime, name)


def test_raw_transport_and_generic_json_paths_are_absent():
    import google_workspace_admin.content as content_package
    import google_workspace_admin.content.http_adapter as adapter_module
    import google_workspace_admin.content.transport as transport_module

    assert not hasattr(content_package, "ContentReadTransport")
    assert not hasattr(transport_module, "ContentReadTransport")
    for name in ("request", "request_json", "_request", "_request_json", "ContentJsonResponse"):
        assert not hasattr(adapter_module, name)
        assert not hasattr(transport_module, name)


def test_malformed_json_is_sanitized(monkeypatch):
    def handler(request):
        return httpx.Response(200, request=request, content=b"secret-not-json")

    with content_runtime_harness(monkeypatch, handler) as (runtime, _):
        with pytest.raises(ContentSafeError) as error:
            runtime.execute(DriveListRequest("drive-discovery", "analyst@cevalente.com.br"))
    assert error.value.code == "RESPONSE_VALIDATION"
    assert "secret-not-json" not in str(error.value)


def test_generic_client_exception_is_sanitized(monkeypatch):
    def handler(request):
        raise RuntimeError("Authorization: fake-secret-token")

    with content_runtime_harness(monkeypatch, handler) as (runtime, _):
        with pytest.raises(ContentSafeError) as error:
            runtime.execute(DriveListRequest("drive-discovery", "analyst@cevalente.com.br"))
    assert error.value.code == "WORKSPACE_HTTP"
    assert "fake-secret-token" not in str(error.value)
    assert "Authorization" not in str(error.value)


def test_redirect_is_not_followed(monkeypatch):
    def handler(request):
        return httpx.Response(302, request=request, headers={"location": "https://attacker.invalid"})

    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        with pytest.raises(ContentSafeError):
            runtime.execute(DriveListRequest("drive-discovery", "analyst@cevalente.com.br"))
    assert len(captured) == 1


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_client_and_authorization_statuses_never_retry(monkeypatch, status):
    policy = RetryPolicy(max_attempts=MAX_ATTEMPTS, initial_delay_seconds=0, max_delay_seconds=0)
    with content_runtime_harness(
        monkeypatch,
        lambda request: httpx.Response(status, request=request, content=b"secret"),
        retry_policy=policy,
    ) as (runtime, captured):
        with pytest.raises(ContentSafeError):
            runtime.execute(DriveListRequest("drive-discovery", "analyst@cevalente.com.br"))
    assert len(captured) == 1


@pytest.mark.parametrize("status", [408, 429, 500, 502, 503, 504])
def test_transient_idempotent_reads_retry_bounded(monkeypatch, status):
    policy = RetryPolicy(max_attempts=2, initial_delay_seconds=0, max_delay_seconds=0)
    with content_runtime_harness(
        monkeypatch,
        lambda request: httpx.Response(status, request=request, content=b"secret"),
        retry_policy=policy,
        sleeper=lambda _: None,
    ) as (runtime, captured):
        with pytest.raises(ContentSafeError):
            runtime.execute(DriveListRequest("drive-discovery", "analyst@cevalente.com.br"))
    assert len(captured) == 2


def test_network_timeout_retries_bounded(monkeypatch):
    policy = RetryPolicy(max_attempts=2, initial_delay_seconds=0, max_delay_seconds=0)

    def handler(request):
        raise httpx.ReadTimeout("safe", request=request)

    with content_runtime_harness(monkeypatch, handler, retry_policy=policy, sleeper=lambda _: None) as (runtime, captured):
        with pytest.raises(ContentSafeError):
            runtime.execute(DriveListRequest("drive-discovery", "analyst@cevalente.com.br"))
    assert len(captured) == 2


def test_retry_category_cannot_override_401_or_403():
    policy = RetryPolicy(max_attempts=MAX_ATTEMPTS)
    for status in (401, 403, 404):
        assert not policy._can_retry(
            idempotent_read=True,
            attempt_number=0,
            error=WorkspaceApiError("drive.list", "transport_error", status),
        )


def test_non_idempotent_operation_never_retries():
    policy = RetryPolicy(max_attempts=MAX_ATTEMPTS)
    assert not policy._can_retry(
        idempotent_read=False,
        attempt_number=0,
        error=WorkspaceApiError("drive.list", "upstream_error", 500),
    )


@pytest.mark.parametrize("value", [0, -1, True, 1.0, "2", 10**100, MAX_ATTEMPTS + 1])
def test_retry_attempts_are_strict_and_bounded(value):
    with pytest.raises(ContentSafeError):
        RetryPolicy(max_attempts=value)  # type: ignore[arg-type]


def test_retry_subclass_and_mutated_policy_fail_closed_at_execution(monkeypatch):
    class BypassRetryPolicy(RetryPolicy):
        def __post_init__(self):
            pass

    with pytest.raises(ContentSafeError):
        with content_runtime_harness(
            monkeypatch,
            lambda request: httpx.Response(500, request=request, content=b"safe"),
            retry_policy=BypassRetryPolicy(max_attempts=10**100),
        ):
            pass

    policy = RetryPolicy(max_attempts=MAX_ATTEMPTS, initial_delay_seconds=0, max_delay_seconds=0)
    object.__setattr__(policy, "max_attempts", MAX_ATTEMPTS + 1)
    with content_runtime_harness(
        monkeypatch,
        lambda request: httpx.Response(500, request=request, content=b"safe"),
        retry_policy=policy,
    ) as (runtime, captured):
        with pytest.raises(ContentSafeError):
            runtime.execute(DriveListRequest("drive-discovery", "analyst@cevalente.com.br"))
    assert len(captured) == 1


def test_cancellation_is_observed_during_backoff():
    cancel = Event()

    def sleeper(_):
        cancel.set()

    with pytest.raises(ContentSafeError):
        _sleep_with_cancellation(0, cancel, sleeper)


def test_admin_mode_is_explicit_and_profile_bound(monkeypatch):
    admin_profile = provisioned_profile(admin=True)
    with content_runtime_harness(
        monkeypatch,
        lambda request: _json(request, {"drives": []}),
        profiles=(admin_profile,),
    ) as (runtime, captured):
        runtime.execute(
            DriveListRequest(
                "drive-discovery",
                "analyst@cevalente.com.br",
                use_domain_admin_access=True,
            )
        )
    assert captured[0].url.params["useDomainAdminAccess"] == "true"


def test_admin_mode_cannot_be_enabled_by_non_admin_profile(monkeypatch):
    with content_runtime_harness(monkeypatch, lambda request: _json(request, {"drives": []})) as (runtime, captured):
        with pytest.raises(ContentSafeError):
            runtime.execute(
                DriveListRequest(
                    "drive-discovery",
                    "analyst@cevalente.com.br",
                    use_domain_admin_access=True,
                )
            )
    assert captured == []
