import httpx
import pytest

from google_workspace_admin.directory import mobile_devices
from google_workspace_admin.http_errors import WorkspaceApiError


def _configure_http(monkeypatch, payload, status_code=200):
    captured = {"calls": 0}

    class FakeResponse:
        def __init__(self):
            self.status_code = status_code

        def raise_for_status(self):
            if self.status_code >= 400:
                request = httpx.Request("GET", mobile_devices.MOBILE_DEVICES_URL)
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

    monkeypatch.setattr(mobile_devices.httpx, "Client", FakeClient)
    monkeypatch.setattr(
        mobile_devices,
        "get_workspace_access_token",
        fake_token,
    )
    return captured


def test_list_mobile_devices_paginates_and_preserves_inventory_fields(monkeypatch):
    captured = _configure_http(
        monkeypatch,
        {
            "mobiledevices": [{"deviceId": "device-1", "imei": "imei-1"}],
            "nextPageToken": "next-device",
        },
    )

    result = mobile_devices.list_mobile_devices(
        max_results=100,
        page_token="previous-device",
    )

    assert captured["calls"] == 1
    assert captured["timeout"] == 30.0
    assert captured["scopes"] == [mobile_devices.DIRECTORY_MOBILE_DEVICE_SCOPE]
    assert captured["params"] == {
        "maxResults": 100,
        "projection": "FULL",
        "pageToken": "previous-device",
    }
    assert result == [{"deviceId": "device-1", "imei": "imei-1"}]
    assert result.next_page_token == "next-device"


@pytest.mark.parametrize("value", [True, 1.5, "100", 0, 101])
def test_list_mobile_devices_rejects_invalid_max_results(monkeypatch, value):
    monkeypatch.setattr(
        mobile_devices,
        "get_workspace_access_token",
        lambda **kwargs: pytest.fail("autenticação não deve ocorrer"),
    )
    with pytest.raises(ValueError):
        mobile_devices.list_mobile_devices(max_results=value)


@pytest.mark.parametrize("value", ["", " ", 42])
def test_list_mobile_devices_rejects_invalid_page_token(monkeypatch, value):
    monkeypatch.setattr(
        mobile_devices,
        "get_workspace_access_token",
        lambda **kwargs: pytest.fail("autenticação não deve ocorrer"),
    )
    with pytest.raises(ValueError):
        mobile_devices.list_mobile_devices(page_token=value)


def test_list_mobile_devices_rejects_malformed_response(monkeypatch):
    _configure_http(monkeypatch, {"mobiledevices": ["unexpected"]})
    with pytest.raises(WorkspaceApiError):
        mobile_devices.list_mobile_devices()


def test_list_mobile_devices_exposes_safe_http_error(monkeypatch):
    _configure_http(monkeypatch, {}, status_code=403)
    with pytest.raises(WorkspaceApiError) as error:
        mobile_devices.list_mobile_devices()
    assert error.value.category == "authorization"
    assert error.value.status_code == 403
    assert error.value.operation == "mobile_devices.list"
    assert error.value.operation != "unknown"
    assert "SECRET BODY" not in str(error.value)
