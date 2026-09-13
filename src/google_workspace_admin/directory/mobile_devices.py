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


DIRECTORY_MOBILE_DEVICE_SCOPE = (
    "https://www.googleapis.com/auth/admin.directory.device.mobile.readonly"
)

MOBILE_DEVICES_URL = (
    "https://admin.googleapis.com/admin/directory/v1/"
    "customer/my_customer/devices/mobile"
)


def _authorization_headers() -> dict[str, str]:
    token, _ = get_workspace_access_token(
        scopes=[DIRECTORY_MOBILE_DEVICE_SCOPE]
    )
    return {"Authorization": f"Bearer {token}"}


def list_mobile_devices(
    max_results: int = 100,
    page_token: str | None = None,
) -> PageResult:
    """
    Lista dispositivos móveis de usuários do Google Workspace.
    """
    validate_max_results(max_results, 100)
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
            MOBILE_DEVICES_URL,
            "Directory mobile devices.list",
            headers=_authorization_headers(),
            params=params,
        )
        payload = parse_json_object(
            response,
            "Directory mobile devices.list",
        )

    return PageResult(
        require_dict_list(
            payload,
            "mobiledevices",
            "Directory mobile devices.list",
        ),
        get_next_page_token(payload, "Directory mobile devices.list"),
    )
