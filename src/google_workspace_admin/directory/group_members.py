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


DIRECTORY_GROUP_MEMBER_SCOPE = (
    "https://www.googleapis.com/auth/admin.directory.group.member.readonly"
)

GROUPS_URL = (
    "https://admin.googleapis.com/admin/directory/v1/groups"
)


def _authorization_headers() -> dict[str, str]:
    token, _ = get_workspace_access_token(
        scopes=[DIRECTORY_GROUP_MEMBER_SCOPE]
    )
    return {"Authorization": f"Bearer {token}"}


def list_group_members(
    group_key: str,
    max_results: int = 200,
    page_token: str | None = None,
) -> PageResult:
    """
    Lista os membros diretos de um grupo do Google Workspace.

    group_key pode ser o e-mail, alias ou ID imutável do grupo.
    """
    normalized_key = group_key.strip()
    if not normalized_key:
        raise ValueError("group_key não pode estar vazio.")

    validate_max_results(max_results, 200)
    validate_page_token(page_token)

    encoded_key = quote(
        normalized_key,
        safe="",
    )

    url = f"{GROUPS_URL}/{encoded_key}/members"

    params = {
        "maxResults": max_results,
    }
    if page_token is not None:
        params["pageToken"] = page_token

    with httpx.Client(timeout=30.0) as client:
        response = request_safe(
            client,
            "get",
            url,
            "Directory group members.list",
            headers=_authorization_headers(),
            params=params,
        )
        payload = parse_json_object(response, "Directory group members.list")

    return PageResult(
        require_dict_list(payload, "members", "Directory group members.list"),
        get_next_page_token(payload, "Directory group members.list"),
    )
