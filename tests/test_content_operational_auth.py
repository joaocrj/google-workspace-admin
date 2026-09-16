import json

import httpx
import pytest

from google_workspace_admin import server
from google_workspace_admin.content import bootstrap
from google_workspace_admin.content import config as content_config
from google_workspace_admin.content.auth import production
from google_workspace_admin.content.auth.scopes import (
    ApprovedScopeProfile,
    all_approved_scopes,
)
from google_workspace_admin.content.errors import ContentSafeError


def _environment(customer_id: str = "customer-123") -> dict[str, str]:
    return {
        content_config.CONTENT_PROJECT_ID_ENV: "synthetic-content-project",
        content_config.CONTENT_SERVICE_ACCOUNT_ENV: (
            "content-research@synthetic-project.iam.gserviceaccount.com"
        ),
        content_config.CONTENT_SUBJECT_ENV: "suporte.ti@cevalente.com.br",
        content_config.CONTENT_CUSTOMER_ID_ENV: customer_id,
        content_config.CONTENT_DOMAIN_ENV: "cevalente.com.br",
    }


class _Credentials:
    token = "synthetic-adc-token"


def _config():
    return content_config.ContentConfig.from_environment(_environment())


def test_complete_configuration_builds_fixed_profile_and_subject():
    config = _config()
    profile = config.to_provisioned_profile().build()
    subject = config.fixed_subject()

    assert config.project_id == "synthetic-content-project"
    assert profile.profile_id == "drive-discovery"
    assert profile.service_account.endswith(".iam.gserviceaccount.com")
    assert profile.customer_id == "customer-123"
    assert profile.approved_scope_profile is ApprovedScopeProfile.DRIVE_DISCOVERY
    assert profile.admin_capability.value == "none"
    assert subject.primary_email == "suporte.ti@cevalente.com.br"
    assert subject.domain == "cevalente.com.br"
    assert subject.customer_id == "customer-123"
    assert repr(config) == "<ContentConfig identifiers-only redacted>"


@pytest.mark.parametrize("missing", content_config.CONTENT_REQUIRED_ENV_VARS)
def test_missing_required_configuration_fails_closed(missing):
    environment = _environment()
    del environment[missing]

    with pytest.raises(ContentSafeError) as error:
        content_config.ContentConfig.from_environment(environment)

    assert error.value.code == "CONTENT_NOT_SUPPORTED"
    assert missing not in str(error.value)


@pytest.mark.parametrize(
    ("name", "value", "code"),
    [
        (content_config.CONTENT_PROJECT_ID_ENV, "Bad Project", "LOCAL_VALIDATION"),
        (
            content_config.CONTENT_SERVICE_ACCOUNT_ENV,
            "operator@example.com",
            "LOCAL_VALIDATION",
        ),
        (content_config.CONTENT_SUBJECT_ENV, "not-an-email", "TARGET_SUBJECT_INVALID"),
        (
            content_config.CONTENT_SUBJECT_ENV,
            "user@other.example",
            "MAILBOX_NOT_ALLOWED",
        ),
        (content_config.CONTENT_DOMAIN_ENV, "other.example", "MAILBOX_NOT_ALLOWED"),
        (
            content_config.CONTENT_CUSTOMER_ID_ENV,
            "my_customer",
            "LOCAL_VALIDATION",
        ),
        (
            content_config.CONTENT_CUSTOMER_ID_ENV,
            "customer with spaces",
            "LOCAL_VALIDATION",
        ),
    ],
)
def test_invalid_configuration_is_safe(name, value, code):
    environment = _environment()
    environment[name] = value

    with pytest.raises(ContentSafeError) as error:
        content_config.ContentConfig.from_environment(environment)

    assert error.value.code == code
    assert value not in str(error.value)


def test_customer_id_has_no_my_customer_fallback_and_scope_is_not_configurable():
    environment = _environment()
    environment["GOOGLE_WORKSPACE_CONTENT_SCOPE"] = (
        "https://www.googleapis.com/auth/drive"
    )
    config = content_config.ContentConfig.from_environment(environment)

    assert not hasattr(config, "scope")
    assert config.to_provisioned_profile().approved_scope_profile is ApprovedScopeProfile.DRIVE_DISCOVERY
    assert (
        "https://www.googleapis.com/auth/drive.readonly"
        in all_approved_scopes()
    )
    assert "https://www.googleapis.com/auth/drive" not in all_approved_scopes()


def test_fixed_subject_lookup_does_not_accept_a_different_subject(monkeypatch):
    monkeypatch.setenv(
        content_config.CONTENT_PROJECT_ID_ENV,
        "synthetic-content-project",
    )
    monkeypatch.setenv(
        content_config.CONTENT_SERVICE_ACCOUNT_ENV,
        "content-research@synthetic-project.iam.gserviceaccount.com",
    )
    monkeypatch.setenv(
        content_config.CONTENT_SUBJECT_ENV,
        "suporte.ti@cevalente.com.br",
    )
    monkeypatch.setenv(content_config.CONTENT_CUSTOMER_ID_ENV, "customer-123")
    monkeypatch.setenv(content_config.CONTENT_DOMAIN_ENV, "cevalente.com.br")

    lookup = bootstrap._build_subject_lookup()
    assert lookup("suporte.ti@cevalente.com.br").primary_email == (
        "suporte.ti@cevalente.com.br"
    )
    assert lookup("other@cevalente.com.br") is None


def test_production_provider_is_lazy_and_does_not_call_ports_at_build():
    calls = {"credentials": 0, "clients": 0}

    def credentials_loader():
        calls["credentials"] += 1
        raise AssertionError("ADC must not run while building the provider")

    def client_factory():
        calls["clients"] += 1
        raise AssertionError("auth HTTP must not run while building the provider")

    provider = production.build_content_token_provider(
        _config(),
        credentials_loader=credentials_loader,
        client_factory=client_factory,
    )

    assert repr(provider) == "<KeylessContentTokenProvider cache=ram-only redacted>"
    assert calls == {"credentials": 0, "clients": 0}


def test_production_provider_uses_fixed_mock_iam_and_oauth_contract():
    config = _config()
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.host == "iamcredentials.googleapis.com":
            assert request.method == "POST"
            assert request.url.path.endswith(
                "/projects/-/serviceAccounts/"
                "content-research@synthetic-project.iam.gserviceaccount.com:signJwt"
            )
            assert request.headers["authorization"] == "Bearer synthetic-adc-token"
            payload = json.loads(request.content)["payload"]
            claims = json.loads(payload)
            assert set(claims) == {"iss", "sub", "scope", "aud", "iat", "exp"}
            assert claims["iss"] == config.service_account
            assert claims["sub"] == config.subject
            assert claims["scope"] == "https://www.googleapis.com/auth/drive.readonly"
            assert claims["aud"] == "https://oauth2.googleapis.com/token"
            assert claims["exp"] - claims["iat"] <= 3600
            assert set(json.loads(request.content)) == {"payload"}
            return httpx.Response(
                200,
                request=request,
                json={"signedJwt": "synthetic-signed-jwt", "unknown": "omit"},
            )
        assert request.url == httpx.URL("https://oauth2.googleapis.com/token")
        assert request.method == "POST"
        body = request.content.decode("ascii")
        assert "grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer" in body
        assert "assertion=synthetic-signed-jwt" in body
        return httpx.Response(
            200,
            request=request,
            json={"access_token": "synthetic-access-token", "expires_in": 3600},
        )

    provider = production.build_content_token_provider(
        config,
        credentials_loader=lambda: (_Credentials(), config.project_id),
        client_factory=lambda: httpx.Client(
            transport=httpx.MockTransport(handler),
            follow_redirects=False,
            timeout=30.0,
        ),
    )
    profile = config.to_provisioned_profile().build()
    subject = config.fixed_subject()

    first = provider.get_access_token(
        profile=profile,
        subject=subject,
        scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
    )
    second = provider.get_access_token(
        profile=profile,
        subject=subject,
        scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
    )

    assert first == second == "synthetic-access-token"
    assert len(requests) == 2


def test_adc_failure_is_safe_and_does_not_reveal_exception(monkeypatch):
    secret = "synthetic ADC secret"

    def credentials_loader():
        raise RuntimeError(secret)

    provider = production.build_content_token_provider(
        _config(),
        credentials_loader=credentials_loader,
        client_factory=lambda: pytest.fail("HTTP must not run after ADC failure"),
    )

    with pytest.raises(ContentSafeError) as error:
        provider.get_access_token(
            profile=_config().to_provisioned_profile().build(),
            subject=_config().fixed_subject(),
            scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
        )

    assert error.value.code == "ADC_REFRESH"
    assert secret not in str(error.value)


@pytest.mark.parametrize(
    ("iam_status", "expected_code"),
    [(403, "IAM_SIGN_JWT"), (200, "RESPONSE_VALIDATION")],
)
def test_iam_failure_and_malformed_response_are_safe(iam_status, expected_code):
    config = _config()

    def handler(request: httpx.Request) -> httpx.Response:
        if iam_status == 403:
            return httpx.Response(
                403,
                request=request,
                content=b"RAW IAM BODY SECRET",
            )
        return httpx.Response(200, request=request, json={"unexpected": "omit"})

    provider = production.build_content_token_provider(
        config,
        credentials_loader=lambda: (_Credentials(), config.project_id),
        client_factory=lambda: httpx.Client(
            transport=httpx.MockTransport(handler),
            follow_redirects=False,
            timeout=30.0,
        ),
    )

    with pytest.raises(ContentSafeError) as error:
        provider.get_access_token(
            profile=config.to_provisioned_profile().build(),
            subject=config.fixed_subject(),
            scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
        )

    assert error.value.code == expected_code
    assert "RAW IAM BODY SECRET" not in str(error.value)


def test_oauth_malformed_response_is_safe():
    config = _config()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "iamcredentials.googleapis.com":
            return httpx.Response(
                200,
                request=request,
                json={"signedJwt": "synthetic-signed-jwt"},
            )
        return httpx.Response(
            200,
            request=request,
            json={"access_token": "synthetic-access-token", "expires_in": "3600"},
        )

    provider = production.build_content_token_provider(
        config,
        credentials_loader=lambda: (_Credentials(), config.project_id),
        client_factory=lambda: httpx.Client(
            transport=httpx.MockTransport(handler),
            follow_redirects=False,
            timeout=30.0,
        ),
    )

    with pytest.raises(ContentSafeError) as error:
        provider.get_access_token(
            profile=config.to_provisioned_profile().build(),
            subject=config.fixed_subject(),
            scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
        )

    assert error.value.code == "RESPONSE_VALIDATION"


def test_runtime_build_is_lazy_even_with_complete_configuration(monkeypatch):
    for name, value in _environment().items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(
        production,
        "_load_adc_credentials",
        lambda: pytest.fail("ADC must not run during runtime assembly"),
    )
    monkeypatch.setattr(server, "_CONTENT_RUNTIME", None)

    runtime = bootstrap.create_content_runtime()
    try:
        assert repr(runtime) == "<ContentRuntime sealed>"
    finally:
        runtime.close()


def test_configured_content_request_uses_only_mock_auth_and_drive(monkeypatch):
    config = _config()
    for name, value in _environment().items():
        monkeypatch.setenv(name, value)

    auth_requests: list[httpx.Request] = []
    drive_requests: list[httpx.Request] = []

    def auth_handler(request: httpx.Request) -> httpx.Response:
        auth_requests.append(request)
        if request.url.host == "iamcredentials.googleapis.com":
            return httpx.Response(
                200,
                request=request,
                json={"signedJwt": "synthetic-signed-jwt"},
            )
        return httpx.Response(
            200,
            request=request,
            json={"access_token": "synthetic-access-token", "expires_in": 3600},
        )

    def drive_handler(request: httpx.Request) -> httpx.Response:
        drive_requests.append(request)
        return httpx.Response(
            200,
            request=request,
            json={"drives": [{"id": "drive-1", "name": "Shared"}]},
        )

    monkeypatch.setattr(
        production,
        "_load_adc_credentials",
        lambda: (_Credentials(), config.project_id),
    )
    monkeypatch.setattr(
        production,
        "_build_auth_http_client",
        lambda: httpx.Client(
            transport=httpx.MockTransport(auth_handler),
            follow_redirects=False,
            timeout=30.0,
        ),
    )
    monkeypatch.setattr(
        bootstrap,
        "_build_http_client",
        lambda: httpx.Client(
            transport=httpx.MockTransport(drive_handler),
            follow_redirects=False,
            timeout=30.0,
        ),
    )
    monkeypatch.setattr(server, "_CONTENT_RUNTIME", None)

    result = server.workspace_drives_list(
        page_size=1,
        max_items=1,
        page_token=None,
        use_domain_admin_access=False,
    )

    runtime = server._CONTENT_RUNTIME
    assert runtime is not None
    try:
        assert result == {
            "drives": [{"drive_id": "drive-1", "name": "Shared"}],
            "next_page_token": None,
        }
        assert len(auth_requests) == 2
        assert len(drive_requests) == 1
        assert drive_requests[0].method == "GET"
        assert drive_requests[0].url.host == "www.googleapis.com"
        assert drive_requests[0].url.path == "/drive/v3/drives"
        assert drive_requests[0].url.params["pageSize"] == "1"
        assert "useDomainAdminAccess" not in drive_requests[0].url.params
    finally:
        runtime.close()
