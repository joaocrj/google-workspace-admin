"""Local, injectable core for future keyless Content authentication.

This module contains no Google client construction and no credential lookup.
Production ports will be bound only by a separately authorized provisioning
delivery.  Tests bind local fakes exclusively.
"""

from __future__ import annotations

from collections.abc import Callable
import json
import math
import time

from google_workspace_admin.content.auth.cache import _build_content_cache_key
from google_workspace_admin.content.auth.capabilities import SubjectCapability
from google_workspace_admin.content.auth.profile import ContentAuthProfile
from google_workspace_admin.content.auth.scopes import (
    ApprovedScopeProfile,
    _ControlledValidationScopeProfile,
    _controlled_validation_scopes_for,
    scopes_for,
)
from google_workspace_admin.content.auth.subject import WorkspaceSubject
from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError
from google_workspace_admin.content.policy import validate_subject_for_capability


OAUTH_TOKEN_AUDIENCE = "https://oauth2.googleapis.com/token"
MAX_JWT_LIFETIME_SECONDS = 3600
MAX_ACCESS_TOKEN_LIFETIME_SECONDS = 3600
DEFAULT_REFRESH_MARGIN_SECONDS = 300
MAX_INTERNAL_TOKEN_LENGTH = 8192


def _safe_failure(code: str, operation: ContentErrorOperation) -> ContentSafeError:
    return ContentSafeError(code=code, operation=operation)


def _valid_internal_secret(value: object) -> bool:
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


def normalize_content_scope(
    scope_profile: object,
) -> tuple[str, ...]:
    """Resolve only the exact read-only scope profile for this vertical."""

    if scope_profile is not ApprovedScopeProfile.DRIVE_DISCOVERY:
        raise _safe_failure("READ_ONLY_OPERATION_FORBIDDEN", ContentErrorOperation.SCOPE_REGISTRY)
    scopes = scopes_for(scope_profile)
    if scopes != ("https://www.googleapis.com/auth/drive.readonly",):
        raise _safe_failure("READ_ONLY_OPERATION_FORBIDDEN", ContentErrorOperation.SCOPE_REGISTRY)
    return scopes


def build_jwt_claims(
    *,
    service_account: str,
    delegated_subject: str,
    scope_profile: ApprovedScopeProfile,
    now: int,
    lifetime_seconds: int = MAX_JWT_LIFETIME_SECONDS,
) -> dict[str, object]:
    """Build bounded DWD claims without signing or persisting a JWT."""

    scopes = normalize_content_scope(scope_profile)
    if (
        not isinstance(service_account, str)
        or not service_account.strip()
        or not isinstance(delegated_subject, str)
        or not delegated_subject.strip()
        or isinstance(now, bool)
        or not isinstance(now, int)
        or isinstance(lifetime_seconds, bool)
        or not isinstance(lifetime_seconds, int)
        or not 1 <= lifetime_seconds <= MAX_JWT_LIFETIME_SECONDS
    ):
        raise _safe_failure("LOCAL_VALIDATION", ContentErrorOperation.AUTH_BROKER)
    normalized_now = now
    return {
        "iss": service_account.strip(),
        "sub": delegated_subject.strip(),
        "scope": " ".join(scopes),
        "aud": OAUTH_TOKEN_AUDIENCE,
        "iat": normalized_now,
        "exp": normalized_now + lifetime_seconds,
    }


def _build_controlled_validation_jwt_claims(
    *,
    service_account: str,
    delegated_subject: str,
    scope_profile: _ControlledValidationScopeProfile,
    now: int,
    lifetime_seconds: int = MAX_JWT_LIFETIME_SECONDS,
) -> dict[str, object]:
    """Build claims for the fixed internal Sheets validation profile only."""

    scopes = _controlled_validation_scopes_for(scope_profile)
    if (
        not isinstance(service_account, str)
        or not service_account.strip()
        or not isinstance(delegated_subject, str)
        or not delegated_subject.strip()
        or isinstance(now, bool)
        or not isinstance(now, int)
        or isinstance(lifetime_seconds, bool)
        or not isinstance(lifetime_seconds, int)
        or not 1 <= lifetime_seconds <= MAX_JWT_LIFETIME_SECONDS
    ):
        raise _safe_failure("LOCAL_VALIDATION", ContentErrorOperation.AUTH_BROKER)
    return {
        "iss": service_account.strip(),
        "sub": delegated_subject.strip(),
        "scope": " ".join(scopes),
        "aud": OAUTH_TOKEN_AUDIENCE,
        "iat": now,
        "exp": now + lifetime_seconds,
    }


class KeylessContentTokenProvider:
    """RAM-only token cache using injected ADC/IAM/OAuth ports.

    The three ports are intentionally narrow and are the only places where a
    future production binding may perform ADC access, IAM ``signJwt`` and the
    OAuth token exchange.  This class itself has no network or auth fallback.
    """

    __slots__ = (
        "_adc_token_loader",
        "_sign_jwt",
        "_exchange_token",
        "_clock",
        "_refresh_margin_seconds",
        "_cache",
    )

    def __init__(
        self,
        *,
        adc_token_loader: Callable[[], str],
        sign_jwt: Callable[[str, str, str], str],
        exchange_token: Callable[[str], tuple[str, int]],
        clock: Callable[[], float] = time.time,
        refresh_margin_seconds: int = DEFAULT_REFRESH_MARGIN_SECONDS,
    ) -> None:
        if not all(
            callable(port)
            for port in (adc_token_loader, sign_jwt, exchange_token, clock)
        ):
            raise _safe_failure("LOCAL_VALIDATION", ContentErrorOperation.AUTH_BROKER)
        if (
            isinstance(refresh_margin_seconds, bool)
            or not isinstance(refresh_margin_seconds, int)
            or not 0 <= refresh_margin_seconds < MAX_ACCESS_TOKEN_LIFETIME_SECONDS
        ):
            raise _safe_failure("LOCAL_VALIDATION", ContentErrorOperation.AUTH_CACHE)
        self._adc_token_loader = adc_token_loader
        self._sign_jwt = sign_jwt
        self._exchange_token = exchange_token
        self._clock = clock
        self._refresh_margin_seconds = refresh_margin_seconds
        self._cache: dict[object, tuple[str, float]] = {}

    def __repr__(self) -> str:
        return "<KeylessContentTokenProvider cache=ram-only redacted>"

    def clear(self) -> None:
        """Clear the in-memory cache without returning token material."""

        self._cache.clear()

    def get_access_token(
        self,
        *,
        profile: ContentAuthProfile,
        subject: WorkspaceSubject,
        scope_profile: ApprovedScopeProfile,
    ) -> str:
        """Return a cached or freshly exchanged token through local ports."""

        if type(profile) is not ContentAuthProfile or type(subject) is not WorkspaceSubject:
            raise _safe_failure("LOCAL_VALIDATION", ContentErrorOperation.AUTH_BROKER)
        if profile.approved_scope_profile is not scope_profile:
            raise _safe_failure("READ_ONLY_OPERATION_FORBIDDEN", ContentErrorOperation.CAPABILITY_MATRIX)
        scopes = normalize_content_scope(scope_profile)
        validate_subject_for_capability(subject, profile, SubjectCapability.DRIVE)
        cache_key = _build_content_cache_key(profile, subject)

        try:
            now = float(self._clock())
        except Exception:
            raise _safe_failure("UNEXPECTED_LOCAL", ContentErrorOperation.AUTH_CACHE) from None
        if not math.isfinite(now):
            raise _safe_failure("UNEXPECTED_LOCAL", ContentErrorOperation.AUTH_CACHE)

        cached = self._cache.get(cache_key)
        if cached is not None:
            access_token, expires_at = cached
            if now < expires_at - self._refresh_margin_seconds:
                return access_token

        try:
            adc_token = self._adc_token_loader()
        except Exception:
            raise _safe_failure("ADC_REFRESH", ContentErrorOperation.AUTH_BROKER) from None
        if not _valid_internal_secret(adc_token):
            raise _safe_failure("ADC_REFRESH", ContentErrorOperation.AUTH_BROKER)

        try:
            claims = build_jwt_claims(
                service_account=profile.service_account,
                delegated_subject=subject.primary_email,
                scope_profile=scope_profile,
                now=int(now),
            )
            serialized_claims = json.dumps(
                claims,
                separators=(",", ":"),
                sort_keys=True,
            )
            signed_jwt = self._sign_jwt(
                profile.service_account,
                serialized_claims,
                adc_token,
            )
        except ContentSafeError:
            raise
        except Exception:
            raise _safe_failure("IAM_SIGN_JWT", ContentErrorOperation.AUTH_BROKER) from None
        if not _valid_internal_secret(signed_jwt):
            raise _safe_failure("IAM_SIGN_JWT", ContentErrorOperation.AUTH_BROKER)

        try:
            exchanged = self._exchange_token(signed_jwt)
        except ContentSafeError:
            raise
        except Exception:
            raise _safe_failure("DWD_TOKEN_EXCHANGE", ContentErrorOperation.AUTH_BROKER) from None
        if (
            not isinstance(exchanged, tuple)
            or len(exchanged) != 2
            or not _valid_internal_secret(exchanged[0])
            or isinstance(exchanged[1], bool)
            or not isinstance(exchanged[1], int)
            or not 1 <= exchanged[1] <= MAX_ACCESS_TOKEN_LIFETIME_SECONDS
        ):
            raise _safe_failure("RESPONSE_VALIDATION", ContentErrorOperation.AUTH_BROKER)

        access_token, expires_in = exchanged
        expires_at = now + expires_in
        self._cache[cache_key] = (access_token, expires_at)
        return access_token


class KeylessControlledValidationTokenProvider:
    """Fixed-scope token provider used only by the internal validation driver.

    There is no runtime scope, subject, or operation parameter. The public
    Content provider above remains pinned to ``drive.readonly``.
    """

    __slots__ = (
        "_service_account",
        "_delegated_subject",
        "_adc_token_loader",
        "_sign_jwt",
        "_exchange_token",
        "_clock",
        "_refresh_margin_seconds",
        "_cache",
    )

    def __init__(
        self,
        *,
        service_account: str,
        delegated_subject: str,
        adc_token_loader: Callable[[], str],
        sign_jwt: Callable[[str, str, str], str],
        exchange_token: Callable[[str], tuple[str, int]],
        clock: Callable[[], float] = time.time,
        refresh_margin_seconds: int = DEFAULT_REFRESH_MARGIN_SECONDS,
    ) -> None:
        if (
            not isinstance(service_account, str)
            or not service_account.strip()
            or not isinstance(delegated_subject, str)
            or not delegated_subject.strip()
            or not all(
                callable(port)
                for port in (adc_token_loader, sign_jwt, exchange_token, clock)
            )
        ):
            raise _safe_failure("LOCAL_VALIDATION", ContentErrorOperation.AUTH_BROKER)
        if (
            isinstance(refresh_margin_seconds, bool)
            or not isinstance(refresh_margin_seconds, int)
            or not 0 <= refresh_margin_seconds < MAX_ACCESS_TOKEN_LIFETIME_SECONDS
        ):
            raise _safe_failure("LOCAL_VALIDATION", ContentErrorOperation.AUTH_CACHE)
        self._service_account = service_account.strip()
        self._delegated_subject = delegated_subject.strip()
        self._adc_token_loader = adc_token_loader
        self._sign_jwt = sign_jwt
        self._exchange_token = exchange_token
        self._clock = clock
        self._refresh_margin_seconds = refresh_margin_seconds
        self._cache: tuple[str, float] | None = None

    def __repr__(self) -> str:
        return "<KeylessControlledValidationTokenProvider cache=ram-only redacted>"

    def clear(self) -> None:
        self._cache = None

    def get_access_token(self) -> str:
        """Return a short-lived token for the one fixed internal scope profile."""

        try:
            now = float(self._clock())
        except Exception:
            raise _safe_failure("UNEXPECTED_LOCAL", ContentErrorOperation.AUTH_CACHE) from None
        if not math.isfinite(now):
            raise _safe_failure("UNEXPECTED_LOCAL", ContentErrorOperation.AUTH_CACHE)

        cached = self._cache
        if cached is not None:
            access_token, expires_at = cached
            if now < expires_at - self._refresh_margin_seconds:
                return access_token

        try:
            adc_token = self._adc_token_loader()
        except Exception:
            raise _safe_failure("ADC_REFRESH", ContentErrorOperation.AUTH_BROKER) from None
        if not _valid_internal_secret(adc_token):
            raise _safe_failure("ADC_REFRESH", ContentErrorOperation.AUTH_BROKER)

        try:
            claims = _build_controlled_validation_jwt_claims(
                service_account=self._service_account,
                delegated_subject=self._delegated_subject,
                scope_profile=(
                    _ControlledValidationScopeProfile.GSHEETS_FIXTURE_WRITE
                ),
                now=int(now),
            )
            serialized_claims = json.dumps(
                claims,
                separators=(",", ":"),
                sort_keys=True,
            )
            signed_jwt = self._sign_jwt(
                self._service_account,
                serialized_claims,
                adc_token,
            )
        except ContentSafeError:
            raise
        except Exception:
            raise _safe_failure("IAM_SIGN_JWT", ContentErrorOperation.AUTH_BROKER) from None
        if not _valid_internal_secret(signed_jwt):
            raise _safe_failure("IAM_SIGN_JWT", ContentErrorOperation.AUTH_BROKER)

        try:
            exchanged = self._exchange_token(signed_jwt)
        except ContentSafeError:
            raise
        except Exception:
            raise _safe_failure("DWD_TOKEN_EXCHANGE", ContentErrorOperation.AUTH_BROKER) from None
        if (
            not isinstance(exchanged, tuple)
            or len(exchanged) != 2
            or not _valid_internal_secret(exchanged[0])
            or isinstance(exchanged[1], bool)
            or not isinstance(exchanged[1], int)
            or not 1 <= exchanged[1] <= MAX_ACCESS_TOKEN_LIFETIME_SECONDS
        ):
            raise _safe_failure("RESPONSE_VALIDATION", ContentErrorOperation.AUTH_BROKER)

        access_token, expires_in = exchanged
        self._cache = (access_token, now + expires_in)
        return access_token
