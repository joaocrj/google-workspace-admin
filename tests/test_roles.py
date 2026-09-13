import httpx
import pytest

from google_workspace_admin.directory import roles
from google_workspace_admin.http_errors import WorkspaceApiError


def _configure_http(monkeypatch, payload, status_code=200):
    captured = {"calls": 0}

    class FakeResponse:
        def __init__(self):
            self.status_code = status_code

        def raise_for_status(self):
            if self.status_code >= 400:
                request = httpx.Request("GET", roles.ROLES_URL)
                response = httpx.Response(
                    self.status_code,
                    request=request,
                    content=b"SECRET BODY",
                )
                raise httpx.HTTPStatusError(
                    "upstream failure", request=request, response=response
                )

        def json(self):
            return payload

    class FakeClient:
        def __init__(self, timeout):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def get(self, url, headers, params=None):
            captured["calls"] += 1
            captured["url"] = url
            captured["params"] = params
            return FakeResponse()

    def fake_token(*, scopes):
        captured["scopes"] = scopes
        return "test-token", 3600

    monkeypatch.setattr(roles.httpx, "Client", FakeClient)
    monkeypatch.setattr(roles, "get_workspace_access_token", fake_token)
    return captured


def test_list_roles_paginates_with_explicit_limit(monkeypatch):
    captured = _configure_http(
        monkeypatch,
        {"items": [{"roleId": "role-1"}], "nextPageToken": "next-role"},
    )

    result = roles.list_roles(max_results=100, page_token="previous-role")

    assert captured["calls"] == 1
    assert captured["timeout"] == 30.0
    assert captured["scopes"] == [roles.DIRECTORY_ROLE_MANAGEMENT_SCOPE]
    assert captured["params"] == {
        "maxResults": 100,
        "pageToken": "previous-role",
    }
    assert result == [{"roleId": "role-1"}]
    assert result.next_page_token == "next-role"


@pytest.mark.parametrize("value", [True, 1.5, "100", 0, 101])
def test_list_roles_rejects_invalid_max_results(monkeypatch, value):
    monkeypatch.setattr(
        roles,
        "get_workspace_access_token",
        lambda **kwargs: pytest.fail("autenticação não deve ocorrer"),
    )
    with pytest.raises(ValueError):
        roles.list_roles(max_results=value)


@pytest.mark.parametrize("value", ["", " ", 42])
def test_list_roles_rejects_invalid_page_token(monkeypatch, value):
    monkeypatch.setattr(
        roles,
        "get_workspace_access_token",
        lambda **kwargs: pytest.fail("autenticação não deve ocorrer"),
    )
    with pytest.raises(ValueError):
        roles.list_roles(page_token=value)


def test_list_roles_rejects_malformed_response(monkeypatch):
    _configure_http(monkeypatch, {"items": [None]})
    with pytest.raises(WorkspaceApiError):
        roles.list_roles()


def test_list_roles_exposes_safe_http_error(monkeypatch):
    _configure_http(monkeypatch, {}, status_code=403)
    with pytest.raises(WorkspaceApiError) as error:
        roles.list_roles()
    assert error.value.category == "authorization"
    assert error.value.status_code == 403
    assert "SECRET BODY" not in str(error.value)
