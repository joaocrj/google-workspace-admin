import json
from pathlib import Path

import pytest
from mcp import Client

from google_workspace_admin import server


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    async with Client(
        server.mcp,
        raise_exceptions=True,
    ) as connected_client:
        yield connected_client


@pytest.fixture
async def non_raising_client():
    async with Client(
        server.mcp,
        raise_exceptions=False,
    ) as connected_client:
        yield connected_client


def _json_result(result):
    """
    Extrai o retorno JSON de uma tool MCP.

    MCP SDK 2.1.1 pode retornar dict/list como TextContent
    serializado em JSON, sem structured_content.
    """
    if result.structured_content is not None:
        return result.structured_content.get(
            "result",
            result.structured_content,
        )

    assert result.content
    assert result.content[0].type == "text"

    return json.loads(result.content[0].text)


_STRICT_MAX_RESULTS_CASES = [
    ("workspace_users_list", "list_users", {}),
    ("workspace_groups_list", "list_groups", {}),
    (
        "workspace_group_members_list",
        "list_group_members",
        {"group_key": "group-fixture@example.invalid"},
    ),
    ("workspace_mobile_devices_list", "list_mobile_devices", {}),
    ("workspace_chromeos_devices_list", "list_chromeos_devices", {}),
    ("workspace_roles_list", "list_roles", {}),
    (
        "workspace_role_assignments_list",
        "list_role_assignments",
        {},
    ),
    ("workspace_buildings_list", "list_buildings", {}),
    (
        "workspace_calendar_resources_list",
        "list_calendar_resources",
        {},
    ),
    (
        "workspace_calendar_features_list",
        "list_calendar_features",
        {},
    ),
    (
        "workspace_admin_audit_list",
        "list_admin_audit_activities",
        {},
    ),
    (
        "workspace_login_audit_list",
        "list_login_audit_activities",
        {},
    ),
    (
        "workspace_drive_audit_list",
        "list_drive_audit_activities",
        {},
    ),
    ("workspace_user_usage_get", "get_user_usage_report", {"date": "2026-09-11"}),
]


@pytest.mark.anyio
async def test_tools_are_registered(client: Client):
    tools = await client.list_tools()

    tool_names = {
        tool.name
        for tool in tools.tools
    }

    assert "workspace_status" in tool_names
    assert "workspace_users_list" in tool_names
    assert "workspace_user_get" in tool_names
    assert "workspace_groups_list" in tool_names
    assert "workspace_group_members_list" in tool_names
    assert "workspace_orgunits_list" in tool_names
    assert "workspace_mobile_devices_list" in tool_names
    assert "workspace_chromeos_devices_list" in tool_names
    assert "workspace_roles_list" in tool_names
    assert "workspace_role_assignments_list" in tool_names
    assert "workspace_domains_list" in tool_names
    assert "workspace_domain_aliases_list" in tool_names
    assert "workspace_buildings_list" in tool_names
    assert "workspace_calendar_resources_list" in tool_names
    assert "workspace_calendar_features_list" in tool_names
    assert "workspace_admin_audit_list" in tool_names
    assert "workspace_login_audit_list" in tool_names
    assert "workspace_drive_audit_list" in tool_names
    assert "workspace_user_usage_get" in tool_names
    assert "workspace_customer_usage_get" in tool_names
    assert "workspace_drives_list" in tool_names
    assert "workspace_drive_get" in tool_names
    assert "workspace_drive_files_list" in tool_names
    assert len(tool_names) == 23
    assert len(tools.tools) == len(tool_names)
    users_tool = next(
        tool for tool in tools.tools if tool.name == "workspace_users_list"
    )
    assert "max_results" in users_tool.input_schema["properties"]
    assert "page_token" in users_tool.input_schema["properties"]
    assert "_serialize_building" not in tool_names
    assert "_serialize_building_address" not in tool_names
    assert "_serialize_calendar_resource" not in tool_names
    assert "_serialize_calendar_feature" not in tool_names
    assert "_serialize_admin_audit_activity" not in tool_names
    assert "_serialize_admin_audit_event" not in tool_names
    assert "_serialize_admin_audit_parameter" not in tool_names
    assert "_serialize_admin_audit_nested_parameter" not in tool_names
    assert "_serialize_login_audit_activity" not in tool_names
    assert "_serialize_login_audit_event" not in tool_names
    assert "_serialize_login_audit_parameter" not in tool_names
    assert "_serialize_login_audit_nested_parameter" not in tool_names
    assert "_serialize_drive_audit_activity" not in tool_names
    assert "_serialize_drive_audit_event" not in tool_names
    assert "_serialize_drive_audit_parameter" not in tool_names
    assert "_serialize_drive_audit_nested_parameter" not in tool_names
    assert "_serialize_user_usage_report" not in tool_names
    assert "_serialize_user_usage_parameter" not in tool_names
    assert "_serialize_user_usage_page" not in tool_names
    assert "_serialize_customer_usage_report" not in tool_names
    assert "_serialize_customer_usage_parameter" not in tool_names
    assert "_serialize_customer_usage_page" not in tool_names


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("tool_name", "dependency_name", "base_arguments"),
    _STRICT_MAX_RESULTS_CASES,
)
@pytest.mark.parametrize("invalid_value", [True, 1.0, "1"])
async def test_mcp_boundary_rejects_coercible_max_results(
    non_raising_client: Client,
    monkeypatch,
    tool_name,
    dependency_name,
    base_arguments,
    invalid_value,
):
    called = False

    def forbidden_dependency(**kwargs):
        nonlocal called
        called = True
        raise AssertionError("a rejeição deve ocorrer antes da execução")

    monkeypatch.setattr(server, dependency_name, forbidden_dependency)

    result = await non_raising_client.call_tool(
        tool_name,
        {
            **base_arguments,
            "max_results": invalid_value,
        },
    )

    assert result.is_error is True
    assert called is False


@pytest.mark.anyio
async def test_mcp_boundary_accepts_valid_integer_and_preserves_limit(
    client: Client,
    monkeypatch,
):
    captured = {}

    def fake_list_groups(max_results=20, page_token=None):
        captured.update(
            max_results=max_results,
            page_token=page_token,
        )
        return {"groups": [], "next_page_token": None}

    monkeypatch.setattr(server, "list_groups", fake_list_groups)

    result = await client.call_tool(
        "workspace_groups_list",
        {"max_results": 10},
    )

    assert result.is_error is False
    assert captured == {"max_results": 10, "page_token": None}


@pytest.mark.anyio
async def test_mcp_boundary_rejects_groups_value_above_endpoint_limit(
    non_raising_client: Client,
    monkeypatch,
):
    called = False

    def forbidden_dependency(**kwargs):
        nonlocal called
        called = True
        raise AssertionError("limite inválido não deve executar a tool")

    monkeypatch.setattr(server, "list_groups", forbidden_dependency)

    result = await non_raising_client.call_tool(
        "workspace_groups_list",
        {"max_results": 201},
    )

    assert result.is_error is True
    assert called is False


@pytest.mark.anyio
async def test_workspace_customer_usage_get_through_mcp(
    client: Client,
    monkeypatch,
):
    captured = {}

    def fake_get_customer_usage_report(**kwargs):
        captured.update(kwargs)
        return {
            "usage_reports": [
                {
                    "kind": "usageReport",
                    "etag": "omit-etag",
                    "date": "2026-09-10",
                    "entity": {
                        "customerId": "omit-customer",
                        "type": "customer",
                    },
                    "parameters": [
                        {
                            "name": "accounts:num_users",
                            "intValue": 10,
                        },
                        {
                            "name": "accounts:used_quota_in_mb",
                            "intValue": 20,
                        },
                        {
                            "name": "accounts:num_suspended_users",
                            "stringValue": "omit",
                        },
                    ],
                }
            ],
            "next_page_token": "next-page",
            "warnings_present": True,
            "warnings_count": 1,
        }

    monkeypatch.setattr(
        server,
        "get_customer_usage_report",
        fake_get_customer_usage_report,
    )

    result = await client.call_tool(
        "workspace_customer_usage_get",
        {
            "date": "2026-09-10",
            "parameters": " accounts:num_users , accounts:used_quota_in_mb ",
            "page_token": "previous-page",
        },
    )

    assert result.is_error is False
    assert captured == {
        "date": "2026-09-10",
        "parameters": "accounts:num_users,accounts:used_quota_in_mb",
        "page_token": "previous-page",
    }

    payload = _json_result(result)
    assert payload == {
        "usage_reports": [
            {
                "date": "2026-09-10",
                "parameters": [
                    {
                        "parameter_name": "accounts:num_users",
                        "integer_value": 10,
                    },
                    {
                        "parameter_name": "accounts:used_quota_in_mb",
                        "integer_value": 20,
                    },
                ],
            }
        ],
        "next_page_token": "next-page",
        "warnings_present": True,
        "warnings_count": 1,
    }


def test_server_keeps_mcp_run_as_final_operation():
    source = Path(server.__file__).read_text(encoding="utf-8")

    assert source.count("mcp.run()") == 1
    assert source.rstrip().endswith("mcp.run()")


@pytest.mark.anyio
async def test_workspace_user_usage_get_through_mcp(client: Client, monkeypatch):
    captured = {}

    def fake_get_user_usage_report(**kwargs):
        captured.update(kwargs)
        return {
            "usage_reports": [
                {
                    "kind": "usageReport",
                    "date": "2026-09-11",
                    "entity": {
                        "profileId": "profile-123",
                        "userEmail": "omit@example.com",
                        "entityId": "omit-entity",
                    },
                    "parameters": [
                        {
                            "name": "accounts:timestamp_last_login",
                            "datetimeValue": "2026-09-10T00:00:00.000Z",
                        },
                        {
                            "name": "accounts:disabled",
                            "boolValue": False,
                        },
                        {
                            "name": "accounts:password_strength",
                            "stringValue": "omit",
                        },
                    ],
                }
            ],
            "next_page_token": "test-page",
            "warnings_present": True,
            "warnings_count": 2,
        }

    monkeypatch.setattr(
        server,
        "get_user_usage_report",
        fake_get_user_usage_report,
    )

    result = await client.call_tool(
        "workspace_user_usage_get",
        {
            "date": "2026-09-11",
            "max_results": 1,
            "page_token": "test-page",
            "user_key": "profile-123",
            "parameters": "accounts:timestamp_last_login,accounts:disabled",
            "filters": "accounts:disabled==false",
            "org_unit_id": "id:org-unit",
        },
    )

    assert result.is_error is False
    assert captured == {
        "date": "2026-09-11",
        "max_results": 1,
        "page_token": "test-page",
        "user_key": "profile-123",
        "parameters": "accounts:timestamp_last_login,accounts:disabled",
        "filters": "accounts:disabled==false",
        "org_unit_id": "id:org-unit",
    }

    payload = _json_result(result)
    assert payload == {
        "usage_reports": [
            {
                "date": "2026-09-11",
                "profile_id": "profile-123",
                "parameters": [
                    {
                        "parameter_name": "accounts:timestamp_last_login",
                        "datetime_value": "2026-09-10T00:00:00.000Z",
                    },
                    {
                        "parameter_name": "accounts:disabled",
                        "boolean_value": False,
                    },
                ],
            }
        ],
        "next_page_token": "test-page",
        "warnings_present": True,
        "warnings_count": 2,
    }
    assert "userEmail" not in str(payload)
    assert "entityId" not in str(payload)
    assert "password_strength" not in str(payload)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"date": "2026-09-11", "max_results": 0},
        {"date": "2026-02-29"},
        {"date": "2026-09-11", "parameters": " "},
    ],
)
async def test_workspace_user_usage_get_validation_through_mcp(
    client: Client,
    arguments,
):
    result = await client.call_tool(
        "workspace_user_usage_get",
        arguments,
    )

    assert result.is_error is True


@pytest.mark.anyio
async def test_workspace_status_through_mcp(client: Client):
    result = await client.call_tool(
        "workspace_status",
        {},
    )

    assert result.is_error is False

    payload = _json_result(result)

    assert payload["status"] == "ok"
    assert payload["server"] == "google-workspace-admin"
    assert payload["authentication"] == "ADC -> IAM signJwt -> DWD"


@pytest.mark.anyio
async def test_workspace_users_list_through_mcp(
    client: Client,
    monkeypatch,
):
    fake_users = [
        {
            "id": "123",
            "primaryEmail": "teste@example.com",
            "name": {
                "fullName": "Usuário Teste",
                "givenName": "Usuário",
                "familyName": "Teste",
            },
            "suspended": False,
            "archived": False,
            "isAdmin": False,
            "isDelegatedAdmin": False,
            "orgUnitPath": "/Teste",
            "creationTime": "2026-01-01T00:00:00.000Z",
            "lastLoginTime": "2026-09-01T12:00:00.000Z",
        }
    ]

    monkeypatch.setattr(
        server,
        "list_users",
        lambda max_results=5, page_token=None: fake_users,
    )

    result = await client.call_tool(
        "workspace_users_list",
        {
            "max_results": 5,
        },
    )

    assert result.is_error is False

    payload = _json_result(result)

    assert len(payload["users"]) == 1
    assert payload["users"][0]["primary_email"] == "teste@example.com"
    assert payload["users"][0]["full_name"] == "Usuário Teste"
    assert payload["users"][0]["org_unit_path"] == "/Teste"
    assert payload["next_page_token"] is None


@pytest.mark.anyio
async def test_workspace_user_get_through_mcp(
    client: Client,
    monkeypatch,
):
    fake_user = {
        "id": "456",
        "primaryEmail": "adm@example.com",
        "name": {
            "fullName": "Administrador",
            "givenName": "Administrador",
            "familyName": "",
        },
        "suspended": False,
        "archived": False,
        "isAdmin": True,
        "isDelegatedAdmin": False,
        "orgUnitPath": "/",
        "creationTime": "2026-01-01T00:00:00.000Z",
        "lastLoginTime": "2026-09-03T12:00:00.000Z",
    }

    monkeypatch.setattr(
        server,
        "get_user",
        lambda user_key: fake_user,
    )

    result = await client.call_tool(
        "workspace_user_get",
        {
            "user_key": "adm@example.com",
        },
    )

    assert result.is_error is False

    payload = _json_result(result)

    assert payload["id"] == "456"
    assert payload["primary_email"] == "adm@example.com"
    assert payload["full_name"] == "Administrador"
    assert payload["is_admin"] is True


@pytest.mark.anyio
async def test_workspace_users_list_validation_through_mcp(
    client: Client,
):
    result = await client.call_tool(
        "workspace_users_list",
        {
            "max_results": 0,
        },
    )

    assert result.is_error is True


@pytest.mark.anyio
async def test_workspace_users_list_error_is_safe_at_mcp_boundary(
    non_raising_client: Client,
    monkeypatch,
):
    def fail_users(**kwargs):
        raise RuntimeError(
            "SECRET_ACCESS_TOKEN_SENTINEL SECRET_BODY_SENTINEL "
            "SECRET_EMAIL_SENTINEL"
        )

    monkeypatch.setattr(server, "list_users", fail_users)

    result = await non_raising_client.call_tool(
        "workspace_users_list",
        {
            "max_results": 1,
            "page_token": None,
        },
    )

    assert result.is_error is True
    diagnostic = " ".join(
        content.text
        for content in result.content
        if content.type == "text"
    )
    assert "UNEXPECTED_LOCAL" in diagnostic
    assert "SECRET_ACCESS_TOKEN_SENTINEL" not in diagnostic
    assert "SECRET_BODY_SENTINEL" not in diagnostic
    assert "SECRET_EMAIL_SENTINEL" not in diagnostic


@pytest.mark.anyio
async def test_workspace_groups_list_through_mcp(
    client: Client,
    monkeypatch,
):
    fake_groups = [
        {
            "id": "group-123",
            "email": "test-group@example.invalid",
            "name": "Classroom Teachers",
            "description": "Grupo de professores",
            "directMembersCount": "3",
            "adminCreated": True,
        }
    ]

    monkeypatch.setattr(
        server,
        "list_groups",
        lambda max_results=20, page_token=None: fake_groups,
    )

    result = await client.call_tool(
        "workspace_groups_list",
        {
            "max_results": 10,
        },
    )

    assert result.is_error is False

    payload = _json_result(result)

    assert len(payload["groups"]) == 1
    assert payload["groups"][0]["id"] == "group-123"
    assert (
        payload["groups"][0]["email"]
        == "test-group@example.invalid"
    )
    assert payload["groups"][0]["name"] == "Classroom Teachers"
    assert payload["groups"][0]["description"] == "Grupo de professores"
    assert payload["groups"][0]["direct_members_count"] == "3"
    assert payload["groups"][0]["admin_created"] is True
    assert payload["next_page_token"] is None


@pytest.mark.anyio
async def test_workspace_group_members_list_through_mcp(
    client: Client,
    monkeypatch,
):
    fake_members = [
        {
            "id": "member-123",
            "email": "usuario@cevalente.com.br",
            "role": "MEMBER",
            "type": "USER",
            "status": "ACTIVE",
            "delivery_settings": "ALL_MAIL",
        }
    ]

    monkeypatch.setattr(
        server,
        "list_group_members",
        lambda group_key, max_results=200, page_token=None: fake_members,
    )

    result = await client.call_tool(
        "workspace_group_members_list",
        {
            "group_key": "grupo@cevalente.com.br",
            "max_results": 100,
        },
    )

    assert result.is_error is False

    payload = _json_result(result)

    assert len(payload["members"]) == 1
    assert payload["members"][0]["id"] == "member-123"
    assert payload["members"][0]["email"] == "usuario@cevalente.com.br"
    assert payload["members"][0]["role"] == "MEMBER"
    assert payload["members"][0]["type"] == "USER"
    assert payload["members"][0]["status"] == "ACTIVE"
    assert payload["members"][0]["delivery_settings"] == "ALL_MAIL"
    assert payload["next_page_token"] is None


@pytest.mark.anyio
async def test_workspace_orgunits_list_through_mcp(
    client: Client,
    monkeypatch,
):
    fake_orgunits = [
        {
            "orgUnitId": "id:cev-users",
            "name": "CEV_USERS",
            "description": "Usuários da organização",
            "orgUnitPath": "/CEV_USERS",
            "parentOrgUnitId": "id:root",
            "parentOrgUnitPath": "/",
            "blockInheritance": False,
        }
    ]

    monkeypatch.setattr(
        server,
        "list_orgunits",
        lambda org_unit_path="/", org_unit_type="all": fake_orgunits,
    )

    result = await client.call_tool(
        "workspace_orgunits_list",
        {
            "org_unit_path": "/CEV_USERS",
            "org_unit_type": "all_including_parent",
        },
    )

    assert result.is_error is False

    payload = _json_result(result)

    assert len(payload) == 1
    assert payload[0]["org_unit_id"] == "id:cev-users"
    assert payload[0]["name"] == "CEV_USERS"
    assert payload[0]["description"] == "Usuários da organização"
    assert payload[0]["org_unit_path"] == "/CEV_USERS"
    assert payload[0]["parent_org_unit_id"] == "id:root"
    assert payload[0]["parent_org_unit_path"] == "/"
    assert payload[0]["block_inheritance"] is False


@pytest.mark.anyio
async def test_workspace_orgunits_list_validation_through_mcp(
    client: Client,
):
    result = await client.call_tool(
        "workspace_orgunits_list",
        {
            "org_unit_path": "CEV_USERS",
            "org_unit_type": "all",
        },
    )

    assert result.is_error is True

@pytest.mark.anyio
async def test_workspace_mobile_devices_list_through_mcp(
    client: Client,
    monkeypatch,
):
    fake_devices = [
        {
            "resourceId": "resource-123",
            "deviceId": "device-123",
            "name": ["Usuário Teste"],
            "email": ["teste@cevalente.com.br"],
            "model": "SM-A155M",
            "manufacturer": "Samsung",
            "type": "ANDROID",
            "os": "Android 16",
            "status": "APPROVED",
            "firstSync": "2026-01-01T10:00:00.000Z",
            "lastSync": "2026-09-08T12:00:00.000Z",
            "hardwareId": "hardware-123",
            "serialNumber": "serial-123",
            "imei": "imei-123",
            "meid": "meid-123",
            "wifiMacAddress": "00:11:22:33:44:55",
            "networkOperator": "Claro",
            "defaultLanguage": "pt-BR",
            "managedAccountIsOnOwnerProfile": True,
        }
    ]

    monkeypatch.setattr(
        server,
        "list_mobile_devices",
        lambda max_results=100, page_token=None: fake_devices,
    )

    result = await client.call_tool(
        "workspace_mobile_devices_list",
        {
            "max_results": 50,
        },
    )

    assert result.is_error is False

    payload = _json_result(result)

    assert len(payload["mobile_devices"]) == 1
    assert payload["mobile_devices"][0]["resource_id"] == "resource-123"
    assert payload["mobile_devices"][0]["device_id"] == "device-123"
    assert payload["mobile_devices"][0]["name"] == ["Usuário Teste"]
    assert payload["mobile_devices"][0]["email"] == ["teste@cevalente.com.br"]
    assert payload["mobile_devices"][0]["model"] == "SM-A155M"
    assert payload["mobile_devices"][0]["manufacturer"] == "Samsung"
    assert payload["mobile_devices"][0]["type"] == "ANDROID"
    assert payload["mobile_devices"][0]["os"] == "Android 16"
    assert payload["mobile_devices"][0]["status"] == "APPROVED"
    assert payload["mobile_devices"][0]["serial_number"] == "serial-123"
    assert payload["mobile_devices"][0]["network_operator"] == "Claro"
    assert payload["mobile_devices"][0]["default_language"] == "pt-BR"
    assert payload["mobile_devices"][0]["managed_account_is_on_owner_profile"] is True
    assert payload["next_page_token"] is None


@pytest.mark.anyio
async def test_workspace_mobile_devices_list_validation_through_mcp(
    client: Client,
):
    result = await client.call_tool(
        "workspace_mobile_devices_list",
        {
            "max_results": 101,
        },
    )

    assert result.is_error is True

@pytest.mark.anyio
async def test_workspace_chromeos_devices_list_through_mcp(
    client: Client,
    monkeypatch,
):
    fake_devices = [
        {
            "deviceId": "chromeos-device-123",
            "serialNumber": "SERIAL-123",
            "model": "Chromebook Plus",
            "manufacturer": "Acer",
            "status": "ACTIVE",
            "osVersion": "140.0.7339.185",
            "platformVersion": "16371.68.0",
            "firmwareVersion": "Google_Test.12345",
            "macAddress": "00:11:22:33:44:55",
            "ethernetMacAddress": "00:11:22:33:44:66",
            "orgUnitPath": "/CEV_USERS",
            "annotatedUser": "usuario@cevalente.com.br",
            "annotatedLocation": "Escritório",
            "annotatedAssetId": "ASSET-123",
            "lastSync": "2026-09-10T12:00:00.000Z",
            "lastEnrollmentTime": "2026-01-01T10:00:00.000Z",
            "supportEndDate": "2030-01-01T00:00:00.000Z",
            "notes": "Equipamento de teste",
        }
    ]

    monkeypatch.setattr(
        server,
        "list_chromeos_devices",
        lambda max_results=100, page_token=None: fake_devices,
    )

    result = await client.call_tool(
        "workspace_chromeos_devices_list",
        {
            "max_results": 50,
        },
    )

    assert result.is_error is False

    payload = _json_result(result)

    assert len(payload["chromeos_devices"]) == 1
    assert payload["chromeos_devices"][0]["device_id"] == "chromeos-device-123"
    assert payload["chromeos_devices"][0]["serial_number"] == "SERIAL-123"
    assert payload["chromeos_devices"][0]["model"] == "Chromebook Plus"
    assert payload["chromeos_devices"][0]["manufacturer"] == "Acer"
    assert payload["chromeos_devices"][0]["status"] == "ACTIVE"
    assert payload["chromeos_devices"][0]["os_version"] == "140.0.7339.185"
    assert payload["chromeos_devices"][0]["org_unit_path"] == "/CEV_USERS"
    assert payload["chromeos_devices"][0]["annotated_user"] == "usuario@cevalente.com.br"
    assert payload["chromeos_devices"][0]["annotated_location"] == "Escritório"
    assert payload["chromeos_devices"][0]["annotated_asset_id"] == "ASSET-123"
    assert payload["chromeos_devices"][0]["notes"] == "Equipamento de teste"
    assert payload["next_page_token"] is None


@pytest.mark.anyio
async def test_workspace_chromeos_devices_list_validation_through_mcp(
    client: Client,
):
    result = await client.call_tool(
        "workspace_chromeos_devices_list",
        {
            "max_results": 301,
        },
    )

    assert result.is_error is True

@pytest.mark.anyio
async def test_workspace_roles_list_through_mcp(
    client: Client,
    monkeypatch,
):
    fake_roles = [
        {
            "roleId": "role-123",
            "roleName": "_SEED_ADMIN_ROLE",
            "roleDescription": "Super administrador",
            "rolePrivileges": [],
            "isSystemRole": True,
            "isSuperAdminRole": True,
        }
    ]

    monkeypatch.setattr(
        server,
        "list_roles",
        lambda max_results=100, page_token=None: fake_roles,
    )

    result = await client.call_tool(
        "workspace_roles_list",
        {
            "max_results": 50,
        },
    )

    assert result.is_error is False

    payload = _json_result(result)

    assert len(payload["roles"]) == 1
    assert payload["roles"][0]["role_id"] == "role-123"
    assert payload["roles"][0]["role_name"] == "_SEED_ADMIN_ROLE"
    assert payload["roles"][0]["role_description"] == "Super administrador"
    assert payload["roles"][0]["role_privileges"] == []
    assert payload["roles"][0]["is_system_role"] is True
    assert payload["roles"][0]["is_super_admin_role"] is True
    assert payload["next_page_token"] is None


@pytest.mark.anyio
async def test_workspace_role_assignments_list_through_mcp(
    client: Client,
    monkeypatch,
):
    fake_assignments = [
        {
            "roleAssignmentId": "assignment-123",
            "roleId": "role-123",
            "assignedTo": "100056319502616315227",
            "scopeType": "CUSTOMER",
            "orgUnitId": None,
        }
    ]

    monkeypatch.setattr(
        server,
        "list_role_assignments",
        lambda max_results=100, page_token=None: fake_assignments,
    )

    result = await client.call_tool(
        "workspace_role_assignments_list",
        {
            "max_results": 50,
        },
    )

    assert result.is_error is False

    payload = _json_result(result)

    assert len(payload["role_assignments"]) == 1
    assert payload["role_assignments"][0]["role_assignment_id"] == "assignment-123"
    assert payload["role_assignments"][0]["role_id"] == "role-123"
    assert payload["role_assignments"][0]["assigned_to"] == "100056319502616315227"
    assert payload["role_assignments"][0]["scope_type"] == "CUSTOMER"
    assert payload["role_assignments"][0]["org_unit_id"] is None
    assert payload["next_page_token"] is None

@pytest.mark.anyio
async def test_workspace_domains_list_through_mcp(
    client: Client,
    monkeypatch,
):
    fake_domains = [
        {
            "domainName": "cevalente.com.br",
            "verified": True,
            "isPrimary": True,
            "creationTime": "1586464166558",
            "domainAliases": [
                {
                    "kind": "admin#directory#domainAlias",
                    "etag": "alias-etag",
                    "domainAliasName": "cevalente.com.br.test-google-a.com",
                    "parentDomainName": "cevalente.com.br",
                    "verified": True,
                    "creationTime": "1586464166558",
                }
            ],
        }
    ]

    monkeypatch.setattr(
        server,
        "list_domains",
        lambda: fake_domains,
    )

    result = await client.call_tool(
        "workspace_domains_list",
        {},
    )

    assert result.is_error is False

    payload = _json_result(result)

    assert len(payload) == 1
    assert payload[0]["domain_name"] == "cevalente.com.br"
    assert payload[0]["verified"] is True
    assert payload[0]["is_primary"] is True
    assert payload[0]["creation_time"] == "1586464166558"

    aliases = payload[0]["domain_aliases"]

    assert len(aliases) == 1
    assert (
        aliases[0]["domain_alias_name"]
        == "cevalente.com.br.test-google-a.com"
    )
    assert aliases[0]["parent_domain_name"] == "cevalente.com.br"
    assert aliases[0]["verified"] is True

@pytest.mark.anyio
async def test_workspace_domain_aliases_list_through_mcp(
    client: Client,
    monkeypatch,
):
    fake_domain_aliases = [
        {
            "kind": "admin#directory#domainAlias",
            "etag": "alias-etag",
            "domainAliasName": "cevalente.com.br.test-google-a.com",
            "parentDomainName": "cevalente.com.br",
            "verified": True,
            "creationTime": "1586464166558",
        }
    ]

    captured = {}

    def fake_list_domain_aliases(parent_domain_name=None):
        captured["parent_domain_name"] = parent_domain_name
        return fake_domain_aliases

    monkeypatch.setattr(
        server,
        "list_domain_aliases",
        fake_list_domain_aliases,
    )

    result = await client.call_tool(
        "workspace_domain_aliases_list",
        {
            "parent_domain_name": "cevalente.com.br",
        },
    )

    assert result.is_error is False
    assert captured["parent_domain_name"] == "cevalente.com.br"

    payload = _json_result(result)

    assert len(payload) == 1
    assert (
        payload[0]["domain_alias_name"]
        == "cevalente.com.br.test-google-a.com"
    )
    assert payload[0]["parent_domain_name"] == "cevalente.com.br"
    assert payload[0]["verified"] is True
    assert payload[0]["creation_time"] == "1586464166558"


@pytest.mark.anyio
async def test_workspace_buildings_list_through_mcp(
    client: Client,
    monkeypatch,
):
    captured = {}

    def fake_list_buildings(max_results=100, page_token=None):
        captured["max_results"] = max_results
        captured["page_token"] = page_token
        return {
            "buildings": [
                {
                    "buildingId": "test-building",
                    "buildingName": "Test Building",
                    "description": "Test description",
                    "floorNames": ["floor-1", "floor-2"],
                    "coordinates": {
                        "latitude": 1.0,
                        "longitude": 2.0,
                    },
                    "address": {
                        "regionCode": "XX",
                        "languageCode": "test",
                        "postalCode": "00000",
                        "administrativeArea": "Test Area",
                        "locality": "Test Locality",
                        "sublocality": "Test Sublocality",
                        "addressLines": ["Test Address"],
                    },
                    "kind": "admin#directory#resources#buildings",
                    "etags": "test-etag",
                }
            ],
            "next_page_token": "test-page",
        }

    monkeypatch.setattr(server, "list_buildings", fake_list_buildings)

    result = await client.call_tool(
        "workspace_buildings_list",
        {
            "max_results": 500,
            "page_token": "test-page",
        },
    )

    assert result.is_error is False
    assert captured == {
        "max_results": 500,
        "page_token": "test-page",
    }

    payload = _json_result(result)

    assert payload == {
        "buildings": [
            {
                "building_id": "test-building",
                "building_name": "Test Building",
                "description": "Test description",
                "floor_names": ["floor-1", "floor-2"],
                "coordinates": {
                    "latitude": 1.0,
                    "longitude": 2.0,
                },
                "address": {
                    "region_code": "XX",
                    "language_code": "test",
                    "postal_code": "00000",
                    "administrative_area": "Test Area",
                    "locality": "Test Locality",
                    "sublocality": "Test Sublocality",
                    "address_lines": ["Test Address"],
                },
            }
        ],
        "next_page_token": "test-page",
    }
    assert "kind" not in payload["buildings"][0]
    assert "etags" not in payload["buildings"][0]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "arguments",
    [
        {"max_results": 0},
        {"max_results": 501},
        {"page_token": "   "},
    ],
)
async def test_workspace_buildings_list_validation_through_mcp(
    client: Client,
    arguments,
):
    result = await client.call_tool(
        "workspace_buildings_list",
        arguments,
    )

    assert result.is_error is True


@pytest.mark.anyio
async def test_workspace_calendar_resources_list_through_mcp(
    client: Client,
    monkeypatch,
):
    captured = {}

    def fake_list_calendar_resources(
        max_results=100,
        page_token=None,
        order_by=None,
        query=None,
    ):
        captured["max_results"] = max_results
        captured["page_token"] = page_token
        captured["order_by"] = order_by
        captured["query"] = query
        return {
            "resources": [
                {
                    "resourceId": "test-resource",
                    "resourceName": "Test Resource",
                    "resourceDescription": "Test description",
                    "resourceType": "CONFERENCE_ROOM",
                    "resourceEmail": "resource@example.com",
                    "resourceCategory": "CONFERENCE_ROOM",
                    "userVisibleDescription": "Test visible description",
                    "generatedResourceName": "test-resource",
                    "capacity": 10,
                    "buildingId": "test-building",
                    "floorName": "floor-1",
                    "floorSection": "section-1",
                    "kind": "admin#directory#resources#calendars#CalendarResource",
                    "etags": "test-etag",
                    "featureInstances": [{"feature": {"name": "display"}}],
                }
            ],
            "next_page_token": "test-page",
        }

    monkeypatch.setattr(
        server,
        "list_calendar_resources",
        fake_list_calendar_resources,
    )

    result = await client.call_tool(
        "workspace_calendar_resources_list",
        {
            "max_results": 500,
            "page_token": "test-page",
            "order_by": "capacity desc",
            "query": "resourceCategory=CONFERENCE_ROOM",
        },
    )

    assert result.is_error is False
    assert captured == {
        "max_results": 500,
        "page_token": "test-page",
        "order_by": "capacity desc",
        "query": "resourceCategory=CONFERENCE_ROOM",
    }

    payload = _json_result(result)

    assert payload == {
        "resources": [
            {
                "resource_id": "test-resource",
                "resource_name": "Test Resource",
                "resource_description": "Test description",
                "resource_type": "CONFERENCE_ROOM",
                "resource_email": "resource@example.com",
                "resource_category": "CONFERENCE_ROOM",
                "user_visible_description": "Test visible description",
                "generated_resource_name": "test-resource",
                "capacity": 10,
                "building_id": "test-building",
                "floor_name": "floor-1",
                "floor_section": "section-1",
            }
        ],
        "next_page_token": "test-page",
    }
    assert "kind" not in payload["resources"][0]
    assert "etags" not in payload["resources"][0]
    assert "feature_instances" not in payload["resources"][0]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "arguments",
    [
        {"max_results": 0},
        {"max_results": 501},
        {"page_token": "   "},
        {"order_by": "   "},
        {"query": "   "},
    ],
)
async def test_workspace_calendar_resources_list_validation_through_mcp(
    client: Client,
    arguments,
):
    result = await client.call_tool(
        "workspace_calendar_resources_list",
        arguments,
    )

    assert result.is_error is True


@pytest.mark.anyio
async def test_workspace_calendar_features_list_through_mcp(
    client: Client,
    monkeypatch,
):
    captured = {}

    def fake_list_calendar_features(max_results=100, page_token=None):
        captured["max_results"] = max_results
        captured["page_token"] = page_token
        return {
            "features": [
                {
                    "name": "test-feature",
                    "kind": "admin#directory#resources#features#Feature",
                    "etags": "test-etag",
                }
            ],
            "next_page_token": "test-page",
        }

    monkeypatch.setattr(
        server,
        "list_calendar_features",
        fake_list_calendar_features,
    )

    result = await client.call_tool(
        "workspace_calendar_features_list",
        {
            "max_results": 500,
            "page_token": "test-page",
        },
    )

    assert result.is_error is False
    assert captured == {
        "max_results": 500,
        "page_token": "test-page",
    }

    payload = _json_result(result)

    assert payload == {
        "features": [{"feature_name": "test-feature"}],
        "next_page_token": "test-page",
    }
    assert "kind" not in payload["features"][0]
    assert "etags" not in payload["features"][0]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "arguments",
    [
        {"max_results": 0},
        {"max_results": 501},
        {"page_token": "   "},
    ],
)
async def test_workspace_calendar_features_list_validation_through_mcp(
    client: Client,
    arguments,
):
    result = await client.call_tool(
        "workspace_calendar_features_list",
        arguments,
    )

    assert result.is_error is True


@pytest.mark.anyio
async def test_workspace_admin_audit_list_through_mcp(
    client: Client,
    monkeypatch,
):
    captured = {}

    def fake_list_admin_audit_activities(**kwargs):
        captured.update(kwargs)
        return {
            "activities": [
                {
                    "kind": "audit#activity",
                    "id": {"time": "0", "uniqueQualifier": "1"},
                    "actor": {
                        "email": "admin@example.com",
                        "callerType": "USER",
                        "profileId": "profile-id",
                    },
                    "ipAddress": "198.51.100.10",
                    "events": [
                        {
                            "type": "SETTINGS",
                            "name": "CHANGE_SETTING",
                            "parameters": [
                                {"name": "value", "value": "example"}
                            ],
                            "sensitiveParameters": [
                                {"name": "secret", "value": "omit"}
                            ],
                        }
                    ],
                }
            ],
            "next_page_token": "test-page",
        }

    monkeypatch.setattr(
        server,
        "list_admin_audit_activities",
        fake_list_admin_audit_activities,
    )

    result = await client.call_tool(
        "workspace_admin_audit_list",
        {
            "max_results": 100,
            "page_token": "test-page",
            "user_key": "admin@example.com",
            "event_name": "CHANGE_SETTING",
            "filters": "SETTING_NAME==EXAMPLE",
            "start_time": "2026-09-10T00:00:00Z",
            "end_time": "2026-09-11T00:00:00Z",
            "actor_ip_address": "198.51.100.10",
            "org_unit_id": "id:org-unit",
        },
    )

    assert result.is_error is False
    assert captured["max_results"] == 100
    assert captured["user_key"] == "admin@example.com"

    payload = _json_result(result)

    assert payload["next_page_token"] == "test-page"
    assert payload["activities"][0]["actor"] == {
        "email": "admin@example.com",
        "caller_type": "USER",
    }
    assert "kind" not in payload["activities"][0]
    assert "profileId" not in payload["activities"][0]["actor"]
    assert "sensitiveParameters" not in payload["activities"][0]["events"][0]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "arguments",
    [
        {"max_results": 0},
        {"max_results": 101},
        {"page_token": "   "},
        {"user_key": "  "},
        {"start_time": "invalid"},
        {
            "start_time": "2026-09-11T00:00:00Z",
            "end_time": "2026-09-10T00:00:00Z",
        },
    ],
)
async def test_workspace_admin_audit_list_validation_through_mcp(
    client: Client,
    arguments,
):
    result = await client.call_tool(
        "workspace_admin_audit_list",
        arguments,
    )

    assert result.is_error is True


@pytest.mark.anyio
async def test_workspace_login_audit_list_through_mcp(
    client: Client,
    monkeypatch,
):
    captured = {}

    def fake_list_login_audit_activities(**kwargs):
        captured.update(kwargs)
        return {
            "activities": [
                {
                    "id": {
                        "time": "0",
                        "uniqueQualifier": "1",
                    },
                    "actor": {
                        "email": "login@example.com",
                        "callerType": "USER",
                        "profileId": "omit-profile",
                    },
                    "ipAddress": "198.51.100.11",
                    "events": [
                        {
                            "type": "login",
                            "name": "login_success",
                            "parameters": [
                                {
                                    "name": "is_suspicious",
                                    "boolValue": False,
                                },
                                {
                                    "name": "login_type",
                                    "value": "saml",
                                },
                                {
                                    "name": "affected_email_address",
                                    "value": "omit-user@example.com",
                                },
                            ],
                            "sensitiveParameters": [
                                {"name": "secret", "value": "omit"}
                            ],
                            "resourceIds": ["omit-resource"],
                            "status": {"statusCode": "200"},
                        }
                    ],
                }
            ],
            "next_page_token": "test-page",
        }

    monkeypatch.setattr(
        server,
        "list_login_audit_activities",
        fake_list_login_audit_activities,
    )

    result = await client.call_tool(
        "workspace_login_audit_list",
        {
            "max_results": 1,
            "user_key": "login@example.com",
            "event_name": "login_success",
            "filters": "is_suspicious==false",
        },
    )

    assert result.is_error is False
    assert captured == {
        "max_results": 1,
        "page_token": None,
        "user_key": "login@example.com",
        "event_name": "login_success",
        "filters": "is_suspicious==false",
        "start_time": None,
        "end_time": None,
        "actor_ip_address": None,
        "org_unit_id": None,
    }

    payload = _json_result(result)
    assert payload["next_page_token"] == "test-page"
    assert payload["activities"][0]["actor"] == {
        "email": "login@example.com",
        "caller_type": "USER",
    }
    assert payload["activities"][0]["events"][0]["parameters"][0] == {
        "parameter_name": "is_suspicious",
        "string_value": None,
        "string_values": None,
        "integer_value": None,
        "integer_values": None,
        "boolean_value": False,
        "nested_parameters": None,
        "nested_parameter_sets": None,
    }
    assert payload["activities"][0]["events"][0]["parameters"][2] == {
        "parameter_name": "affected_email_address",
        "string_value": None,
        "string_values": None,
        "integer_value": None,
        "integer_values": None,
        "boolean_value": None,
        "nested_parameters": None,
        "nested_parameter_sets": None,
    }
    assert "sensitiveParameters" not in payload["activities"][0]["events"][0]
    assert "resourceIds" not in payload["activities"][0]["events"][0]
    assert "status" not in payload["activities"][0]["events"][0]
    assert "omit-user@example.com" not in str(payload)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "arguments",
    [
        {"max_results": 0},
        {"max_results": 101},
        {"page_token": "   "},
        {"user_key": "  "},
        {"event_name": "\t"},
        {"filters": ""},
        {"start_time": "invalid"},
        {
            "start_time": "2026-09-11T00:00:00Z",
            "end_time": "2026-09-10T00:00:00Z",
        },
    ],
)
async def test_workspace_login_audit_list_validation_through_mcp(
    client: Client,
    arguments,
):
    result = await client.call_tool(
        "workspace_login_audit_list",
        arguments,
    )

    assert result.is_error is True


@pytest.mark.anyio
async def test_workspace_drive_audit_list_through_mcp(
    client: Client,
    monkeypatch,
):
    captured = {}

    def fake_list_drive_audit_activities(**kwargs):
        captured.update(kwargs)
        return {
            "activities": [
                {
                    "id": {
                        "time": "0",
                        "uniqueQualifier": "1",
                    },
                    "actor": {
                        "email": "drive@example.com",
                        "callerType": "USER",
                        "profileId": "omit-profile",
                    },
                    "ipAddress": "198.51.100.13",
                    "events": [
                        {
                            "type": "DRIVE",
                            "name": "create",
                            "parameters": [
                                {"name": "doc_id", "value": "doc-123"},
                                {
                                    "name": "doc_title",
                                    "value": "omit title",
                                },
                                {"name": "billable", "boolValue": False},
                            ],
                            "sensitiveParameters": [
                                {"name": "secret", "value": "omit"}
                            ],
                            "resourceIds": ["omit-resource"],
                        }
                    ],
                }
            ],
            "next_page_token": "test-page",
        }

    monkeypatch.setattr(
        server,
        "list_drive_audit_activities",
        fake_list_drive_audit_activities,
    )

    result = await client.call_tool(
        "workspace_drive_audit_list",
        {
            "max_results": 1,
            "user_key": "drive@example.com",
            "event_name": "create",
            "filters": "doc_type==document",
        },
    )

    assert result.is_error is False
    assert captured == {
        "max_results": 1,
        "page_token": None,
        "user_key": "drive@example.com",
        "event_name": "create",
        "filters": "doc_type==document",
        "start_time": None,
        "end_time": None,
        "actor_ip_address": None,
        "org_unit_id": None,
    }

    payload = _json_result(result)
    assert payload["next_page_token"] == "test-page"
    assert payload["activities"][0]["actor"] == {
        "email": "drive@example.com",
        "caller_type": "USER",
    }
    assert payload["activities"][0]["events"][0]["parameters"][0][
        "string_value"
    ] == "doc-123"
    assert payload["activities"][0]["events"][0]["parameters"][1][
        "string_value"
    ] is None
    assert payload["activities"][0]["events"][0]["parameters"][2][
        "boolean_value"
    ] is False
    assert "sensitiveParameters" not in str(payload)
    assert "resourceIds" not in str(payload)
    assert "omit title" not in str(payload)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "arguments",
    [
        {"max_results": 0},
        {"max_results": 101},
        {"page_token": "   "},
        {"user_key": "  "},
        {"event_name": "\t"},
        {"filters": ""},
        {"start_time": "invalid"},
        {
            "start_time": "2026-09-11T00:00:00Z",
            "end_time": "2026-09-10T00:00:00Z",
        },
    ],
)
async def test_workspace_drive_audit_list_validation_through_mcp(
    client: Client,
    arguments,
):
    result = await client.call_tool(
        "workspace_drive_audit_list",
        arguments,
    )

    assert result.is_error is True
