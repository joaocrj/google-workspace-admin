"""Lazy production ports for the keyless Content authentication chain.

This module contains no credential lookup at import time.  The default ports
are invoked only after a functional Content operation needs an access token.
Tests replace the credential loader and HTTP client factory with local fakes.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import json
from urllib.parse import quote

import httpx

from google_workspace_admin.content.auth.keyless import (
    KeylessContentTokenProvider,
    KeylessControlledValidationTokenProvider,
    MAX_INTERNAL_TOKEN_LENGTH,
    OAUTH_TOKEN_AUDIENCE,
)
from google_workspace_admin.content.auth.scopes import (
    _ControlledValidationScopeProfile,
    _controlled_validation_scopes_for,
)
from google_workspace_admin.content.config import ContentConfig
from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError
from google_workspace_admin.http_errors import (
    WorkspaceApiError,
    parse_json_object,
    request_safe,
)


IAM_SIGNJWT_ROOT = (
    "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/"
)
AUTH_HTTP_TIMEOUT = 30.0
_JWT_CLAIM_KEYS = frozenset({"aud", "exp", "iat", "iss", "scope", "sub"})
_DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.readonly"

_CredentialsLoader = Callable[[], tuple[object, str | None]]
_ClientFactory = Callable[[], httpx.Client]


def _safe_failure(
    code: str,
    operation: ContentErrorOperation = ContentErrorOperation.AUTH_BROKER,
    *,
    http_status: int | None = None,
    category: str | None = None,
) -> ContentSafeError:
    return ContentSafeError(
        code=code,
        operation=operation,
        http_status=http_status,
        category=category,
    )


def _valid_secret(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and len(value) <= MAX_INTERNAL_TOKEN_LENGTH
        and not any(
            character.isspace()
            or ord(character) < 32
            or 0x7F <= ord(character) <= 0x9F
            for character in value
        )
    )


def _valid_serialized_claims(value: object) -> bool:
    """Validate compact claims JSON while permitting the scope separator."""

    return (
        isinstance(value, str)
        and bool(value)
        and len(value) <= MAX_INTERNAL_TOKEN_LENGTH
        and not any(
            ord(character) < 32 or 0x7F <= ord(character) <= 0x9F
            for character in value
        )
    )


def _build_auth_http_client() -> httpx.Client:
    return httpx.Client(
        follow_redirects=False,
        timeout=AUTH_HTTP_TIMEOUT,
    )


def _load_adc_credentials() -> tuple[object, str | None]:
    """Load ADC only when the token provider is actually refreshed."""

    try:
        from google_workspace_admin.auth.adc import get_adc_credentials

        return get_adc_credentials()
    except Exception:
        raise _safe_failure("ADC_REFRESH") from None


def _load_authorized_user_adc_credentials(
    *,
    environment: Mapping[str, str] | None = None,
    request_factory: Callable[[], object] | None = None,
) -> tuple[object, str | None]:
    """Private load-and-refresh seam for explicitly selected Content runners.

    The default Content path remains ``_load_adc_credentials``. A caller may
    inject this helper as ``credentials_loader`` when it needs the explicit
    authorized-user-only ADC source. Refresh is lazy and uses google-auth's
    OAuth HTTP request transport only when the constructed credentials are
    invalid.
    """

    try:
        from google.auth.transport.requests import Request
        from google_workspace_admin.auth.adc import (
            load_local_authorized_user_adc_no_subprocess,
        )

        credentials, project_id = load_local_authorized_user_adc_no_subprocess(
            environment
        )
        if not credentials.valid:
            request = request_factory() if request_factory is not None else Request()
            credentials.refresh(request)
        if not credentials.valid:
            raise ValueError("ADC credentials remain invalid after refresh")
        return credentials, project_id
    except Exception:
        raise _safe_failure("ADC_REFRESH") from None


def _build_adc_token_loader(
    config: ContentConfig,
    credentials_loader: _CredentialsLoader,
) -> Callable[[], str]:
    def load() -> str:
        credentials, detected_project_id = credentials_loader()
        if detected_project_id is not None and detected_project_id != config.project_id:
            raise _safe_failure("ADC_REFRESH")
        token = getattr(credentials, "token", None)
        if not _valid_secret(token):
            raise _safe_failure("ADC_REFRESH")
        return token

    return load


def _validate_claims(
    *,
    service_account: str,
    delegated_subject: str,
    serialized_claims: str,
    expected_scope: str = _DRIVE_SCOPE,
) -> None:
    if not _valid_serialized_claims(serialized_claims):
        raise _safe_failure("IAM_SIGN_JWT")
    try:
        claims = json.loads(serialized_claims)
    except (TypeError, ValueError):
        raise _safe_failure("IAM_SIGN_JWT") from None
    if not isinstance(claims, dict) or set(claims) != _JWT_CLAIM_KEYS:
        raise _safe_failure("IAM_SIGN_JWT")
    if (
        claims.get("iss") != service_account
        or claims.get("sub") != delegated_subject
        or expected_scope not in {
            _DRIVE_SCOPE,
            " ".join(
                _controlled_validation_scopes_for(
                    _ControlledValidationScopeProfile.GSHEETS_FIXTURE_WRITE
                )
            ),
        }
        or claims.get("scope") != expected_scope
        or claims.get("aud") != OAUTH_TOKEN_AUDIENCE
        or isinstance(claims.get("iat"), bool)
        or not isinstance(claims.get("iat"), int)
        or isinstance(claims.get("exp"), bool)
        or not isinstance(claims.get("exp"), int)
        or claims["exp"] <= claims["iat"]
        or claims["exp"] - claims["iat"] > 3600
    ):
        raise _safe_failure("IAM_SIGN_JWT")


def _build_sign_jwt_adapter(
    config: ContentConfig,
    client_factory: _ClientFactory,
    *,
    expected_scope: str = _DRIVE_SCOPE,
) -> Callable[[str, str, str], str]:
    expected_service_account = config.service_account
    expected_subject = config.subject
    endpoint = (
        IAM_SIGNJWT_ROOT
        + quote(expected_service_account, safe="@")
        + ":signJwt"
    )

    def sign_jwt(
        service_account: str,
        serialized_claims: str,
        adc_token: str,
    ) -> str:
        if service_account != expected_service_account or not _valid_secret(adc_token):
            raise _safe_failure("IAM_SIGN_JWT")
        _validate_claims(
            service_account=expected_service_account,
            delegated_subject=expected_subject,
            serialized_claims=serialized_claims,
            expected_scope=expected_scope,
        )
        try:
            client = client_factory()
            if type(client) is not httpx.Client:
                raise _safe_failure("IAM_SIGN_JWT")
            try:
                response = request_safe(
                    client,
                    "post",
                    endpoint,
                    "IAM signJwt",
                    headers={
                        "Authorization": f"Bearer {adc_token}",
                        "Content-Type": "application/json",
                    },
                    json={"payload": serialized_claims},
                    timeout=AUTH_HTTP_TIMEOUT,
                )
            finally:
                client.close()
        except WorkspaceApiError as error:
            raise _safe_failure(
                "IAM_SIGN_JWT",
                http_status=error.http_status,
                category=error.category,
            ) from None
        except ContentSafeError:
            raise
        except Exception:
            raise _safe_failure("IAM_SIGN_JWT") from None

        try:
            payload = parse_json_object(response, "IAM signJwt")
        except WorkspaceApiError as error:
            raise _safe_failure(
                "RESPONSE_VALIDATION",
                http_status=error.http_status,
                category=error.category,
            ) from None
        signed_jwt = payload.get("signedJwt")
        if not _valid_secret(signed_jwt):
            raise _safe_failure(
                "RESPONSE_VALIDATION",
                http_status=response.status_code,
            )
        return signed_jwt

    return sign_jwt


def _build_oauth_exchange_adapter(
    client_factory: _ClientFactory,
) -> Callable[[str], tuple[str, int]]:
    def exchange_token(signed_jwt: str) -> tuple[str, int]:
        if not _valid_secret(signed_jwt):
            raise _safe_failure("DWD_TOKEN_EXCHANGE")
        try:
            client = client_factory()
            if type(client) is not httpx.Client:
                raise _safe_failure("DWD_TOKEN_EXCHANGE")
            try:
                response = request_safe(
                    client,
                    "post",
                    OAUTH_TOKEN_AUDIENCE,
                    "OAuth DWD",
                    data={
                        "grant_type": (
                            "urn:ietf:params:oauth:grant-type:jwt-bearer"
                        ),
                        "assertion": signed_jwt,
                    },
                    timeout=AUTH_HTTP_TIMEOUT,
                )
            finally:
                client.close()
        except WorkspaceApiError as error:
            raise _safe_failure(
                "DWD_TOKEN_EXCHANGE",
                http_status=error.http_status,
                category=error.category,
            ) from None
        except ContentSafeError:
            raise
        except Exception:
            raise _safe_failure("DWD_TOKEN_EXCHANGE") from None

        try:
            payload = parse_json_object(response, "OAuth DWD")
        except WorkspaceApiError as error:
            raise _safe_failure(
                "RESPONSE_VALIDATION",
                http_status=error.http_status,
                category=error.category,
            ) from None
        access_token = payload.get("access_token")
        expires_in = payload.get("expires_in")
        if (
            not _valid_secret(access_token)
            or isinstance(expires_in, bool)
            or not isinstance(expires_in, int)
            or not 1 <= expires_in <= 3600
        ):
            raise _safe_failure(
                "RESPONSE_VALIDATION",
                http_status=response.status_code,
            )
        return access_token, expires_in

    return exchange_token


def build_content_token_provider(
    config: ContentConfig,
    *,
    credentials_loader: _CredentialsLoader | None = None,
    client_factory: _ClientFactory | None = None,
) -> KeylessContentTokenProvider:
    """Build the lazy production provider; ports remain uncalled here."""

    if type(config) is not ContentConfig:
        raise _safe_failure("LOCAL_VALIDATION")
    loader = credentials_loader or _load_adc_credentials
    factory = client_factory or _build_auth_http_client
    if not callable(loader) or not callable(factory):
        raise _safe_failure("LOCAL_VALIDATION")
    return KeylessContentTokenProvider(
        adc_token_loader=_build_adc_token_loader(config, loader),
        sign_jwt=_build_sign_jwt_adapter(config, factory),
        exchange_token=_build_oauth_exchange_adapter(factory),
    )


def _build_controlled_validation_token_provider(
    config: ContentConfig,
    *,
    credentials_loader: _CredentialsLoader | None = None,
    client_factory: _ClientFactory | None = None,
) -> KeylessControlledValidationTokenProvider:
    """Build the internal fixed-scope provider for the controlled driver.

    This builder is deliberately private and is not used by Content bootstrap
    or any MCP tool. It adds no DWD/Admin Console configuration.
    """

    if type(config) is not ContentConfig:
        raise _safe_failure("LOCAL_VALIDATION")
    loader = credentials_loader or _load_adc_credentials
    factory = client_factory or _build_auth_http_client
    if not callable(loader) or not callable(factory):
        raise _safe_failure("LOCAL_VALIDATION")
    expected_scope = " ".join(
        _controlled_validation_scopes_for(
            _ControlledValidationScopeProfile.GSHEETS_FIXTURE_WRITE
        )
    )
    return KeylessControlledValidationTokenProvider(
        service_account=config.service_account,
        delegated_subject=config.subject,
        adc_token_loader=_build_adc_token_loader(config, loader),
        sign_jwt=_build_sign_jwt_adapter(
            config,
            factory,
            expected_scope=expected_scope,
        ),
        exchange_token=_build_oauth_exchange_adapter(factory),
    )
