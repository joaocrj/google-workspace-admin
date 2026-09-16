import ast
import json
from pathlib import Path

import pytest

from content_runtime_harness import provisioned_profile, workspace_subject
from google_workspace_admin.content.auth.keyless import (
    DEFAULT_REFRESH_MARGIN_SECONDS,
    KeylessContentTokenProvider,
    build_jwt_claims,
    normalize_content_scope,
)
from google_workspace_admin.content.auth.profile import ContentAuthProfile
from google_workspace_admin.content.auth.scopes import ApprovedScopeProfile
from google_workspace_admin.content.errors import ContentSafeError


def _profile(profile_id: str = "drive-discovery") -> ContentAuthProfile:
    return provisioned_profile(profile_id=profile_id).build()


def test_claims_use_fixed_audience_normalized_readonly_scope_and_bounded_expiry():
    claims = build_jwt_claims(
        service_account="content-research@example.iam.gserviceaccount.com",
        delegated_subject="Analyst@cevalente.com.br",
        scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
        now=1_000,
    )

    assert claims == {
        "iss": "content-research@example.iam.gserviceaccount.com",
        "sub": "Analyst@cevalente.com.br",
        "scope": "https://www.googleapis.com/auth/drive.readonly",
        "aud": "https://oauth2.googleapis.com/token",
        "iat": 1_000,
        "exp": 4_600,
    }
    assert normalize_content_scope(ApprovedScopeProfile.DRIVE_DISCOVERY) == (
        "https://www.googleapis.com/auth/drive.readonly",
    )


@pytest.mark.parametrize(
    "scope_profile",
    [
        ApprovedScopeProfile.DRIVE_METADATA,
        ApprovedScopeProfile.GMAIL_CONTENT,
        "https://www.googleapis.com/auth/drive",
    ],
)
def test_keyless_vertical_rejects_non_discovery_scope(scope_profile):
    with pytest.raises(ContentSafeError):
        normalize_content_scope(scope_profile)


def test_provider_uses_only_local_ports_and_reuses_ram_cache():
    now = [1_000.0]
    calls = {"adc": 0, "sign": 0, "exchange": 0}

    def adc():
        calls["adc"] += 1
        return "synthetic-adc-token"

    def sign(service_account, serialized_claims, adc_token):
        calls["sign"] += 1
        assert service_account.endswith(".iam.gserviceaccount.com")
        assert adc_token == "synthetic-adc-token"
        claims = json.loads(serialized_claims)
        assert claims["scope"] == "https://www.googleapis.com/auth/drive.readonly"
        return "synthetic-signed-jwt"

    def exchange(signed_jwt):
        calls["exchange"] += 1
        assert signed_jwt == "synthetic-signed-jwt"
        return "synthetic-access-token", 3_600

    provider = KeylessContentTokenProvider(
        adc_token_loader=adc,
        sign_jwt=sign,
        exchange_token=exchange,
        clock=lambda: now[0],
    )
    profile = _profile()
    subject = workspace_subject()

    assert provider.get_access_token(
        profile=profile,
        subject=subject,
        scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
    ) == "synthetic-access-token"
    now[0] = 1_001.0
    assert provider.get_access_token(
        profile=profile,
        subject=subject,
        scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
    ) == "synthetic-access-token"
    assert calls == {"adc": 1, "sign": 1, "exchange": 1}


def test_provider_refreshes_at_margin_and_clear_discards_ram_cache():
    now = [10_000.0]
    exchanges = []

    provider = KeylessContentTokenProvider(
        adc_token_loader=lambda: "adc",
        sign_jwt=lambda service_account, claims, adc_token: "signed",
        exchange_token=lambda signed_jwt: (
            exchanges.append("refresh") or (f"access-{len(exchanges)}", 600)
        ),
        clock=lambda: now[0],
        refresh_margin_seconds=DEFAULT_REFRESH_MARGIN_SECONDS,
    )
    profile = _profile()
    subject = workspace_subject()

    assert provider.get_access_token(
        profile=profile,
        subject=subject,
        scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
    ) == "access-1"
    now[0] += 299
    assert provider.get_access_token(
        profile=profile,
        subject=subject,
        scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
    ) == "access-1"
    now[0] += 1
    assert provider.get_access_token(
        profile=profile,
        subject=subject,
        scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
    ) == "access-2"
    provider.clear()
    assert provider.get_access_token(
        profile=profile,
        subject=subject,
        scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
    ) == "access-3"
    assert exchanges == ["refresh", "refresh", "refresh"]


def test_cache_key_isolation_covers_profile_and_subject():
    calls = []
    provider = KeylessContentTokenProvider(
        adc_token_loader=lambda: "adc",
        sign_jwt=lambda service_account, claims, adc_token: "signed",
        exchange_token=lambda signed_jwt: (
            calls.append("exchange") or (f"access-{len(calls)}", 3_600)
        ),
        clock=lambda: 1_000.0,
    )
    first_profile = _profile("drive-discovery")
    second_profile = _profile("drive-discovery-alt")
    first_subject = workspace_subject()

    assert provider.get_access_token(
        profile=first_profile,
        subject=first_subject,
        scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
    ) == "access-1"
    assert provider.get_access_token(
        profile=second_profile,
        subject=first_subject,
        scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
    ) == "access-2"
    assert len(calls) == 2


@pytest.mark.parametrize(
    ("stage", "expected_code"),
    [("adc", "ADC_REFRESH"), ("sign", "IAM_SIGN_JWT"), ("exchange", "DWD_TOKEN_EXCHANGE")],
)
def test_provider_safe_failures_redact_secret_material(stage, expected_code):
    secret = "SECRET_TOKEN_JWT_CREDENTIAL"

    def adc():
        if stage == "adc":
            raise RuntimeError(secret)
        return "adc"

    def sign(service_account, claims, adc_token):
        if stage == "sign":
            raise RuntimeError(secret)
        return "signed"

    def exchange(signed_jwt):
        if stage == "exchange":
            raise RuntimeError(secret)
        return "access", 3_600

    provider = KeylessContentTokenProvider(
        adc_token_loader=adc,
        sign_jwt=sign,
        exchange_token=exchange,
    )
    with pytest.raises(ContentSafeError) as error:
        provider.get_access_token(
            profile=_profile(),
            subject=workspace_subject(),
            scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
        )
    assert error.value.code == expected_code
    assert secret not in str(error.value)
    assert secret not in repr(error.value)
    assert secret not in repr(provider)


@pytest.mark.parametrize(
    "exchange_result",
    [("", 3_600), ("access", 0), ("access", True), ("access", 3_601), ["access", 300]],
)
def test_provider_rejects_unbounded_or_malformed_exchange(exchange_result):
    provider = KeylessContentTokenProvider(
        adc_token_loader=lambda: "adc",
        sign_jwt=lambda service_account, claims, adc_token: "signed",
        exchange_token=lambda signed_jwt: exchange_result,
    )
    with pytest.raises(ContentSafeError) as error:
        provider.get_access_token(
            profile=_profile(),
            subject=workspace_subject(),
            scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
        )
    assert error.value.code == "RESPONSE_VALIDATION"


def test_keyless_module_has_no_real_credential_fallback_or_gcloud_call():
    path = (
        Path(__file__).parents[1]
        / "src"
        / "google_workspace_admin"
        / "content"
        / "auth"
        / "keyless.py"
    )
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert "google.auth.default" not in source
    assert "gcloud" not in source
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"default", "refresh"}
        for node in ast.walk(tree)
    )


def test_provider_does_not_expose_token_in_repr():
    provider = KeylessContentTokenProvider(
        adc_token_loader=lambda: "sensitive-adc",
        sign_jwt=lambda service_account, claims, adc_token: "sensitive-jwt",
        exchange_token=lambda signed_jwt: ("sensitive-access", 3_600),
    )
    assert "sensitive" not in repr(provider)
