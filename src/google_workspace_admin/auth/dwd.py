import json
import time
from typing import Iterable

import httpx

from google.auth.exceptions import RefreshError

from google_workspace_admin.auth.adc import get_adc_credentials
from google_workspace_admin.auth.token_cache import (
    get_cached_token,
    store_token,
)
from google_workspace_admin.config import settings
from google_workspace_admin.http_errors import (
    SafeOperationError,
    WorkspaceApiError,
    parse_json_object,
    request_safe,
)


class DwdAuthenticationError(SafeOperationError):
    """Erro durante autenticação Domain-Wide Delegation."""


def _dwd_error(
    *,
    code: str,
    layer: str,
    operation: str,
    http_status: int | None = None,
) -> DwdAuthenticationError:
    return DwdAuthenticationError(
        code=code,
        layer=layer,
        operation=operation,
        http_status=http_status,
    )


def _reclassify_workspace_error(
    error: WorkspaceApiError,
    *,
    code: str,
    layer: str,
    operation: str,
) -> DwdAuthenticationError:
    return _dwd_error(
        code=code,
        layer=layer,
        operation=operation,
        http_status=error.http_status,
    )


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

    adc_refresh_failed = False
    try:
        credentials, _ = get_adc_credentials()
    except RefreshError:
        adc_refresh_failed = True

    if adc_refresh_failed:
        raise _dwd_error(
            code="ADC_REFRESH",
            layer="adc",
            operation="credential_refresh",
        )

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
        sign_error = None
        try:
            sign_response = request_safe(
                client,
                "post",
                sign_url,
                "IAM signJwt",
                headers=headers,
                json={"payload": serialized_payload},
            )
        except WorkspaceApiError as error:
            sign_error = _reclassify_workspace_error(
                error,
                code="IAM_SIGN_JWT",
                layer="iam",
                operation="signJwt",
            )

        if sign_error is not None:
            raise sign_error

        sign_response_error = None
        try:
            sign_payload = parse_json_object(
                sign_response,
                "IAM signJwt",
            )
        except WorkspaceApiError as error:
            sign_response_error = _reclassify_workspace_error(
                error,
                code="RESPONSE_VALIDATION",
                layer="response",
                operation="signJwt",
            )

        if sign_response_error is not None:
            raise sign_response_error

        signed_jwt = sign_payload.get("signedJwt")

        if not isinstance(signed_jwt, str) or not signed_jwt:
            raise _dwd_error(
                code="RESPONSE_VALIDATION",
                layer="response",
                operation="signJwt",
                http_status=getattr(sign_response, "status_code", None),
            )

        token_exchange_error = None
        try:
            token_response = request_safe(
                client,
                "post",
                settings.oauth_token_url,
                "OAuth DWD",
                data={
                    "grant_type": (
                        "urn:ietf:params:oauth:grant-type:jwt-bearer"
                    ),
                    "assertion": signed_jwt,
                },
            )
        except WorkspaceApiError as error:
            token_exchange_error = _reclassify_workspace_error(
                error,
                code="DWD_TOKEN_EXCHANGE",
                layer="dwd",
                operation="token_exchange",
            )

        if token_exchange_error is not None:
            raise token_exchange_error

        token_response_error = None
        try:
            token_data = parse_json_object(
                token_response,
                "OAuth DWD",
            )
        except WorkspaceApiError as error:
            token_response_error = _reclassify_workspace_error(
                error,
                code="RESPONSE_VALIDATION",
                layer="response",
                operation="token_exchange",
            )

        if token_response_error is not None:
            raise token_response_error

        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 0)

        if not isinstance(access_token, str) or not access_token:
            raise _dwd_error(
                code="RESPONSE_VALIDATION",
                layer="response",
                operation="token_exchange",
                http_status=getattr(token_response, "status_code", None),
            )

        if (
            isinstance(expires_in, bool)
            or not isinstance(expires_in, int)
            or expires_in < 0
        ):
            raise _dwd_error(
                code="RESPONSE_VALIDATION",
                layer="response",
                operation="token_exchange",
                http_status=getattr(token_response, "status_code", None),
            )

        store_token(
            subject=delegated_subject,
            scopes=scope_list,
            access_token=access_token,
            expires_in=expires_in,
        )

        return access_token, expires_in
