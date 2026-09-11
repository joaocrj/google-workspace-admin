import pytest

from google_workspace_admin.directory.resources import buildings


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

    monkeypatch.setattr(buildings.httpx, "Client", FakeClient)
    monkeypatch.setattr(
        buildings,
        "get_workspace_access_token",
        fake_get_workspace_access_token,
    )

    return captured


def test_list_buildings_uses_directory_endpoint_and_default_page(
    monkeypatch,
):
    captured = _configure_http(
        monkeypatch,
        {
            "buildings": [{"buildingId": "test-building"}],
            "nextPageToken": "test-page",
        },
    )

    result = buildings.list_buildings()

    assert captured["method"] == "GET"
    assert captured["url"] == buildings.BUILDINGS_URL
    assert captured["timeout"] == 30.0
    assert captured["scopes"] == [
        buildings.DIRECTORY_RESOURCE_CALENDAR_READONLY_SCOPE
    ]
    assert captured["params"] == {"maxResults": 100}
    assert captured["raised_for_status"] is True
    assert result == {
        "buildings": [{"buildingId": "test-building"}],
        "next_page_token": "test-page",
    }


@pytest.mark.parametrize("max_results", [1, 500])
def test_list_buildings_accepts_documented_page_limits(
    monkeypatch,
    max_results,
):
    captured = _configure_http(monkeypatch, {})

    result = buildings.list_buildings(max_results=max_results)

    assert captured["params"] == {"maxResults": max_results}
    assert result == {
        "buildings": [],
        "next_page_token": None,
    }


def test_list_buildings_preserves_a_valid_page_token(monkeypatch):
    captured = _configure_http(monkeypatch, {})

    buildings.list_buildings(page_token="test-page")

    assert captured["params"] == {
        "maxResults": 100,
        "pageToken": "test-page",
    }


@pytest.mark.parametrize("max_results", [0, 501])
def test_list_buildings_rejects_invalid_page_limits_before_authentication(
    monkeypatch,
    max_results,
):
    def fail_if_authentication_is_requested(*, scopes):
        pytest.fail("A autenticação não deve ser chamada para limite inválido.")

    monkeypatch.setattr(
        buildings,
        "get_workspace_access_token",
        fail_if_authentication_is_requested,
    )

    with pytest.raises(
        ValueError,
        match="max_results deve estar entre 1 e 500",
    ):
        buildings.list_buildings(max_results=max_results)


@pytest.mark.parametrize("page_token", ["", "   ", "\t"])
def test_list_buildings_rejects_blank_page_token_before_authentication(
    monkeypatch,
    page_token,
):
    def fail_if_authentication_is_requested(*, scopes):
        pytest.fail("A autenticação não deve ser chamada para token inválido.")

    monkeypatch.setattr(
        buildings,
        "get_workspace_access_token",
        fail_if_authentication_is_requested,
    )

    with pytest.raises(
        ValueError,
        match="page_token não pode estar vazio",
    ):
        buildings.list_buildings(page_token=page_token)
