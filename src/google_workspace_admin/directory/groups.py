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


DIRECTORY_GROUP_SCOPE = (
    "https://www.googleapis.com/auth/admin.directory.group.readonly"
)

GROUPS_URL = (
    "https://admin.googleapis.com/admin/directory/v1/groups"
)


def _authorization_headers() -> dict[str, str]:
    token, _ = get_workspace_access_token(
        scopes=[DIRECTORY_GROUP_SCOPE]
    )
    return {"Authorization": f"Bearer {token}"}


def list_groups(
    max_results: int = 20,
    page_token: str | None = None,
) -> PageResult:
    """
    Lista grupos do Google Workspace pertencentes ao customer atual.
    """
    validate_max_results(max_results, 200)
    validate_page_token(page_token)

    params = {
        "customer": "my_customer",
        "maxResults": max_results,
    }
    if page_token is not None:
        params["pageToken"] = page_token

    with httpx.Client(timeout=30.0) as client:
        response = request_safe(
            client,
            "get",
            GROUPS_URL,
            "Directory groups.list",
            headers=_authorization_headers(),
            params=params,
        )
        payload = parse_json_object(response, "Directory groups.list")

    return PageResult(
        require_dict_list(payload, "groups", "Directory groups.list"),
        get_next_page_token(payload, "Directory groups.list"),
    )
