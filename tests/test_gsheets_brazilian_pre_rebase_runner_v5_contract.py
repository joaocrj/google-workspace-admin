from __future__ import annotations

import ast
import json
from pathlib import Path
import tempfile


V5_PATH = Path(tempfile.gettempdir()) / "gworkspace_gsheets_brazilian_pre_rebase_runner_v5.py"
FIXTURE_PATH = Path(__file__).resolve().parents[1] / "validation/fixtures/gsheets_validation_v1.json"


def _source_tree() -> tuple[str, ast.Module]:
    source = V5_PATH.read_bytes().decode("utf-8", "strict")
    return source, ast.parse(source, filename=V5_PATH.name)


def _assignment(module: ast.Module, name: str) -> ast.expr:
    for node in module.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return node.value
    raise AssertionError(name)


def _function(module: ast.Module, name: str) -> ast.FunctionDef:
    return next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == name)


def _returned_literal(function: ast.FunctionDef) -> dict:
    returned = next(node.value for node in ast.walk(function) if isinstance(node, ast.Return))
    value = ast.literal_eval(returned)
    assert type(value) is dict
    return value


def test_v5_is_source_only_utf8_python_and_never_imported_by_the_test():
    source, module = _source_tree()
    assert source
    assert isinstance(module, ast.Module)
    assert "__import__(" not in source
    assert "importlib.import_module" not in source


def test_v5_preserves_v4_exit_meanings_and_adds_unique_cell_failures():
    _, module = _source_tree()
    codes = ast.literal_eval(_assignment(module, "_EXIT_CODE_BY_CLASS"))
    assert {name: codes[name] for name in (
        "ARGUMENT_CONTRACT_FAILURE", "EVIDENCE_DESTINATION_FAILURE",
        "BOOTSTRAP_IMPORT_FAILURE", "CONFIGURATION_FAILURE", "ADC_AUTH_FAILURE",
        "IAM_DWD_AUTH_FAILURE", "DRIVE_PREFLIGHT_FAILURE", "SHEETS_READ_FAILURE",
        "DRIVE_POSTFLIGHT_FAILURE", "TOCTOU_FAILURE", "EXPECTED_CELL_NOT_ESTABLISHED",
        "EVIDENCE_WRITE_FAILURE", "UNEXPECTED_LOCAL_FAILURE", "REGIONAL_METADATA_UNAVAILABLE",
        "REGIONAL_METADATA_MISMATCH", "SHEET_IDENTITY_ORIGIN_FAILURE", "TRASHED_STATE",
    )} == {
        "ARGUMENT_CONTRACT_FAILURE": 10,
        "EVIDENCE_DESTINATION_FAILURE": 11,
        "BOOTSTRAP_IMPORT_FAILURE": 12,
        "CONFIGURATION_FAILURE": 13,
        "ADC_AUTH_FAILURE": 14,
        "IAM_DWD_AUTH_FAILURE": 15,
        "DRIVE_PREFLIGHT_FAILURE": 16,
        "SHEETS_READ_FAILURE": 17,
        "DRIVE_POSTFLIGHT_FAILURE": 18,
        "TOCTOU_FAILURE": 19,
        "EXPECTED_CELL_NOT_ESTABLISHED": 20,
        "EVIDENCE_WRITE_FAILURE": 21,
        "UNEXPECTED_LOCAL_FAILURE": 22,
        "REGIONAL_METADATA_UNAVAILABLE": 23,
        "REGIONAL_METADATA_MISMATCH": 24,
        "SHEET_IDENTITY_ORIGIN_FAILURE": 25,
        "TRASHED_STATE": 26,
    }
    assert codes["K1_NUMERIC_EXPECTATION_MISMATCH"] == 27
    assert codes["L1_NUMERIC_EXPECTATION_MISMATCH"] == 28
    assert codes["P1_UNEXPECTED_NOT_ESTABLISHED"] == 30
    assert len(codes.values()) == len(set(codes.values()))
    assert 0 not in codes.values()
    assert "EXPECTED_TRAILING_OMISSION" not in codes


def test_v5_keeps_k1_l1_states_independent_and_preserves_both_before_exit_choice():
    source, module = _source_tree()
    evidence = _returned_literal(_function(module, "_base_evidence"))
    assert evidence["cells"]["K1"]["numeric_expectation_state"] == "NOT_ESTABLISHED"
    assert evidence["cells"]["L1"]["numeric_expectation_state"] == "NOT_ESTABLISHED"
    assert evidence["cells"]["P1"]["slot_state"] == "NOT_ESTABLISHED"
    precedence = ast.literal_eval(_assignment(module, "_CELL_FAILURE_PRECEDENCE"))
    assert precedence[:2] == (
        "K1_NUMERIC_EXPECTATION_MISMATCH",
        "L1_NUMERIC_EXPECTATION_MISMATCH",
    )
    assert "both differ never erases L1's evidence" in source
    observation = _function(module, "_fixed_observations")
    observed_source = ast.get_source_segment(source, observation)
    assert '("K1", 10, "K1")' in observed_source
    assert '("L1", 11, "L1")' in observed_source
    assert 'evidence["cells"] = cell_evidence' in observed_source
    assert 'journal.checkpoint("CELL_MAPPING_COMPLETED")' in observed_source


def test_v5_numeric_assertion_uses_effective_number_and_never_display_text():
    source, module = _source_tree()
    numeric = _function(module, "_numeric_cell_evidence")
    numeric_source = ast.get_source_segment(source, numeric)
    assert "effective_number == expected_number" in numeric_source
    assert "formattedValue" not in numeric_source
    assert "float(" not in numeric_source
    assert "isclose" not in numeric_source
    assert "tolerance" not in numeric_source
    constants = ast.literal_eval(_assignment(module, "_EXPECTED_NUMBER"))
    assert constants == {"K1": 1234.5, "L1": 0.125}


def test_v5_p1_trailing_omission_is_accepted_without_padding():
    source, module = _source_tree()
    constants = ast.literal_eval(_assignment(module, "_P1_TRAILING_OMISSION_ALLOWED"))
    assert constants is True
    assert ast.literal_eval(_assignment(module, "_P1_HOST_COORDINATE")) == "O1"
    assert ast.literal_eval(_assignment(module, "_P1_HOST_FORMULA")) == "=SEQUENCE(1,2)"
    omitted = _function(module, "_p1_expected_trailing_omission_evidence")
    assert _returned_literal(omitted)["slot_state"] == "EXPECTED_TRAILING_OMISSION"
    unexpected = _function(module, "_p1_unexpected_not_established_evidence")
    assert _returned_literal(unexpected)["slot_state"] == "UNEXPECTED_NOT_ESTABLISHED"
    failure_source = ast.get_source_segment(source, _function(module, "_cell_failure_category"))
    assert '"EXPECTED_TRAILING_OMISSION"' not in failure_source
    assert '"P1_UNEXPECTED_NOT_ESTABLISHED"' in failure_source
    observation_source = ast.get_source_segment(source, _function(module, "_fixed_observations"))
    assert "lookup_raw_cell(" in observation_source
    assert "values.append" not in observation_source


def test_v5_o1_exact_formula_is_an_independent_control_and_display_is_secondary():
    source, module = _source_tree()
    assert ast.literal_eval(_assignment(module, "_EXPECTED_FORMULA")) == "=SEQUENCE(1,2)"
    formula_source = ast.get_source_segment(source, _function(module, "_formula_cell_evidence"))
    assert "formula == _EXPECTED_FORMULA" in formula_source
    assert "formattedValue" not in formula_source
    assert '"P1"' in ast.get_source_segment(source, _function(module, "_fixed_observations"))
    spec = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert spec["spreadsheet"] == {"locale": "pt_BR", "timeZone": "America/Sao_Paulo"}
    assert ast.literal_eval(_assignment(module, "_EXPECTED_LOCALE")) == "pt_BR"
    assert ast.literal_eval(_assignment(module, "_EXPECTED_TIME_ZONE")) == "America/Sao_Paulo"


def test_v5_retains_closed_offline_runner_architecture_statically():
    source, module = _source_tree()
    fixed_ranges = ast.literal_eval(_assignment(module, "_FIXED_RANGES"))
    assert fixed_ranges == (
        ("'Validation Main'!K1:L1", 10, 2),
        ("'Validation Main'!O1:O1", 14, 1),
        ("'Validation Main'!P1:P1", 15, 1),
    )
    for forbidden in (
        "subprocess", "gcloud", "google.auth.default", "httpx", "requests.",
        "urllib.request", "@mcp.tool", "retry", "polling", "--range",
    ):
        assert forbidden not in source.casefold()
    for required in (
        "_read_drive_file_metadata", "_read_sheets_rich",
        "_load_authorized_user_adc_credentials", "os.fsync", "os.replace",
        "sys.stderr.write", "_closed_runtime_environment",
    ):
        assert required in source
    main = ast.get_source_segment(source, _function(module, "main"))
    assert main.index("journal.initialize()") < main.index("journal.checkpoint(\"IMPORTS_STARTED\")")
    writer = ast.get_source_segment(source, _function(module, "_write_atomic_evidence"))
    assert "readback = destination.read_bytes()" in writer
    assert "if initial" in writer
