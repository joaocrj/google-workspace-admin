import httpx

from google_workspace_admin.auth.dwd import get_workspace_access_token


DIRECTORY_DOMAIN_SCOPE = (
    "https://www.googleapis.com/auth/admin.directory.domain.readonly"
)

DOMAIN_ALIASES_URL = (
    "https://admin.googleapis.com/admin/directory/v1/"
    "customer/my_customer/domainaliases"
)


def _authorization_headers() -> dict[str, str]:
    token, _ = get_workspace_access_token(
        scopes=[DIRECTORY_DOMAIN_SCOPE]
    )
    return {"Authorization": f"Bearer {token}"}


def list_domain_aliases(
    parent_domain_name: str | None = None,
) -> list[dict]:
    """
    Lista os aliases de domínio do Google Workspace.

    Quando parent_domain_name é informado, retorna somente os aliases
    associados ao domínio pai especificado.
    """
    params = {}

    if parent_domain_name is not None:
        params["parentDomainName"] = parent_domain_name

    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            DOMAIN_ALIASES_URL,
            headers=_authorization_headers(),
            params=params,
        )
        response.raise_for_status()

        return response.json().get("domainAliases", [])