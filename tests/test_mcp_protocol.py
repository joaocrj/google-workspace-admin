import json

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
        lambda max_results=5: fake_users,
    )

    result = await client.call_tool(
        "workspace_users_list",
        {
            "max_results": 5,
        },
    )

    assert result.is_error is False

    payload = _json_result(result)

    assert len(payload) == 1
    assert payload[0]["primary_email"] == "teste@example.com"
    assert payload[0]["full_name"] == "Usuário Teste"
    assert payload[0]["org_unit_path"] == "/Teste"


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
async def test_workspace_groups_list_through_mcp(
    client: Client,
    monkeypatch,
):
    fake_groups = [
        {
            "id": "group-123",
            "email": "classroom_teachers@cevalente.com.br",
            "name": "Classroom Teachers",
            "description": "Grupo de professores",
            "directMembersCount": "3",
            "adminCreated": True,
        }
    ]

    monkeypatch.setattr(
        server,
        "list_groups",
        lambda max_results=20: fake_groups,
    )

    result = await client.call_tool(
        "workspace_groups_list",
        {
            "max_results": 10,
        },
    )

    assert result.is_error is False

    payload = _json_result(result)

    assert len(payload) == 1
    assert payload[0]["id"] == "group-123"
    assert (
        payload[0]["email"]
        == "classroom_teachers@cevalente.com.br"
    )
    assert payload[0]["name"] == "Classroom Teachers"
    assert payload[0]["description"] == "Grupo de professores"
    assert payload[0]["direct_members_count"] == "3"
    assert payload[0]["admin_created"] is True


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
        lambda group_key, max_results=200: fake_members,
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

    assert len(payload) == 1
    assert payload[0]["id"] == "member-123"
    assert payload[0]["email"] == "usuario@cevalente.com.br"
    assert payload[0]["role"] == "MEMBER"
    assert payload[0]["type"] == "USER"
    assert payload[0]["status"] == "ACTIVE"
    assert payload[0]["delivery_settings"] == "ALL_MAIL"


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
        lambda max_results=100: fake_devices,
    )

    result = await client.call_tool(
        "workspace_mobile_devices_list",
        {
            "max_results": 50,
        },
    )

    assert result.is_error is False

    payload = _json_result(result)

    assert len(payload) == 1
    assert payload[0]["resource_id"] == "resource-123"
    assert payload[0]["device_id"] == "device-123"
    assert payload[0]["name"] == ["Usuário Teste"]
    assert payload[0]["email"] == ["teste@cevalente.com.br"]
    assert payload[0]["model"] == "SM-A155M"
    assert payload[0]["manufacturer"] == "Samsung"
    assert payload[0]["type"] == "ANDROID"
    assert payload[0]["os"] == "Android 16"
    assert payload[0]["status"] == "APPROVED"
    assert payload[0]["serial_number"] == "serial-123"
    assert payload[0]["network_operator"] == "Claro"
    assert payload[0]["default_language"] == "pt-BR"
    assert payload[0]["managed_account_is_on_owner_profile"] is True


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
        lambda max_results=100: fake_devices,
    )

    result = await client.call_tool(
        "workspace_chromeos_devices_list",
        {
            "max_results": 50,
        },
    )

    assert result.is_error is False

    payload = _json_result(result)

    assert len(payload) == 1
    assert payload[0]["device_id"] == "chromeos-device-123"
    assert payload[0]["serial_number"] == "SERIAL-123"
    assert payload[0]["model"] == "Chromebook Plus"
    assert payload[0]["manufacturer"] == "Acer"
    assert payload[0]["status"] == "ACTIVE"
    assert payload[0]["os_version"] == "140.0.7339.185"
    assert payload[0]["org_unit_path"] == "/CEV_USERS"
    assert payload[0]["annotated_user"] == "usuario@cevalente.com.br"
    assert payload[0]["annotated_location"] == "Escritório"
    assert payload[0]["annotated_asset_id"] == "ASSET-123"
    assert payload[0]["notes"] == "Equipamento de teste"


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
        lambda max_results=100: fake_roles,
    )

    result = await client.call_tool(
        "workspace_roles_list",
        {
            "max_results": 50,
        },
    )

    assert result.is_error is False

    payload = _json_result(result)

    assert len(payload) == 1
    assert payload[0]["role_id"] == "role-123"
    assert payload[0]["role_name"] == "_SEED_ADMIN_ROLE"
    assert payload[0]["role_description"] == "Super administrador"
    assert payload[0]["role_privileges"] == []
    assert payload[0]["is_system_role"] is True
    assert payload[0]["is_super_admin_role"] is True


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
        lambda max_results=100: fake_assignments,
    )

    result = await client.call_tool(
        "workspace_role_assignments_list",
        {
            "max_results": 50,
        },
    )

    assert result.is_error is False

    payload = _json_result(result)

    assert len(payload) == 1
    assert payload[0]["role_assignment_id"] == "assignment-123"
    assert payload[0]["role_id"] == "role-123"
    assert payload[0]["assigned_to"] == "100056319502616315227"
    assert payload[0]["scope_type"] == "CUSTOMER"
    assert payload[0]["org_unit_id"] is None

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
        aliases[0]["domainAliasName"]
        == "cevalente.com.br.test-google-a.com"
    )
    assert aliases[0]["parentDomainName"] == "cevalente.com.br"
    assert aliases[0]["verified"] is True