import httpx
import pytest

from google_workspace_admin.reports import admin_audit


def _configure_http(monkeypatch, payload: dict) -> dict:
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            captured["raised_for_status"] = True

        def json(self):
            return payload

    class FakeClient:
        def __init__(self, timeout):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def get(self, url, headers, params):
            captured["calls"] = captured.get("calls", 0) + 1
            captured["method"] = "GET"
            captured["url"] = url
            captured["headers"] = headers
            captured["params"] = params
            return FakeResponse()

    def fake_get_workspace_access_token(*, scopes):
        captured["scopes"] = scopes
        return "test-value", 3600

    monkeypatch.setattr(admin_audit.httpx, "Client", FakeClient)
    monkeypatch.setattr(
        admin_audit,
        "get_workspace_access_token",
        fake_get_workspace_access_token,
    )

    return captured


def test_list_admin_audit_uses_default_all_path_and_page(monkeypatch):
    captured = _configure_http(
        monkeypatch,
        {
            "items": [{"id": {"time": "0"}}],
            "nextPageToken": "test-page",
        },
    )

    result = admin_audit.list_admin_audit_activities()

    assert captured["method"] == "GET"
    assert captured["url"] == admin_audit.ADMIN_AUDIT_ACTIVITIES_URL.format(
        user_key="all"
    )
    assert captured["timeout"] == 30.0
    assert captured["scopes"] == [
        admin_audit.ADMIN_REPORTS_AUDIT_READONLY_SCOPE
    ]
    assert captured["params"] == {"maxResults": 25}
    assert captured["raised_for_status"] is True
    assert captured["calls"] == 1
    assert result == {
        "activities": [{"id": {"time": "0"}}],
        "next_page_token": "test-page",
    }


def test_list_admin_audit_encodes_user_key_and_forwards_parameters(
    monkeypatch,
):
    captured = _configure_http(monkeypatch, {})

    result = admin_audit.list_admin_audit_activities(
        max_results=100,
        page_token="test-page",
        user_key="admin+audit@example.com",
        event_name="CHANGE_SETTING",
        filters="SETTING_NAME==EXAMPLE",
        start_time="2026-09-10T00:00:00Z",
        end_time="2026-09-11T00:00:00+00:00",
        actor_ip_address="2001:db8::1",
        org_unit_id="id:org-unit",
    )

    assert captured["url"].endswith(
        "/users/admin%2Baudit%40example.com/applications/admin"
    )
    assert captured["params"] == {
        "maxResults": 100,
        "pageToken": "test-page",
        "eventName": "CHANGE_SETTING",
        "filters": "SETTING_NAME==EXAMPLE",
        "startTime": "2026-09-10T00:00:00Z",
        "endTime": "2026-09-11T00:00:00+00:00",
        "actorIpAddress": "2001:db8::1",
        "orgUnitID": "id:org-unit",
    }
    assert "customerId" not in captured["params"]
    assert result == {"activities": [], "next_page_token": None}


@pytest.mark.parametrize("max_results", [1, 100])
def test_list_admin_audit_accepts_mcp_page_limits(
    monkeypatch,
    max_results,
):
    captured = _configure_http(monkeypatch, {})

    result = admin_audit.list_admin_audit_activities(
        max_results=max_results,
    )

    assert captured["params"] == {"maxResults": max_results}
    assert result == {"activities": [], "next_page_token": None}


@pytest.mark.parametrize("max_results", [0, 101])
def test_list_admin_audit_rejects_invalid_limits_before_authentication(
    monkeypatch,
    max_results,
):
    def fail_if_authentication_is_requested(*, scopes):
        pytest.fail("A autenticação não deve ser chamada para limite inválido.")

    monkeypatch.setattr(
        admin_audit,
        "get_workspace_access_token",
        fail_if_authentication_is_requested,
    )

    with pytest.raises(
        ValueError,
        match="max_results deve estar entre 1 e 100",
    ):
        admin_audit.list_admin_audit_activities(max_results=max_results)


@pytest.mark.parametrize(
    ("parameter_name", "value"),
    [
        ("page_token", ""),
        ("user_key", "  "),
        ("event_name", "\t"),
        ("filters", "  "),
        ("start_time", ""),
        ("end_time", "  "),
        ("actor_ip_address", "\t"),
        ("org_unit_id", " "),
    ],
)
def test_list_admin_audit_rejects_blank_strings_before_authentication(
    monkeypatch,
    parameter_name,
    value,
):
    def fail_if_authentication_is_requested(*, scopes):
        pytest.fail("A autenticação não deve ser chamada para string inválida.")

    monkeypatch.setattr(
        admin_audit,
        "get_workspace_access_token",
        fail_if_authentication_is_requested,
    )

    with pytest.raises(
        ValueError,
        match=f"{parameter_name} não pode estar vazio",
    ):
        admin_audit.list_admin_audit_activities(**{parameter_name: value})


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({"start_time": "2026-09-10"}, "start_time deve estar"),
        ({"end_time": "2026-09-10T00:00:00"}, "end_time deve estar"),
        (
            {
                "start_time": "2026-09-11T00:00:00Z",
                "end_time": "2026-09-10T00:00:00Z",
            },
            "start_time deve ser anterior",
        ),
    ],
)
def test_list_admin_audit_validates_times_before_authentication(
    monkeypatch,
    arguments,
    message,
):
    def fail_if_authentication_is_requested(*, scopes):
        pytest.fail("A autenticação não deve ser chamada para data inválida.")

    monkeypatch.setattr(
        admin_audit,
        "get_workspace_access_token",
        fail_if_authentication_is_requested,
    )

    with pytest.raises(ValueError, match=message):
        admin_audit.list_admin_audit_activities(**arguments)


def test_list_admin_audit_propagates_http_errors_without_retry(monkeypatch):
    request = httpx.Request(
        "GET",
        admin_audit.ADMIN_AUDIT_ACTIVITIES_URL.format(user_key="all"),
    )
    response = httpx.Response(403, request=request)
    calls = []

    class FailingResponse:
        def raise_for_status(self):
            raise httpx.HTTPStatusError(
                "forbidden",
                request=request,
                response=response,
            )

    class FakeClient:
        def __init__(self, timeout):
            assert timeout == 30.0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def get(self, url, headers, params):
            calls.append((url, params))
            return FailingResponse()

    monkeypatch.setattr(admin_audit.httpx, "Client", FakeClient)
    monkeypatch.setattr(
        admin_audit,
        "get_workspace_access_token",
        lambda *, scopes: ("test-value", 3600),
    )

    with pytest.raises(httpx.HTTPStatusError, match="forbidden"):
        admin_audit.list_admin_audit_activities()

    assert calls == [
        (
            admin_audit.ADMIN_AUDIT_ACTIVITIES_URL.format(user_key="all"),
            {"maxResults": 25},
        )
    ]
