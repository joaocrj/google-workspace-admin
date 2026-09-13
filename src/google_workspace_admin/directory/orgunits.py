import httpx

from google_workspace_admin.auth.dwd import get_workspace_access_token
from google_workspace_admin.http_errors import (
    parse_json_object,
    require_dict_list,
    request_safe,
)


DIRECTORY_ORGUNIT_SCOPE = (
    "https://www.googleapis.com/auth/admin.directory.orgunit.readonly"
)

ORGUNITS_URL = (
    "https://admin.googleapis.com/admin/directory/v1/"
    "customer/my_customer/orgunits"
)


def _authorization_headers() -> dict[str, str]:
    token, _ = get_workspace_access_token(
        scopes=[DIRECTORY_ORGUNIT_SCOPE]
    )
    return {"Authorization": f"Bearer {token}"}


def list_orgunits(
    org_unit_path: str = "/",
    org_unit_type: str = "all",
) -> list[dict]:
    """
    Lista unidades organizacionais do Google Workspace.

    org_unit_path define a raiz da consulta.
    org_unit_type pode ser "all", "children" ou "all_including_parent".
    """
    normalized_path = org_unit_path.strip()
    if not normalized_path:
        raise ValueError("org_unit_path não pode estar vazio.")

    if not normalized_path.startswith("/"):
        raise ValueError("org_unit_path deve começar com '/'.")

    allowed_types = {
        "all",
        "children",
        "all_including_parent",
    }
    if org_unit_type not in allowed_types:
        raise ValueError(
            "org_unit_type deve ser 'all', 'children' "
            "ou 'all_including_parent'."
        )

    params = {
        "orgUnitPath": normalized_path,
        "type": org_unit_type,
    }

    with httpx.Client(timeout=30.0) as client:
        response = request_safe(
            client,
            "get",
            ORGUNITS_URL,
            "Directory orgunits.list",
            headers=_authorization_headers(),
            params=params,
        )
        payload = parse_json_object(response, "Directory orgunits.list")

    return require_dict_list(
        payload,
        "organizationUnits",
        "Directory orgunits.list",
    )
