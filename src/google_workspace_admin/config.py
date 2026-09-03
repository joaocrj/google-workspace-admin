from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    project_id: str = "codex-workspace-admin"

    service_account: str = (
        "codex-workspace@codex-workspace-admin.iam.gserviceaccount.com"
    )

    default_subject: str = "suporte.ti@cevalente.com.br"

    iam_signjwt_url: str = (
        "https://iamcredentials.googleapis.com/v1/projects/-/"
        "serviceAccounts/{service_account}:signJwt"
    )

    oauth_token_url: str = "https://oauth2.googleapis.com/token"


settings = Settings()
