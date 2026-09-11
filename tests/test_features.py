import httpx
import pytest

from google_workspace_admin.directory.resources import features


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

    monkeypatch.setattr(features.httpx, "Client", FakeClient)
    monkeypatch.setattr(
        features,
        "get_workspace_access_token",
        fake_get_workspace_access_token,
    )

    return captured


def test_list_calendar_features_uses_directory_endpoint_and_default_page(
    monkeypatch,
):
    captured = _configure_http(
        monkeypatch,
        {
            "features": [{"name": "test-feature"}],
            "nextPageToken": "test-page",
        },
    )

    result = features.list_calendar_features()

    assert captured["method"] == "GET"
    assert captured["url"] == features.CALENDAR_FEATURES_URL
    assert captured["timeout"] == 30.0
    assert captured["scopes"] == [
        features.DIRECTORY_RESOURCE_CALENDAR_READONLY_SCOPE
    ]
    assert captured["params"] == {"maxResults": 100}
    assert captured["raised_for_status"] is True
    assert result == {
        "features": [{"name": "test-feature"}],
        "next_page_token": "test-page",
    }


@pytest.mark.parametrize("max_results", [1, 500])
def test_list_calendar_features_accepts_documented_page_limits(
    monkeypatch,
    max_results,
):
    captured = _configure_http(monkeypatch, {})

    result = features.list_calendar_features(max_results=max_results)

    assert captured["params"] == {"maxResults": max_results}
    assert result == {"features": [], "next_page_token": None}


def test_list_calendar_features_preserves_a_valid_page_token(monkeypatch):
    captured = _configure_http(monkeypatch, {})

    features.list_calendar_features(page_token="test-page")

    assert captured["params"] == {
        "maxResults": 100,
        "pageToken": "test-page",
    }


@pytest.mark.parametrize("max_results", [0, 501])
def test_list_calendar_features_rejects_invalid_page_limits_before_authentication(
    monkeypatch,
    max_results,
):
    def fail_if_authentication_is_requested(*, scopes):
        pytest.fail("A autenticação não deve ser chamada para limite inválido.")

    monkeypatch.setattr(
        features,
        "get_workspace_access_token",
        fail_if_authentication_is_requested,
    )

    with pytest.raises(
        ValueError,
        match="max_results deve estar entre 1 e 500",
    ):
        features.list_calendar_features(max_results=max_results)


@pytest.mark.parametrize("page_token", ["", "   ", "\t"])
def test_list_calendar_features_rejects_blank_page_token_before_authentication(
    monkeypatch,
    page_token,
):
    def fail_if_authentication_is_requested(*, scopes):
        pytest.fail("A autenticação não deve ser chamada para token inválido.")

    monkeypatch.setattr(
        features,
        "get_workspace_access_token",
        fail_if_authentication_is_requested,
    )

    with pytest.raises(
        ValueError,
        match="page_token não pode estar vazio",
    ):
        features.list_calendar_features(page_token=page_token)


def test_list_calendar_features_propagates_http_errors(monkeypatch):
    request = httpx.Request("GET", features.CALENDAR_FEATURES_URL)
    response = httpx.Response(403, request=request)

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
            assert url == features.CALENDAR_FEATURES_URL
            assert params == {"maxResults": 100}
            return FailingResponse()

    monkeypatch.setattr(features.httpx, "Client", FakeClient)
    monkeypatch.setattr(
        features,
        "get_workspace_access_token",
        lambda *, scopes: ("test-value", 3600),
    )

    with pytest.raises(httpx.HTTPStatusError, match="forbidden"):
        features.list_calendar_features()
