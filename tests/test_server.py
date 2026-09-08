import pytest

from google_workspace_admin import server


def test_workspace_status():
    result = server.workspace_status()

    assert result["status"] == "ok"
    assert result["server"] == "google-workspace-admin"
    assert result["authentication"] == "ADC -> IAM signJwt -> DWD"


def test_workspace_users_list(monkeypatch):
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

    result = server.workspace_users_list(max_results=5)

    assert len(result) == 1
    assert result[0]["primary_email"] == "teste@example.com"
    assert result[0]["full_name"] == "Usuário Teste"
    assert result[0]["suspended"] is False
    assert result[0]["org_unit_path"] == "/Teste"


def test_workspace_user_get(monkeypatch):
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

    result = server.workspace_user_get(
        "adm@example.com"
    )

    assert result["id"] == "456"
    assert result["primary_email"] == "adm@example.com"
    assert result["full_name"] == "Administrador"
    assert result["is_admin"] is True


def test_workspace_users_list_rejects_zero():
    try:
        server.workspace_users_list(max_results=0)
    except ValueError as exc:
        assert "entre 1 e 100" in str(exc)
    else:
        raise AssertionError("ValueError esperado.")


def test_workspace_users_list_rejects_above_100():
    try:
        server.workspace_users_list(max_results=101)
    except ValueError as exc:
        assert "entre 1 e 100" in str(exc)
    else:
        raise AssertionError("ValueError esperado.")
        
def test_workspace_groups_list(monkeypatch):
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
        "google_workspace_admin.server.list_groups",
        lambda max_results: fake_groups,
    )

    result = server.workspace_groups_list(max_results=10)

    assert result == [
        {
            "id": "group-123",
            "email": "classroom_teachers@cevalente.com.br",
            "name": "Classroom Teachers",
            "description": "Grupo de professores",
            "direct_members_count": "3",
            "admin_created": True,
        }
    ]

def test_workspace_groups_list_rejects_zero():
    with pytest.raises(
        ValueError,
        match="max_results deve estar entre 1 e 200",
    ):
        server.workspace_groups_list(max_results=0)


def test_workspace_groups_list_rejects_above_limit():
    with pytest.raises(
        ValueError,
        match="max_results deve estar entre 1 e 200",
    ):
        server.workspace_groups_list(max_results=201)

def test_workspace_group_members_list(monkeypatch):
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
        "google_workspace_admin.server.list_group_members",
        lambda group_key, max_results: fake_members,
    )

    result = server.workspace_group_members_list(
        group_key="grupo@cevalente.com.br",
        max_results=100,
    )

    assert result == [
        {
            "id": "member-123",
            "email": "usuario@cevalente.com.br",
            "role": "MEMBER",
            "type": "USER",
            "status": "ACTIVE",
            "delivery_settings": "ALL_MAIL",
        }
    ]


def test_workspace_group_members_list_rejects_empty_group_key():
    with pytest.raises(
        ValueError,
        match="group_key não pode estar vazio",
    ):
        server.workspace_group_members_list(
            group_key="   ",
            max_results=100,
        )


def test_workspace_group_members_list_rejects_zero():
    with pytest.raises(
        ValueError,
        match="max_results deve estar entre 1 e 200",
    ):
        server.workspace_group_members_list(
            group_key="grupo@cevalente.com.br",
            max_results=0,
        )


def test_workspace_group_members_list_rejects_above_limit():
    with pytest.raises(
        ValueError,
        match="max_results deve estar entre 1 e 200",
    ):
        server.workspace_group_members_list(
            group_key="grupo@cevalente.com.br",
            max_results=201,
        )

def test_workspace_orgunits_list(monkeypatch):
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
        "google_workspace_admin.server.list_orgunits",
        lambda org_unit_path, org_unit_type: fake_orgunits,
    )

    result = server.workspace_orgunits_list(
        org_unit_path="/CEV_USERS",
        org_unit_type="all_including_parent",
    )

    assert result == [
        {
            "org_unit_id": "id:cev-users",
            "name": "CEV_USERS",
            "description": "Usuários da organização",
            "org_unit_path": "/CEV_USERS",
            "parent_org_unit_id": "id:root",
            "parent_org_unit_path": "/",
            "block_inheritance": False,
        }
    ]


def test_workspace_orgunits_list_uses_defaults(monkeypatch):
    captured = {}

    def fake_list_orgunits(
        org_unit_path="/",
        org_unit_type="all",
    ):
        captured["org_unit_path"] = org_unit_path
        captured["org_unit_type"] = org_unit_type
        return []

    monkeypatch.setattr(
        "google_workspace_admin.server.list_orgunits",
        fake_list_orgunits,
    )

    result = server.workspace_orgunits_list()

    assert result == []
    assert captured["org_unit_path"] == "/"
    assert captured["org_unit_type"] == "all"


def test_workspace_orgunits_list_accepts_children(monkeypatch):
    captured = {}

    def fake_list_orgunits(
        org_unit_path,
        org_unit_type,
    ):
        captured["org_unit_path"] = org_unit_path
        captured["org_unit_type"] = org_unit_type
        return []

    monkeypatch.setattr(
        "google_workspace_admin.server.list_orgunits",
        fake_list_orgunits,
    )

    result = server.workspace_orgunits_list(
        org_unit_path="/CEV_USERS",
        org_unit_type="children",
    )

    assert result == []
    assert captured["org_unit_path"] == "/CEV_USERS"
    assert captured["org_unit_type"] == "children"


def test_workspace_orgunits_list_rejects_empty_path():
    with pytest.raises(
        ValueError,
        match="org_unit_path não pode estar vazio",
    ):
        server.workspace_orgunits_list(
            org_unit_path="   ",
        )


def test_workspace_orgunits_list_rejects_path_without_slash():
    with pytest.raises(
        ValueError,
        match="org_unit_path deve começar com '/'",
    ):
        server.workspace_orgunits_list(
            org_unit_path="CEV_USERS",
        )


def test_workspace_orgunits_list_rejects_invalid_type():
    with pytest.raises(
        ValueError,
        match="org_unit_type deve ser",
    ):
        server.workspace_orgunits_list(
            org_unit_path="/",
            org_unit_type="invalid",
        )