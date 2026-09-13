import httpx
import pytest

from google_workspace_admin.directory import group_members
from google_workspace_admin.http_errors import WorkspaceApiError


def _configure_http(monkeypatch, payload, status_code=200):
    captured = {"calls": 0}

    class FakeResponse:
        def __init__(self):
            self.status_code = status_code

        def raise_for_status(self):
            if self.status_code >= 400:
                request = httpx.Request("GET", group_members.GROUPS_URL)
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

    monkeypatch.setattr(group_members.httpx, "Client", FakeClient)
    monkeypatch.setattr(
        group_members,
        "get_workspace_access_token",
        fake_token,
    )
    return captured


def test_list_group_members_paginates_with_readonly_scope(monkeypatch):
    captured = _configure_http(
        monkeypatch,
        {"members": [{"id": "member-1"}], "nextPageToken": "next-member"},
    )

    result = group_members.list_group_members(
        "group@example.com",
        max_results=25,
        page_token="previous-member",
    )

    assert captured["calls"] == 1
    assert captured["timeout"] == 30.0
    assert captured["scopes"] == [group_members.DIRECTORY_GROUP_MEMBER_SCOPE]
    assert group_members.DIRECTORY_GROUP_MEMBER_SCOPE.endswith(
        "admin.directory.group.member.readonly"
    )
    assert captured["params"] == {
        "maxResults": 25,
        "pageToken": "previous-member",
    }
    assert result == [{"id": "member-1"}]
    assert result.next_page_token == "next-member"


@pytest.mark.parametrize("value", [True, 1.5, "20", 0, 201])
def test_list_group_members_rejects_invalid_max_results(monkeypatch, value):
    monkeypatch.setattr(
        group_members,
        "get_workspace_access_token",
        lambda **kwargs: pytest.fail("autenticação não deve ocorrer"),
    )
    with pytest.raises(ValueError):
        group_members.list_group_members("group@example.com", max_results=value)


@pytest.mark.parametrize("value", ["", "\t", 42])
def test_list_group_members_rejects_invalid_page_token(monkeypatch, value):
    monkeypatch.setattr(
        group_members,
        "get_workspace_access_token",
        lambda **kwargs: pytest.fail("autenticação não deve ocorrer"),
    )
    with pytest.raises(ValueError):
        group_members.list_group_members(
            "group@example.com", page_token=value
        )


def test_list_group_members_rejects_malformed_response(monkeypatch):
    _configure_http(monkeypatch, {"members": {}})
    with pytest.raises(WorkspaceApiError) as error:
        group_members.list_group_members("group@example.com")
    assert error.value.category == "malformed_response"


def test_list_group_members_exposes_safe_http_error(monkeypatch):
    _configure_http(monkeypatch, {}, status_code=401)
    with pytest.raises(WorkspaceApiError) as error:
        group_members.list_group_members("group@example.com")
    assert error.value.category == "authentication"
    assert error.value.status_code == 401
    assert error.value.operation == "group_members.list"
    assert error.value.operation != "unknown"
    assert "SECRET BODY" not in str(error.value)
