import httpx

from google_workspace_admin.auth.dwd import get_workspace_access_token


DIRECTORY_USER_SCOPE = (
    "https://www.googleapis.com/auth/admin.directory.user"
)

USERS_URL = (
    "https://admin.googleapis.com/admin/directory/v1/users"
)


def list_users(max_results: int = 5) -> list[dict]:
    token, _ = get_workspace_access_token(
        scopes=[DIRECTORY_USER_SCOPE]
    )

    headers = {
        "Authorization": f"Bearer {token}",
    }

    params = {
        "customer": "my_customer",
        "maxResults": max_results,
        "orderBy": "email",
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            USERS_URL,
            headers=headers,
            params=params,
        )

        response.raise_for_status()

        return response.json().get("users", [])
