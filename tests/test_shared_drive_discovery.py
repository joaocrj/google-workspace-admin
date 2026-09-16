import json
from pathlib import Path

import httpx
import pytest
from mcp import Client

from content_runtime_harness import content_runtime_harness
from google_workspace_admin import server
from google_workspace_admin.content import config as content_config
from google_workspace_admin.content.auth.scopes import (
    ApprovedScopeProfile,
    all_approved_scopes,
    scopes_for,
)
from google_workspace_admin.content.errors import ContentSafeError
from google_workspace_admin.content.operations import (
    DRIVE_GET_FIELDS,
    DRIVE_LIST_FIELDS,
    DriveGetRequest,
    DriveListRequest,
)
from google_workspace_admin.content.results import DriveGetResult, DriveListPage


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    async with Client(server.mcp, raise_exceptions=True) as connected_client:
        yield connected_client


@pytest.fixture
async def non_raising_client():
    async with Client(server.mcp, raise_exceptions=False) as connected_client:
        yield connected_client


def _json(request: httpx.Request, payload: object, status: int = 200):
    return httpx.Response(status, request=request, json=payload)


def _tool_result_json(result):
    if result.structured_content is not None:
        return result.structured_content.get("result", result.structured_content)
    return json.loads(result.content[0].text)


def _bind_runtime(monkeypatch, runtime):
    monkeypatch.setattr(server, "_CONTENT_RUNTIME", runtime)
    monkeypatch.setattr(
        content_config,
        "CONTENT_DISCOVERY_PROFILE_ID",
        "drive-discovery",
    )
    monkeypatch.setenv(
        content_config.CONTENT_PROJECT_ID_ENV,
        "synthetic-content-project",
    )
    monkeypatch.setenv(
        content_config.CONTENT_SERVICE_ACCOUNT_ENV,
        "content-research@synthetic-project.iam.gserviceaccount.com",
    )
    monkeypatch.setenv(
        content_config.CONTENT_SUBJECT_ENV,
        "analyst@cevalente.com.br",
    )
    monkeypatch.setenv(content_config.CONTENT_CUSTOMER_ID_ENV, "synthetic-customer")
    monkeypatch.setenv(content_config.CONTENT_DOMAIN_ENV, "cevalente.com.br")


@pytest.mark.anyio
async def test_catalog_has_exactly_twenty_read_and_two_content_tools(client: Client):
    tools = await client.list_tools()
    names = [tool.name for tool in tools.tools]

    assert len(names) == len(set(names)) == 22
    assert {
        "workspace_drives_list",
        "workspace_drive_get",
    } <= set(names)
    assert "workspace_drive_files_list" not in names
    assert len([name for name in names if name.startswith("workspace_")]) == 22
    assert not any(
        name.endswith(("_create", "_update", "_delete", "_move", "_send"))
        for name in names
    )


@pytest.mark.anyio
async def test_content_tool_schemas_are_strict_and_bounded(client: Client):
    tools = await client.list_tools()
    by_name = {tool.name: tool for tool in tools.tools}

    list_properties = by_name["workspace_drives_list"].input_schema["properties"]
    assert list_properties["page_size"]["type"] == "integer"
    assert list_properties["page_size"]["default"] == 25
    assert list_properties["max_items"]["type"] == "integer"
    assert list_properties["max_items"]["default"] == 100
    assert list_properties["use_domain_admin_access"]["type"] == "boolean"
    assert list_properties["use_domain_admin_access"]["default"] is False
    assert list_properties["page_token"]["anyOf"]

    get_properties = by_name["workspace_drive_get"].input_schema["properties"]
    assert get_properties["drive_id"]["type"] == "string"
    assert get_properties["use_domain_admin_access"]["type"] == "boolean"
    assert "workspace_drive_files_list" not in by_name


@pytest.mark.anyio
async def test_catalog_enumeration_does_not_construct_runtime(
    client: Client,
    monkeypatch,
):
    monkeypatch.setattr(server, "_CONTENT_RUNTIME", None)

    def forbidden_bootstrap():
        raise AssertionError("catalog enumeration must remain lazy")

    monkeypatch.setattr(server, "create_content_runtime", forbidden_bootstrap)
    await client.list_tools()
    assert server._CONTENT_RUNTIME is None


def test_content_without_provisioning_fails_before_http(monkeypatch):
    for name in content_config.CONTENT_REQUIRED_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(server, "_CONTENT_RUNTIME", None)
    with pytest.raises(ContentSafeError) as error:
        server.workspace_drives_list()
    assert error.value.code == "CONTENT_NOT_SUPPORTED"


def test_drives_list_projects_only_allowlisted_fields_and_preserves_duplicates(monkeypatch):
    def handler(request):
        return _json(
            request,
            {
                "drives": [
                    {"id": "drive-a", "name": "Shared", "permissions": ["omit"]},
                    {"id": "drive-b", "name": "Shared", "capabilities": {"canListChildren": True}},
                ],
                "nextPageToken": "google-next",
                "kind": "omit",
            },
        )

    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _bind_runtime(monkeypatch, runtime)
        result = server.workspace_drives_list(page_size=100, max_items=2)

    assert result == {
        "drives": [
            {"drive_id": "drive-a", "name": "Shared"},
            {"drive_id": "drive-b", "name": "Shared"},
        ],
        "next_page_token": "google-next",
    }
    assert captured[0].url.params["pageSize"] == "2"
    assert captured[0].url.params["fields"] == DRIVE_LIST_FIELDS
    assert len(captured) == 1


@pytest.mark.anyio
async def test_drives_list_invocation_through_mcp_uses_typed_public_result(
    client: Client,
    monkeypatch,
):
    with content_runtime_harness(
        monkeypatch,
        lambda request: _json(
            request,
            {"drives": [{"id": "drive-1", "name": "Shared"}]},
        ),
    ) as (runtime, captured):
        _bind_runtime(monkeypatch, runtime)
        result = await client.call_tool(
            "workspace_drives_list",
            {"page_size": 25, "max_items": 25},
        )

    assert result.is_error is False
    assert _tool_result_json(result) == {
        "drives": [{"drive_id": "drive-1", "name": "Shared"}],
        "next_page_token": None,
    }
    assert len(captured) == 1


def test_drives_list_forwards_only_opaque_page_token_and_never_autopaginates(monkeypatch):
    def handler(request):
        return _json(request, {"drives": [], "nextPageToken": "next-from-google"})

    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _bind_runtime(monkeypatch, runtime)
        result = server.workspace_drives_list(
            page_size=40,
            page_token="opaque-input",
            max_items=100,
        )

    assert result["next_page_token"] == "next-from-google"
    assert len(captured) == 1
    assert captured[0].url.params["pageToken"] == "opaque-input"
    assert captured[0].url.params["pageSize"] == "40"
    assert "q" not in captured[0].url.params
    assert "useDomainAdminAccess" not in captured[0].url.params


@pytest.mark.parametrize(
    ("parameter", "value"),
    [
        ("page_size", 0),
        ("page_size", 101),
        ("page_size", True),
        ("page_size", 1.0),
        ("page_size", "25"),
        ("max_items", 0),
        ("max_items", 101),
        ("max_items", True),
        ("max_items", 1.0),
        ("max_items", "100"),
        ("page_token", ""),
        ("page_token", "   "),
        ("page_token", 1),
    ],
)
def test_drives_list_rejects_invalid_bounds_and_tokens(monkeypatch, parameter, value):
    with content_runtime_harness(
        monkeypatch,
        lambda request: _json(request, {"drives": []}),
    ) as (runtime, captured):
        _bind_runtime(monkeypatch, runtime)
        with pytest.raises(ContentSafeError):
            server.workspace_drives_list(**{parameter: value})
    assert captured == []


@pytest.mark.parametrize("invalid_value", [True, 1.0, "25"])
@pytest.mark.anyio
async def test_mcp_list_rejects_coercible_strict_integers(
    non_raising_client: Client,
    monkeypatch,
    invalid_value,
):
    called = False

    def forbidden_execute(request):
        nonlocal called
        called = True
        raise AssertionError("invalid schema input reached Content execution")

    monkeypatch.setattr(server, "_execute_content", forbidden_execute)
    result = await non_raising_client.call_tool(
        "workspace_drives_list",
        {"page_size": invalid_value},
    )
    assert result.is_error is True
    assert called is False


@pytest.mark.parametrize("invalid_value", [0, 1.0, "false", None])
@pytest.mark.anyio
async def test_mcp_get_rejects_coercible_strict_boolean(
    non_raising_client: Client,
    monkeypatch,
    invalid_value,
):
    called = False

    def forbidden_execute(request):
        nonlocal called
        called = True
        raise AssertionError("invalid schema input reached Content execution")

    monkeypatch.setattr(server, "_execute_content", forbidden_execute)
    result = await non_raising_client.call_tool(
        "workspace_drive_get",
        {"drive_id": "drive-1", "use_domain_admin_access": invalid_value},
    )
    assert result.is_error is True
    assert called is False


@pytest.mark.parametrize("invalid_value", [1, False, 1.0, ""])
@pytest.mark.anyio
async def test_mcp_list_rejects_non_string_page_token(
    non_raising_client: Client,
    monkeypatch,
    invalid_value,
):
    called = False

    def forbidden_execute(request):
        nonlocal called
        called = True
        raise AssertionError("invalid page token reached Content execution")

    monkeypatch.setattr(server, "_execute_content", forbidden_execute)
    result = await non_raising_client.call_tool(
        "workspace_drives_list",
        {"page_token": invalid_value},
    )
    assert result.is_error is True
    assert called is False


def test_drive_get_uses_stable_id_and_single_encoded_path_segment(monkeypatch):
    def handler(request):
        return _json(request, {"id": "Drive/Case", "name": "Shared", "owners": ["omit"]})

    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _bind_runtime(monkeypatch, runtime)
        result = server.workspace_drive_get(" Drive/Case ")

    assert result == {"drive": {"drive_id": "Drive/Case", "name": "Shared"}}
    assert isinstance(result, dict)
    assert captured[0].method == "GET"
    assert str(captured[0].url).startswith(
        "https://www.googleapis.com/drive/v3/drives/Drive%2FCase"
    )
    assert captured[0].url.params["fields"] == DRIVE_GET_FIELDS
    assert set(captured[0].url.params) == {"fields"}


@pytest.mark.anyio
async def test_drive_get_invocation_through_mcp_uses_typed_public_result(
    client: Client,
    monkeypatch,
):
    with content_runtime_harness(
        monkeypatch,
        lambda request: _json(request, {"id": "drive-1", "name": "Shared"}),
    ) as (runtime, captured):
        _bind_runtime(monkeypatch, runtime)
        result = await client.call_tool(
            "workspace_drive_get",
            {"drive_id": "drive-1"},
        )

    assert result.is_error is False
    assert _tool_result_json(result) == {
        "drive": {"drive_id": "drive-1", "name": "Shared"}
    }
    assert len(captured) == 1


@pytest.mark.parametrize(
    "drive_id",
    [
        "",
        "   ",
        "drive id",
        "drive\tid",
        "drive\nid",
        "drive\x00id",
        "drive\x7fid",
        "x" * 257,
        True,
        1,
    ],
)
def test_drive_get_rejects_invalid_opaque_ids(monkeypatch, drive_id):
    with content_runtime_harness(
        monkeypatch,
        lambda request: _json(request, {"id": "drive-1", "name": "Shared"}),
    ) as (runtime, captured):
        _bind_runtime(monkeypatch, runtime)
        with pytest.raises(ContentSafeError):
            server.workspace_drive_get(drive_id)
    assert captured == []


def test_drive_get_accepts_256_char_id_and_preserves_case(monkeypatch):
    drive_id = "A" * 256

    with content_runtime_harness(
        monkeypatch,
        lambda request: _json(request, {"id": drive_id, "name": "Shared"}),
    ) as (runtime, captured):
        _bind_runtime(monkeypatch, runtime)
        result = server.workspace_drive_get(drive_id)

    assert result["drive"]["drive_id"] == drive_id
    assert captured[0].url.path.endswith("/" + drive_id)


@pytest.mark.parametrize("drive_id", [".", ".."])
def test_drive_get_dot_ids_are_encoded_as_data_segments(monkeypatch, drive_id):
    with content_runtime_harness(
        monkeypatch,
        lambda request: _json(request, {"id": drive_id, "name": "Shared"}),
    ) as (runtime, captured):
        _bind_runtime(monkeypatch, runtime)
        server.workspace_drive_get(drive_id)
    assert str(captured[0].url).split("?", 1)[0].endswith(
        "/" + ("%2E" * len(drive_id))
    )


@pytest.mark.parametrize("status", [403, 404])
def test_drive_get_maps_permission_and_not_found_without_google_body(monkeypatch, status):
    raw = "RAW GOOGLE ERROR BODY SECRET"

    with content_runtime_harness(
        monkeypatch,
        lambda request: httpx.Response(status, request=request, content=raw.encode()),
    ) as (runtime, captured):
        _bind_runtime(monkeypatch, runtime)
        with pytest.raises(ContentSafeError) as error:
            server.workspace_drive_get("drive-1")

    assert error.value.code == "WORKSPACE_HTTP"
    assert error.value.http_status == status
    assert raw not in str(error.value)
    assert len(captured) == 1


def test_admin_mode_defaults_false_and_true_requires_authorized_profile(monkeypatch):
    with content_runtime_harness(
        monkeypatch,
        lambda request: _json(request, {"drives": []}),
    ) as (runtime, captured):
        _bind_runtime(monkeypatch, runtime)
        server.workspace_drives_list()
    assert "useDomainAdminAccess" not in captured[0].url.params

    with content_runtime_harness(
        monkeypatch,
        lambda request: _json(request, {"drives": []}),
    ) as (runtime, captured):
        _bind_runtime(monkeypatch, runtime)
        with pytest.raises(ContentSafeError):
            server.workspace_drives_list(use_domain_admin_access=True)
    assert captured == []


def test_content_runtime_result_types_and_raw_fields_are_not_public(monkeypatch):
    with content_runtime_harness(
        monkeypatch,
        lambda request: _json(
            request,
            {
                "drives": [{"id": "drive-1", "name": "Shared", "permissions": ["omit"]}],
                "unknown": "omit",
            },
        ),
    ) as (runtime, _):
        result = runtime.execute(
            DriveListRequest(
                "drive-discovery",
                "analyst@cevalente.com.br",
                page_size=25,
                max_items=25,
            )
        )
    assert type(result) is DriveListPage
    assert result.items[0].drive_id == "drive-1"
    assert not hasattr(result.items[0], "permissions")


def test_malformed_drive_response_is_rejected_without_raw_leakage(monkeypatch):
    raw = "MALFORMED GOOGLE BODY SECRET"
    with content_runtime_harness(
        monkeypatch,
        lambda request: httpx.Response(200, request=request, content=raw.encode()),
    ) as (runtime, _):
        with pytest.raises(ContentSafeError) as error:
            runtime.execute(
                DriveListRequest(
                    "drive-discovery",
                    "analyst@cevalente.com.br",
                    page_size=25,
                    max_items=25,
                )
            )
    assert error.value.code == "RESPONSE_VALIDATION"
    assert raw not in str(error.value)


def test_public_error_does_not_reflect_pii_or_token_shaped_drive_id(monkeypatch):
    secret_input = "eyJhbGciOiJSUzI1NiJ9.secret\nsignature"
    with content_runtime_harness(
        monkeypatch,
        lambda request: _json(request, {"id": "drive-1", "name": "Shared"}),
    ) as (runtime, captured):
        _bind_runtime(monkeypatch, runtime)
        with pytest.raises(ContentSafeError) as error:
            server.workspace_drive_get(secret_input)
    assert secret_input not in str(error.value)
    assert captured == []


def test_content_scope_and_mutation_barriers_are_closed():
    assert scopes_for(ApprovedScopeProfile.DRIVE_DISCOVERY) == (
        "https://www.googleapis.com/auth/drive.readonly",
    )
    assert "https://www.googleapis.com/auth/drive" not in all_approved_scopes()
    assert "https://www.googleapis.com/auth/drive.file" not in all_approved_scopes()
    assert not {
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.send",
        "https://mail.google.com/",
    } & all_approved_scopes()


def test_server_registration_and_run_invariants_are_preserved():
    source = Path(server.__file__).read_text(encoding="utf-8")
    assert source.count("@mcp.tool()") == 22
    assert source.count("mcp.run()") == 1
    assert source.rstrip().endswith("mcp.run()")
    assert "workspace_drive_files_list" not in source
