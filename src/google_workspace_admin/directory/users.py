from urllib.parse import quote

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


DIRECTORY_USER_SCOPE = (
    "https://www.googleapis.com/auth/admin.directory.user.readonly"
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


def list_users(
    max_results: int = 5,
    page_token: str | None = None,
) -> PageResult:
    validate_max_results(max_results, 100)
    validate_page_token(page_token)

    params = {
        "customer": "my_customer",
        "maxResults": max_results,
        "orderBy": "email",
    }
    if page_token is not None:
        params["pageToken"] = page_token

    with httpx.Client(timeout=30.0) as client:
        response = request_safe(
            client,
            "get",
            USERS_URL,
            "Directory users.list",
            headers=_authorization_headers(),
            params=params,
        )
        payload = parse_json_object(response, "Directory users.list")

    return PageResult(
        require_dict_list(payload, "users", "Directory users.list"),
        get_next_page_token(payload, "Directory users.list"),
    )


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
        response = request_safe(
            client,
            "get",
            url,
            "Directory users.get",
            headers=_authorization_headers(),
        )
        return parse_json_object(response, "Directory users.get")
