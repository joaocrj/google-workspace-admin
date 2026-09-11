import pytest

from google_workspace_admin.directory.resources import calendars


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
            captured["method"] = "GET"
            captured["url"] = url
            captured["headers"] = headers
            captured["params"] = params
            return FakeResponse()

    def fake_get_workspace_access_token(*, scopes):
        captured["scopes"] = scopes
        return "test-value", 3600

    monkeypatch.setattr(calendars.httpx, "Client", FakeClient)
    monkeypatch.setattr(
        calendars,
        "get_workspace_access_token",
        fake_get_workspace_access_token,
    )

    return captured


def test_list_calendar_resources_uses_directory_endpoint_and_default_page(
    monkeypatch,
):
    captured = _configure_http(
        monkeypatch,
        {
            "items": [{"resourceId": "test-resource"}],
            "nextPageToken": "test-page",
        },
    )

    result = calendars.list_calendar_resources()

    assert captured["method"] == "GET"
    assert captured["url"] == calendars.CALENDAR_RESOURCES_URL
    assert captured["timeout"] == 30.0
    assert captured["scopes"] == [
        calendars.DIRECTORY_RESOURCE_CALENDAR_READONLY_SCOPE
    ]
    assert captured["params"] == {"maxResults": 100}
    assert captured["raised_for_status"] is True
    assert result == {
        "resources": [{"resourceId": "test-resource"}],
        "next_page_token": "test-page",
    }


@pytest.mark.parametrize("max_results", [1, 500])
def test_list_calendar_resources_accepts_documented_page_limits(
    monkeypatch,
    max_results,
):
    captured = _configure_http(monkeypatch, {})

    result = calendars.list_calendar_resources(max_results=max_results)

    assert captured["params"] == {"maxResults": max_results}
    assert result == {"resources": [], "next_page_token": None}


def test_list_calendar_resources_preserves_optional_query_parameters(
    monkeypatch,
):
    captured = _configure_http(monkeypatch, {})

    calendars.list_calendar_resources(
        page_token="test-page",
        order_by="buildingId, capacity desc",
        query="resourceCategory=CONFERENCE_ROOM",
    )

    assert captured["params"] == {
        "maxResults": 100,
        "pageToken": "test-page",
        "orderBy": "buildingId, capacity desc",
        "query": "resourceCategory=CONFERENCE_ROOM",
    }


@pytest.mark.parametrize("max_results", [0, 501])
def test_list_calendar_resources_rejects_invalid_page_limits_before_authentication(
    monkeypatch,
    max_results,
):
    def fail_if_authentication_is_requested(*, scopes):
        pytest.fail("A autenticação não deve ser chamada para limite inválido.")

    monkeypatch.setattr(
        calendars,
        "get_workspace_access_token",
        fail_if_authentication_is_requested,
    )

    with pytest.raises(
        ValueError,
        match="max_results deve estar entre 1 e 500",
    ):
        calendars.list_calendar_resources(max_results=max_results)


@pytest.mark.parametrize(
    ("parameter_name", "value"),
    [
        ("page_token", ""),
        ("page_token", "   "),
        ("order_by", "\t"),
        ("query", "  "),
    ],
)
def test_list_calendar_resources_rejects_blank_strings_before_authentication(
    monkeypatch,
    parameter_name,
    value,
):
    def fail_if_authentication_is_requested(*, scopes):
        pytest.fail("A autenticação não deve ser chamada para parâmetro inválido.")

    monkeypatch.setattr(
        calendars,
        "get_workspace_access_token",
        fail_if_authentication_is_requested,
    )

    with pytest.raises(
        ValueError,
        match=f"{parameter_name} não pode estar vazio",
    ):
        calendars.list_calendar_resources(**{parameter_name: value})
