from __future__ import annotations

import copy
import ast
import hashlib
import json
import re
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
from pathlib import Path

import pytest

from validation.fixtures.fixture_contract import (
    AuthoredState,
    FixtureContractError,
    PresencePolicy,
    load_fixture_spec,
    locale_precondition_classification,
)
from validation.fixtures.setup_gsheets_validation_v1 import (
    AuthoredCellState,
    ComponentObservation,
    DriveMetadata,
    FixtureSnapshot,
    RegionalEvidence,
    SetupMode,
    apply_explicit_repair,
    authorize_explicit_repair,
    build_repair_plan,
    evaluate_snapshot,
    main as helper_main,
    ranges_for_verify_only,
    verify_only,
)


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "validation/fixtures/gsheets_validation_v1.json"
SYNTHETIC_ID = "syntheticFixture012345"


def _read_raw_spec() -> dict:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def _load_mutation(tmp_path: Path, mutate) -> FixtureContractError:
    raw = copy.deepcopy(_read_raw_spec())
    mutate(raw)
    path = tmp_path / "mutated.json"
    path.write_text(json.dumps(raw, ensure_ascii=True), encoding="utf-8")
    with pytest.raises(FixtureContractError) as error:
        load_fixture_spec(path)
    return error.value


def _cell(raw: dict, coordinate: str) -> dict:
    return next(cell for cell in raw["cells"] if cell["coordinate"] == coordinate)


def _snapshot(*, drift_numeric: bool = False) -> FixtureSnapshot:
    from validation import gworkspace_rerun4_harness_safe as harness

    observations = tuple(
        ComponentObservation(
            chunk["provenance"]["a1"],
            chunk["provenance"]["component"],
            chunk["text"],
            chunk["provenance"].get("rich_text_run_ordinal"),
        )
        for chunk in harness._matrix()
    )
    k_value = Decimal("9") if drift_numeric else Decimal("1234.5")
    l_value = Decimal("0.9") if drift_numeric else Decimal("0.125")
    authored = (
        AuthoredCellState("K1", "NUMBER", k_value, None, "NUMBER", "0.00"),
        AuthoredCellState("L1", "NUMBER", l_value, None, "PERCENT", "0.0%"),
        AuthoredCellState("O1", None, None, "=SEQUENCE(1,2)", None, None),
        AuthoredCellState("P1", None, None, None, None, None),
    )
    return FixtureSnapshot(observations, authored)


class FakeDriver:
    def __init__(
        self,
        snapshot: FixtureSnapshot,
        locale: str = "pt_BR",
        time_zone: str = "America/Sao_Paulo",
        verified: bool = True,
    ):
        self.snapshot = snapshot
        self.locale = locale
        self.time_zone = time_zone
        self.verified = verified
        self.metadata_reads = 0
        self.locale_reads = 0
        self.range_reads: list[tuple[str, ...]] = []
        self.write_calls = []
        self.metadata = DriveMetadata(SYNTHETIC_ID, "application/vnd.google-apps.spreadsheet", "t1", False)

    def read_exact_drive_metadata(self, fixture_id: str) -> DriveMetadata:
        self.metadata_reads += 1
        return self.metadata

    def read_exact_spreadsheet_properties(self, fixture_id: str, sheet_ordinal: int) -> RegionalEvidence:
        self.locale_reads += 1
        return RegionalEvidence(
            self.verified,
            self.locale,
            self.time_zone,
            "SHEETS_SPREADSHEET_PROPERTIES",
            True,
        )

    def read_contract_ranges(self, fixture_id: str, sheet_ordinal: int, ranges: tuple[str, ...]) -> FixtureSnapshot:
        self.range_reads.append(ranges)
        return self.snapshot

    def write_user_entered_values(self, fixture_id, sheet_ordinal, updates, *, fields):
        self.write_calls.append((updates, fields))
        state_by_coordinate = {cell.coordinate: cell for cell in self.snapshot.authored_cells}
        display_updates = {}
        for update in updates:
            state_by_coordinate[update.coordinate] = replace(
                state_by_coordinate[update.coordinate], user_entered_value_type=update.value_type,
                user_entered_value=update.value,
            )
            if update.coordinate == "K1":
                display_updates[update.coordinate] = f"{update.value:.2f}"
            else:
                display_updates[update.coordinate] = f"{update.value * Decimal(100):.1f}%"
        components = tuple(
            replace(item, value=display_updates[item.coordinate])
            if item.component == "CELL_DISPLAY" and item.coordinate in display_updates else item
            for item in self.snapshot.components
        )
        self.snapshot = FixtureSnapshot(components, tuple(state_by_coordinate.values()))
        self.metadata = replace(self.metadata, modified_time=f"t{self.metadata_reads + len(self.write_calls)}")


class CorruptFirstPostWriteDriver(FakeDriver):
    def write_user_entered_values(self, fixture_id, sheet_ordinal, updates, *, fields):
        super().write_user_entered_values(fixture_id, sheet_ordinal, updates, fields=fields)
        if len(self.write_calls) == 1:
            self.snapshot = replace(
                self.snapshot,
                authored_cells=tuple(
                    replace(item, user_entered_value=Decimal("9"))
                    if item.coordinate == "K1" else item
                    for item in self.snapshot.authored_cells
                ),
            )


def test_spec_versions_alias_locale_and_immutable_typed_model():
    spec = load_fixture_spec()
    assert spec.spec_schema_version == 1
    assert spec.fixture_contract_version == 2
    assert spec.fixture_alias == "GSHEETS_VALIDATION_V1"
    assert spec.target_sheet_ordinal == 0
    assert spec.locale == "pt_BR"
    assert spec.time_zone == "America/Sao_Paulo"
    assert len(spec.cells) == 19
    with pytest.raises(FrozenInstanceError):
        spec.cells[0].coordinate = "X1"


def test_spec_contains_no_fixture_identity_or_credential_material():
    raw = SPEC_PATH.read_text(encoding="utf-8").casefold()
    forbidden = (
        "drive_file_id", "fixture_id", "file_id", "public_file_ref",
        "access_token", "refresh_token", "authorization: bearer", "private_key",
        "client_secret", "-----begin", "hmac_value", "hmac_fingerprint",
    )
    assert all(marker not in raw for marker in forbidden)


def test_k1_and_l1_operator_contracts_are_exact():
    spec = load_fixture_spec()
    k1 = spec.cell("K1")
    assert k1.user_entered_value.value_type == "NUMBER"
    assert k1.user_entered_value.value == Decimal("1234.5")
    assert k1.number_format.format_type == "NUMBER"
    assert k1.number_format.pattern == "0.00"
    assert k1.numeric_expectation.source == "CANONICAL_AUTHORED_SEED"
    assert k1.numeric_expectation.mismatch_classification == "CANONICAL_FIXTURE_SOURCE_DRIFT"
    assert all(item.policy is PresencePolicy.UNSPECIFIED for item in k1.expected_components if item.component == "CELL_DISPLAY")
    assert Decimal.from_float(float(k1.user_entered_value.value)) == Decimal("1234.5")
    l1 = spec.cell("L1")
    assert l1.user_entered_value.value_type == "NUMBER"
    assert l1.user_entered_value.value == Decimal("0.125")
    assert l1.number_format.format_type == "PERCENT"
    assert l1.number_format.pattern == "0.0%"
    assert l1.numeric_expectation.source == "CANONICAL_AUTHORED_SEED"
    assert l1.numeric_expectation.mismatch_classification == "CANONICAL_FIXTURE_SOURCE_DRIFT"
    assert all(item.policy is PresencePolicy.UNSPECIFIED for item in l1.expected_components if item.component == "CELL_DISPLAY")
    assert Decimal.from_float(float(l1.user_entered_value.value)) == Decimal("0.125")


def test_o1_and_p1_operator_contracts_are_exact():
    spec = load_fixture_spec()
    o1 = spec.cell("O1")
    assert o1.authored_state is AuthoredState.AUTHORED
    assert o1.formula.policy is PresencePolicy.REQUIRED
    assert o1.formula.value == "=SEQUENCE(1,2)"
    assert spec.expected_component("O1", "CELL_FORMULA") == "=SEQUENCE(1,2)"
    assert spec.expected_component("O1", "CELL_DISPLAY") == "1"
    p1 = spec.cell("P1")
    assert p1.authored_state is AuthoredState.UNAUTHORED
    assert p1.user_entered_value.policy is PresencePolicy.PROHIBITED
    assert p1.user_entered_value.value is None
    assert p1.formula.policy is PresencePolicy.PROHIBITED
    assert p1.derived_state["expectation"] == "NON_AUTHORED_DYNAMIC_RESULT_AT_EXPECTED_COORDINATE"
    assert p1.derived_state["host_formula"] == "=SEQUENCE(1,2)"
    assert p1.derived_state["relationship"] == "RIGHT_ADJACENT_DYNAMIC_SPILL_NEIGHBOR"
    assert p1.derived_state["api_proves_spill_linkage"] is False
    assert p1.sparse_semantics["omission_classification"] == "EXPECTED_TRAILING_OMISSION"
    assert p1.sparse_semantics["synthesize_missing_cell_data"] is False
    assert p1.sparse_semantics["omission_means_authored_absence"] is False
    assert spec.expected_component("P1", "CELL_DISPLAY") == "2"


def test_m1_n1_and_a4_j1_keep_only_accepted_semantics():
    spec = load_fixture_spec()
    for coordinate in ("M1", "N1"):
        assert spec.cell(coordinate).user_entered_value.policy is PresencePolicy.UNSPECIFIED
        assert spec.cell(coordinate).number_format.policy is PresencePolicy.UNSPECIFIED
    for coordinate in ("A4", "J1"):
        assert spec.expected_component(coordinate, "CELL_DISPLAY")
        assert spec.cell(coordinate).visibility_policy is PresencePolicy.UNSPECIFIED


def test_fixture_id_does_not_appear_in_spec_or_test_sources():
    spec = _read_raw_spec()
    assert set(spec) == {
        "spec_schema_version", "fixture_contract_version", "fixture_alias", "target_sheet_ordinal",
        "spreadsheet", "cells", "structures", "validation_policies",
    }


def test_loader_rejects_malformed_json_and_duplicate_keys(tmp_path):
    malformed = tmp_path / "bad.json"
    malformed.write_text("{not-json", encoding="utf-8")
    with pytest.raises(FixtureContractError, match="JSON_INVALID"):
        load_fixture_spec(malformed)
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"spec_schema_version":1,"spec_schema_version":1}', encoding="utf-8")
    with pytest.raises(FixtureContractError, match="DUPLICATE_JSON_FIELD"):
        load_fixture_spec(duplicate)


def test_loader_rejects_unsupported_schema_version(tmp_path):
    error = _load_mutation(tmp_path, lambda raw: raw.update(spec_schema_version=2))
    assert error.code == "SCHEMA_VERSION_UNSUPPORTED"


def test_loader_rejects_unsupported_contract_version_separately(tmp_path):
    error = _load_mutation(tmp_path, lambda raw: raw.update(fixture_contract_version=3))
    assert error.code == "CONTRACT_VERSION_UNSUPPORTED"


def test_loader_rejects_duplicate_coordinates_and_components(tmp_path):
    def duplicate_coordinate(raw):
        raw["cells"].append(copy.deepcopy(raw["cells"][0]))
    assert _load_mutation(tmp_path, duplicate_coordinate).code == "DUPLICATE_COORDINATE"

    def duplicate_component(raw):
        raw["cells"][0]["expected_components"].append(copy.deepcopy(raw["cells"][0]["expected_components"][0]))
    assert _load_mutation(tmp_path, duplicate_component).code == "DUPLICATE_OR_UNKNOWN_COMPONENT"


def test_loader_rejects_duplicate_structural_component_assertions(tmp_path):
    def duplicate_type(raw):
        raw["structures"][3]["assertions"].append(copy.deepcopy(raw["structures"][3]["assertions"][0]))
    assert _load_mutation(tmp_path, duplicate_type).code == "TYPE_COVERAGE_INVALID"


def test_loader_fails_closed_for_unknown_fields_and_nulls(tmp_path):
    assert _load_mutation(tmp_path, lambda raw: raw.update(unrecognized=True)).code == "UNKNOWN_OR_MISSING_FIELD"
    assert _load_mutation(tmp_path, lambda raw: raw["cells"][0].update(note=None)).code == "NULL_NOT_ALLOWED"


def test_loader_rejects_direct_authored_p1_and_numeric_coercion(tmp_path):
    def author_p1(raw):
        p1 = _cell(raw, "P1")
        p1["authored_state"] = "AUTHORED"
        p1["user_entered_value"] = {"policy": "REQUIRED", "type": "NUMBER", "value": 2.0}
    assert _load_mutation(tmp_path, author_p1).code == "P1_CONTRACT_INVALID"

    def integer_for_decimal(raw):
        _cell(raw, "K1")["user_entered_value"]["value"] = 1234
    assert _load_mutation(tmp_path, integer_for_decimal).code == "DECIMAL_NUMBER_REQUIRED"


def test_all_33_assertions_and_migration_classes_are_derived_from_spec():
    spec = load_fixture_spec()
    assert len(spec.assertion_ids) == 33
    assert len(set(spec.assertion_ids)) == 33
    assert spec.migration_counts["SPEC_BACKED_DIRECTLY"] == 22
    assert spec.migration_counts["SPEC_BACKED_STRUCTURALLY"] == 9
    assert spec.migration_counts["CANONICAL_NUMERIC_SEED"] == 2
    assert spec.migration_counts["HARNESS_BEHAVIOR_ONLY"] == 0
    assert spec.migration_counts["NEEDS_CONTRACT_COMPLETION"] == 0


def test_harness_loads_the_canonical_spec_and_has_no_second_assertion_map():
    from validation import gworkspace_rerun4_harness_safe as harness

    spec = load_fixture_spec()
    assert harness.SPEC.path == spec.path
    assert harness.EXPECTED == {(coordinate, component): value for coordinate, component, value in spec.direct_expectations}
    source = (ROOT / "validation/gworkspace_rerun4_harness_safe.py").read_text(encoding="utf-8")
    module = ast.parse(source)
    expected_assignments = [
        node.value for node in module.body
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "EXPECTED" for target in node.targets)
    ]
    assert len(expected_assignments) == 1 and isinstance(expected_assignments[0], ast.DictComp)
    instance = harness.Rerun4Harness()
    instance.ingest({"processing_status": "PROCESSED", "chunks": harness._matrix()})
    assert len(instance.final_assertions()) == 31
    assert set(instance.final_assertions()) == set(spec.content_assertion_ids)


def test_helper_loads_same_spec_and_fixed_operational_ranges():
    spec = load_fixture_spec()
    assert ranges_for_verify_only(spec) == spec.operational_ranges == ("A1:P1", "A4", "A6:B6", "Z900")
    assert SetupMode.VERIFY_ONLY.value == "VERIFY_ONLY"
    assert SetupMode.APPLY_EXPLICIT_REPAIR.value == "APPLY_EXPLICIT_REPAIR"


def test_harness_has_repository_relative_canonical_path_only():
    source = (ROOT / "validation/gworkspace_rerun4_harness_safe.py").read_text(encoding="utf-8")
    assert "D:\\AI\\CODEX\\" not in source
    assert "C:\\Users\\" not in source
    assert "Path.cwd" not in source
    assert "rglob(" not in source and ".glob(" not in source
    from validation import gworkspace_rerun4_harness_safe as harness
    assert harness._canonical_location_valid()


def test_locale_precondition_classification_fails_closed():
    regional = {"verified_time_zone": "America/Sao_Paulo"}
    assert locale_precondition_classification("pt_BR", verified=True, **regional) == "PASS"
    assert locale_precondition_classification("en_US", verified=True, **regional) == "FIXTURE_LOCALE_MISMATCH"
    assert locale_precondition_classification(
        "pt_BR", verified=True, verified_time_zone="UTC"
    ) == "FIXTURE_TIME_ZONE_MISMATCH"
    assert locale_precondition_classification("pt_BR", verified=False, **regional) == "FIXTURE_LOCALE_UNVERIFIED"
    assert locale_precondition_classification(None, verified=True, **regional) == "FIXTURE_LOCALE_UNVERIFIED"
    assert locale_precondition_classification("pt_BR", verified=True, verified_time_zone=None) == "FIXTURE_LOCALE_UNVERIFIED"


def test_verify_only_reads_exact_ranges_and_never_writes():
    driver = FakeDriver(_snapshot())
    result = verify_only(driver, SYNTHETIC_ID)
    assert result.classification == "PASS"
    assert len(result.assertion_states) == 33
    assert driver.range_reads == [("A1:P1", "A4", "A6:B6", "Z900")]
    assert driver.write_calls == []
    assert driver.metadata_reads == 2


def test_numeric_seed_drift_is_per_cell_blocking_and_display_independent():
    spec = load_fixture_spec()
    base = _snapshot(drift_numeric=True)
    displays = (
        ComponentObservation("K1", "CELL_DISPLAY", "localized_display_a"),
        ComponentObservation("L1", "CELL_DISPLAY", "localized_display_b"),
    )
    changed_displays = replace(base, components=base.components + displays)
    states = evaluate_snapshot(spec, changed_displays)
    assert states["K1/NUMERIC_EXPECTATION"] == "CANONICAL_FIXTURE_SOURCE_DRIFT"
    assert states["L1/NUMERIC_EXPECTATION"] == "CANONICAL_FIXTURE_SOURCE_DRIFT"
    assert states["K1/NUMERIC_EXPECTATION"] == evaluate_snapshot(spec, base)["K1/NUMERIC_EXPECTATION"]
    assert states["L1/NUMERIC_EXPECTATION"] == evaluate_snapshot(spec, base)["L1/NUMERIC_EXPECTATION"]

    result = verify_only(FakeDriver(changed_displays), SYNTHETIC_ID)
    result_states = dict(result.assertion_states)
    assert result.classification == "CANONICAL_FIXTURE_SOURCE_DRIFT"
    assert result_states["K1/NUMERIC_EXPECTATION"] == "CANONICAL_FIXTURE_SOURCE_DRIFT"
    assert result_states["L1/NUMERIC_EXPECTATION"] == "CANONICAL_FIXTURE_SOURCE_DRIFT"

    k_only_authored = tuple(
        replace(item, user_entered_value=Decimal("0.125"))
        if item.coordinate == "L1" else item
        for item in base.authored_cells
    )
    k_only = evaluate_snapshot(spec, replace(base, authored_cells=k_only_authored))
    assert k_only["K1/NUMERIC_EXPECTATION"] == "CANONICAL_FIXTURE_SOURCE_DRIFT"
    assert k_only["L1/NUMERIC_EXPECTATION"] == "PASS"

    l_only_authored = tuple(
        replace(item, user_entered_value=Decimal("1234.5"))
        if item.coordinate == "K1" else item
        for item in base.authored_cells
    )
    l_only = evaluate_snapshot(spec, replace(base, authored_cells=l_only_authored))
    assert l_only["K1/NUMERIC_EXPECTATION"] == "PASS"
    assert l_only["L1/NUMERIC_EXPECTATION"] == "CANONICAL_FIXTURE_SOURCE_DRIFT"


def test_missing_numeric_seed_is_not_reported_as_a_match():
    spec = load_fixture_spec()
    base = _snapshot()
    authored = tuple(
        replace(item, user_entered_value=None) if item.coordinate == "K1" else item
        for item in base.authored_cells
    )
    states = evaluate_snapshot(spec, replace(base, authored_cells=authored))
    assert states["K1/NUMERIC_EXPECTATION"] == "NUMERIC_EXPECTATION_NOT_ESTABLISHED"
    assert states["L1/NUMERIC_EXPECTATION"] == "PASS"


def test_locale_mismatch_stops_before_contract_ranges_or_mutation():
    driver = FakeDriver(_snapshot(), locale="en_US")
    result = verify_only(driver, SYNTHETIC_ID)
    assert result.classification == "FIXTURE_LOCALE_MISMATCH"
    assert driver.range_reads == []
    assert driver.write_calls == []


def test_time_zone_mismatch_stops_before_contract_ranges_or_mutation():
    driver = FakeDriver(_snapshot(), time_zone="UTC")
    result = verify_only(driver, SYNTHETIC_ID)
    assert result.classification == "FIXTURE_TIME_ZONE_MISMATCH"
    assert driver.range_reads == []
    assert driver.write_calls == []


def test_unverified_locale_fails_closed_before_contract_ranges():
    driver = FakeDriver(_snapshot(), verified=False)
    result = verify_only(driver, SYNTHETIC_ID)
    assert result.classification == "FIXTURE_LOCALE_UNVERIFIED"
    assert driver.range_reads == []
    assert driver.write_calls == []


def test_repair_requires_explicit_invocation_and_gate_id():
    with pytest.raises(ValueError, match="EXPLICIT_REPAIR_AUTHORIZATION_REQUIRED"):
        authorize_explicit_repair(authorization_gate_id="", explicit_invocation=False)
    driver = FakeDriver(_snapshot(drift_numeric=True))
    result = apply_explicit_repair(driver, SYNTHETIC_ID, None)
    assert result.classification == "EXPLICIT_REPAIR_AUTHORIZATION_REQUIRED"
    assert driver.write_calls == []


def test_apply_cli_cannot_silently_activate_repair(capsys):
    result = helper_main(["--mode", "APPLY_EXPLICIT_REPAIR", "--fixture-id", SYNTHETIC_ID])
    assert result == 2
    assert "BLOCKED_AUTHORIZATION_REQUIRED" in capsys.readouterr().out


def test_repair_plan_is_deterministic_value_only_and_never_targets_o1_or_p1():
    spec = load_fixture_spec()
    driver = FakeDriver(_snapshot(drift_numeric=True))
    authorization = authorize_explicit_repair(
        authorization_gate_id="WORKSPACE-CONTENT-GSHEETS-FIXTURE-CORRECTION-V1",
        explicit_invocation=True,
    )
    plan = build_repair_plan(spec, driver.snapshot, authorization)
    assert tuple(update.coordinate for update in plan.updates) == ("K1", "L1")
    assert plan.field_mask == "userEnteredValue"
    assert {update.coordinate for update in plan.rollback_updates} == {"K1", "L1"}
    assert plan.gated_actions == (("O1", "REQUIRES_CONTROLLED_REAL_TEST"), ("P1", "DIRECT_WRITE_PROHIBITED"))
    assert all(update.coordinate not in {"O1", "P1"} for update in plan.updates + plan.rollback_updates)
    assert plan.updates[0].value == Decimal("1234.5")
    assert plan.updates[1].value == Decimal("0.125")


def test_apply_repair_requires_explicit_mode_and_verifies_post_write():
    spec = load_fixture_spec()
    driver = FakeDriver(_snapshot(drift_numeric=True))
    authorization = authorize_explicit_repair(
        authorization_gate_id="WORKSPACE-CONTENT-GSHEETS-FIXTURE-CORRECTION-V1",
        explicit_invocation=True,
    )
    result = apply_explicit_repair(driver, SYNTHETIC_ID, authorization, spec)
    assert result.classification == "REPAIR_VERIFIED"
    assert result.writes_attempted == 1
    assert len(driver.write_calls) == 1
    assert driver.write_calls[0][1] == "userEnteredValue"
    assert tuple(update.coordinate for update in driver.write_calls[0][0]) == ("K1", "L1")
    assert all(update.coordinate not in {"O1", "P1"} for update in driver.write_calls[0][0])


def test_failed_focused_postcondition_rolls_back_exact_in_memory_values():
    spec = load_fixture_spec()
    driver = CorruptFirstPostWriteDriver(_snapshot(drift_numeric=True))
    authorization = authorize_explicit_repair(
        authorization_gate_id="WORKSPACE-CONTENT-GSHEETS-FIXTURE-CORRECTION-V1",
        explicit_invocation=True,
    )
    result = apply_explicit_repair(driver, SYNTHETIC_ID, authorization, spec)
    assert result.classification == "REPAIR_FAILED_ROLLED_BACK"
    assert result.writes_attempted == 2
    assert len(driver.write_calls) == 2
    assert all(fields == "userEnteredValue" for _, fields in driver.write_calls)
    assert all(update.coordinate in {"K1", "L1"} for call, _ in driver.write_calls for update in call)


def test_no_secret_or_machine_path_material_in_authorized_implementation_files():
    paths = (
        SPEC_PATH,
        ROOT / "validation/fixtures/fixture_contract.py",
        ROOT / "validation/fixtures/canonical_state_repair.py",
        ROOT / "validation/fixtures/setup_gsheets_validation_v1.py",
        ROOT / "validation/gworkspace_rerun4_harness_safe.py",
        Path(__file__),
    )
    secret_patterns = (
        re.compile(r"ya29\.[A-Za-z0-9_-]{20,}"),
        re.compile(r"1//[A-Za-z0-9_-]{20,}"),
        re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
        re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"),
    )
    workstation_fragments = (
        "".join(("D:", chr(92), "AI", chr(92), "CODEX", chr(92))),
        "".join(("C:", chr(92), "Users", chr(92))),
    )
    for path in paths:
        contents = path.read_text(encoding="utf-8")
        assert all(fragment not in contents for fragment in workstation_fragments)
        assert all(pattern.search(contents) is None for pattern in secret_patterns)
        assert hashlib.sha256(contents.encode("utf-8")).hexdigest()
