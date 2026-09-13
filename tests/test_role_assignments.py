import httpx
import pytest

from google_workspace_admin.directory import role_assignments
from google_workspace_admin.http_errors import WorkspaceApiError


def _configure_http(monkeypatch, payload, status_code=200):
    captured = {"calls": 0}

    class FakeResponse:
        def __init__(self):
            self.status_code = status_code

        def raise_for_status(self):
            if self.status_code >= 400:
                request = httpx.Request(
                    "GET",
                    role_assignments.ROLE_ASSIGNMENTS_URL,
                )
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

    monkeypatch.setattr(role_assignments.httpx, "Client", FakeClient)
    monkeypatch.setattr(
        role_assignments,
        "get_workspace_access_token",
        fake_token,
    )
    return captured


def test_list_role_assignments_paginates_with_explicit_limit(monkeypatch):
    captured = _configure_http(
        monkeypatch,
        {
            "items": [{"roleAssignmentId": "assignment-1"}],
            "nextPageToken": "next-assignment",
        },
    )

    result = role_assignments.list_role_assignments(
        max_results=100,
        page_token="previous-assignment",
    )

    assert captured["calls"] == 1
    assert captured["timeout"] == 30.0
    assert captured["scopes"] == [
        role_assignments.DIRECTORY_ROLE_MANAGEMENT_SCOPE
    ]
    assert captured["params"] == {
        "maxResults": 100,
        "pageToken": "previous-assignment",
    }
    assert result == [{"roleAssignmentId": "assignment-1"}]
    assert result.next_page_token == "next-assignment"


@pytest.mark.parametrize("value", [True, 1.5, "100", 0, 101])
def test_list_role_assignments_rejects_invalid_max_results(monkeypatch, value):
    monkeypatch.setattr(
        role_assignments,
        "get_workspace_access_token",
        lambda **kwargs: pytest.fail("autenticação não deve ocorrer"),
    )
    with pytest.raises(ValueError):
        role_assignments.list_role_assignments(max_results=value)


@pytest.mark.parametrize("value", ["", "\t", 42])
def test_list_role_assignments_rejects_invalid_page_token(monkeypatch, value):
    monkeypatch.setattr(
        role_assignments,
        "get_workspace_access_token",
        lambda **kwargs: pytest.fail("autenticação não deve ocorrer"),
    )
    with pytest.raises(ValueError):
        role_assignments.list_role_assignments(page_token=value)


def test_list_role_assignments_rejects_malformed_response(monkeypatch):
    _configure_http(monkeypatch, {"items": ["unexpected"]})
    with pytest.raises(WorkspaceApiError):
        role_assignments.list_role_assignments()


def test_list_role_assignments_exposes_safe_http_error(monkeypatch):
    _configure_http(monkeypatch, {}, status_code=500)
    with pytest.raises(WorkspaceApiError) as error:
        role_assignments.list_role_assignments()
    assert error.value.category == "upstream_error"
    assert error.value.status_code == 500
    assert error.value.operation == "role_assignments.list"
    assert error.value.operation != "unknown"
    assert "SECRET BODY" not in str(error.value)
