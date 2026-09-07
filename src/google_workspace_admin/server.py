from mcp.server import MCPServer

from google_workspace_admin.directory.users import (
    get_user,
    list_users,
)


mcp = MCPServer(
    name="Google Workspace Admin",
)


def _serialize_user(user: dict) -> dict:
    """Seleciona os campos de usuário que podem ser expostos pelo MCP."""
    return {
        "id": user.get("id"),
        "primary_email": user.get("primaryEmail"),
        "full_name": user.get("name", {}).get("fullName"),
        "given_name": user.get("name", {}).get("givenName"),
        "family_name": user.get("name", {}).get("familyName"),
        "suspended": user.get("suspended"),
        "archived": user.get("archived"),
        "is_admin": user.get("isAdmin"),
        "is_delegated_admin": user.get("isDelegatedAdmin"),
        "org_unit_path": user.get("orgUnitPath"),
        "creation_time": user.get("creationTime"),
        "last_login_time": user.get("lastLoginTime"),
    }


@mcp.tool()
def workspace_status() -> dict:
    """Retorna o status básico do servidor Google Workspace Admin MCP."""
    return {
        "status": "ok",
        "server": "google-workspace-admin",
        "authentication": "ADC -> IAM signJwt -> DWD",
    }


@mcp.tool()
def workspace_users_list(max_results: int = 5) -> list[dict]:
    """
    Lista usuários do Google Workspace.

    Args:
        max_results: Quantidade máxima de usuários a retornar.
    """
    if max_results < 1 or max_results > 100:
        raise ValueError("max_results deve estar entre 1 e 100.")

    users = list_users(max_results=max_results)

    return [_serialize_user(user) for user in users]


@mcp.tool()
def workspace_user_get(user_key: str) -> dict:
    """
    Obtém detalhes de um usuário do Google Workspace.

    Args:
        user_key: E-mail principal, alias ou ID do usuário.
    """
    user = get_user(user_key)

    return _serialize_user(user)


if __name__ == "__main__":
    mcp.run()