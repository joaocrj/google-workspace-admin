from google_workspace_admin.auth.dwd import (
    get_workspace_access_token,
)
from google_workspace_admin.directory.users import (
    DIRECTORY_USER_SCOPE,
    list_users,
)


def main():
    print("Google Workspace Admin MCP")
    print("--------------------------")
    print("Teste de autenticação keyless DWD")
    print()

    token, expires_in = get_workspace_access_token(
        scopes=[DIRECTORY_USER_SCOPE]
    )

    print("[OK] DWD access token obtido")
    print(f"[OK] Validade aproximada: {expires_in} segundos")
    print(f"[OK] Token presente: {bool(token)}")
    print()

    users = list_users(max_results=5)

    print(f"[OK] Directory API respondeu: {len(users)} usuários")
    print()

    for user in users:
        print(
            user.get("primaryEmail"),
            "| suspended:",
            user.get("suspended"),
        )


if __name__ == "__main__":
    main()
