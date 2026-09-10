import httpx

from google_workspace_admin.auth.dwd import get_workspace_access_token


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
) -> list[dict]:
    """
    Lista dispositivos móveis de usuários do Google Workspace.
    """
    if max_results < 1 or max_results > 100:
        raise ValueError("max_results deve estar entre 1 e 100.")

    params = {
        "maxResults": max_results,
        "projection": "FULL",
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            MOBILE_DEVICES_URL,
            headers=_authorization_headers(),
            params=params,
        )
        response.raise_for_status()

        return response.json().get("mobiledevices", [])