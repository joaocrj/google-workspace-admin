import httpx

from google_workspace_admin.auth.dwd import get_workspace_access_token


DIRECTORY_DOMAIN_SCOPE = (
    "https://www.googleapis.com/auth/admin.directory.domain.readonly"
)

DOMAINS_URL = (
    "https://admin.googleapis.com/admin/directory/v1/"
    "customer/my_customer/domains"
)


def _authorization_headers() -> dict[str, str]:
    token, _ = get_workspace_access_token(
        scopes=[DIRECTORY_DOMAIN_SCOPE]
    )
    return {"Authorization": f"Bearer {token}"}


def list_domains() -> list[dict]:
    """
    Lista os domínios do Google Workspace.
    """
    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            DOMAINS_URL,
            headers=_authorization_headers(),
        )
        response.raise_for_status()

        return response.json().get("domains", [])