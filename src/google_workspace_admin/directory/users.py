from urllib.parse import quote

import httpx

from google_workspace_admin.auth.dwd import get_workspace_access_token


DIRECTORY_USER_SCOPE = (
    "https://www.googleapis.com/auth/admin.directory.user"
)

USERS_URL = (
    "https://admin.googleapis.com/admin/directory/v1/users"
)


def _authorization_headers() -> dict[str, str]:
    token, _ = get_workspace_access_token(
        scopes=[DIRECTORY_USER_SCOPE]
    )

    return {
        "Authorization": f"Bearer {token}",
    }


def list_users(max_results: int = 5) -> list[dict]:
    params = {
        "customer": "my_customer",
        "maxResults": max_results,
        "orderBy": "email",
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            USERS_URL,
            headers=_authorization_headers(),
            params=params,
        )

        response.raise_for_status()

        return response.json().get("users", [])


def get_user(user_key: str) -> dict:
    """
    Obtém um usuário do Google Workspace por e-mail,
    alias ou ID imutável.
    """
    normalized_key = user_key.strip()

    if not normalized_key:
        raise ValueError("user_key não pode estar vazio.")

    encoded_key = quote(
        normalized_key,
        safe="",
    )

    url = f"{USERS_URL}/{encoded_key}"

    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            url,
            headers=_authorization_headers(),
        )

        response.raise_for_status()

        return response.json()