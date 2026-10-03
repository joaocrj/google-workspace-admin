"""Repo-local offline-first driver for the controlled O1 spill test.

The public MCP does not import this module. ``--execute-controlled-test`` is
reserved for a separately authorized future run and requires a process-local
fixture ID that matches the fixed identity guard before config or auth access.
"""

from __future__ import annotations

import argparse
import ast
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from datetime import datetime
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
import re
import sys
import tomllib
from typing import Any, Callable, MutableMapping


DRIVER_VERSION = "2.1"
FIXTURE_ID_ENV = "GSHEETS_VALIDATION_V1_FILE_ID"
APPROVED_FIXTURE_ID_SHA256 = (
    "88935b60192fd0370dce2bde8658e4d5ded2b172cbc75d5ecd64528714162711"
)
SAFE_FIXTURE_ID_REFERENCE = "…qWp-Js"
INITIAL_SHEETS_WRITE_BUDGET = 1

CONTENT_ENV_KEYS = (
    "GOOGLE_WORKSPACE_CONTENT_PROJECT_ID",
    "GOOGLE_WORKSPACE_CONTENT_SERVICE_ACCOUNT",
    "GOOGLE_WORKSPACE_CONTENT_SUBJECT",
    "GOOGLE_WORKSPACE_CONTENT_CUSTOMER_ID",
    "GOOGLE_WORKSPACE_CONTENT_DOMAIN",
)
_CONTENT_HMAC_ENV_KEY = "GOOGLE_WORKSPACE_CONTENT_PUBLIC_FILE_REF_HMAC_KEY_B64"
_GOOGLE_APPLICATION_CREDENTIALS = "GOOGLE_APPLICATION_CREDENTIALS"
_IDENTITY_SHA_RE = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
_SAFE_REFERENCE_RE = re.compile(r"^…[A-Za-z0-9_-]{2,32}$", re.ASCII)

CLASS_A = "A — SAME_FORMULA_REWRITE_RESTORED_SPILL"
CLASS_B = "B — SAME_FORMULA_REWRITE_DID_NOT_RESTORE_SPILL"
CLASS_C = "C — P1_ALREADY_RESTORED"
CLASS_D = "D — O1_POSTWRITE_CONTRACT_VIOLATION"
CLASS_E = "E — FIXTURE_LOCALE_MISMATCH"
CLASS_F = "F — PRECONDITION_DRIFT"
CLASS_G = "G — WRITE_FAILURE"
CLASS_H = "H — INSUFFICIENT_EVIDENCE"
CLASS_I = "I — FIXTURE_TIME_ZONE_MISMATCH"


class _LocalDriverError(RuntimeError):
    __slots__ = ("classification",)

    def __init__(self, classification: str) -> None:
        allowed = {
            "LOCAL_BOOTSTRAP_FAILURE",
            "FIXTURE_ID_INPUT_MISSING",
            "FIXTURE_ID_IDENTITY_MISMATCH",
            "CONFIG_BRIDGE_FAILURE",
            "AUTH_FAILURE",
        }
        self.classification = (
            classification if classification in allowed else "LOCAL_BOOTSTRAP_FAILURE"
        )
        super().__init__(self.classification)


@dataclass(frozen=True, slots=True)
class SafeResult:
    driver_version: str = DRIVER_VERSION
    local_bootstrap: str = "PASS"
    spec_loaded: bool = True
    fixture_identity_validated: bool = False
    privacy_barrier: str = "NOT_REACHED"
    config_bridge: str = "NOT_REACHED"
    hmac_copied: str = "NO"
    auth_status: str = "NOT_REACHED"
    drive_reads: int = 0
    sheets_metadata_reads: int = 0
    sheets_data_reads: int = 0
    sheets_write_attempts: int = 0
    sheets_writes_succeeded: int = 0
    p1_writes: int = 0
    retries: int = 0
    drive_search_list: int = 0
    public_continuations: int = 0
    locale_match: str = "NOT_CHECKED"
    time_zone_match: str = "NOT_CHECKED"
    o1_precondition: str = "NOT_CHECKED"
    p1_precondition: str = "NOT_CHECKED"
    precondition_subreason: str = "NONE"
    write_executed: bool = False
    o1_post_state: str = "NOT_CHECKED"
    p1_post_state: str = "NOT_CHECKED"
    modified_time_integrity: str = "NOT_CHECKED"
    classification: str = "NOT_REACHED"
    restoration_proven: bool = False
    rollback_executed: bool = False
    fixture_id_sha256_guard: str = APPROVED_FIXTURE_ID_SHA256
    safe_fixture_reference: str = SAFE_FIXTURE_ID_REFERENCE

    def as_safe_dict(self) -> dict[str, Any]:
        """Return deterministic fields only; never includes IDs or API data."""

        return asdict(self)


@dataclass(frozen=True, slots=True)
class ExecutionPorts:
    load_config: Callable[[], object]
    build_token_provider: Callable[[object], object]
    build_transport: Callable[[object, str, object], object]


@dataclass(frozen=True, slots=True)
class _ValidatedFixtureIdentity:
    value: str

    def __repr__(self) -> str:
        return "<_ValidatedFixtureIdentity redacted>"


class _MutationBudget:
    __slots__ = ("remaining", "attempts", "succeeded")

    def __init__(self) -> None:
        self.remaining = INITIAL_SHEETS_WRITE_BUDGET
        self.attempts = 0
        self.succeeded = 0

    def consume_before_attempt(self) -> None:
        if self.remaining != 1 or self.attempts != 0:
            raise _LocalDriverError("LOCAL_BOOTSTRAP_FAILURE")
        self.remaining = 0
        self.attempts = 1


def _repo_root_from_file(script_file: str | Path = __file__) -> Path:
    script = Path(script_file).resolve()
    root = script.parents[2]
    expected_script = root / "validation" / "fixtures" / Path(script_file).name
    required = (
        root / "pyproject.toml",
        root / "docs" / "00_AGENT_GUIDE.md",
        root / "validation" / "fixtures" / "fixture_contract.py",
        root / "validation" / "fixtures" / "gsheets_validation_v1.json",
    )
    if script != expected_script or any(not path.is_file() for path in required):
        raise _LocalDriverError("LOCAL_BOOTSTRAP_FAILURE")
    return root


def _load_canonical_spec(root: Path) -> object:
    root = root.resolve()
    root_text = str(root)
    src_text = str((root / "src").resolve())
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    if src_text not in sys.path:
        sys.path.insert(0, src_text)
    try:
        from validation.fixtures.fixture_contract import load_fixture_spec

        spec = load_fixture_spec()
    except Exception:
        raise _LocalDriverError("LOCAL_BOOTSTRAP_FAILURE") from None
    expected_path = (root / "validation" / "fixtures" / "gsheets_validation_v1.json").resolve()
    if getattr(spec, "path", None) != expected_path:
        raise _LocalDriverError("LOCAL_BOOTSTRAP_FAILURE")
    if (
        getattr(spec, "fixture_alias", None) != "GSHEETS_VALIDATION_V1"
        or getattr(spec, "locale", None) != "pt_BR"
        or getattr(spec, "time_zone", None) != "America/Sao_Paulo"
        or getattr(spec, "target_sheet_ordinal", None) != 0
        or not _valid_o1_p1_contract(spec)
    ):
        raise _LocalDriverError("LOCAL_BOOTSTRAP_FAILURE")
    return spec


def _valid_o1_p1_contract(spec: object) -> bool:
    try:
        o1 = spec.cell("O1")  # type: ignore[attr-defined]
        p1 = spec.cell("P1")  # type: ignore[attr-defined]
        return (
            o1.authored_state.value == "AUTHORED"
            and o1.formula.value == "=SEQUENCE(1,2)"
            and spec.expected_component("O1", "CELL_DISPLAY") == "1"  # type: ignore[attr-defined]
            and p1.authored_state.value == "UNAUTHORED"
            and p1.user_entered_value.policy.value == "PROHIBITED"
            and p1.formula.policy.value == "PROHIBITED"
            and spec.expected_component("P1", "CELL_DISPLAY") == "2"  # type: ignore[attr-defined]
        )
    except Exception:
        return False


def _install_privacy_barrier() -> tuple[int, dict[str, tuple[bool, bool]]]:
    previous_disable = logging.root.manager.disable
    names = ("httpx", "httpcore", "google.auth", "urllib3")
    previous_loggers = {
        name: (logging.getLogger(name).disabled, logging.getLogger(name).propagate)
        for name in names
    }
    logging.disable(logging.CRITICAL)
    for name in names:
        logger = logging.getLogger(name)
        logger.disabled = True
        logger.propagate = False
    return previous_disable, previous_loggers


def _restore_privacy_barrier(
    previous: tuple[int, dict[str, tuple[bool, bool]]],
) -> None:
    previous_disable, previous_loggers = previous
    for name, (disabled, propagate) in previous_loggers.items():
        logger = logging.getLogger(name)
        logger.disabled = disabled
        logger.propagate = propagate
    logging.disable(previous_disable)


def _identity_guard_shape_valid() -> bool:
    return bool(
        _IDENTITY_SHA_RE.fullmatch(APPROVED_FIXTURE_ID_SHA256)
        and APPROVED_FIXTURE_ID_SHA256
        == "88935b60192fd0370dce2bde8658e4d5ded2b172cbc75d5ecd64528714162711"
        and _SAFE_REFERENCE_RE.fullmatch(SAFE_FIXTURE_ID_REFERENCE)
        and SAFE_FIXTURE_ID_REFERENCE == "…qWp-Js"
    )


def _ingest_fixture_identity(
    environment: MutableMapping[str, str],
) -> _ValidatedFixtureIdentity:
    try:
        supplied = environment.get(FIXTURE_ID_ENV)
    finally:
        try:
            environment.pop(FIXTURE_ID_ENV, None)
        except Exception:
            pass
    if not isinstance(supplied, str) or not supplied or not supplied.strip():
        raise _LocalDriverError("FIXTURE_ID_INPUT_MISSING")
    try:
        candidate_digest = hashlib.sha256(supplied.encode("utf-8", "strict")).hexdigest()
    except Exception:
        raise _LocalDriverError("FIXTURE_ID_IDENTITY_MISMATCH") from None
    if not hmac.compare_digest(candidate_digest, APPROVED_FIXTURE_ID_SHA256):
        raise _LocalDriverError("FIXTURE_ID_IDENTITY_MISMATCH")
    return _ValidatedFixtureIdentity(supplied)


def _read_config_values(config_path: Path | None = None) -> dict[str, str]:
    path = config_path if config_path is not None else Path.home() / ".codex" / "config.toml"
    try:
        with path.open("rb") as stream:
            parsed = tomllib.load(stream)
        env_values = parsed["mcp_servers"]["google_workspace_admin"]["env"]
        if type(env_values) is not dict:
            raise ValueError
        values = {key: env_values[key] for key in CONTENT_ENV_KEYS}
        if any(not isinstance(value, str) or not value.strip() for value in values.values()):
            raise ValueError
        return values
    except Exception:
        raise _LocalDriverError("CONFIG_BRIDGE_FAILURE") from None


@contextmanager
def _temporary_content_environment(
    environment: MutableMapping[str, str],
    values: dict[str, str],
):
    missing = object()
    previous = {key: environment.get(key, missing) for key in CONTENT_ENV_KEYS}
    previous_hmac = environment.get(_CONTENT_HMAC_ENV_KEY, missing)
    try:
        for key in CONTENT_ENV_KEYS:
            environment[key] = values[key]
        environment.pop(_CONTENT_HMAC_ENV_KEY, None)
        yield
    finally:
        for key, value in previous.items():
            if value is missing:
                environment.pop(key, None)
            else:
                environment[key] = value  # type: ignore[assignment]
        if previous_hmac is missing:
            environment.pop(_CONTENT_HMAC_ENV_KEY, None)
        else:
            environment[_CONTENT_HMAC_ENV_KEY] = previous_hmac  # type: ignore[assignment]


def _default_execution_ports() -> ExecutionPorts:
    try:
        from google_workspace_admin.content.auth.production import (
            _build_controlled_validation_token_provider,
        )
        from google_workspace_admin.content.config import load_content_config
        from validation.fixtures.gsheets_controlled_write import ControlledSheetsTransport
    except Exception:
        raise _LocalDriverError("LOCAL_BOOTSTRAP_FAILURE") from None

    def build_transport(
        fixture_identity: object,
        access_token: str,
        spec: object,
    ) -> object:
        return ControlledSheetsTransport(
            fixture_identity=fixture_identity,
            access_token=access_token,
            formula=spec.cell("O1").formula.value,  # type: ignore[attr-defined]
            expected_o1_display=spec.expected_component("O1", "CELL_DISPLAY"),  # type: ignore[attr-defined]
            expected_p1_display=spec.expected_component("P1", "CELL_DISPLAY"),  # type: ignore[attr-defined]
        )

    return ExecutionPorts(
        load_config=load_content_config,
        build_token_provider=_build_controlled_validation_token_provider,
        build_transport=build_transport,
    )


def _snapshot_is_canonical_o1(snapshot: object) -> bool:
    return bool(
        snapshot.cell_data_present  # type: ignore[attr-defined]
        and snapshot.user_entered_value_present  # type: ignore[attr-defined]
        and snapshot.authored_formula_present  # type: ignore[attr-defined]
        and snapshot.canonical_formula_match  # type: ignore[attr-defined]
        and snapshot.formatted_value_present  # type: ignore[attr-defined]
        and snapshot.formatted_expectation_match  # type: ignore[attr-defined]
        and snapshot.effective_value_present  # type: ignore[attr-defined]
        and snapshot.effective_value_type == "NUMBER"  # type: ignore[attr-defined]
        and snapshot.effective_expectation_match  # type: ignore[attr-defined]
    )


def _snapshot_has_authored_p1(snapshot: object) -> bool:
    return bool(
        snapshot.user_entered_value_present  # type: ignore[attr-defined]
        or snapshot.authored_formula_present  # type: ignore[attr-defined]
    )


def _snapshot_is_canonical_p1(snapshot: object, *, require_effective: bool) -> bool:
    if not (
        snapshot.cell_data_present  # type: ignore[attr-defined]
        and not snapshot.user_entered_value_present  # type: ignore[attr-defined]
        and not snapshot.authored_formula_present  # type: ignore[attr-defined]
        and snapshot.formatted_value_present  # type: ignore[attr-defined]
        and snapshot.formatted_expectation_match  # type: ignore[attr-defined]
    ):
        return False
    if not snapshot.effective_value_present:  # type: ignore[attr-defined]
        return not require_effective
    return bool(
        snapshot.effective_value_type == "NUMBER"  # type: ignore[attr-defined]
        and snapshot.effective_expectation_match  # type: ignore[attr-defined]
    )


def _modified_time_is_non_decreasing(before: str | None, after: str | None) -> bool:
    if not before or not after:
        return False
    try:
        left = datetime.fromisoformat(before.replace("Z", "+00:00"))
        right = datetime.fromisoformat(after.replace("Z", "+00:00"))
        if left.tzinfo is None or right.tzinfo is None:
            return False
        return right >= left
    except (TypeError, ValueError, OverflowError):
        return False


def _run_google_state_machine(
    spec: object,
    transport: object,
) -> SafeResult:
    drive_reads = 0
    sheets_metadata_reads = 0
    sheets_data_reads = 0
    budget = _MutationBudget()
    result = SafeResult(
        fixture_identity_validated=True,
        privacy_barrier="PASS",
        config_bridge="PASS",
        auth_status="PASS",
    )

    try:
        drive_reads += 1
        drive_before = transport.read_drive_metadata()  # type: ignore[attr-defined]
    except Exception:
        return _safe_replace(
            result,
            drive_reads=drive_reads,
            classification=CLASS_H,
            modified_time_integrity="NOT_VERIFIED",
        )
    if not (
        drive_before.id_present
        and drive_before.id_matches_requested_exact_id
        and drive_before.mime_type_present
        and drive_before.is_google_sheet
        and drive_before.trashed_present
        and drive_before.not_trashed
        and drive_before.modified_time_present
    ):
        return _safe_replace(
            result,
            drive_reads=drive_reads,
            classification=CLASS_H,
            modified_time_integrity="NOT_VERIFIED",
        )

    try:
        sheets_metadata_reads += 1
        workbook = transport.read_workbook_metadata()  # type: ignore[attr-defined]
    except Exception:
        return _safe_replace(
            result,
            drive_reads=drive_reads,
            sheets_metadata_reads=sheets_metadata_reads,
            classification=CLASS_H,
        )
    if workbook.locale is None:
        return _safe_replace(
            result,
            drive_reads=drive_reads,
            sheets_metadata_reads=sheets_metadata_reads,
            locale_match="NOT_VERIFIED",
            classification=CLASS_H,
        )
    if workbook.locale != spec.locale:  # type: ignore[attr-defined]
        return _safe_replace(
            result,
            drive_reads=drive_reads,
            sheets_metadata_reads=sheets_metadata_reads,
            locale_match="NO",
            classification=CLASS_E,
        )
    if workbook.time_zone is None:
        return _safe_replace(
            result,
            drive_reads=drive_reads,
            sheets_metadata_reads=sheets_metadata_reads,
            locale_match="YES",
            time_zone_match="NOT_VERIFIED",
            classification=CLASS_H,
        )
    if workbook.time_zone != spec.time_zone:  # type: ignore[attr-defined]
        return _safe_replace(
            result,
            drive_reads=drive_reads,
            sheets_metadata_reads=sheets_metadata_reads,
            locale_match="YES",
            time_zone_match="NO",
            classification=CLASS_I,
        )
    if workbook.ordinal_zero_sheet_id is None or workbook.ordinal_zero_sheet_title is None:
        return _safe_replace(
            result,
            drive_reads=drive_reads,
            sheets_metadata_reads=sheets_metadata_reads,
            locale_match="YES",
            time_zone_match="YES",
            classification=CLASS_H,
        )

    result = _safe_replace(result, locale_match="YES", time_zone_match="YES")

    try:
        sheets_data_reads += 1
        o1_before, p1_before = transport.read_o1_p1_prewrite()  # type: ignore[attr-defined]
    except Exception:
        return _safe_replace(
            result,
            drive_reads=drive_reads,
            sheets_metadata_reads=sheets_metadata_reads,
            sheets_data_reads=sheets_data_reads,
            locale_match="YES",
            classification=CLASS_H,
        )
    o1_ok = _snapshot_is_canonical_o1(o1_before)
    p1_authored = _snapshot_has_authored_p1(p1_before)
    p1_already = _snapshot_is_canonical_p1(p1_before, require_effective=True)
    if not o1_ok:
        return _safe_replace(
            result,
            drive_reads=drive_reads,
            sheets_metadata_reads=sheets_metadata_reads,
            sheets_data_reads=sheets_data_reads,
            locale_match="YES",
            o1_precondition="DRIFT",
            p1_precondition="AUTHORED_STATE_VIOLATION" if p1_authored else "UNAUTHORED",
            precondition_subreason=(
                "P1_AUTHORED_STATE_VIOLATION"
                if p1_authored
                else "O1_CANONICAL_CONTRACT_MISMATCH"
            ),
            classification=CLASS_F,
        )
    if p1_authored:
        return _safe_replace(
            result,
            drive_reads=drive_reads,
            sheets_metadata_reads=sheets_metadata_reads,
            sheets_data_reads=sheets_data_reads,
            locale_match="YES",
            o1_precondition="PASS",
            p1_precondition="AUTHORED_STATE_VIOLATION",
            precondition_subreason="P1_AUTHORED_STATE_VIOLATION",
            classification=CLASS_F,
        )
    if p1_already:
        return _safe_replace(
            result,
            drive_reads=drive_reads,
            sheets_metadata_reads=sheets_metadata_reads,
            sheets_data_reads=sheets_data_reads,
            locale_match="YES",
            o1_precondition="PASS",
            p1_precondition="ALREADY_CANONICAL",
            classification=CLASS_C,
        )

    try:
        budget.consume_before_attempt()
        transport.write_o1_once()  # type: ignore[attr-defined]
        budget.succeeded = 1
    except Exception:
        return _safe_replace(
            result,
            drive_reads=drive_reads,
            sheets_metadata_reads=sheets_metadata_reads,
            sheets_data_reads=sheets_data_reads,
            sheets_write_attempts=budget.attempts,
            sheets_writes_succeeded=budget.succeeded,
            p1_writes=0,
            retries=0,
            locale_match="YES",
            o1_precondition="PASS",
            p1_precondition="UNAUTHORED",
            write_executed=budget.attempts == 1,
            classification=CLASS_G,
        )

    try:
        sheets_data_reads += 1
        o1_after, p1_after = transport.read_o1_p1_postwrite()  # type: ignore[attr-defined]
    except Exception:
        return _safe_replace(
            result,
            drive_reads=drive_reads,
            sheets_metadata_reads=sheets_metadata_reads,
            sheets_data_reads=sheets_data_reads,
            sheets_write_attempts=budget.attempts,
            sheets_writes_succeeded=budget.succeeded,
            locale_match="YES",
            o1_precondition="PASS",
            p1_precondition="UNAUTHORED",
            write_executed=budget.attempts == 1,
            classification=CLASS_H,
        )

    o1_post_ok = _snapshot_is_canonical_o1(o1_after)
    p1_post_authored = _snapshot_has_authored_p1(p1_after)
    p1_post_ok = _snapshot_is_canonical_p1(p1_after, require_effective=False)
    try:
        drive_reads += 1
        drive_after = transport.read_drive_metadata()  # type: ignore[attr-defined]
    except Exception:
        return _safe_replace(
            result,
            drive_reads=drive_reads,
            sheets_metadata_reads=sheets_metadata_reads,
            sheets_data_reads=sheets_data_reads,
            sheets_write_attempts=budget.attempts,
            sheets_writes_succeeded=budget.succeeded,
            locale_match="YES",
            o1_precondition="PASS",
            p1_precondition="UNAUTHORED",
            write_executed=budget.attempts == 1,
            o1_post_state="CANONICAL" if o1_post_ok else "CONTRACT_VIOLATION",
            p1_post_state="AUTHORED_VIOLATION" if p1_post_authored else (
                "CANONICAL" if p1_post_ok else "NOT_RESTORED"
            ),
            classification=CLASS_H,
        )
    metadata_ok = bool(
        drive_after.id_present
        and drive_after.id_matches_requested_exact_id
        and drive_after.mime_type_present
        and drive_after.is_google_sheet
        and drive_after.trashed_present
        and drive_after.not_trashed
        and drive_after.modified_time_present
        and _modified_time_is_non_decreasing(
            drive_before.modified_time_value,
            drive_after.modified_time_value,
        )
    )
    if not o1_post_ok:
        classification = CLASS_D
    elif p1_post_authored or not metadata_ok:
        classification = CLASS_H
    elif p1_post_ok:
        classification = CLASS_A
    else:
        classification = CLASS_B
    return _safe_replace(
        result,
        drive_reads=drive_reads,
        sheets_metadata_reads=sheets_metadata_reads,
        sheets_data_reads=sheets_data_reads,
        sheets_write_attempts=budget.attempts,
        sheets_writes_succeeded=budget.succeeded,
        p1_writes=0,
        retries=0,
        locale_match="YES",
        o1_precondition="PASS",
        p1_precondition="UNAUTHORED",
        write_executed=budget.attempts == 1,
        o1_post_state="CANONICAL" if o1_post_ok else "CONTRACT_VIOLATION",
        p1_post_state=(
            "AUTHORED_VIOLATION"
            if p1_post_authored
            else "CANONICAL"
            if p1_post_ok
            else "NOT_RESTORED"
        ),
        modified_time_integrity="PASS" if metadata_ok else "FAIL",
        classification=classification,
        restoration_proven=(classification == CLASS_A),
    )


def _safe_replace(result: SafeResult, **changes: Any) -> SafeResult:
    return replace(result, **changes)


def _load_execution_ports(ports: ExecutionPorts | None) -> ExecutionPorts:
    return ports if ports is not None else _default_execution_ports()


def execute_controlled_mode(
    *,
    environment: MutableMapping[str, str] | None = None,
    ports: ExecutionPorts | None = None,
    config_path: Path | None = None,
) -> SafeResult:
    """Run the controlled state machine after the strict pre-auth input gate."""

    root = _repo_root_from_file()
    spec = _load_canonical_spec(root)
    if not _identity_guard_shape_valid():
        return SafeResult(classification="LOCAL_BOOTSTRAP_FAILURE")
    barrier_state = _install_privacy_barrier()
    try:
        return _execute_after_privacy_barrier(
            spec,
            environment=os.environ if environment is None else environment,
            ports=ports,
            config_path=config_path,
        )
    finally:
        _restore_privacy_barrier(barrier_state)


def _execute_after_privacy_barrier(
    spec: object,
    *,
    environment: MutableMapping[str, str],
    ports: ExecutionPorts | None,
    config_path: Path | None,
) -> SafeResult:
    try:
        identity = _ingest_fixture_identity(environment)
    except _LocalDriverError as error:
        return SafeResult(
            privacy_barrier="PASS",
            classification=error.classification,
        )

    try:
        config_values = _read_config_values(config_path)
    except _LocalDriverError as error:
        return SafeResult(
            fixture_identity_validated=True,
            privacy_barrier="PASS",
            classification=error.classification,
        )

    try:
        execution_ports = _load_execution_ports(ports)
    except Exception:
        return SafeResult(
            fixture_identity_validated=True,
            privacy_barrier="PASS",
            classification="LOCAL_BOOTSTRAP_FAILURE",
        )

    try:
        with _temporary_content_environment(environment, config_values):
            config = execution_ports.load_config()
    except Exception:
        return SafeResult(
            fixture_identity_validated=True,
            privacy_barrier="PASS",
            config_bridge="PASS",
            classification="CONFIG_BRIDGE_FAILURE",
        )

    try:
        token_provider = execution_ports.build_token_provider(config)
    except Exception:
        return SafeResult(
            fixture_identity_validated=True,
            privacy_barrier="PASS",
            config_bridge="PASS",
            auth_status="FAIL",
            classification="AUTH_FAILURE",
        )

    try:
        access_token = token_provider.get_access_token()  # type: ignore[attr-defined]
        if not isinstance(access_token, str) or not access_token:
            raise ValueError
    except Exception:
        return SafeResult(
            fixture_identity_validated=True,
            privacy_barrier="PASS",
            config_bridge="PASS",
            auth_status="FAIL",
            classification="AUTH_FAILURE",
        )

    try:
        transport = execution_ports.build_transport(identity, access_token, spec)
    except Exception:
        return SafeResult(
            fixture_identity_validated=True,
            privacy_barrier="PASS",
            config_bridge="PASS",
            auth_status="PASS",
            classification="LOCAL_BOOTSTRAP_FAILURE",
        )
    try:
        try:
            return _run_google_state_machine(spec, transport)
        except Exception:
            return SafeResult(
                fixture_identity_validated=True,
                privacy_barrier="PASS",
                config_bridge="PASS",
                auth_status="PASS",
                classification=CLASS_H,
            )
    finally:
        try:
            transport.close()  # type: ignore[attr-defined]
        except Exception:
            pass


def local_preflight(*, script_file: str | Path = __file__) -> tuple[bool, tuple[str, ...]]:
    """Validate local contracts without reading env, auth, clients, or network."""

    root = _repo_root_from_file(script_file)
    spec = _load_canonical_spec(root)
    if not _identity_guard_shape_valid():
        return False, ("IDENTITY_GUARD=FAIL",)
    from validation.fixtures import gsheets_controlled_write as transport_module

    expected_operations = {
        "drive.read_exact_file_metadata",
        "drive.read_exact_file_metadata_postwrite",
        "sheets.read_workbook_metadata",
        "sheets.read_o1_p1_prewrite",
        "sheets.batch_update_o1_once",
        "sheets.read_o1_p1_postwrite",
    }
    if set(transport_module.OPERATION_REGISTRY) != expected_operations:
        return False, ("TRANSPORT_REGISTRY=FAIL",)
    if transport_module.INITIAL_SHEETS_WRITE_BUDGET != 1:
        return False, ("WRITE_BUDGET=FAIL",)
    if not _valid_o1_p1_contract(spec):
        return False, ("FIXTURE_CONTRACT=FAIL",)
    option_strings = {
        option
        for action in _build_parser()._actions
        for option in action.option_strings
    }
    if option_strings != {"-h", "--help", "--local-preflight", "--execute-controlled-test"}:
        return False, ("CLI_SURFACE=FAIL",)
    public_sources = (
        root / "src" / "google_workspace_admin" / "server.py",
        root / "src" / "google_workspace_admin" / "content" / "bootstrap.py",
        root / "src" / "google_workspace_admin" / "content" / "runtime.py",
        root / "src" / "google_workspace_admin" / "content" / "readers.py",
        root / "src" / "google_workspace_admin" / "content" / "google_sheets_adapter.py",
    )
    forbidden_public_references = (
        "gsheets_controlled_write",
        "run_gsheets_spill_restoration_controlled_v1",
    )
    if any(
        not path.is_file()
        or any(reference in path.read_text(encoding="utf-8") for reference in forbidden_public_references)
        for path in public_sources
    ):
        return False, ("PUBLIC_MCP_INTEGRATION=FAIL",)
    try:
        server_ast = ast.parse(public_sources[0].read_text(encoding="utf-8"))
        tool_names = []
        for node in ast.walk(server_ast):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if any(
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Attribute)
                    and decorator.func.attr == "tool"
                    and isinstance(decorator.func.value, ast.Name)
                    and decorator.func.value.id == "mcp"
                    for decorator in node.decorator_list
                ):
                    tool_names.append(node.name.casefold())
    except Exception:
        return False, ("PUBLIC_MCP_CATALOG=FAIL",)
    if len(tool_names) != 24 or any(
        marker in name for name in tool_names for marker in ("write", "create", "update", "delete")
    ):
        return False, ("PUBLIC_MCP_CATALOG=FAIL",)
    return True, (
        "LOCAL_BOOTSTRAP=PASS",
        "CANONICAL_FIXTURE=PASS",
        "IDENTITY_GUARD=PASS",
        "TRANSPORT_REGISTRY=PASS",
        "WRITE_BUDGET=1",
        "PUBLIC_MCP_INTEGRATION=NO",
        "PUBLIC_TOOLS=24",
        "PUBLIC_WRITE_TOOLS=0",
    )


class _SafeArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        raise _LocalDriverError("LOCAL_BOOTSTRAP_FAILURE")


def _build_parser() -> argparse.ArgumentParser:
    parser = _SafeArgumentParser(
        prog="run_gsheets_spill_restoration_controlled_v1",
        description="Offline-first controlled Google Sheets validation driver.",
    )
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--local-preflight", action="store_true")
    modes.add_argument("--execute-controlled-test", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except _LocalDriverError as error:
        print(error.classification)
        return 2
    if args.local_preflight:
        try:
            passed, classifications = local_preflight()
        except Exception:
            print("LOCAL_BOOTSTRAP_FAILURE")
            return 2
        for classification in classifications:
            print(classification)
        return 0 if passed else 2
    if args.execute_controlled_test:
        try:
            result = execute_controlled_mode()
        except Exception:
            result = SafeResult(classification="LOCAL_BOOTSTRAP_FAILURE")
        print(json.dumps(result.as_safe_dict(), ensure_ascii=False, sort_keys=True))
        return 0 if result.classification in {CLASS_A, CLASS_B, CLASS_C, CLASS_D, CLASS_E, CLASS_F, CLASS_G, CLASS_H, CLASS_I} else 2
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
