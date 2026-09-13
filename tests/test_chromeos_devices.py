import httpx
import pytest

from google_workspace_admin.directory import chromeos_devices
from google_workspace_admin.http_errors import WorkspaceApiError


def _configure_http(monkeypatch, payload, status_code=200):
    captured = {"calls": 0}

    class FakeResponse:
        def __init__(self):
            self.status_code = status_code

        def raise_for_status(self):
            if self.status_code >= 400:
                request = httpx.Request("GET", chromeos_devices.CHROMEOS_DEVICES_URL)
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

    monkeypatch.setattr(chromeos_devices.httpx, "Client", FakeClient)
    monkeypatch.setattr(
        chromeos_devices,
        "get_workspace_access_token",
        fake_token,
    )
    return captured


def test_list_chromeos_devices_paginates_with_explicit_limit(monkeypatch):
    captured = _configure_http(
        monkeypatch,
        {
            "chromeosdevices": [{"deviceId": "chrome-1", "serialNumber": "s-1"}],
            "nextPageToken": "next-chrome",
        },
    )

    result = chromeos_devices.list_chromeos_devices(
        max_results=300,
        page_token="previous-chrome",
    )

    assert captured["calls"] == 1
    assert captured["timeout"] == 30.0
    assert captured["scopes"] == [chromeos_devices.DIRECTORY_CHROMEOS_DEVICE_SCOPE]
    assert captured["params"] == {
        "maxResults": 300,
        "projection": "FULL",
        "pageToken": "previous-chrome",
    }
    assert result == [{"deviceId": "chrome-1", "serialNumber": "s-1"}]
    assert result.next_page_token == "next-chrome"


@pytest.mark.parametrize("value", [True, 1.5, "300", 0, 301])
def test_list_chromeos_devices_rejects_invalid_max_results(monkeypatch, value):
    monkeypatch.setattr(
        chromeos_devices,
        "get_workspace_access_token",
        lambda **kwargs: pytest.fail("autenticação não deve ocorrer"),
    )
    with pytest.raises(ValueError):
        chromeos_devices.list_chromeos_devices(max_results=value)


@pytest.mark.parametrize("value", ["", "\t", 42])
def test_list_chromeos_devices_rejects_invalid_page_token(monkeypatch, value):
    monkeypatch.setattr(
        chromeos_devices,
        "get_workspace_access_token",
        lambda **kwargs: pytest.fail("autenticação não deve ocorrer"),
    )
    with pytest.raises(ValueError):
        chromeos_devices.list_chromeos_devices(page_token=value)


def test_list_chromeos_devices_rejects_malformed_response(monkeypatch):
    _configure_http(monkeypatch, {"chromeosdevices": {}})
    with pytest.raises(WorkspaceApiError):
        chromeos_devices.list_chromeos_devices()


def test_list_chromeos_devices_exposes_safe_http_error(monkeypatch):
    _configure_http(monkeypatch, {}, status_code=500)
    with pytest.raises(WorkspaceApiError) as error:
        chromeos_devices.list_chromeos_devices()
    assert error.value.category == "upstream_error"
    assert error.value.status_code == 500
    assert error.value.operation == "chromeos_devices.list"
    assert error.value.operation != "unknown"
    assert "SECRET BODY" not in str(error.value)
