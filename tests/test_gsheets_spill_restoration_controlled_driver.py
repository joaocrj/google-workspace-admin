from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
import re
import socket
import subprocess
import sys
from typing import Any

import httpx
import pytest

from google_workspace_admin import server
from google_workspace_admin.content import bootstrap, runtime
from google_workspace_admin.content.auth import production
from validation.fixtures import gsheets_controlled_write as transport_module
from validation.fixtures.fixture_contract import load_fixture_spec
from validation.fixtures import run_gsheets_spill_restoration_controlled_v1 as driver


_SPEC = load_fixture_spec()
_DUMMY_ID = "dummy-fixture-id-123"
_DUMMY_TOKEN = "synthetic-validation-token"
_DUMMY_CONFIG = "synthetic-config"
_MODIFIED_BEFORE = "2026-09-27T00:00:00Z"
_MODIFIED_AFTER = "2026-09-27T00:00:01Z"


@pytest.fixture(autouse=True)
def _deny_network(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("external network access is forbidden in this suite")

    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(socket.socket, "connect", fail)
    monkeypatch.setattr(socket.socket, "connect_ex", fail)


def _snapshots(*, o1_ok=True, p1="blank"):
    o1 = transport_module.CellDataSnapshot(
        cell_data_present=True,
        user_entered_value_present=True,
        authored_formula_present=True,
        canonical_formula_match=o1_ok,
        formatted_value_present=True,
        formatted_expectation_match=o1_ok,
        effective_value_present=True,
        effective_value_type="NUMBER" if o1_ok else "STRING",
        effective_expectation_match=o1_ok,
    )
    if p1 == "blank":
        p1_snapshot = transport_module.CellDataSnapshot(
            True, False, False, False, False, False, False, "ABSENT", False
        )
    elif p1 == "canonical":
        p1_snapshot = transport_module.CellDataSnapshot(
            True, False, False, False, True, True, True, "NUMBER", True
        )
    elif p1 == "authored":
        p1_snapshot = transport_module.CellDataSnapshot(
            True, True, True, False, True, False, True, "NUMBER", False
        )
    elif p1 == "wrong-display":
        p1_snapshot = transport_module.CellDataSnapshot(
            True, False, False, False, True, False, True, "NUMBER", False
        )
    else:
        raise AssertionError("unknown fake state")
    return o1, p1_snapshot


class _FakeTransport:
    def __init__(
        self,
        *,
        locale="pt_BR",
        time_zone="America/Sao_Paulo",
        pre=None,
        post=None,
        write_fails=False,
        modified_after=_MODIFIED_AFTER,
        drive_valid=True,
        drive_id_present=True,
        drive_id_matches=True,
        drive_mime_type_present=True,
        drive_is_google_sheet=True,
        drive_trashed_present=True,
        drive_not_trashed=True,
        drive_modified_time_present=True,
    ):
        self.locale = locale
        self.time_zone = time_zone
        self.pre = pre if pre is not None else _snapshots()
        self.post = post if post is not None else _snapshots(p1="canonical")
        self.write_fails = write_fails
        self.modified_after = modified_after
        self.drive_valid = drive_valid
        self.drive_id_present = drive_id_present
        self.drive_id_matches = drive_id_matches
        self.drive_mime_type_present = drive_mime_type_present
        self.drive_is_google_sheet = drive_is_google_sheet
        self.drive_trashed_present = drive_trashed_present
        self.drive_not_trashed = drive_not_trashed
        self.drive_modified_time_present = drive_modified_time_present
        self.calls = []
        self.writes = 0
        self.closed = False

    def read_drive_metadata(self):
        self.calls.append("drive_metadata")
        modified = _MODIFIED_BEFORE if self.calls.count("drive_metadata") == 1 else self.modified_after
        return transport_module.DriveMetadata(
            id_present=self.drive_valid and self.drive_id_present,
            id_matches_requested_exact_id=self.drive_valid and self.drive_id_matches,
            mime_type_present=self.drive_valid and self.drive_mime_type_present,
            is_google_sheet=self.drive_valid and self.drive_is_google_sheet,
            trashed_present=self.drive_valid and self.drive_trashed_present,
            not_trashed=self.drive_valid and self.drive_not_trashed,
            modified_time_present=(
                self.drive_valid and self.drive_modified_time_present
            ),
            modified_time_value=(
                modified
                if self.drive_valid and self.drive_modified_time_present
                else None
            ),
        )

    def read_workbook_metadata(self):
        self.calls.append("workbook_metadata")
        return transport_module.WorkbookMetadata(
            self.locale, 42, "Validation", 1, time_zone=self.time_zone
        )

    def read_o1_p1_prewrite(self):
        self.calls.append("prewrite_cells")
        return self.pre

    def write_o1_once(self):
        self.writes += 1
        self.calls.append("write_o1")
        if self.write_fails:
            raise transport_module.ControlledTransportError("TRANSPORT_FAILURE")

    def read_o1_p1_postwrite(self):
        self.calls.append("postwrite_cells")
        return self.post

    def close(self):
        self.closed = True


def _fixture_toml(*, include_hmac=True):
    rows = [
        "[mcp_servers.google_workspace_admin.env]",
        'GOOGLE_WORKSPACE_CONTENT_PROJECT_ID = "synthetic-project"',
        'GOOGLE_WORKSPACE_CONTENT_SERVICE_ACCOUNT = "svc@synthetic-project.iam.gserviceaccount.com"',
        'GOOGLE_WORKSPACE_CONTENT_SUBJECT = "reader@cevalente.com.br"',
        'GOOGLE_WORKSPACE_CONTENT_CUSTOMER_ID = "synthetic-customer"',
        'GOOGLE_WORKSPACE_CONTENT_DOMAIN = "cevalente.com.br"',
    ]
    if include_hmac:
        rows.append('GOOGLE_WORKSPACE_CONTENT_PUBLIC_FILE_REF_HMAC_KEY_B64 = "synthetic-hmac-value"')
    return "\n".join(rows) + "\n"


def _patch_dummy_hash(monkeypatch, dummy_id=_DUMMY_ID):
    real_sha256 = hashlib.sha256
    approved = driver.APPROVED_FIXTURE_ID_SHA256

    class _Digest:
        def hexdigest(self):
            return approved

    def fake_sha256(value=b"", *args, **kwargs):
        if value == dummy_id.encode("utf-8"):
            return _Digest()
        return real_sha256(value, *args, **kwargs)

    monkeypatch.setattr(driver.hashlib, "sha256", fake_sha256)


def _ports(monkeypatch, env, fake_transport, events=None, *, auth_fails=False):
    events = events if events is not None else []

    class Provider:
        def get_access_token(self):
            events.append("auth")
            if auth_fails:
                raise RuntimeError("synthetic auth detail must not escape")
            return _DUMMY_TOKEN

    def load_config():
        events.append("config")
        visible = {key: env.get(key) for key in driver.CONTENT_ENV_KEYS}
        visible["hmac_present"] = "GOOGLE_WORKSPACE_CONTENT_PUBLIC_FILE_REF_HMAC_KEY_B64" in env
        visible["application_credentials_present"] = "GOOGLE_APPLICATION_CREDENTIALS" in env
        events.append(visible)
        return _DUMMY_CONFIG

    def build_provider(config):
        events.append(("provider_builder", config))
        return Provider()

    def build_transport(fixture_identity, access_token, spec):
        events.append(("transport_builder", fixture_identity.value, access_token, spec.fixture_alias))
        return fake_transport

    return driver.ExecutionPorts(load_config, build_provider, build_transport)


def _run_fake(monkeypatch, *, fake_transport=None, environment=None, config_path=None, auth_fails=False):
    fake_transport = fake_transport or _FakeTransport()
    env = environment if environment is not None else {driver.FIXTURE_ID_ENV: _DUMMY_ID}
    events = []
    ports = _ports(monkeypatch, env, fake_transport, events, auth_fails=auth_fails)
    _patch_dummy_hash(monkeypatch)
    result = driver.execute_controlled_mode(
        environment=env,
        ports=ports,
        config_path=config_path,
    )
    return result, fake_transport, events, env


def test_import_driver_is_local_and_redacted():
    assert driver.DRIVER_VERSION == "2.1"
    assert driver._repo_root_from_file() == Path(driver.__file__).resolve().parents[2]
    assert "dummy" not in repr(driver._ValidatedFixtureIdentity(_DUMMY_ID))


def test_help_is_safe_and_contains_only_supported_modes():
    result = subprocess.run(
        [sys.executable, "-B", str(Path(driver.__file__).resolve()), "--help"],
        cwd=Path(driver.__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--local-preflight" in result.stdout
    assert "--execute-controlled-test" in result.stdout
    assert "--fixture-id" not in result.stdout
    assert "--file-id" not in result.stdout
    assert result.stderr == ""


def test_local_preflight_passes_without_environment_or_http_client(monkeypatch):
    monkeypatch.setattr(httpx, "Client", lambda *a, **k: pytest.fail("client must not be created"))
    passed, classifications = driver.local_preflight()
    assert passed
    assert classifications == (
        "LOCAL_BOOTSTRAP=PASS",
        "CANONICAL_FIXTURE=PASS",
        "IDENTITY_GUARD=PASS",
        "TRANSPORT_REGISTRY=PASS",
        "WRITE_BUDGET=1",
        "PUBLIC_MCP_INTEGRATION=NO",
        "PUBLIC_TOOLS=24",
        "PUBLIC_WRITE_TOOLS=0",
    )


def test_repo_cwd_local_preflight_launch():
    root = Path(driver.__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-B", str(Path(driver.__file__).resolve()), "--local-preflight"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "LOCAL_BOOTSTRAP=PASS" in result.stdout
    assert result.stderr == ""


def test_external_cwd_local_preflight_launch(tmp_path):
    script = Path(driver.__file__).resolve()
    result = subprocess.run(
        [sys.executable, "-B", str(script), "--local-preflight"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "CANONICAL_FIXTURE=PASS" in result.stdout
    assert result.stderr == ""


def test_driver_and_tests_contain_no_personal_absolute_path():
    paths = (Path(driver.__file__), Path(__file__))
    text = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    assert re.search(r"(?m)^[A-Za-z]:\\", text) is None


def test_cli_has_no_id_range_scope_or_subject_options():
    options = {
        option
        for action in driver._build_parser()._actions
        for option in action.option_strings
    }
    assert options == {"-h", "--help", "--local-preflight", "--execute-controlled-test"}
    assert not any(any(word in option for word in ("id", "range", "scope", "subject", "target")) for option in options if option != "--help")


def test_rejected_cli_id_value_is_not_echoed(capsys):
    result = driver.main(["--fixture-id", _DUMMY_ID])
    output = capsys.readouterr().out
    assert result == 2
    assert output.strip() == "LOCAL_BOOTSTRAP_FAILURE"
    assert _DUMMY_ID not in output


@pytest.mark.parametrize("value", [None, "", "   ", "\t\r\n"])
def test_missing_empty_and_whitespace_id_fail_before_config_auth(value, monkeypatch, tmp_path):
    env = {} if value is None else {driver.FIXTURE_ID_ENV: value}
    events = []
    fake = _FakeTransport()
    ports = _ports(monkeypatch, env, fake, events)
    path = tmp_path / "config.toml"
    path.write_text(_fixture_toml(), encoding="utf-8")
    result = driver.execute_controlled_mode(environment=env, ports=ports, config_path=path)
    assert result.classification == "FIXTURE_ID_INPUT_MISSING"
    assert events == []
    assert fake.calls == []
    assert driver.FIXTURE_ID_ENV not in env


def test_wrong_identity_fails_before_config_auth_and_never_echoes_input(monkeypatch, tmp_path):
    wrong = "dummy-wrong-fixture-id"
    env = {driver.FIXTURE_ID_ENV: wrong}
    events = []
    fake = _FakeTransport()
    ports = _ports(monkeypatch, env, fake, events)
    path = tmp_path / "config.toml"
    path.write_text(_fixture_toml(), encoding="utf-8")
    result = driver.execute_controlled_mode(environment=env, ports=ports, config_path=path)
    rendered = json.dumps(result.as_safe_dict(), ensure_ascii=False)
    assert result.classification == "FIXTURE_ID_IDENTITY_MISMATCH"
    assert wrong not in rendered
    assert events == []
    assert fake.calls == []
    assert driver.FIXTURE_ID_ENV not in env


def test_dummy_identity_sha_algorithm_and_environment_removal(monkeypatch):
    dummy = "dummy-only-id-456"
    expected = hashlib.sha256(dummy.encode("utf-8")).hexdigest()
    monkeypatch.setattr(driver, "APPROVED_FIXTURE_ID_SHA256", expected)
    env = {driver.FIXTURE_ID_ENV: dummy}
    identity = driver._ingest_fixture_identity(env)
    assert identity.value == dummy
    assert driver.FIXTURE_ID_ENV not in env
    assert repr(identity) == "<_ValidatedFixtureIdentity redacted>"


def test_process_local_config_bridge_copies_exact_five_and_never_hmac_or_adc_path(monkeypatch, tmp_path):
    env = {driver.FIXTURE_ID_ENV: _DUMMY_ID}
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.delenv("GOOGLE_WORKSPACE_CONTENT_PUBLIC_FILE_REF_HMAC_KEY_B64", raising=False)
    fake = _FakeTransport()
    path = tmp_path / "config.toml"
    path.write_text(_fixture_toml(), encoding="utf-8")
    result, _, events, final_env = _run_fake(
        monkeypatch,
        fake_transport=fake,
        environment=env,
        config_path=path,
    )
    observed = next(event for event in events if isinstance(event, dict))
    assert result.classification == driver.CLASS_A
    assert set(key for key in observed if key not in {"hmac_present", "application_credentials_present"}) == set(driver.CONTENT_ENV_KEYS)
    assert all(observed[key] for key in driver.CONTENT_ENV_KEYS)
    assert observed["hmac_present"] is False
    assert observed["application_credentials_present"] is False
    assert "GOOGLE_APPLICATION_CREDENTIALS" not in final_env
    assert driver.FIXTURE_ID_ENV not in final_env
    assert not any(key in final_env for key in driver.CONTENT_ENV_KEYS)


def test_hmac_in_toml_is_not_copied_and_preexisting_hmac_is_temporarily_hidden(monkeypatch, tmp_path):
    env = {
        driver.FIXTURE_ID_ENV: _DUMMY_ID,
        "GOOGLE_WORKSPACE_CONTENT_PUBLIC_FILE_REF_HMAC_KEY_B64": "process-local-sentinel",
    }
    path = tmp_path / "config.toml"
    path.write_text(_fixture_toml(include_hmac=True), encoding="utf-8")
    fake = _FakeTransport()
    result, _, events, final_env = _run_fake(
        monkeypatch,
        fake_transport=fake,
        environment=env,
        config_path=path,
    )
    observed = next(event for event in events if isinstance(event, dict))
    assert result.hmac_copied == "NO"
    assert observed["hmac_present"] is False
    assert final_env["GOOGLE_WORKSPACE_CONTENT_PUBLIC_FILE_REF_HMAC_KEY_B64"] == "process-local-sentinel"


def test_auth_provider_is_injected_after_identity_and_config(monkeypatch, tmp_path):
    events = []

    class OrderedTransport(_FakeTransport):
        def read_drive_metadata(self):
            events.append("drive")
            return super().read_drive_metadata()

    env = {driver.FIXTURE_ID_ENV: _DUMMY_ID}
    fake = OrderedTransport()
    ports = _ports(monkeypatch, env, fake, events)
    path = tmp_path / "config.toml"
    path.write_text(_fixture_toml(), encoding="utf-8")
    _patch_dummy_hash(monkeypatch)
    result = driver.execute_controlled_mode(environment=env, ports=ports, config_path=path)
    assert result.classification == driver.CLASS_A
    assert events.index("config") < events.index(("provider_builder", _DUMMY_CONFIG))
    assert events.index("auth") < events.index(("transport_builder", _DUMMY_ID, _DUMMY_TOKEN, "GSHEETS_VALIDATION_V1"))
    assert events.index("auth") < events.index("drive")


def test_config_failure_never_constructs_auth_or_transport(monkeypatch, tmp_path):
    env = {driver.FIXTURE_ID_ENV: _DUMMY_ID}
    events = []
    fake = _FakeTransport()
    ports = _ports(monkeypatch, env, fake, events)
    path = tmp_path / "absent.toml"
    _patch_dummy_hash(monkeypatch)
    result = driver.execute_controlled_mode(environment=env, ports=ports, config_path=path)
    assert result.classification == "CONFIG_BRIDGE_FAILURE"
    assert events == []
    assert fake.calls == []


def test_auth_failure_is_sanitized_and_stops_before_google(monkeypatch, tmp_path):
    env = {driver.FIXTURE_ID_ENV: _DUMMY_ID}
    fake = _FakeTransport()
    path = tmp_path / "config.toml"
    path.write_text(_fixture_toml(), encoding="utf-8")
    result, _, _, _ = _run_fake(monkeypatch, fake_transport=fake, environment=env, config_path=path, auth_fails=True)
    rendered = json.dumps(result.as_safe_dict(), ensure_ascii=False)
    assert result.classification == "AUTH_FAILURE"
    assert result.auth_status == "FAIL"
    assert "synthetic auth detail" not in rendered
    assert fake.calls == []


def test_state_machine_locale_mismatch_stops_before_cells_or_write():
    fake = _FakeTransport(locale="fr_FR")
    result = driver._run_google_state_machine(_SPEC, fake)
    assert result.classification == driver.CLASS_E
    assert result.sheets_data_reads == 0
    assert result.sheets_write_attempts == 0
    assert "prewrite_cells" not in fake.calls


def test_state_machine_time_zone_mismatch_stops_before_cells_or_write():
    fake = _FakeTransport(time_zone="UTC")
    result = driver._run_google_state_machine(_SPEC, fake)
    assert result.classification == driver.CLASS_I
    assert result.locale_match == "YES"
    assert result.time_zone_match == "NO"
    assert result.sheets_data_reads == 0
    assert result.sheets_write_attempts == 0
    assert "prewrite_cells" not in fake.calls


def test_state_machine_missing_time_zone_is_insufficient_evidence_without_write():
    fake = _FakeTransport(time_zone=None)
    result = driver._run_google_state_machine(_SPEC, fake)
    assert result.classification == driver.CLASS_H
    assert result.locale_match == "YES"
    assert result.time_zone_match == "NOT_VERIFIED"
    assert result.sheets_data_reads == 0
    assert result.sheets_write_attempts == 0


def test_state_machine_missing_locale_is_insufficient_evidence_without_write():
    fake = _FakeTransport(locale=None)
    result = driver._run_google_state_machine(_SPEC, fake)
    assert result.classification == driver.CLASS_H
    assert result.locale_match == "NOT_VERIFIED"
    assert result.sheets_write_attempts == 0


def test_drive_preflight_requires_sheet_type_untrashed_and_modified_time():
    fake = _FakeTransport(drive_valid=False)
    result = driver._run_google_state_machine(_SPEC, fake)
    assert result.classification == driver.CLASS_H
    assert result.drive_reads == 1
    assert result.sheets_metadata_reads == 0
    assert result.sheets_write_attempts == 0


@pytest.mark.parametrize(
    "evidence",
    [
        {"drive_id_present": False},
        {"drive_id_matches": False},
        {"drive_mime_type_present": False},
        {"drive_is_google_sheet": False},
        {"drive_trashed_present": False},
        {"drive_not_trashed": False},
        {"drive_modified_time_present": False},
    ],
)
def test_drive_preflight_rejects_missing_or_mismatched_required_evidence(evidence):
    fake = _FakeTransport(**evidence)
    result = driver._run_google_state_machine(_SPEC, fake)
    assert result.classification == driver.CLASS_H
    assert result.drive_reads == 1
    assert result.sheets_metadata_reads == 0
    assert result.sheets_data_reads == 0
    assert result.sheets_write_attempts == 0
    assert "workbook_metadata" not in fake.calls


def test_drive_preflight_accepts_matching_exact_id_and_valid_metadata():
    fake = _FakeTransport(drive_id_present=True, drive_id_matches=True)
    result = driver._run_google_state_machine(_SPEC, fake)
    assert result.classification == driver.CLASS_A
    assert result.drive_reads == 2
    assert result.sheets_metadata_reads == 1
    assert result.sheets_write_attempts == 1


def test_state_machine_o1_mismatch_has_zero_writes():
    fake = _FakeTransport(pre=_snapshots(o1_ok=False))
    result = driver._run_google_state_machine(_SPEC, fake)
    assert result.classification == driver.CLASS_F
    assert result.o1_precondition == "DRIFT"
    assert result.sheets_write_attempts == 0
    assert fake.writes == 0


def test_state_machine_authored_p1_has_zero_writes_and_safe_subreason():
    fake = _FakeTransport(pre=_snapshots(p1="authored"))
    result = driver._run_google_state_machine(_SPEC, fake)
    assert result.classification == driver.CLASS_F
    assert result.p1_precondition == "AUTHORED_STATE_VIOLATION"
    assert result.precondition_subreason == "P1_AUTHORED_STATE_VIOLATION"
    assert result.sheets_write_attempts == 0


def test_state_machine_already_canonical_p1_has_zero_writes():
    fake = _FakeTransport(pre=_snapshots(p1="canonical"))
    result = driver._run_google_state_machine(_SPEC, fake)
    assert result.classification == driver.CLASS_C
    assert result.sheets_write_attempts == 0
    assert result.sheets_data_reads == 1


def test_happy_fake_path_attempts_exactly_one_write_and_proves_restoration():
    fake = _FakeTransport()
    result = driver._run_google_state_machine(_SPEC, fake)
    assert result.classification == driver.CLASS_A
    assert result.sheets_write_attempts == 1
    assert result.sheets_writes_succeeded == 1
    assert result.p1_writes == 0
    assert result.retries == 0
    assert result.restoration_proven
    assert fake.calls.count("write_o1") == 1
    assert fake.calls.count("postwrite_cells") == 1
    assert result.sheets_data_reads == 2
    assert fake.calls.count("drive_metadata") == 2
    assert result.drive_reads == 2


def test_postwrite_without_spill_classifies_b():
    fake = _FakeTransport(post=_snapshots(p1="blank"))
    result = driver._run_google_state_machine(_SPEC, fake)
    assert result.classification == driver.CLASS_B
    assert result.sheets_write_attempts == 1
    assert result.sheets_writes_succeeded == 1
    assert fake.calls.count("postwrite_cells") == 1
    assert result.sheets_data_reads == 2
    assert fake.calls.count("drive_metadata") == 2
    assert result.drive_reads == 2
    assert not result.restoration_proven


def test_postwrite_o1_contract_violation_classifies_d():
    fake = _FakeTransport(post=_snapshots(o1_ok=False, p1="canonical"))
    result = driver._run_google_state_machine(_SPEC, fake)
    assert result.classification == driver.CLASS_D
    assert result.sheets_write_attempts == 1
    assert result.sheets_writes_succeeded == 1
    assert fake.calls.count("postwrite_cells") == 1
    assert result.sheets_data_reads == 2
    assert fake.calls.count("drive_metadata") == 2
    assert result.drive_reads == 2
    assert result.o1_post_state == "CONTRACT_VIOLATION"


def test_failed_write_is_terminal_and_consumes_mutation_budget(monkeypatch):
    fake = _FakeTransport(write_fails=True)
    result, transport, events, _ = _run_fake(monkeypatch, fake_transport=fake)
    assert result.local_bootstrap == "PASS"
    assert result.fixture_identity_validated is True
    assert result.privacy_barrier == "PASS"
    assert result.config_bridge == "PASS"
    assert result.auth_status == "PASS"
    assert "config" in events
    assert "auth" in events
    assert result.classification == driver.CLASS_G
    assert result.sheets_write_attempts == 1
    assert result.sheets_writes_succeeded == 0
    assert result.retries == 0
    assert result.write_executed is True
    assert result.p1_writes == 0
    assert result.rollback_executed is False
    assert result.drive_reads == 1
    assert result.sheets_data_reads == 1
    assert transport.calls.count("prewrite_cells") == 1
    assert transport.calls.count("write_o1") == 1
    assert transport.calls.count("postwrite_cells") == 0
    assert transport.calls.count("drive_metadata") == 1
    assert transport.writes == 1


def test_safe_report_contains_no_dummy_id_formula_or_api_url(monkeypatch, tmp_path):
    env = {driver.FIXTURE_ID_ENV: _DUMMY_ID}
    fake = _FakeTransport()
    path = tmp_path / "config.toml"
    path.write_text(_fixture_toml(), encoding="utf-8")
    result, _, _, _ = _run_fake(monkeypatch, fake_transport=fake, environment=env, config_path=path)
    rendered = json.dumps(result.as_safe_dict(), ensure_ascii=False, sort_keys=True)
    for forbidden in (
        _DUMMY_ID,
        _DUMMY_TOKEN,
        _DUMMY_CONFIG,
        _MODIFIED_BEFORE,
        "=SEQUENCE(1,2)",
        "https://",
        "Authorization",
    ):
        assert forbidden not in rendered
    assert result.public_continuations == 0
    assert result.drive_search_list == 0
    assert result.rollback_executed is False


def test_result_does_not_expose_raw_google_formula_or_unexpected_values():
    fake = _FakeTransport(post=_snapshots(p1="wrong-display"))
    result = driver._run_google_state_machine(_SPEC, fake)
    assert result.p1_post_state == "NOT_RESTORED"
    rendered = json.dumps(result.as_safe_dict(), ensure_ascii=False)
    assert "=SEQUENCE(1,2)" not in rendered
    assert "unexpected" not in rendered


def test_driver_has_no_full_traversal_secondary_driver_or_google_subprocess_path():
    source = Path(driver.__file__).read_text(encoding="utf-8")
    assert ".rglob(" not in source
    assert ".glob(" not in source
    assert "nextPageToken" not in source
    assert "files.list" not in source
    assert "subprocess" not in source
    assert "tempfile" not in source


def test_public_bootstrap_server_runtime_cannot_reach_validation_write_driver():
    public_paths = (
        Path(server.__file__),
        Path(bootstrap.__file__),
        Path(runtime.__file__),
        Path("src/google_workspace_admin/content/readers.py"),
        Path("src/google_workspace_admin/content/google_sheets_adapter.py"),
    )
    for path in public_paths:
        source = path.read_text(encoding="utf-8")
        assert "gsheets_controlled_write" not in source
        assert "run_gsheets_spill_restoration_controlled_v1" not in source


def test_public_bootstrap_selects_only_public_builder_with_spy(monkeypatch):
    selected = []
    internal = []
    monkeypatch.setattr(bootstrap, "load_content_config", lambda: _DUMMY_CONFIG)
    monkeypatch.setattr(
        bootstrap,
        "build_content_token_provider",
        lambda config: selected.append(("public", config)) or "public-provider",
    )
    monkeypatch.setattr(
        production,
        "_build_controlled_validation_token_provider",
        lambda *_a, **_k: internal.append("internal") or "write-provider",
    )
    assert bootstrap._build_token_provider() == "public-provider"
    assert selected == [("public", _DUMMY_CONFIG)]
    assert internal == []
    assert "_build_controlled_validation_token_provider" not in Path(server.__file__).read_text(encoding="utf-8")
    assert "_build_controlled_validation_token_provider" not in Path(runtime.__file__).read_text(encoding="utf-8")


def test_operation_registry_is_closed_and_exact():
    assert transport_module.OPERATION_REGISTRY == frozenset(
        {
            "drive.read_exact_file_metadata",
            "drive.read_exact_file_metadata_postwrite",
            "sheets.read_workbook_metadata",
            "sheets.read_o1_p1_prewrite",
            "sheets.batch_update_o1_once",
            "sheets.read_o1_p1_postwrite",
        }
    )
    assert transport_module.CLOSED_HTTP_METHODS == {"GET", "POST"}
    assert transport_module.CLOSED_HTTP_HOSTS == {"www.googleapis.com", "sheets.googleapis.com"}


def test_drive_transport_is_exact_id_metadata_only():
    result = transport_module.validate_http_boundary(
        method="GET",
        url=f"https://www.googleapis.com/drive/v3/files/{_DUMMY_ID}",
        fixture_id=_DUMMY_ID,
    )
    assert result == "drive.read_exact_file_metadata"
    for path in ("/drive/v3/files", f"/drive/v3/files/{_DUMMY_ID}/permissions", "/drive/v3/files/fileId"):
        with pytest.raises(transport_module.ControlledTransportError):
            transport_module.validate_http_boundary(
                method="GET",
                url=f"https://www.googleapis.com{path}",
                fixture_id=_DUMMY_ID,
            )


def test_drive_search_and_list_are_impossible():
    for method, path in (
        ("GET", "/drive/v3/files"),
        ("GET", "/drive/v3/files?q=trashed%3Dfalse"),
        ("POST", f"/drive/v3/files/{_DUMMY_ID}"),
    ):
        with pytest.raises(transport_module.ControlledTransportError):
            transport_module.validate_http_boundary(
                method=method,
                url=f"https://www.googleapis.com{path}",
                fixture_id=_DUMMY_ID,
            )


def test_closed_boundary_rejects_wrong_host_method_endpoint_id_and_query():
    candidates = (
        ("GET", f"https://example.com/drive/v3/files/{_DUMMY_ID}"),
        ("PUT", f"https://www.googleapis.com/drive/v3/files/{_DUMMY_ID}"),
        ("POST", f"https://sheets.googleapis.com/v4/spreadsheets/{_DUMMY_ID}/values/O1"),
        ("GET", "https://sheets.googleapis.com/v4/spreadsheets/other-file"),
        ("GET", f"https://www.googleapis.com/drive/v3/files/{_DUMMY_ID}?alt=media"),
    )
    for method, url in candidates:
        with pytest.raises(transport_module.ControlledTransportError):
            transport_module.validate_http_boundary(method=method, url=url, fixture_id=_DUMMY_ID)


def _http_transport(handler):
    return httpx.MockTransport(handler)


def _workbook_payload():
    return {
        "properties": {"locale": "pt_BR", "timeZone": "America/Sao_Paulo"},
        "sheets": [{"properties": {"sheetId": 42, "index": 0, "title": "Validation"}}],
    }


def _cell_payload(*, p1_present=False, p1_value="2"):
    values = [
        {
            "userEnteredValue": {"formulaValue": "=SEQUENCE(1,2)"},
            "formattedValue": "1",
            "effectiveValue": {"numberValue": 1},
        }
    ]
    if p1_present:
        values.append({"formattedValue": p1_value, "effectiveValue": {"numberValue": int(p1_value)}})
    return {
        "sheets": [
            {
                "properties": {"sheetId": 42},
                "data": [
                    {"startRow": 0, "startColumn": 14, "rowData": [{"values": values}]}
                ],
            }
        ]
    }


def _drive_payload():
    return {
        "id": _DUMMY_ID,
        "mimeType": transport_module.GOOGLE_SHEETS_MIME,
        "trashed": False,
        "modifiedTime": _MODIFIED_BEFORE,
    }


def _transport_for(handler):
    return transport_module.ControlledSheetsTransport(
        fixture_identity=driver._ValidatedFixtureIdentity(_DUMMY_ID),
        access_token=_DUMMY_TOKEN,
        formula=_SPEC.cell("O1").formula.value,
        expected_o1_display=_SPEC.expected_component("O1", "CELL_DISPLAY"),
        expected_p1_display=_SPEC.expected_component("P1", "CELL_DISPLAY"),
        http_transport=_http_transport(handler),
    )


def test_transport_reads_only_bounded_workbook_metadata_and_o1_p1():
    seen = []

    def handler(request):
        seen.append(request)
        if request.url.params.get("ranges"):
            return httpx.Response(200, request=request, json=_cell_payload())
        return httpx.Response(200, request=request, json=_workbook_payload())

    transport = _transport_for(handler)
    workbook = transport.read_workbook_metadata()
    cells = transport.read_o1_p1_prewrite()
    assert workbook.locale == "pt_BR"
    assert workbook.time_zone == "America/Sao_Paulo"
    assert workbook.ordinal_zero_sheet_id == 42
    assert cells[0].canonical_formula_match
    assert len(seen) == 2
    assert all(request.method == "GET" for request in seen)
    assert all(request.url.path == f"/v4/spreadsheets/{_DUMMY_ID}" for request in seen)
    assert seen[0].url.params["fields"] == "properties(locale,timeZone),sheets(properties(sheetId,index,title))"
    assert seen[1].url.params["ranges"] == "'Validation'!O1:P1"
    assert "O1:P1" in seen[1].url.params["ranges"]
    assert transport.sheets_writes_attempted == 0
    transport.close()


def test_transport_range_api_has_no_arbitrary_range_or_id_parameters():
    assert tuple(inspect.signature(transport_module.ControlledSheetsTransport.read_o1_p1_prewrite).parameters) == ("self",)
    assert tuple(inspect.signature(transport_module.ControlledSheetsTransport.read_o1_p1_postwrite).parameters) == ("self",)
    assert tuple(inspect.signature(transport_module.ControlledSheetsTransport.write_o1_once).parameters) == ("self",)
    constructor_parameters = inspect.signature(transport_module.ControlledSheetsTransport).parameters
    assert "fixture_id" not in constructor_parameters
    assert "fixture_identity" in constructor_parameters
    assert not hasattr(transport_module.ControlledSheetsTransport, "read_range")
    assert not hasattr(transport_module.ControlledSheetsTransport, "write_p1")


def test_transport_exact_id_is_bound_to_every_request():
    seen = []

    def handler(request):
        seen.append(request)
        if request.url.host == "www.googleapis.com":
            return httpx.Response(
                200,
                request=request,
                json={"id": _DUMMY_ID, "mimeType": transport_module.GOOGLE_SHEETS_MIME, "trashed": False, "modifiedTime": _MODIFIED_BEFORE},
            )
        return httpx.Response(200, request=request, json=_workbook_payload())

    transport = _transport_for(handler)
    transport.read_drive_metadata()
    transport.read_workbook_metadata()
    assert len(seen) == 2
    assert all(_DUMMY_ID in request.url.path for request in seen)
    transport.close()


def test_drive_metadata_request_is_exact_id_get_with_closed_shared_drive_projection():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, request=request, json=_drive_payload())

    transport = _transport_for(handler)
    metadata = transport.read_drive_metadata()
    request = seen[0]
    params = dict(request.url.params)
    fields = params["fields"].split(",")
    assert request.method == "GET"
    assert request.url.host == "www.googleapis.com"
    assert request.url.path.endswith("/" + _DUMMY_ID)
    assert transport_module.validate_http_boundary(
        method=request.method,
        url=str(request.url.copy_with(query=None)),
        fixture_id=_DUMMY_ID,
    ) == "drive.read_exact_file_metadata"
    assert fields == ["id", "mimeType", "trashed", "modifiedTime"]
    assert params["supportsAllDrives"] == "true"
    assert set(params) == {"fields", "supportsAllDrives"}
    assert not ({"q", "corpora", "driveId", "includeItemsFromAllDrives"} & set(params))
    assert metadata.id_present is True
    assert metadata.id_matches_requested_exact_id is True
    assert metadata.mime_type_present is True
    assert metadata.is_google_sheet is True
    assert metadata.trashed_present is True
    assert metadata.not_trashed is True
    assert metadata.modified_time_present is True
    rendered = repr(metadata)
    assert _DUMMY_ID not in rendered
    assert _MODIFIED_BEFORE not in rendered
    transport.close()


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("mismatched_id", (True, False, True, True, True, True, True)),
        ("absent_id", (False, False, True, True, True, True, True)),
        ("absent_mime", (True, True, False, False, True, True, True)),
        ("wrong_mime", (True, True, True, False, True, True, True)),
        ("absent_trashed", (True, True, True, True, False, False, True)),
        ("trashed_true", (True, True, True, True, True, False, True)),
        ("absent_modified_time", (True, True, True, True, True, True, False)),
        ("empty_modified_time", (True, True, True, True, True, True, False)),
        ("invalid_modified_time", (True, True, True, True, True, True, False)),
    ],
)
def test_drive_metadata_parser_fails_closed_for_incomplete_or_invalid_evidence(
    mutation, expected
):
    payload = _drive_payload()
    if mutation == "mismatched_id":
        payload["id"] = "other-synthetic-file-id"
    elif mutation == "absent_id":
        payload.pop("id")
    elif mutation == "absent_mime":
        payload.pop("mimeType")
    elif mutation == "wrong_mime":
        payload["mimeType"] = "text/plain"
    elif mutation == "absent_trashed":
        payload.pop("trashed")
    elif mutation == "trashed_true":
        payload["trashed"] = True
    elif mutation == "absent_modified_time":
        payload.pop("modifiedTime")
    elif mutation == "empty_modified_time":
        payload["modifiedTime"] = ""
    elif mutation == "invalid_modified_time":
        payload["modifiedTime"] = "not-a-timestamp"
    metadata = transport_module._parse_drive_metadata(payload, _DUMMY_ID)
    actual = (
        metadata.id_present,
        metadata.id_matches_requested_exact_id,
        metadata.mime_type_present,
        metadata.is_google_sheet,
        metadata.trashed_present,
        metadata.not_trashed,
        metadata.modified_time_present,
    )
    assert actual == expected
    assert _DUMMY_ID not in repr(metadata)


def test_transport_requires_opaque_identity_binding_not_an_arbitrary_id():
    with pytest.raises(TypeError):
        transport_module.ControlledSheetsTransport(
            fixture_id=_DUMMY_ID,
            access_token=_DUMMY_TOKEN,
            formula="=SEQUENCE(1,2)",
            expected_o1_display="1",
            expected_p1_display="2",
        )
    with pytest.raises(transport_module.ControlledTransportError):
        transport_module.ControlledSheetsTransport(
            fixture_identity=_DUMMY_ID,
            access_token=_DUMMY_TOKEN,
            formula="=SEQUENCE(1,2)",
            expected_o1_display="1",
            expected_p1_display="2",
        )


def test_transport_treats_any_p1_user_entered_value_field_as_authored():
    snapshot = transport_module._cell_snapshot(
        {"userEnteredValue": {}, "formattedValue": "2"},
        None,
        "2",
    )
    assert snapshot.cell_data_present
    assert snapshot.user_entered_value_present
    assert driver._snapshot_has_authored_p1(snapshot)


def test_transport_emits_exactly_one_batch_update_o1_request():
    seen = []

    def handler(request):
        seen.append(request)
        if request.method == "POST":
            return httpx.Response(200, request=request, json={})
        if request.url.params.get("fields", "").startswith("properties(locale,timeZone)"):
            return httpx.Response(200, request=request, json=_workbook_payload())
        return httpx.Response(200, request=request, json={"sheets": []})

    transport = _transport_for(handler)
    transport.read_workbook_metadata()
    transport.write_o1_once()
    posts = [request for request in seen if request.method == "POST"]
    assert len(posts) == 1
    assert posts[0].url.host == "sheets.googleapis.com"
    assert posts[0].url.path == f"/v4/spreadsheets/{_DUMMY_ID}:batchUpdate"
    assert json.loads(posts[0].content) == {
        "requests": [
            {
                "updateCells": {
                    "range": {
                        "sheetId": 42,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                        "startColumnIndex": 14,
                        "endColumnIndex": 15,
                    },
                    "rows": [{"values": [{"userEnteredValue": {"formulaValue": "=SEQUENCE(1,2)"}}]}],
                    "fields": "userEnteredValue",
                }
            }
        ]
    }
    transport.close()


def test_transport_field_mask_formula_and_no_arbitrary_cell_data():
    payload = {
        "requests": [
            {
                "updateCells": {
                    "range": {"sheetId": 42, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 14, "endColumnIndex": 15},
                    "rows": [{"values": [{"userEnteredValue": {"formulaValue": _SPEC.cell("O1").formula.value}}]}],
                    "fields": "userEnteredValue",
                }
            }
        ]
    }
    assert transport_module._is_exact_o1_update(payload)
    assert payload["requests"][0]["updateCells"]["fields"] == "userEnteredValue"
    assert payload["requests"][0]["updateCells"]["rows"][0]["values"][0]["userEnteredValue"]["formulaValue"] == _SPEC.cell("O1").formula.value
    for extra in ({"note": "x"}, {"userEnteredFormat": {"numberFormat": {"type": "NUMBER"}}}, {"textFormatRuns": []}):
        invalid = json.loads(json.dumps(payload))
        invalid["requests"][0]["updateCells"]["rows"][0]["values"][0].update(extra)
        assert not transport_module._is_exact_o1_update(invalid)


@pytest.mark.parametrize("column", [15, 10, 11])
def test_transport_rejects_p1_k1_and_l1_mutation_targets(column):
    payload = {
        "requests": [
            {
                "updateCells": {
                    "range": {"sheetId": 42, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": column, "endColumnIndex": column + 1},
                    "rows": [{"values": [{"userEnteredValue": {"formulaValue": "=SEQUENCE(1,2)"}}]}],
                    "fields": "userEnteredValue",
                }
            }
        ]
    }
    assert not transport_module._is_exact_o1_update(payload)


def test_transport_rejects_locale_formatting_multiple_requests_and_arbitrary_body():
    base = {
        "requests": [
            {
                "updateCells": {
                    "range": {"sheetId": 42, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 14, "endColumnIndex": 15},
                    "rows": [{"values": [{"userEnteredValue": {"formulaValue": "=SEQUENCE(1,2)"}}]}],
                    "fields": "userEnteredValue",
                }
            }
        ]
    }
    variants = []
    two = json.loads(json.dumps(base))
    two["requests"].append(two["requests"][0])
    variants.append(two)
    locale = json.loads(json.dumps(base))
    locale["requests"][0]["updateCells"]["range"]["sheetId"] = 42
    locale["requests"][0]["updateCells"]["fields"] = "userEnteredValue,userEnteredFormat"
    variants.append(locale)
    format_request = json.loads(json.dumps(base))
    format_request["requests"][0]["updateCells"]["rows"][0]["values"][0]["userEnteredFormat"] = {"numberFormat": {"type": "NUMBER"}}
    variants.append(format_request)
    for payload in variants:
        assert not transport_module._is_exact_o1_update(payload)
    with pytest.raises(transport_module.ControlledTransportError):
        transport_module.validate_http_boundary(
            method="POST",
            url=f"https://sheets.googleapis.com/v4/spreadsheets/{_DUMMY_ID}:batchUpdate",
            fixture_id=_DUMMY_ID,
            sheet_title="Validation",
            body=b"x" * (transport_module.MAX_REQUEST_BODY_BYTES + 1),
        )


def test_transport_binds_batch_update_to_metadata_sheet_id_and_formula():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, request=request, json=_workbook_payload())

    transport = _transport_for(handler)
    transport.read_workbook_metadata()
    arbitrary = json.dumps(
        {
            "requests": [
                {
                    "updateCells": {
                        "range": {"sheetId": 999, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 14, "endColumnIndex": 15},
                        "rows": [{"values": [{"userEnteredValue": {"formulaValue": "=1"}}]}],
                        "fields": "userEnteredValue",
                    }
                }
            ]
        }
    ).encode()
    with pytest.raises(transport_module.ControlledTransportError):
        transport._send_post_o1_update(arbitrary, object())
    assert len(seen) == 1
    transport.close()


def test_failed_mutation_consumes_transport_budget_and_second_attempt_is_local():
    calls = []

    def handler(request):
        calls.append(request)
        if request.method == "POST":
            return httpx.Response(500, request=request, content=b"private-response-marker")
        return httpx.Response(200, request=request, json=_workbook_payload())

    transport = _transport_for(handler)
    transport.read_workbook_metadata()
    with pytest.raises(transport_module.ControlledTransportError) as first:
        transport.write_o1_once()
    assert str(first.value) == "HTTP_FAILURE"
    assert transport.write_budget_remaining == 0
    assert transport.sheets_writes_attempted == 1
    assert transport.sheets_writes_succeeded == 0
    with pytest.raises(transport_module.ControlledTransportError) as second:
        transport.write_o1_once()
    assert str(second.value) == "WRITE_BUDGET_EXHAUSTED"
    assert transport.sheets_writes_attempted == 1
    assert transport.p1_writes == 0
    assert transport.retries == 0
    assert len([request for request in calls if request.method == "POST"]) == 1
    transport.close()


def test_private_http_primitive_cannot_bypass_closed_boundary_or_write_permit():
    seen = []

    def handler(request):
        seen.append(request)
        if request.url.path.endswith(":batchUpdate"):
            return httpx.Response(200, request=request, json={})
        return httpx.Response(200, request=request, json=_workbook_payload())

    transport = _transport_for(handler)
    transport.read_workbook_metadata()
    transport.write_o1_once()
    posts_before = len([request for request in seen if request.method == "POST"])
    with pytest.raises(transport_module.ControlledTransportError):
        transport._perform_request(
            "POST",
            f"https://sheets.googleapis.com/v4/spreadsheets/{_DUMMY_ID}:batchUpdate",
            params=None,
            body=b'{"requests":[]}',
        )
    with pytest.raises(transport_module.ControlledTransportError):
        transport._perform_request(
            "GET",
            f"https://www.googleapis.com/drive/v3/files",
            params={"q": "trashed=false"},
            body=None,
        )
    assert len([request for request in seen if request.method == "POST"]) == posts_before == 1
    transport.close()


def test_transport_bounded_response_redirect_timeout_and_no_retry(caplog):
    seen = []

    def large(request):
        seen.append(request)
        return httpx.Response(200, request=request, content=b"x" * (transport_module.MAX_RESPONSE_BODY_BYTES + 1))

    transport = _transport_for(large)
    with pytest.raises(transport_module.ControlledTransportError) as error:
        transport.read_drive_metadata()
    assert str(error.value) == "RESPONSE_TOO_LARGE"
    assert len(seen) == 1
    transport.close()

    redirects = []
    def redirect(request):
        redirects.append(request)
        return httpx.Response(302, request=request, headers={"Location": "https://example.com"})
    transport = _transport_for(redirect)
    with pytest.raises(transport_module.ControlledTransportError) as error:
        transport.read_drive_metadata()
    assert str(error.value) == "HTTP_FAILURE"
    assert len(redirects) == 1
    transport.close()

    failures = []
    def broken(request):
        failures.append(request)
        raise httpx.ConnectError("private network exception", request=request)
    transport = _transport_for(broken)
    with pytest.raises(transport_module.ControlledTransportError) as error:
        transport.read_drive_metadata()
    assert str(error.value) == "TRANSPORT_FAILURE"
    assert "private network exception" not in str(error.value)
    assert len(failures) == 1
    assert transport.retries == 0
    assert "private network exception" not in caplog.text
    transport.close()


def test_transport_timeout_is_finite_and_redirects_disabled():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(
            200,
            request=request,
            json=_drive_payload(),
        )

    transport = _transport_for(handler)
    transport.read_drive_metadata()
    extensions = seen[0].extensions["timeout"]
    assert all(value is not None and value <= transport_module.HTTP_TIMEOUT_SECONDS for value in extensions.values())
    assert transport._client.follow_redirects is False
    transport.close()


def test_transport_never_logs_request_response_values_or_urls(caplog):
    marker = "unexpected-private-cell-marker"

    def handler(request):
        return httpx.Response(
            200,
            request=request,
            json={**_drive_payload(), "mimeType": marker},
        )

    transport = _transport_for(handler)
    metadata = transport.read_drive_metadata()
    assert not metadata.is_google_sheet
    assert marker not in caplog.text
    assert _DUMMY_ID not in caplog.text
    assert _DUMMY_TOKEN not in caplog.text
    assert _MODIFIED_BEFORE not in caplog.text
    assert "Authorization" not in caplog.text
    assert "https://" not in caplog.text
    transport.close()


def test_driver_uses_identity_guard_and_safe_reference_exactly():
    assert driver.APPROVED_FIXTURE_ID_SHA256 == "88935b60192fd0370dce2bde8658e4d5ded2b172cbc75d5ecd64528714162711"
    assert driver.SAFE_FIXTURE_ID_REFERENCE == "…qWp-Js"
    assert driver._identity_guard_shape_valid()


def test_public_and_internal_scope_parameters_stay_closed():
    assert tuple(inspect.signature(production._build_controlled_validation_token_provider).parameters) == (
        "config", "credentials_loader", "client_factory"
    )
    assert tuple(inspect.signature(driver.execute_controlled_mode).parameters) == (
        "environment", "ports", "config_path"
    )
    assert "scope" not in inspect.signature(production._build_controlled_validation_token_provider).parameters
    assert "subject" not in inspect.signature(production._build_controlled_validation_token_provider).parameters
    assert "target" not in inspect.signature(driver.execute_controlled_mode).parameters


def test_default_driver_reuses_audited_private_provider_without_copying_auth_logic():
    ports = driver._default_execution_ports()
    assert ports.build_token_provider is production._build_controlled_validation_token_provider
    validation_source = "\n".join(
        Path(path).read_text(encoding="utf-8")
        for path in (driver.__file__, transport_module.__file__)
    )
    assert "build_jwt_claims" not in validation_source
    assert "_build_controlled_validation_jwt_claims" not in validation_source
    assert "iamcredentials.googleapis.com" not in validation_source
    assert "oauth2.googleapis.com/token" not in validation_source
    assert 'data={"grant_type"' not in validation_source


def test_preflight_no_auth_network_fixture_id_or_http_client(monkeypatch):
    calls = []
    monkeypatch.setattr(production, "_build_controlled_validation_token_provider", lambda *_a, **_k: calls.append("auth"))
    monkeypatch.setattr(httpx, "Client", lambda *_a, **_k: calls.append("http"))
    monkeypatch.setattr(driver, "_read_config_values", lambda *_a, **_k: calls.append("config"))
    driver.local_preflight()
    assert calls == []
