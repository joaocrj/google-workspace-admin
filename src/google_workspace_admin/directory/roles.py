import httpx

from google_workspace_admin.auth.dwd import get_workspace_access_token


DIRECTORY_ROLE_MANAGEMENT_SCOPE = (
    "https://www.googleapis.com/auth/admin.directory.rolemanagement.readonly"
)

ROLES_URL = (
    "https://admin.googleapis.com/admin/directory/v1/"
    "customer/my_customer/roles"
)


def _authorization_headers() -> dict[str, str]:
    token, _ = get_workspace_access_token(
        scopes=[DIRECTORY_ROLE_MANAGEMENT_SCOPE]
    )
    return {"Authorization": f"Bearer {token}"}


def list_roles(
    max_results: int = 100,
) -> list[dict]:
    """
    Lista funções administrativas do Google Workspace.
    """
    if max_results < 1 or max_results > 100:
        raise ValueError("max_results deve estar entre 1 e 100.")

    params = {
        "maxResults": max_results,
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            ROLES_URL,
            headers=_authorization_headers(),
            params=params,
        )
        response.raise_for_status()

        return response.json().get("items", [])