from urllib.parse import quote

import httpx

from google_workspace_admin.auth.dwd import get_workspace_access_token


DIRECTORY_GROUP_MEMBER_SCOPE = (
    "https://www.googleapis.com/auth/admin.directory.group.member"
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
) -> list[dict]:
    """
    Lista os membros diretos de um grupo do Google Workspace.

    group_key pode ser o e-mail, alias ou ID imutável do grupo.
    """
    normalized_key = group_key.strip()
    if not normalized_key:
        raise ValueError("group_key não pode estar vazio.")

    if max_results < 1 or max_results > 200:
        raise ValueError("max_results deve estar entre 1 e 200.")

    encoded_key = quote(
        normalized_key,
        safe="",
    )

    url = f"{GROUPS_URL}/{encoded_key}/members"

    params = {
        "maxResults": max_results,
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            url,
            headers=_authorization_headers(),
            params=params,
        )
        response.raise_for_status()
        return response.json().get("members", [])