import json
import time
from typing import Iterable

import httpx

from google_workspace_admin.auth.adc import get_adc_credentials
from google_workspace_admin.auth.token_cache import (
    get_cached_token,
    store_token,
)
from google_workspace_admin.config import settings


class DwdAuthenticationError(RuntimeError):
    """Erro durante autenticação Domain-Wide Delegation."""


def _build_jwt_payload(
    subject: str,
    scopes: Iterable[str],
) -> dict:
    now = int(time.time())

    return {
        "iss": settings.service_account,
        "sub": subject,
        "scope": " ".join(scopes),
        "aud": settings.oauth_token_url,
        "iat": now,
        "exp": now + 3600,
    }


def get_workspace_access_token(
    scopes: Iterable[str],
    subject: str | None = None,
) -> tuple[str, int]:
    """
    Obtém um access token Google Workspace através de:

    ADC -> IAM Credentials signJwt -> DWD -> OAuth 2.0

    Tokens válidos são reutilizados somente em memória.
    Nenhuma chave privada ou access token é persistido em disco.
    """

    delegated_subject = subject or settings.default_subject
    scope_list = list(scopes)

    cached_token = get_cached_token(
        subject=delegated_subject,
        scopes=scope_list,
    )

    if cached_token:
        return cached_token, 0

    credentials, _ = get_adc_credentials()

    payload = _build_jwt_payload(
        subject=delegated_subject,
        scopes=scope_list,
    )

    serialized_payload = json.dumps(
        payload,
        separators=(",", ":"),
    )

    sign_url = settings.iam_signjwt_url.format(
        service_account=settings.service_account
    )

    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=30.0) as client:
        sign_response = client.post(
            sign_url,
            headers=headers,
            json={"payload": serialized_payload},
        )

        if not sign_response.is_success:
            raise DwdAuthenticationError(
                "IAM signJwt falhou: "
                f"HTTP {sign_response.status_code} "
                f"{sign_response.text}"
            )

        signed_jwt = sign_response.json().get("signedJwt")

        if not signed_jwt:
            raise DwdAuthenticationError(
                "IAM signJwt não retornou signedJwt."
            )

        token_response = client.post(
            settings.oauth_token_url,
            data={
                "grant_type": (
                    "urn:ietf:params:oauth:grant-type:jwt-bearer"
                ),
                "assertion": signed_jwt,
            },
        )

        if not token_response.is_success:
            raise DwdAuthenticationError(
                "OAuth DWD falhou: "
                f"HTTP {token_response.status_code} "
                f"{token_response.text}"
            )

        token_data = token_response.json()

        access_token = token_data.get("access_token")
        expires_in = int(token_data.get("expires_in", 0))

        if not access_token:
            raise DwdAuthenticationError(
                "OAuth não retornou access_token."
            )

        store_token(
            subject=delegated_subject,
            scopes=scope_list,
            access_token=access_token,
            expires_in=expires_in,
        )

        return access_token, expires_in
