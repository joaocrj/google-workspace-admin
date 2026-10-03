import base64
import inspect
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from google.oauth2.credentials import Credentials

from google_workspace_admin import server
from google_workspace_admin.auth import adc
from google_workspace_admin.content import bootstrap
from google_workspace_admin.content import config as content_config
from google_workspace_admin.content.auth import production
from google_workspace_admin.content.auth.scopes import (
    ApprovedScopeProfile,
    all_approved_scopes,
    scopes_for,
)
from google_workspace_admin.content.errors import ContentSafeError
from google_workspace_admin.content.public_file_ref import PublicFileRefProvider


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


def _synthetic_authorized_user_info() -> dict[str, object]:
    return {
        "type": "authorized_user",
        "client_id": "SYNTHETIC_CLIENT_ID_DO_NOT_LEAK",
        "client_secret": "SYNTHETIC_CLIENT_SECRET_DO_NOT_LEAK",
        "refresh_token": "SYNTHETIC_REFRESH_TOKEN_DO_NOT_LEAK",
        "token_uri": "https://oauth2.googleapis.com/token",
        "quota_project_id": "synthetic-quota-project",
        "universe_domain": "googleapis.com",
    }


def _write_synthetic_adc(
    tmp_path: Path,
    *,
    info: dict[str, object] | None = None,
    serialized: str | None = None,
) -> tuple[Path, Path]:
    appdata = tmp_path / "synthetic-appdata"
    adc_path = appdata / "gcloud" / "application_default_credentials.json"
    adc_path.parent.mkdir(parents=True, exist_ok=True)
    if serialized is None:
        adc_path.write_text(
            json.dumps(info if info is not None else _synthetic_authorized_user_info()),
            encoding="utf-8",
        )
    else:
        adc_path.write_text(serialized, encoding="utf-8")
    return appdata, adc_path


def _block_auth_discovery_and_processes(monkeypatch):
    import os
    import socket
    import subprocess

    import google.auth
    import google.auth._cloud_sdk as cloud_sdk
    import google.auth._default as auth_default
    from google.auth.compute_engine import _metadata

    def forbidden(*_args, **_kwargs):
        raise AssertionError("discovery, process, or network path was called")

    monkeypatch.setattr(google.auth, "default", forbidden)
    monkeypatch.setattr(auth_default, "default", forbidden)
    monkeypatch.setattr(google.auth, "load_credentials_from_file", forbidden)
    monkeypatch.setattr(auth_default, "load_credentials_from_file", forbidden)
    if hasattr(google.auth, "load_credentials_from_dict"):
        monkeypatch.setattr(google.auth, "load_credentials_from_dict", forbidden)
    if hasattr(auth_default, "load_credentials_from_dict"):
        monkeypatch.setattr(auth_default, "load_credentials_from_dict", forbidden)
    monkeypatch.setattr(cloud_sdk, "get_project_id", forbidden)
    monkeypatch.setattr(_metadata, "is_on_gce", forbidden)
    monkeypatch.setattr(_metadata, "ping", forbidden)
    for name in ("run", "call", "check_call", "check_output", "Popen"):
        monkeypatch.setattr(subprocess, name, forbidden)
    monkeypatch.setattr(os, "system", forbidden)
    monkeypatch.setattr(os, "popen", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)


def test_explicit_authorized_user_adc_loader_uses_only_appdata_and_is_load_only(
    tmp_path, monkeypatch
):
    _block_auth_discovery_and_processes(monkeypatch)
    appdata, adc_path = _write_synthetic_adc(tmp_path)
    decoy_root = tmp_path / "decoys"
    decoy_root.mkdir()
    gac_decoy = decoy_root / "gac-decoy.json"
    gac_decoy.write_text(
        json.dumps({"type": "service_account", "private_key": "SYNTHETIC"}),
        encoding="utf-8",
    )
    cloudsdk_config = decoy_root / "cloudsdk"
    cloudsdk_config.mkdir()
    (cloudsdk_config / "application_default_credentials.json").write_text(
        json.dumps({"type": "external_account", "audience": "SYNTHETIC"}),
        encoding="utf-8",
    )

    reads: list[Path] = []
    original_read_text = Path.read_text

    def tracked_read_text(path, *args, **kwargs):
        reads.append(path)
        return original_read_text(path, *args, **kwargs)

    def forbidden_refresh(_credentials, _request):
        raise AssertionError("credential refresh must remain caller-owned")

    monkeypatch.setattr(Path, "read_text", tracked_read_text)
    monkeypatch.setattr(Credentials, "refresh", forbidden_refresh)
    credentials, project_id = adc.load_local_authorized_user_adc_no_subprocess(
        {
            "APPDATA": str(appdata),
            "GOOGLE_APPLICATION_CREDENTIALS": str(gac_decoy),
            "CLOUDSDK_CONFIG": str(cloudsdk_config),
            "HOME": str(decoy_root),
            "GOOGLE_CLOUD_PROJECT": "synthetic-decoy-project",
        }
    )

    assert isinstance(credentials, Credentials)
    assert credentials.token is None
    assert not credentials.valid
    assert project_id is None
    assert reads == [adc_path]


@pytest.mark.parametrize(
    "appdata", [None, "", "   ", "relative-appdata", "bad\x00path"]
)
def test_explicit_authorized_user_adc_loader_fails_closed_without_appdata(
    appdata, tmp_path, monkeypatch
):
    _block_auth_discovery_and_processes(monkeypatch)
    decoy_root = tmp_path / "decoys"
    decoy_root.mkdir()
    cloudsdk_config = decoy_root / "cloudsdk"
    cloudsdk_config.mkdir()
    (cloudsdk_config / "application_default_credentials.json").write_text(
        json.dumps(_synthetic_authorized_user_info()),
        encoding="utf-8",
    )
    environment = {
        "GOOGLE_APPLICATION_CREDENTIALS": str(decoy_root / "gac-decoy.json"),
        "CLOUDSDK_CONFIG": str(cloudsdk_config),
        "HOME": str(decoy_root),
        "GOOGLE_CLOUD_PROJECT": "synthetic-decoy-project",
    }
    if appdata is not None:
        environment["APPDATA"] = appdata

    def forbidden_read(_path, *_args, **_kwargs):
        raise AssertionError("loader attempted a fallback file read")

    monkeypatch.setattr(Path, "read_text", forbidden_read)
    with pytest.raises(adc.ADCLoadError) as error:
        adc.load_local_authorized_user_adc_no_subprocess(environment)

    assert error.value.code == adc.ADC_CONFIGURATION_UNSUPPORTED
    assert str(decoy_root) not in str(error.value)
    if appdata is None:
        monkeypatch.delenv("APPDATA", raising=False)
        with pytest.raises(adc.ADCLoadError) as default_error:
            adc.load_local_authorized_user_adc_no_subprocess()
        assert default_error.value.code == adc.ADC_CONFIGURATION_UNSUPPORTED


def test_explicit_authorized_user_adc_loader_reports_missing_standard_file_safely(
    tmp_path, monkeypatch
):
    _block_auth_discovery_and_processes(monkeypatch)
    appdata = tmp_path / "synthetic-appdata"
    appdata.mkdir()
    decoy_root = tmp_path / "decoys"
    decoy_root.mkdir()
    cloudsdk_config = decoy_root / "cloudsdk"
    cloudsdk_config.mkdir()
    decoy_adc = cloudsdk_config / "application_default_credentials.json"
    decoy_adc.write_text(
        json.dumps(_synthetic_authorized_user_info()),
        encoding="utf-8",
    )

    with pytest.raises(adc.ADCLoadError) as error:
        adc.load_local_authorized_user_adc_no_subprocess(
            {
                "APPDATA": str(appdata),
                "CLOUDSDK_CONFIG": str(cloudsdk_config),
                "GOOGLE_APPLICATION_CREDENTIALS": str(decoy_adc),
                "HOME": str(decoy_root),
            }
        )

    assert error.value.code == adc.ADC_FILE_NOT_FOUND
    assert str(appdata) not in str(error.value)


def test_explicit_authorized_user_adc_loader_sanitizes_malformed_json(
    tmp_path, monkeypatch, caplog, capsys
):
    _block_auth_discovery_and_processes(monkeypatch)
    appdata, _ = _write_synthetic_adc(
        tmp_path,
        serialized=(
            '{"type":"authorized_user","client_secret":"'
            "SYNTHETIC_CLIENT_SECRET_DO_NOT_LEAK"
        ),
    )

    with pytest.raises(adc.ADCLoadError) as error:
        adc.load_local_authorized_user_adc_no_subprocess({"APPDATA": str(appdata)})

    assert error.value.code == adc.ADC_FILE_INVALID
    captured = capsys.readouterr()
    for secret in (
        "SYNTHETIC_CLIENT_SECRET_DO_NOT_LEAK",
        "SYNTHETIC_REFRESH_TOKEN_DO_NOT_LEAK",
        "SYNTHETIC_CLIENT_ID_DO_NOT_LEAK",
    ):
        assert secret not in str(error.value)
        assert secret not in caplog.text
        assert secret not in captured.out
        assert secret not in captured.err


@pytest.mark.parametrize(
    "credential_type",
    [
        "service_account",
        "external_account",
        "external_account_authorized_user",
        "impersonated_service_account",
        "gdch_service_account",
        "unknown_type",
        "missing_type",
        23,
    ],
)
def test_explicit_authorized_user_adc_loader_rejects_other_types_before_construction(
    credential_type, tmp_path, monkeypatch
):
    _block_auth_discovery_and_processes(monkeypatch)
    info: dict[str, object] = _synthetic_authorized_user_info()
    if credential_type == "missing_type":
        info.pop("type")
    else:
        info["type"] = credential_type
    if credential_type == "external_account":
        info["credential_source"] = {
            "executable": {"command": "SYNTHETIC_COMMAND_MUST_NOT_RUN"}
        }
    appdata, _ = _write_synthetic_adc(tmp_path, info=info)
    constructed: list[object] = []

    def tracked_constructor(_cls, supplied_info, *_args, **_kwargs):
        constructed.append(supplied_info)
        raise AssertionError("unsupported credential reached construction")

    monkeypatch.setattr(
        Credentials,
        "from_authorized_user_info",
        classmethod(tracked_constructor),
    )
    with pytest.raises(adc.ADCLoadError) as error:
        adc.load_local_authorized_user_adc_no_subprocess({"APPDATA": str(appdata)})

    assert error.value.code == adc.ADC_TYPE_UNSUPPORTED
    assert constructed == []


def test_explicit_adc_private_content_seam_refreshes_once_and_reaches_mock_iam(
    tmp_path, monkeypatch
):
    _block_auth_discovery_and_processes(monkeypatch)
    appdata, _ = _write_synthetic_adc(tmp_path)
    environment = {"APPDATA": str(appdata)}
    with monkeypatch.context() as no_refresh:
        no_refresh.setattr(
            Credentials,
            "refresh",
            lambda *_args, **_kwargs: pytest.fail("ADC load must not refresh"),
        )
        loaded_credentials, loaded_project_id = (
            adc.load_local_authorized_user_adc_no_subprocess(environment)
        )
    assert loaded_credentials.token is None
    assert loaded_project_id is None

    refresh_calls = 0
    refresh_request_calls = 0

    class _Response:
        status = 200
        headers = {"content-type": "application/json"}
        data = json.dumps(
            {
                "access_token": "SYNTHETIC_ADC_ACCESS_TOKEN",
                "expires_in": 3600,
                "token_type": "Bearer",
            }
        ).encode("utf-8")

    def oauth_request(*, url, method, **_kwargs):
        nonlocal refresh_calls
        refresh_calls += 1
        assert url == "https://oauth2.googleapis.com/token"
        assert method == "POST"
        return _Response()

    def request_factory():
        nonlocal refresh_request_calls
        refresh_request_calls += 1
        return oauth_request

    auth_requests: list[httpx.Request] = []

    def auth_handler(request: httpx.Request) -> httpx.Response:
        auth_requests.append(request)
        if request.url.host == "iamcredentials.googleapis.com":
            assert request.headers["authorization"] == (
                "Bearer SYNTHETIC_ADC_ACCESS_TOKEN"
            )
            assert "/projects/-/serviceAccounts/" in request.url.path
            return httpx.Response(
                200,
                request=request,
                json={"signedJwt": "SYNTHETIC_SIGNED_JWT"},
            )
        assert request.url == httpx.URL("https://oauth2.googleapis.com/token")
        assert "assertion=SYNTHETIC_SIGNED_JWT" in request.content.decode("ascii")
        return httpx.Response(
            200,
            request=request,
            json={"access_token": "SYNTHETIC_WORKSPACE_TOKEN", "expires_in": 3600},
        )

    def credentials_loader():
        return production._load_authorized_user_adc_credentials(
            environment=environment,
            request_factory=request_factory,
        )

    provider = production.build_content_token_provider(
        _config(),
        credentials_loader=credentials_loader,
        client_factory=lambda: httpx.Client(
            transport=httpx.MockTransport(auth_handler),
            follow_redirects=False,
            timeout=30.0,
        ),
    )
    access_token = provider.get_access_token(
        profile=_config().to_provisioned_profile().build(),
        subject=_config().fixed_subject(),
        scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
    )

    assert access_token == "SYNTHETIC_WORKSPACE_TOKEN"
    assert refresh_calls == 1
    assert refresh_request_calls == 1
    assert len(auth_requests) == 2


def test_explicit_adc_private_content_seam_skips_refresh_for_valid_credentials(
    tmp_path, monkeypatch
):
    _block_auth_discovery_and_processes(monkeypatch)
    info = _synthetic_authorized_user_info()
    info["token"] = "SYNTHETIC_VALID_ADC_ACCESS_TOKEN"
    info["expiry"] = (
        (datetime.now(timezone.utc) + timedelta(hours=1))
        .strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    )
    appdata, _ = _write_synthetic_adc(tmp_path, info=info)

    credentials, project_id = production._load_authorized_user_adc_credentials(
        environment={"APPDATA": str(appdata)},
        request_factory=lambda: pytest.fail("valid ADC must not refresh"),
    )

    assert credentials.valid
    assert credentials.token == "SYNTHETIC_VALID_ADC_ACCESS_TOKEN"
    assert project_id is None


def test_explicit_adc_refresh_failure_is_secret_safe(
    tmp_path, monkeypatch, caplog, capsys
):
    _block_auth_discovery_and_processes(monkeypatch)
    appdata, _ = _write_synthetic_adc(tmp_path)

    def failed_oauth_request(**_kwargs):
        raise RuntimeError(
            "SYNTHETIC_CLIENT_ID_DO_NOT_LEAK "
            "SYNTHETIC_CLIENT_SECRET_DO_NOT_LEAK "
            "SYNTHETIC_REFRESH_TOKEN_DO_NOT_LEAK"
        )

    with pytest.raises(ContentSafeError) as error:
        production._load_authorized_user_adc_credentials(
            environment={"APPDATA": str(appdata)},
            request_factory=lambda: failed_oauth_request,
        )

    assert error.value.code == "ADC_REFRESH"
    captured = capsys.readouterr()
    for secret in (
        "SYNTHETIC_CLIENT_SECRET_DO_NOT_LEAK",
        "SYNTHETIC_REFRESH_TOKEN_DO_NOT_LEAK",
        "SYNTHETIC_CLIENT_ID_DO_NOT_LEAK",
    ):
        assert secret not in str(error.value)
        assert secret not in caplog.text
        assert secret not in captured.out
        assert secret not in captured.err


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
    assert config.public_file_ref_hmac_key is None
    assert repr(config) == "<ContentConfig redacted>"


def test_content_config_loads_dedicated_synthetic_public_file_ref_key_redacted():
    key = bytes(range(32))
    encoded = base64.b64encode(key).decode("ascii")
    environment = _environment()
    environment[content_config.CONTENT_PUBLIC_FILE_REF_HMAC_KEY_ENV] = encoded

    config = content_config.ContentConfig.from_environment(environment)

    assert config.public_file_ref_hmac_key == key
    assert encoded not in repr(config)
    assert b"synthetic" not in repr(config).encode("ascii")


def test_malformed_public_file_ref_key_fails_closed_without_echoing_value():
    environment = _environment()
    malformed = base64.b64encode(b"too short").decode("ascii")
    environment[content_config.CONTENT_PUBLIC_FILE_REF_HMAC_KEY_ENV] = malformed

    with pytest.raises(ContentSafeError) as error:
        content_config.ContentConfig.from_environment(environment)

    assert error.value.code == "LOCAL_VALIDATION"
    assert malformed not in str(error.value)


def test_bootstrap_binds_public_file_ref_provider_to_configured_customer_and_key(monkeypatch):
    key = bytes(range(32))
    environment = _environment(customer_id="customer-123")
    environment[content_config.CONTENT_PUBLIC_FILE_REF_HMAC_KEY_ENV] = (
        base64.b64encode(key).decode("ascii")
    )
    configured = content_config.ContentConfig.from_environment(environment)
    monkeypatch.setattr(bootstrap, "load_content_config", lambda: configured)

    provider = bootstrap._build_public_file_ref_provider()

    assert provider is not None
    assert provider("exact-Drive-ID") == PublicFileRefProvider(
        "customer-123",
        key,
    )("exact-Drive-ID")

    without_key = content_config.ContentConfig.from_environment(_environment())
    monkeypatch.setattr(bootstrap, "load_content_config", lambda: without_key)
    assert bootstrap._build_public_file_ref_provider() is None


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


def test_public_mcp_scope_profiles_remain_read_only_and_exclude_internal_write_scope():
    assert scopes_for(ApprovedScopeProfile.DRIVE_DISCOVERY) == (
        "https://www.googleapis.com/auth/drive.readonly",
    )
    assert scopes_for(ApprovedScopeProfile.SHEETS_CONTENT) == (
        "https://www.googleapis.com/auth/spreadsheets.readonly",
    )
    assert "https://www.googleapis.com/auth/spreadsheets" not in all_approved_scopes()
    assert not hasattr(ApprovedScopeProfile, "GSHEETS_FIXTURE_WRITE")


def test_controlled_validation_provider_uses_its_fixed_scopes_and_never_changes_public_provider():
    config = _config()
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.host == "iamcredentials.googleapis.com":
            payload = json.loads(request.content)["payload"]
            claims = json.loads(payload)
            assert claims["iss"] == config.service_account
            assert claims["sub"] == config.subject
            assert claims["scope"] == (
                "https://www.googleapis.com/auth/drive.readonly "
                "https://www.googleapis.com/auth/spreadsheets"
            )
            return httpx.Response(
                200,
                request=request,
                json={"signedJwt": "synthetic-validation-signed-jwt"},
            )
        return httpx.Response(
            200,
            request=request,
            json={"access_token": "synthetic-validation-token", "expires_in": 3600},
        )

    provider = production._build_controlled_validation_token_provider(
        config,
        credentials_loader=lambda: (_Credentials(), config.project_id),
        client_factory=lambda: httpx.Client(
            transport=httpx.MockTransport(handler),
            follow_redirects=False,
            timeout=30.0,
        ),
    )

    assert "synthetic" not in repr(provider)
    assert provider.get_access_token() == "synthetic-validation-token"
    assert provider.get_access_token() == "synthetic-validation-token"
    assert len(requests) == 2
    with pytest.raises(TypeError):
        provider.get_access_token(scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY)


def test_public_production_provider_claims_remain_drive_readonly_only():
    config = _config()
    observed_scopes: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "iamcredentials.googleapis.com":
            payload = json.loads(request.content)["payload"]
            observed_scopes.append(json.loads(payload)["scope"])
            return httpx.Response(
                200,
                request=request,
                json={"signedJwt": "synthetic-public-signed-jwt"},
            )
        return httpx.Response(
            200,
            request=request,
            json={"access_token": "synthetic-public-token", "expires_in": 3600},
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
    provider.get_access_token(
        profile=config.to_provisioned_profile().build(),
        subject=config.fixed_subject(),
        scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
    )

    assert observed_scopes == ["https://www.googleapis.com/auth/drive.readonly"]


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


def test_configured_file_inventory_reuses_mock_drive_readonly_auth(monkeypatch):
    config = _config()
    for name, value in _environment().items():
        monkeypatch.setenv(name, value)

    signed_scopes: list[str] = []
    drive_requests: list[httpx.Request] = []

    def auth_handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "iamcredentials.googleapis.com":
            claims = json.loads(json.loads(request.content)["payload"])
            signed_scopes.append(claims["scope"])
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
            json={
                "files": [
                    {
                        "id": "file-1",
                        "name": "Report",
                        "mimeType": "application/pdf",
                        "trashed": False,
                    }
                ]
            },
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

    result = server.workspace_drive_files_list(
        "drive-1",
        page_size=1,
        max_items=1,
    )

    runtime = server._CONTENT_RUNTIME
    assert runtime is not None
    try:
        assert result.model_dump() == {
            "files": [
                {
                    "file_id": "file-1",
                    "name": "Report",
                    "mime_type": "application/pdf",
                    "modified_time": None,
                    "size": None,
                    "parents": [],
                }
            ],
            "next_page_token": None,
        }
        assert signed_scopes == ["https://www.googleapis.com/auth/drive.readonly"]
        assert len(drive_requests) == 1
        assert drive_requests[0].url.path == "/drive/v3/files"
        assert "useDomainAdminAccess" not in drive_requests[0].url.params
    finally:
        runtime.close()


def test_public_bootstrap_server_runtime_spy_never_selects_internal_builder(monkeypatch):
    config = _config()
    for name, value in _environment().items():
        monkeypatch.setenv(name, value)

    internal_builder_calls = []
    requested_scopes = []
    drive_requests = []

    def forbidden_internal_builder(*args, **kwargs):
        internal_builder_calls.append((args, kwargs))
        raise AssertionError("public runtime selected the internal builder")

    def auth_handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "iamcredentials.googleapis.com":
            claims = json.loads(json.loads(request.content)["payload"])
            requested_scopes.append(claims["scope"])
            return httpx.Response(
                200,
                request=request,
                json={"signedJwt": "synthetic-public-path-signed-jwt"},
            )
        return httpx.Response(
            200,
            request=request,
            json={"access_token": "synthetic-public-path-token", "expires_in": 3600},
        )

    def drive_handler(request: httpx.Request) -> httpx.Response:
        drive_requests.append(request)
        return httpx.Response(
            200,
            request=request,
            json={"drives": [{"id": "synthetic-drive", "name": "Shared"}]},
        )

    monkeypatch.setattr(
        production,
        "_build_controlled_validation_token_provider",
        forbidden_internal_builder,
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

    active_runtime = server._CONTENT_RUNTIME
    assert active_runtime is not None
    try:
        assert result["drives"] == [
            {"drive_id": "synthetic-drive", "name": "Shared"}
        ]
        assert requested_scopes == ["https://www.googleapis.com/auth/drive.readonly"]
        assert len(drive_requests) == 1
        assert drive_requests[0].method == "GET"
        assert internal_builder_calls == []
    finally:
        active_runtime.close()


def test_public_and_internal_provider_caches_and_tokens_are_independent():
    config = _config()
    public_requests = []
    internal_requests = []

    def provider_factory(target, token):
        def handler(request: httpx.Request) -> httpx.Response:
            target.append(request.url.host)
            if request.url.host == "iamcredentials.googleapis.com":
                return httpx.Response(
                    200,
                    request=request,
                    json={"signedJwt": f"synthetic-{token}-signed-jwt"},
                )
            return httpx.Response(
                200,
                request=request,
                json={"access_token": token, "expires_in": 3600},
            )

        return lambda: httpx.Client(
            transport=httpx.MockTransport(handler),
            follow_redirects=False,
            timeout=30.0,
        )

    public = production.build_content_token_provider(
        config,
        credentials_loader=lambda: (_Credentials(), config.project_id),
        client_factory=provider_factory(public_requests, "synthetic-public-token"),
    )
    internal = production._build_controlled_validation_token_provider(
        config,
        credentials_loader=lambda: (_Credentials(), config.project_id),
        client_factory=provider_factory(internal_requests, "synthetic-internal-token"),
    )
    profile = config.to_provisioned_profile().build()
    subject = config.fixed_subject()

    public_token = public.get_access_token(
        profile=profile,
        subject=subject,
        scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
    )
    internal_token = internal.get_access_token()
    assert public_token == "synthetic-public-token"
    assert internal_token == "synthetic-internal-token"
    assert public_token != internal_token
    assert public._cache is not internal._cache
    assert isinstance(public._cache, dict)
    assert isinstance(internal._cache, tuple)

    public_calls = len(public_requests)
    internal_calls = len(internal_requests)
    assert public.get_access_token(
        profile=profile,
        subject=subject,
        scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
    ) == public_token
    assert internal.get_access_token() == internal_token
    assert len(public_requests) == public_calls
    assert len(internal_requests) == internal_calls


def test_controlled_provider_supported_claim_serialization_has_unique_names():
    config = _config()
    captured = []

    def sign_jwt(service_account, serialized_claims, adc_token):
        captured.append(serialized_claims)
        return "synthetic-unique-claims-signed-jwt"

    provider = production._build_controlled_validation_token_provider(
        config,
        credentials_loader=lambda: (_Credentials(), config.project_id),
        client_factory=lambda: pytest.fail("captured fake signer must bypass HTTP"),
    )
    provider._sign_jwt = sign_jwt
    provider._exchange_token = lambda _jwt: ("synthetic-claims-access-token", 3600)
    assert provider.get_access_token() == "synthetic-claims-access-token"
    assert len(captured) == 1

    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            assert key not in result
            result[key] = value
        return result

    claims = json.loads(captured[0], object_pairs_hook=unique_pairs)
    assert set(claims) == {"iss", "sub", "scope", "aud", "iat", "exp"}
    assert claims["iss"] == config.service_account
    assert claims["sub"] == config.subject


def test_controlled_auth_and_driver_surfaces_have_no_runtime_scope_subject_or_target_parameters():
    from validation.fixtures import run_gsheets_spill_restoration_controlled_v1 as driver
    from validation.fixtures.gsheets_controlled_write import ControlledSheetsTransport

    provider_signature = inspect.signature(
        production._build_controlled_validation_token_provider
    )
    access_token_signature = inspect.signature(
        production._build_controlled_validation_token_provider(_config()).get_access_token
    )
    driver_signature = inspect.signature(driver.execute_controlled_mode)
    transport_write_signature = inspect.signature(ControlledSheetsTransport.write_o1_once)

    assert not {"scope", "scope_profile", "subject", "operation", "target", "range"} & set(provider_signature.parameters)
    assert tuple(access_token_signature.parameters) == ()
    assert not {"scope", "subject", "target", "range", "fixture_id"} & set(driver_signature.parameters)
    assert tuple(transport_write_signature.parameters) == ("self",)
