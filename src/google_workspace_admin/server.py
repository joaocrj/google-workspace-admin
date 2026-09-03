from mcp.server import MCPServer

from google_workspace_admin.directory.users import list_users


mcp = MCPServer(
    name="Google Workspace Admin",
)


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

    return [
        {
            "primary_email": user.get("primaryEmail"),
            "full_name": user.get("name", {}).get("fullName"),
            "suspended": user.get("suspended"),
            "org_unit_path": user.get("orgUnitPath"),
        }
        for user in users
    ]


if __name__ == "__main__":
    mcp.run()
