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
