import httpx

from google_workspace_admin.auth.dwd import get_workspace_access_token


DIRECTORY_GROUP_SCOPE = (
    "https://www.googleapis.com/auth/admin.directory.group"
)

GROUPS_URL = (
    "https://admin.googleapis.com/admin/directory/v1/groups"
)


def _authorization_headers() -> dict[str, str]:
    token, _ = get_workspace_access_token(
        scopes=[DIRECTORY_GROUP_SCOPE]
    )
    return {"Authorization": f"Bearer {token}"}


def list_groups(max_results: int = 20) -> list[dict]:
    """
    Lista grupos do Google Workspace pertencentes ao customer atual.
    """
    if max_results < 1 or max_results > 200:
        raise ValueError("max_results deve estar entre 1 e 200.")

    params = {
        "customer": "my_customer",
        "maxResults": max_results,
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            GROUPS_URL,
            headers=_authorization_headers(),
            params=params,
        )
        response.raise_for_status()
        return response.json().get("groups", [])