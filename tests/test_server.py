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