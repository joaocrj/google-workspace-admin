"""Package entry points for the Google Workspace Admin MCP."""


def main() -> None:
    """Start the MCP stdio server from the installed console script."""

    from google_workspace_admin.server import mcp

    mcp.run()
