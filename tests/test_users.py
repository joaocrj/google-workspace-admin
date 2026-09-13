import httpx
import pytest

from google_workspace_admin.directory import users
from google_workspace_admin.http_errors import WorkspaceApiError


def _configure_http(
    monkeypatch,
    payload,
    status_code=200,
    json_error=None,
):
    captured = {"calls": 0}

    class FakeResponse:
        def __init__(self):
            self.status_code = status_code

        def raise_for_status(self):
            if self.status_code >= 400:
                request = httpx.Request("GET", users.USERS_URL)
                response = httpx.Response(
                    self.status_code,
                    request=request,
                    content=b"SECRET BODY",
                )
                raise httpx.HTTPStatusError(
                    "upstream failure",
                    request=request,
                    response=response,
                )
            captured["raised_for_status"] = True

        def json(self):
            if json_error is not None:
                raise ValueError(json_error)
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
            captured["headers"] = headers
            captured["params"] = params
            return FakeResponse()

    def fake_token(*, scopes):
        captured["scopes"] = scopes
        return "test-token", 3600

    monkeypatch.setattr(users.httpx, "Client", FakeClient)
    monkeypatch.setattr(users, "get_workspace_access_token", fake_token)
    return captured


def test_list_users_paginates_with_readonly_scope(monkeypatch):
    captured = _configure_http(
        monkeypatch,
        {"users": [{"id": "user-1"}], "nextPageToken": "next-user"},
    )

    result = users.list_users(max_results=7, page_token="previous-user")

    assert captured["calls"] == 1
    assert captured["timeout"] == 30.0
    assert captured["scopes"] == [users.DIRECTORY_USER_SCOPE]
    assert users.DIRECTORY_USER_SCOPE.endswith("admin.directory.user.readonly")
    assert captured["params"] == {
        "customer": "my_customer",
        "maxResults": 7,
        "orderBy": "email",
        "pageToken": "previous-user",
    }
    assert result == [{"id": "user-1"}]
    assert result.next_page_token == "next-user"


def test_get_user_uses_same_readonly_scope(monkeypatch):
    captured = _configure_http(monkeypatch, {"id": "user-1"})

    result = users.get_user("user-1")

    assert result == {"id": "user-1"}
    assert captured["url"].endswith("/user-1")
    assert captured["scopes"] == [users.DIRECTORY_USER_SCOPE]


@pytest.mark.parametrize("value", [True, 1.5, "7", 0, 101])
def test_list_users_rejects_invalid_max_results(monkeypatch, value):
    def fail_authentication(*, scopes):
        pytest.fail("autenticação não deve ocorrer")

    monkeypatch.setattr(users, "get_workspace_access_token", fail_authentication)

    with pytest.raises(ValueError):
        users.list_users(max_results=value)


@pytest.mark.parametrize("value", ["", "   ", 123])
def test_list_users_rejects_invalid_page_token(monkeypatch, value):
    def fail_authentication(*, scopes):
        pytest.fail("autenticação não deve ocorrer")

    monkeypatch.setattr(users, "get_workspace_access_token", fail_authentication)

    with pytest.raises(ValueError):
        users.list_users(page_token=value)


def test_list_users_rejects_malformed_response(monkeypatch):
    _configure_http(monkeypatch, {"users": "not-a-list"})

    with pytest.raises(WorkspaceApiError) as error:
        users.list_users()

    assert error.value.category == "malformed_response"
    assert error.value.code == "RESPONSE_VALIDATION"
    assert error.value.layer == "response"
    assert error.value.operation == "users.list"
    assert error.value.http_status is None
    assert "SECRET BODY" not in str(error.value)


def test_list_users_rejects_malformed_json_safely(monkeypatch):
    _configure_http(
        monkeypatch,
        {},
        json_error="SECRET_BODY_SENTINEL",
    )

    with pytest.raises(WorkspaceApiError) as error:
        users.list_users()

    assert error.value.code == "RESPONSE_VALIDATION"
    assert error.value.layer == "response"
    assert error.value.operation == "users.list"
    assert error.value.http_status == 200
    assert "SECRET_BODY_SENTINEL" not in str(error.value)


@pytest.mark.parametrize("status_code", [401, 403, 500])
def test_list_users_exposes_safe_http_error(monkeypatch, status_code):
    _configure_http(monkeypatch, {}, status_code=status_code)

    with pytest.raises(WorkspaceApiError) as error:
        users.list_users()

    expected_category = {
        401: "authentication",
        403: "authorization",
        500: "upstream_error",
    }[status_code]
    assert error.value.category == expected_category
    assert error.value.code == "WORKSPACE_HTTP"
    assert error.value.layer == "workspace"
    assert error.value.operation == "users.list"
    assert error.value.http_status == status_code
    assert error.value.status_code == status_code
    assert "SECRET BODY" not in str(error.value)
    assert "Authorization" not in str(error.value)
    assert "SECRET BODY" not in repr(vars(error.value))


def test_list_users_rejects_unexpected_next_page_token_type(monkeypatch):
    _configure_http(
        monkeypatch,
        {"users": [], "nextPageToken": 123},
    )

    with pytest.raises(WorkspaceApiError) as error:
        users.list_users()

    assert error.value.category == "malformed_response"
    assert error.value.code == "RESPONSE_VALIDATION"
    assert error.value.layer == "response"
    assert error.value.operation == "users.list"
    assert error.value.http_status is None


def test_list_users_exposes_safe_timeout(monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self, timeout):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def get(self, url, headers, params=None):
            request = httpx.Request("GET", url)
            raise httpx.ReadTimeout("SECRET TIMEOUT", request=request)

    monkeypatch.setattr(users.httpx, "Client", FakeClient)
    monkeypatch.setattr(
        users,
        "get_workspace_access_token",
        lambda **kwargs: ("test-token", 3600),
    )

    with pytest.raises(WorkspaceApiError) as error:
        users.list_users()

    assert captured["timeout"] == 30.0
    assert error.value.category == "timeout"
    assert error.value.code == "WORKSPACE_HTTP"
    assert error.value.layer == "workspace"
    assert error.value.operation == "users.list"
    assert error.value.http_status is None
    assert "SECRET TIMEOUT" not in str(error.value)
