import json
from datetime import datetime, timezone

import httpx
import pytest
from mcp import Client

from content_runtime_harness import content_runtime_harness
from google_workspace_admin import server
from google_workspace_admin.content import config as content_config
from google_workspace_admin.content.audit import (
    AuditEvent,
    AuditExtent,
    AuditScopeSummary,
    AuditTargetKind,
    ContentAuditOperation,
    pseudonymize_target,
)
from google_workspace_admin.content.auth.capabilities import (
    AdminCapability,
    ContentCapability,
    capability_rule,
)
from google_workspace_admin.content.auth.scopes import (
    ApprovedScopeProfile,
    all_approved_scopes,
    scopes_for,
)
from google_workspace_admin.content.errors import ContentSafeError
from google_workspace_admin.content.operations import (
    DRIVE_FILES_LIST_FIELDS,
    ContentOperation,
    DriveFilesListRequest,
    get_operation_contract,
)
from google_workspace_admin.content.results import DriveFileInventoryPage


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


def _bind_runtime(monkeypatch, runtime):
    monkeypatch.setattr(server, "_CONTENT_RUNTIME", runtime)
    monkeypatch.setattr(content_config, "CONTENT_DISCOVERY_PROFILE_ID", "drive-discovery")
    monkeypatch.setenv(content_config.CONTENT_PROJECT_ID_ENV, "synthetic-project")
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


def _tool_result_json(result):
    if result.structured_content is not None:
        return result.structured_content.get("result", result.structured_content)
    return json.loads(result.content[0].text)


def _file(
    file_id: str = "file-1",
    *,
    name: str = "Quarterly report",
    mime_type: str = "application/vnd.google-apps.document",
    modified_time: str | None = "2026-09-01T12:00:00.000Z",
    size: str | None = None,
    parents: list[str] | None = None,
):
    item = {
        "id": file_id,
        "name": name,
        "mimeType": mime_type,
        "parents": ["folder-1"] if parents is None else parents,
        "trashed": False,
        "unknown": {"must": "drop"},
    }
    if modified_time is not None:
        item["modifiedTime"] = modified_time
    if size is not None:
        item["size"] = size
    return item


def test_happy_path_returns_exact_typed_metadata_and_discards_unknown_fields(monkeypatch):
    payload = {
        "files": [
            _file(),
            _file(
                "binary-1",
                name="archive.bin",
                mime_type="application/octet-stream",
                modified_time=None,
                size="42",
                parents=[],
            ),
        ],
        "nextPageToken": "Next+/=",
        "kind": "drive#fileList",
    }
    with content_runtime_harness(monkeypatch, lambda request: _json(request, payload)) as (
        runtime,
        captured,
    ):
        _bind_runtime(monkeypatch, runtime)
        result = server.workspace_drive_files_list(" DriveCase ")

    assert type(result) is DriveFileInventoryPage
    assert result.model_dump() == {
        "files": [
            {
                "file_id": "file-1",
                "name": "Quarterly report",
                "mime_type": "application/vnd.google-apps.document",
                "modified_time": "2026-09-01T12:00:00.000Z",
                "size": None,
                "parents": ["folder-1"],
            },
            {
                "file_id": "binary-1",
                "name": "archive.bin",
                "mime_type": "application/octet-stream",
                "modified_time": None,
                "size": 42,
                "parents": [],
            },
        ],
        "next_page_token": "Next+/=",
    }
    assert len(captured) == 1


@pytest.mark.anyio
async def test_mcp_invocation_returns_exact_public_dto(client: Client, monkeypatch):
    with content_runtime_harness(
        monkeypatch,
        lambda request: _json(request, {"files": [_file(size="0")]}),
    ) as (runtime, captured):
        _bind_runtime(monkeypatch, runtime)
        result = await client.call_tool(
            "workspace_drive_files_list",
            {"drive_id": "drive-1", "page_size": 1, "max_items": 1},
        )

    assert result.is_error is False
    assert _tool_result_json(result) == {
        "files": [
            {
                "file_id": "file-1",
                "name": "Quarterly report",
                "mime_type": "application/vnd.google-apps.document",
                "modified_time": "2026-09-01T12:00:00.000Z",
                "size": 0,
                "parents": ["folder-1"],
            }
        ],
        "next_page_token": None,
    }
    assert len(captured) == 1


@pytest.mark.parametrize(
    ("payload", "expected_count"),
    [({"files": []}, 0), ({"files": [_file()]}, 1)],
)
def test_empty_and_single_item_drives(monkeypatch, payload, expected_count):
    with content_runtime_harness(monkeypatch, lambda request: _json(request, payload)) as (
        runtime,
        captured,
    ):
        _bind_runtime(monkeypatch, runtime)
        result = server.workspace_drive_files_list("drive-1")
    assert len(result.files) == expected_count
    assert result.next_page_token is None
    assert len(captured) == 1


def test_exact_fixed_request_and_single_page_guarantee(monkeypatch):
    def handler(request):
        return _json(request, {"files": [], "nextPageToken": "next-google-page"})

    with content_runtime_harness(monkeypatch, handler) as (runtime, captured):
        _bind_runtime(monkeypatch, runtime)
        result = server.workspace_drive_files_list(
            "DriveCase",
            page_size=500,
            max_items=7,
            page_token="Opaque+/=",
        )

    assert result.next_page_token == "next-google-page"
    assert len(captured) == 1
    request = captured[0]
    assert request.method == "GET"
    assert request.url.scheme == "https"
    assert request.url.host == "www.googleapis.com"
    assert request.url.path == "/drive/v3/files"
    assert request.content == b""
    assert dict(request.url.params) == {
        "fields": DRIVE_FILES_LIST_FIELDS,
        "pageSize": "7",
        "corpora": "drive",
        "driveId": "DriveCase",
        "includeItemsFromAllDrives": "true",
        "supportsAllDrives": "true",
        "spaces": "drive",
        "q": "trashed = false",
        "pageToken": "Opaque+/=",
    }


@pytest.mark.parametrize(
    ("page_size", "max_items", "expected"),
    [(100, 500, 100), (500, 500, 500), (500, 13, 13), (7, 500, 7)],
)
def test_page_size_and_max_items_resolve_to_content_cap(
    monkeypatch, page_size, max_items, expected
):
    with content_runtime_harness(
        monkeypatch, lambda request: _json(request, {"files": []})
    ) as (runtime, captured):
        runtime.execute(
            DriveFilesListRequest(
                "drive-discovery",
                "analyst@cevalente.com.br",
                "drive-1",
                page_size=page_size,
                max_items=max_items,
            )
        )
    assert captured[0].url.params["pageSize"] == str(expected)


def test_folders_and_native_office_pdf_binary_mime_types_are_preserved(monkeypatch):
    mime_types = [
        "application/vnd.google-apps.folder",
        "application/vnd.google-apps.document",
        "application/vnd.google-apps.spreadsheet",
        "application/vnd.google-apps.presentation",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    ]
    payload = {
        "files": [
            _file(f"file-{index}", mime_type=mime_type, size=None)
            for index, mime_type in enumerate(mime_types)
        ]
    }
    with content_runtime_harness(monkeypatch, lambda request: _json(request, payload)) as (
        runtime,
        captured,
    ):
        _bind_runtime(monkeypatch, runtime)
        result = server.workspace_drive_files_list("drive-1")
    assert [item.mime_type for item in result.files] == mime_types
    assert result.files[0].parents == ["folder-1"]
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
        "https://drive.google.com/drive/folders/id",
        "drive.google.com/drive/folders/id",
        True,
        1,
    ],
)
def test_malformed_drive_id_is_rejected_before_http(monkeypatch, drive_id):
    with content_runtime_harness(
        monkeypatch, lambda request: _json(request, {"files": []})
    ) as (runtime, captured):
        _bind_runtime(monkeypatch, runtime)
        with pytest.raises(ContentSafeError):
            server.workspace_drive_files_list(drive_id)
    assert captured == []


@pytest.mark.parametrize(
    "drive_id",
    [
        "drive-1&q=trashed=true&corpora=allDrives",
        "../files?fields=*&supportsAllDrives=false",
    ],
)
def test_injection_shaped_opaque_id_cannot_change_fixed_request(monkeypatch, drive_id):
    with content_runtime_harness(
        monkeypatch, lambda request: _json(request, {"files": []})
    ) as (runtime, captured):
        _bind_runtime(monkeypatch, runtime)
        server.workspace_drive_files_list(drive_id)
    request = captured[0]
    assert request.url.path == "/drive/v3/files"
    assert request.url.params["driveId"] == drive_id
    assert request.url.params["q"] == "trashed = false"
    assert request.url.params["corpora"] == "drive"
    assert request.url.params["fields"] == DRIVE_FILES_LIST_FIELDS


@pytest.mark.parametrize(
    ("parameter", "value"),
    [
        ("page_size", True),
        ("page_size", 1.5),
        ("page_size", "100"),
        ("page_size", 0),
        ("page_size", -1),
        ("page_size", 501),
        ("max_items", True),
        ("max_items", 1.5),
        ("max_items", "500"),
        ("max_items", 0),
        ("max_items", -1),
        ("max_items", 501),
        ("page_token", ""),
        ("page_token", "   "),
        ("page_token", "bad\ntoken"),
        ("page_token", "bad\x00token"),
        ("page_token", 1),
    ],
)
def test_invalid_pagination_input_is_rejected_before_http(monkeypatch, parameter, value):
    with content_runtime_harness(
        monkeypatch, lambda request: _json(request, {"files": []})
    ) as (runtime, captured):
        _bind_runtime(monkeypatch, runtime)
        with pytest.raises(ContentSafeError):
            server.workspace_drive_files_list("drive-1", **{parameter: value})
    assert captured == []


@pytest.mark.parametrize("invalid", [True, 1.5, "100"])
@pytest.mark.anyio
async def test_mcp_rejects_non_strict_integer_types(
    non_raising_client: Client, monkeypatch, invalid
):
    called = False

    def forbidden_execute(request):
        nonlocal called
        called = True
        raise AssertionError("schema-invalid input reached execution")

    monkeypatch.setattr(server, "_execute_content", forbidden_execute)
    result = await non_raising_client.call_tool(
        "workspace_drive_files_list",
        {"drive_id": "drive-1", "page_size": invalid},
    )
    assert result.is_error is True
    assert called is False


@pytest.mark.parametrize(
    "extra",
    [
        "q",
        "filters",
        "corpora",
        "spaces",
        "fields",
        "host",
        "endpoint",
        "method",
        "scope",
        "profile",
        "subject",
        "recursive",
        "retry",
        "automatic_pagination",
        "use_domain_admin_access",
    ],
)
@pytest.mark.anyio
async def test_mcp_closed_contract_rejects_extra_parameters(
    non_raising_client: Client, monkeypatch, extra
):
    called = False

    def forbidden_execute(request):
        nonlocal called
        called = True
        raise AssertionError("extra input reached execution")

    monkeypatch.setattr(server, "_execute_content", forbidden_execute)
    result = await non_raising_client.call_tool(
        "workspace_drive_files_list",
        {"drive_id": "drive-1", extra: "attacker-value"},
    )
    assert result.is_error is True
    assert called is False


@pytest.mark.parametrize(
    "mutator",
    [
        lambda item: item.pop("trashed"),
        lambda item: item.__setitem__("trashed", True),
        lambda item: item.__setitem__("trashed", "false"),
        lambda item: item.__setitem__("id", None),
        lambda item: item.__setitem__("name", []),
        lambda item: item.__setitem__("mimeType", 1),
        lambda item: item.__setitem__("modifiedTime", 1),
        lambda item: item.__setitem__("parents", "folder-1"),
        lambda item: item.__setitem__("parents", [1]),
    ],
)
def test_malformed_file_metadata_fails_closed(monkeypatch, mutator):
    item = _file(size="1")
    mutator(item)
    with content_runtime_harness(
        monkeypatch, lambda request: _json(request, {"files": [item]})
    ) as (runtime, _):
        _bind_runtime(monkeypatch, runtime)
        with pytest.raises(ContentSafeError) as error:
            server.workspace_drive_files_list("drive-1")
    assert error.value.code == "RESPONSE_VALIDATION"


@pytest.mark.parametrize(
    "size",
    ["-1", "1.5", "", "+1", "９", "9223372036854775808", 1, True, 1.0, []],
)
def test_malformed_or_out_of_range_size_fails_closed(monkeypatch, size):
    item = _file()
    item["size"] = size
    with content_runtime_harness(
        monkeypatch, lambda request: _json(request, {"files": [item]})
    ) as (runtime, _):
        _bind_runtime(monkeypatch, runtime)
        with pytest.raises(ContentSafeError) as error:
            server.workspace_drive_files_list("drive-1")
    assert error.value.code == "RESPONSE_VALIDATION"


@pytest.mark.parametrize("payload", [[], {"files": {}}, {"files": ["not-an-object"]}])
def test_malformed_top_level_response_fails_closed(monkeypatch, payload):
    with content_runtime_harness(monkeypatch, lambda request: _json(request, payload)) as (
        runtime,
        _,
    ):
        _bind_runtime(monkeypatch, runtime)
        with pytest.raises(ContentSafeError) as error:
            server.workspace_drive_files_list("drive-1")
    assert error.value.code == "RESPONSE_VALIDATION"


@pytest.mark.parametrize("token", ["", "   ", "bad\ntoken", "bad\x00token", 1])
def test_malformed_response_page_token_fails_closed(monkeypatch, token):
    with content_runtime_harness(
        monkeypatch,
        lambda request: _json(request, {"files": [], "nextPageToken": token}),
    ) as (runtime, _):
        _bind_runtime(monkeypatch, runtime)
        with pytest.raises(ContentSafeError) as error:
            server.workspace_drive_files_list("drive-1")
    assert error.value.code == "RESPONSE_VALIDATION"


@pytest.mark.parametrize(
    ("status", "expected_code"),
    [(400, "WORKSPACE_HTTP"), (401, "WORKSPACE_HTTP"), (403, "WORKSPACE_HTTP"),
     (404, "WORKSPACE_HTTP"), (429, "QUOTA_EXCEEDED"), (500, "WORKSPACE_HTTP")],
)
def test_google_failures_are_safe_and_default_to_one_attempt(
    monkeypatch, status, expected_code
):
    raw = "RAW GOOGLE BODY access-token JWT Authorization ADC"
    with content_runtime_harness(
        monkeypatch,
        lambda request: httpx.Response(status, request=request, content=raw.encode()),
    ) as (runtime, captured):
        _bind_runtime(monkeypatch, runtime)
        with pytest.raises(ContentSafeError) as error:
            server.workspace_drive_files_list("drive-1")
    assert error.value.code == expected_code
    assert raw not in str(error.value)
    assert len(captured) == 1


def test_inventory_authorization_reuses_only_drive_readonly_without_admin_mode():
    rule = capability_rule(ContentOperation.DRIVE_FILES_LIST)
    contract = get_operation_contract(ContentOperation.DRIVE_FILES_LIST)
    assert rule.capability is ContentCapability.DRIVE_DISCOVERY
    assert rule.scope_profile is ApprovedScopeProfile.DRIVE_DISCOVERY
    assert contract.scope_profile is ApprovedScopeProfile.DRIVE_DISCOVERY
    assert rule.admin_capability is AdminCapability.NONE
    assert scopes_for(rule.scope_profile) == (
        "https://www.googleapis.com/auth/drive.readonly",
    )
    assert "https://www.googleapis.com/auth/drive" not in all_approved_scopes()
    assert not any("write" in scope for scope in all_approved_scopes())


def test_inventory_audit_value_is_single_page_and_hmac_pseudonymous():
    class KeyProvider:
        def get_key(self):
            return b"synthetic-audit-key"

    raw_drive_id = "SensitiveDriveId"
    pseudonym = pseudonymize_target(raw_drive_id, key_provider=KeyProvider())
    event = AuditEvent(
        timestamp=datetime.now(timezone.utc),
        operation=ContentAuditOperation.DRIVE_FILES_LIST,
        auditor_profile_id="drive-discovery",
        target_pseudonym=pseudonym,
        scope_summary=AuditScopeSummary(
            operation=ContentAuditOperation.DRIVE_FILES_LIST,
            scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
            target_kind=AuditTargetKind.DRIVE,
            extent=AuditExtent.SINGLE_PAGE,
        ),
        result_count=2,
        success=True,
    )
    rendered = repr(event)
    assert raw_drive_id not in rendered
    assert "file-1" not in rendered
    assert "Quarterly report" not in rendered
    assert event.target_pseudonym.startswith("target_")
