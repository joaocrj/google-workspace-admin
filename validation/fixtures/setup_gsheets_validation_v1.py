"""Offline planning and explicitly gated operations for the validation fixture.

This module has no Google client and makes no network calls. A future authorized
driver may implement the narrow read/write protocols below.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from enum import Enum
from typing import Protocol

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from validation.fixtures.fixture_contract import (
    FixtureContractError,
    FixtureSpec,
    PresencePolicy,
    load_fixture_spec,
)


SPREADSHEET_MIME_TYPE = "application/vnd.google-apps.spreadsheet"
_FIXTURE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{10,}$", re.ASCII)


class SetupMode(str, Enum):
    VERIFY_ONLY = "VERIFY_ONLY"
    APPLY_EXPLICIT_REPAIR = "APPLY_EXPLICIT_REPAIR"


@dataclass(frozen=True)
class DriveMetadata:
    file_id: str
    mime_type: str
    modified_time: str
    trashed: bool


@dataclass(frozen=True)
class RegionalEvidence:
    verified: bool
    locale: str | None
    time_zone: str | None
    source: str
    bound_to_exact_fixture_id: bool


@dataclass(frozen=True)
class ComponentObservation:
    coordinate: str
    component: str
    value: str
    run_ordinal: int | None = None


@dataclass(frozen=True)
class AuthoredCellState:
    coordinate: str
    user_entered_value_type: str | None
    user_entered_value: str | Decimal | None
    formula: str | None
    number_format_type: str | None
    number_format_pattern: str | None


@dataclass(frozen=True)
class FixtureSnapshot:
    components: tuple[ComponentObservation, ...]
    authored_cells: tuple[AuthoredCellState, ...]


@dataclass(frozen=True)
class UserEnteredUpdate:
    coordinate: str
    value_type: str
    value: Decimal


@dataclass(frozen=True)
class RepairAuthorization:
    authorization_gate_id: str
    explicitly_invoked: bool


@dataclass(frozen=True)
class RepairPlan:
    updates: tuple[UserEnteredUpdate, ...]
    field_mask: str
    rollback_updates: tuple[UserEnteredUpdate, ...]
    gated_actions: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class SafeResult:
    classification: str
    assertion_states: tuple[tuple[str, str], ...] = ()
    repair_plan_created: bool = False
    writes_attempted: int = 0


class VerifyOnlyReader(Protocol):
    def read_exact_drive_metadata(self, fixture_id: str) -> DriveMetadata: ...

    def read_exact_spreadsheet_properties(self, fixture_id: str, sheet_ordinal: int) -> RegionalEvidence: ...

    def read_contract_ranges(
        self, fixture_id: str, sheet_ordinal: int, ranges: tuple[str, ...]
    ) -> FixtureSnapshot: ...


class ExplicitRepairDriver(VerifyOnlyReader, Protocol):
    def write_user_entered_values(
        self,
        fixture_id: str,
        sheet_ordinal: int,
        updates: tuple[UserEnteredUpdate, ...],
        *,
        fields: str,
    ) -> None: ...


def authorize_explicit_repair(
    *, authorization_gate_id: str, explicit_invocation: bool
) -> RepairAuthorization:
    """Create the explicit runtime gate required before a repair plan can run."""
    if (
        type(explicit_invocation) is not bool
        or not explicit_invocation
        or type(authorization_gate_id) is not str
        or not authorization_gate_id.startswith("WORKSPACE-CONTENT-GSHEETS-")
        or authorization_gate_id.endswith("-")
    ):
        raise ValueError("EXPLICIT_REPAIR_AUTHORIZATION_REQUIRED")
    return RepairAuthorization(authorization_gate_id, True)


def _fixture_id_valid(fixture_id: str) -> bool:
    # The exact ID is runtime-only. It is never returned or written by this helper.
    return type(fixture_id) is str and _FIXTURE_ID_RE.fullmatch(fixture_id) is not None


def _safe_metadata(metadata: DriveMetadata, fixture_id: str) -> bool:
    return (
        type(metadata) is DriveMetadata
        and metadata.file_id == fixture_id
        and metadata.mime_type == SPREADSHEET_MIME_TYPE
        and type(metadata.modified_time) is str
        and bool(metadata.modified_time)
        and metadata.trashed is False
    )


def _verified_regional_metadata(reader: VerifyOnlyReader, fixture_id: str, spec: FixtureSpec) -> str:
    try:
        evidence = reader.read_exact_spreadsheet_properties(fixture_id, spec.target_sheet_ordinal)
    except Exception:
        return "FIXTURE_LOCALE_UNVERIFIED"
    if (
        type(evidence) is not RegionalEvidence
        or evidence.verified is not True
        or evidence.bound_to_exact_fixture_id is not True
        or evidence.source != "SHEETS_SPREADSHEET_PROPERTIES"
        or type(evidence.locale) is not str
        or type(evidence.time_zone) is not str
    ):
        return "FIXTURE_LOCALE_UNVERIFIED"
    if evidence.locale != spec.locale:
        return spec.locale_mismatch_classification
    if evidence.time_zone != spec.time_zone:
        return spec.time_zone_mismatch_classification
    return "PASS"


def evaluate_snapshot(spec: FixtureSpec, snapshot: FixtureSnapshot) -> dict[str, str]:
    """Pure exact assertion evaluator shared by offline and future driver tests."""
    if type(snapshot) is not FixtureSnapshot or type(snapshot.components) is not tuple:
        raise ValueError("FIXTURE_SNAPSHOT_INVALID")
    seen: set[tuple[str, str, int | None]] = set()
    types: set[str] = set()
    values: dict[tuple[str, str], list[str]] = {}
    rich: list[tuple[int, str]] = []
    for item in snapshot.components:
        if type(item) is not ComponentObservation or item.component not in {
            "CELL_DISPLAY", "CELL_FORMULA", "CELL_NOTE", "CELL_HYPERLINK", "CELL_RICH_TEXT_LINK"
        }:
            raise ValueError("FIXTURE_COMPONENT_INVALID")
        key = (item.coordinate, item.component, item.run_ordinal if item.component == "CELL_RICH_TEXT_LINK" else None)
        if key in seen:
            raise ValueError("FIXTURE_COMPONENT_DUPLICATE")
        seen.add(key)
        types.add(item.component)
        values.setdefault((item.coordinate, item.component), []).append(item.value)
        if item.component == "CELL_RICH_TEXT_LINK":
            if type(item.run_ordinal) is not int or item.run_ordinal < 0:
                raise ValueError("FIXTURE_RICH_TEXT_ORDINAL_INVALID")
            rich_coordinate = next(
                assertion.coordinate for assertion in spec.structural_assertions
                if assertion.assertion_type == "RICH_TEXT_LINK_ORDER"
            )
            if item.coordinate == rich_coordinate:
                rich.append((item.run_ordinal, item.value))

    result: dict[str, str] = {}
    for coordinate, component, expected in spec.direct_expectations:
        observed = values.get((coordinate, component), [])
        result[f"{coordinate}/{component}"] = "MISSING" if not observed else ("PASS" if observed == [expected] else "FAIL")

    authored_by_coordinate = _authored_cells(snapshot)
    for expectation in spec.numeric_expectations:
        assertion_id = f"{expectation.coordinate}/NUMERIC_EXPECTATION"
        actual = authored_by_coordinate.get(expectation.coordinate)
        if actual is None or actual.user_entered_value is None:
            result[assertion_id] = "NUMERIC_EXPECTATION_NOT_ESTABLISHED"
            continue
        if (
            actual.user_entered_value_type != "NUMBER"
            or type(actual.user_entered_value) is not Decimal
            or actual.user_entered_value != expectation.value
        ):
            result[assertion_id] = expectation.mismatch_classification
            continue
        contract = spec.cell(expectation.coordinate)
        if (
            actual.number_format_type != contract.number_format.format_type
            or actual.number_format_pattern != contract.number_format.pattern
        ):
            result[assertion_id] = "NUMBER_FORMAT_MISMATCH"
            continue
        result[assertion_id] = "PASS"

    structural_by_type = {assertion.assertion_type: assertion for assertion in spec.structural_assertions}
    rich_count = structural_by_type["RICH_TEXT_LINK_COUNT"]
    ordered = sorted(rich, key=lambda pair: pair[0])
    result[rich_count.assertion_id] = "MISSING" if not ordered else ("PASS" if len(ordered) == rich_count.expected_count else "FAIL")
    rich_order = structural_by_type["RICH_TEXT_LINK_ORDER"]
    result[rich_order.assertion_id] = "MISSING" if not ordered else (
        "PASS" if tuple(value for _, value in ordered) == rich_order.expected_targets else "FAIL"
    )
    merged = structural_by_type["MERGED_RANGE"]
    result[merged.assertion_id] = (
        "PASS" if result.get(f"{merged.coordinate}/CELL_DISPLAY") == "PASS"
        and (merged.related_coordinate, "CELL_DISPLAY") not in values else "FAIL"
    )
    no_formula = structural_by_type["COMPONENT_PROHIBITED"]
    result[no_formula.assertion_id] = "PASS" if (no_formula.coordinate, no_formula.component) not in values else "FAIL"
    for assertion in spec.structural_assertions:
        if assertion.assertion_type == "COMPONENT_TYPE_PRESENT":
            result[assertion.assertion_id] = "PASS" if assertion.component in types else "MISSING"
    return {assertion_id: result[assertion_id] for assertion_id in spec.assertion_ids}


def verify_only(reader: VerifyOnlyReader, fixture_id: str, spec: FixtureSpec | None = None) -> SafeResult:
    """Read-only exact-ID preflight and contract verification; the protocol has no write method."""
    spec = spec or load_fixture_spec()
    if not _fixture_id_valid(fixture_id):
        return SafeResult("FIXTURE_ID_INVALID")
    try:
        before = reader.read_exact_drive_metadata(fixture_id)
    except Exception:
        return SafeResult("FIXTURE_METADATA_UNAVAILABLE")
    if not _safe_metadata(before, fixture_id):
        return SafeResult("FIXTURE_IDENTITY_MISMATCH")
    locale_result = _verified_regional_metadata(reader, fixture_id, spec)
    if locale_result != "PASS":
        return SafeResult(locale_result)
    try:
        snapshot = reader.read_contract_ranges(fixture_id, spec.target_sheet_ordinal, spec.operational_ranges)
    except Exception:
        return SafeResult("FIXTURE_READ_FAILED")
    try:
        states = evaluate_snapshot(spec, snapshot)
    except Exception:
        return SafeResult("FIXTURE_SNAPSHOT_INVALID")
    try:
        after = reader.read_exact_drive_metadata(fixture_id)
    except Exception:
        return SafeResult("FIXTURE_POSTFLIGHT_UNAVAILABLE", tuple(states.items()))
    if not _safe_metadata(after, fixture_id) or after != before:
        return SafeResult("FIXTURE_CHANGED_DURING_VERIFY", tuple(states.items()))
    if any(value == "CANONICAL_FIXTURE_SOURCE_DRIFT" for value in states.values()):
        classification = "CANONICAL_FIXTURE_SOURCE_DRIFT"
    elif any(value == "NUMBER_FORMAT_MISMATCH" for value in states.values()):
        classification = "NUMBER_FORMAT_MISMATCH"
    elif all(value == "PASS" for value in states.values()):
        classification = "PASS"
    else:
        classification = "ASSERTIONS_NOT_ALL_PASS"
    return SafeResult(classification, tuple(states.items()))


def _authored_cells(snapshot: FixtureSnapshot) -> dict[str, AuthoredCellState]:
    if type(snapshot) is not FixtureSnapshot:
        raise ValueError("FIXTURE_SNAPSHOT_INVALID")
    result: dict[str, AuthoredCellState] = {}
    for cell in snapshot.authored_cells:
        if type(cell) is not AuthoredCellState or cell.coordinate in result:
            raise ValueError("AUTHORED_STATE_INVALID")
        result[cell.coordinate] = cell
    return result


def build_repair_plan(
    spec: FixtureSpec,
    snapshot: FixtureSnapshot,
    authorization: RepairAuthorization,
) -> RepairPlan:
    """Build deterministic K1/L1 value-only repair after explicit authorization."""
    if type(authorization) is not RepairAuthorization or authorization.explicitly_invoked is not True:
        raise ValueError("EXPLICIT_REPAIR_AUTHORIZATION_REQUIRED")
    if not authorization.authorization_gate_id.startswith("WORKSPACE-CONTENT-GSHEETS-"):
        raise ValueError("EXPLICIT_REPAIR_AUTHORIZATION_REQUIRED")
    if spec.repair_safety["P1_direct_write"] != "PROHIBITED" or spec.repair_safety["O1_same_formula_rewrite"] != "REQUIRES_CONTROLLED_REAL_TEST":
        raise ValueError("REPAIR_POLICY_INVALID")
    cells = _authored_cells(snapshot)
    updates: list[UserEnteredUpdate] = []
    rollback: list[UserEnteredUpdate] = []
    for coordinate in ("K1", "L1"):
        contract = spec.cell(coordinate)
        prior = cells.get(coordinate)
        if prior is None or prior.user_entered_value_type != "NUMBER" or type(prior.user_entered_value) is not Decimal:
            raise ValueError("REPAIR_BACKUP_UNSAFE")
        if prior.number_format_type != contract.number_format.format_type or prior.number_format_pattern != contract.number_format.pattern:
            raise ValueError("CANONICAL_NUMBER_FORMAT_REQUIRED")
        canonical = contract.user_entered_value.value
        if type(canonical) is not Decimal:
            raise ValueError("CANONICAL_NUMERIC_INPUT_REQUIRED")
        updates.append(UserEnteredUpdate(coordinate, "NUMBER", canonical))
        rollback.append(UserEnteredUpdate(coordinate, "NUMBER", prior.user_entered_value))
    return RepairPlan(
        tuple(updates),
        "userEnteredValue",
        tuple(rollback),
        (("O1", spec.repair_safety["O1_same_formula_rewrite"]), ("P1", "DIRECT_WRITE_PROHIBITED")),
    )


def _repair_postconditions(spec: FixtureSpec, snapshot: FixtureSnapshot) -> bool:
    cells = _authored_cells(snapshot)
    for coordinate in ("K1", "L1"):
        contract = spec.cell(coordinate)
        actual = cells.get(coordinate)
        if actual is None or actual.user_entered_value_type != "NUMBER" or actual.user_entered_value != contract.user_entered_value.value:
            return False
        if actual.number_format_type != contract.number_format.format_type or actual.number_format_pattern != contract.number_format.pattern:
            return False
    expected = (
        ("O1", "CELL_FORMULA"),
        ("O1", "CELL_DISPLAY"),
        ("P1", "CELL_DISPLAY"),
    )
    observed = {(item.coordinate, item.component): item.value for item in snapshot.components}
    if any(observed.get(pair) != spec.expected_component(*pair) for pair in expected):
        return False
    p1 = cells.get("P1")
    return p1 is not None and p1.user_entered_value is None and p1.formula is None


def apply_explicit_repair(
    driver: ExplicitRepairDriver,
    fixture_id: str,
    authorization: RepairAuthorization,
    spec: FixtureSpec | None = None,
) -> SafeResult:
    """Apply only authorized K1/L1 updates, verify them, and rollback from memory on failure."""
    spec = spec or load_fixture_spec()
    if type(authorization) is not RepairAuthorization or authorization.explicitly_invoked is not True:
        return SafeResult("EXPLICIT_REPAIR_AUTHORIZATION_REQUIRED")
    if not _fixture_id_valid(fixture_id):
        return SafeResult("FIXTURE_ID_INVALID")
    try:
        before = driver.read_exact_drive_metadata(fixture_id)
    except Exception:
        return SafeResult("FIXTURE_METADATA_UNAVAILABLE")
    if not _safe_metadata(before, fixture_id):
        return SafeResult("FIXTURE_IDENTITY_MISMATCH")
    locale_result = _verified_regional_metadata(driver, fixture_id, spec)
    if locale_result != "PASS":
        return SafeResult(locale_result)
    try:
        backup = driver.read_contract_ranges(fixture_id, spec.target_sheet_ordinal, spec.operational_ranges)
        plan = build_repair_plan(spec, backup, authorization)
    except ValueError as exc:
        return SafeResult(str(exc) if str(exc) in {"REPAIR_BACKUP_UNSAFE", "CANONICAL_NUMBER_FORMAT_REQUIRED", "CANONICAL_NUMERIC_INPUT_REQUIRED"} else "REPAIR_PLAN_INVALID")
    except Exception:
        return SafeResult("REPAIR_BACKUP_UNAVAILABLE")
    write_error = False
    try:
        driver.write_user_entered_values(fixture_id, spec.target_sheet_ordinal, plan.updates, fields=plan.field_mask)
    except Exception:
        write_error = True
    try:
        after = driver.read_contract_ranges(fixture_id, spec.target_sheet_ordinal, spec.operational_ranges)
        metadata_after = driver.read_exact_drive_metadata(fixture_id)
        if write_error and after == backup:
            return SafeResult("REPAIR_WRITE_FAILED_NO_CHANGE", repair_plan_created=True, writes_attempted=1)
        if _safe_metadata(metadata_after, fixture_id) and _repair_postconditions(spec, after):
            classification = "REPAIR_VERIFIED_AFTER_WRITE_ERROR" if write_error else "REPAIR_VERIFIED"
            return SafeResult(classification, repair_plan_created=True, writes_attempted=1)
    except Exception:
        after = None
    try:
        driver.write_user_entered_values(fixture_id, spec.target_sheet_ordinal, plan.rollback_updates, fields=plan.field_mask)
    except Exception:
        return SafeResult("ROLLBACK_UNCONFIRMED", repair_plan_created=True, writes_attempted=2)
    try:
        restored = driver.read_contract_ranges(fixture_id, spec.target_sheet_ordinal, spec.operational_ranges)
        restored_cells = _authored_cells(restored)
        backup_cells = _authored_cells(backup)
        restored_ok = restored == backup and all(restored_cells.get(c) == backup_cells.get(c) for c in ("K1", "L1"))
    except Exception:
        restored_ok = False
    return SafeResult("REPAIR_FAILED_ROLLED_BACK" if restored_ok else "ROLLBACK_UNCONFIRMED", repair_plan_created=True, writes_attempted=2)


def ranges_for_verify_only(spec: FixtureSpec | None = None) -> tuple[str, ...]:
    return (spec or load_fixture_spec()).operational_ranges


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline plan for the Sheets validation fixture")
    parser.add_argument("--mode", choices=[mode.value for mode in SetupMode], required=True)
    parser.add_argument("--fixture-id", required=True, help="Exact runtime-only Drive file ID; never persisted")
    parser.add_argument("--authorization-gate-id")
    parser.add_argument("--authorize-explicit-repair", action="store_true")
    args = parser.parse_args(argv)
    if not _fixture_id_valid(args.fixture_id):
        print("FIXTURE_ID=INVALID")
        return 2
    if args.mode == SetupMode.APPLY_EXPLICIT_REPAIR.value:
        try:
            authorize_explicit_repair(
                authorization_gate_id=args.authorization_gate_id or "",
                explicit_invocation=args.authorize_explicit_repair,
            )
        except ValueError:
            print("APPLY_EXPLICIT_REPAIR=BLOCKED_AUTHORIZATION_REQUIRED")
            return 2
        print("APPLY_EXPLICIT_REPAIR=PLAN_ONLY_DRIVER_REQUIRED")
        return 3
    if args.authorization_gate_id is not None or args.authorize_explicit_repair:
        print("VERIFY_ONLY=INVALID_REPAIR_FLAGS")
        return 2
    try:
        spec = load_fixture_spec()
    except FixtureContractError:
        print("VERIFY_ONLY=SPEC_INVALID")
        return 2
    print("VERIFY_ONLY=PLAN_ONLY_DRIVER_REQUIRED")
    print("FIXTURE_ALIAS=" + spec.fixture_alias)
    print("LOCALE_PRECONDITION=" + spec.locale)
    print("TIME_ZONE_PRECONDITION=" + spec.time_zone)
    print("RANGE_COUNT=" + str(len(spec.operational_ranges)))
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
