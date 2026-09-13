import httpx

from google_workspace_admin.auth.dwd import get_workspace_access_token
from google_workspace_admin.http_errors import (
    PageResult,
    get_next_page_token,
    parse_json_object,
    require_dict_list,
    request_safe,
    validate_max_results,
    validate_page_token,
)


DIRECTORY_CHROMEOS_DEVICE_SCOPE = (
    "https://www.googleapis.com/auth/admin.directory.device.chromeos.readonly"
)

CHROMEOS_DEVICES_URL = (
    "https://admin.googleapis.com/admin/directory/v1/"
    "customer/my_customer/devices/chromeos"
)


def _authorization_headers() -> dict[str, str]:
    token, _ = get_workspace_access_token(
        scopes=[DIRECTORY_CHROMEOS_DEVICE_SCOPE]
    )
    return {"Authorization": f"Bearer {token}"}


def list_chromeos_devices(
    max_results: int = 100,
    page_token: str | None = None,
) -> PageResult:
    """
    Lista dispositivos ChromeOS do Google Workspace.
    """
    validate_max_results(max_results, 300)
    validate_page_token(page_token)

    params = {
        "maxResults": max_results,
        "projection": "FULL",
    }
    if page_token is not None:
        params["pageToken"] = page_token

    with httpx.Client(timeout=30.0) as client:
        response = request_safe(
            client,
            "get",
            CHROMEOS_DEVICES_URL,
            "Directory chromeos devices.list",
            headers=_authorization_headers(),
            params=params,
        )
        payload = parse_json_object(
            response,
            "Directory chromeos devices.list",
        )

    return PageResult(
        require_dict_list(
            payload,
            "chromeosdevices",
            "Directory chromeos devices.list",
        ),
        get_next_page_token(payload, "Directory chromeos devices.list"),
    )
