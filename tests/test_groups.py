import httpx
import pytest

from google_workspace_admin.directory import groups
from google_workspace_admin.http_errors import WorkspaceApiError


def _configure_http(monkeypatch, payload, status_code=200):
    captured = {"calls": 0}

    class FakeResponse:
        def __init__(self):
            self.status_code = status_code

        def raise_for_status(self):
            if self.status_code >= 400:
                request = httpx.Request("GET", groups.GROUPS_URL)
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

    monkeypatch.setattr(groups.httpx, "Client", FakeClient)
    monkeypatch.setattr(groups, "get_workspace_access_token", fake_token)
    return captured


def test_list_groups_paginates_with_readonly_scope(monkeypatch):
    captured = _configure_http(
        monkeypatch,
        {"groups": [{"id": "group-1"}], "nextPageToken": "next-group"},
    )

    result = groups.list_groups(max_results=20, page_token="previous-group")

    assert captured["calls"] == 1
    assert captured["timeout"] == 30.0
    assert captured["scopes"] == [groups.DIRECTORY_GROUP_SCOPE]
    assert groups.DIRECTORY_GROUP_SCOPE.endswith("admin.directory.group.readonly")
    assert captured["params"] == {
        "customer": "my_customer",
        "maxResults": 20,
        "pageToken": "previous-group",
    }
    assert result == [{"id": "group-1"}]
    assert result.next_page_token == "next-group"


@pytest.mark.parametrize("value", [True, 1.5, "20", 0, 201])
def test_list_groups_rejects_invalid_max_results(monkeypatch, value):
    monkeypatch.setattr(
        groups,
        "get_workspace_access_token",
        lambda **kwargs: pytest.fail("autenticação não deve ocorrer"),
    )
    with pytest.raises(ValueError):
        groups.list_groups(max_results=value)


@pytest.mark.parametrize("value", ["", " ", 42])
def test_list_groups_rejects_invalid_page_token(monkeypatch, value):
    monkeypatch.setattr(
        groups,
        "get_workspace_access_token",
        lambda **kwargs: pytest.fail("autenticação não deve ocorrer"),
    )
    with pytest.raises(ValueError):
        groups.list_groups(page_token=value)


def test_list_groups_rejects_malformed_response(monkeypatch):
    _configure_http(monkeypatch, {"groups": ["unexpected"]})
    with pytest.raises(WorkspaceApiError) as error:
        groups.list_groups()
    assert error.value.category == "malformed_response"


def test_list_groups_exposes_safe_http_error(monkeypatch):
    _configure_http(monkeypatch, {}, status_code=500)
    with pytest.raises(WorkspaceApiError) as error:
        groups.list_groups()
    assert error.value.category == "upstream_error"
    assert error.value.status_code == 500
    assert "SECRET BODY" not in str(error.value)
