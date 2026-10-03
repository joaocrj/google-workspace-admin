"""Strict, offline loader for the canonical Google Sheets validation fixture."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


DEFAULT_SPEC_PATH = Path(__file__).with_name("gsheets_validation_v1.json")
_COORDINATE_RE = re.compile(r"^([A-Z]+)([1-9][0-9]*)$", re.ASCII)
_RANGE_RE = re.compile(r"^([A-Z]+[1-9][0-9]*):([A-Z]+[1-9][0-9]*)$", re.ASCII)
_COMPONENTS = (
    "CELL_DISPLAY",
    "CELL_FORMULA",
    "CELL_NOTE",
    "CELL_HYPERLINK",
    "CELL_RICH_TEXT_LINK",
)


class FixtureContractError(ValueError):
    """Safe error code for invalid or unsupported fixture contract data."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class PresencePolicy(str, Enum):
    REQUIRED = "REQUIRED"
    PROHIBITED = "PROHIBITED"
    UNSPECIFIED = "UNSPECIFIED"


class AuthoredState(str, Enum):
    AUTHORED = "AUTHORED"
    UNAUTHORED = "UNAUTHORED"
    UNSPECIFIED = "UNSPECIFIED"


class MigrationClass(str, Enum):
    SPEC_BACKED_DIRECTLY = "SPEC_BACKED_DIRECTLY"
    SPEC_BACKED_STRUCTURALLY = "SPEC_BACKED_STRUCTURALLY"


@dataclass(frozen=True)
class ValueContract:
    policy: PresencePolicy
    value_type: str | None = None
    value: str | Decimal | bool | None = None


@dataclass(frozen=True)
class NumberFormatContract:
    policy: PresencePolicy
    format_type: str | None = None
    pattern: str | None = None


@dataclass(frozen=True)
class NumericExpectationContract:
    source: str
    comparison: str
    mismatch_classification: str


@dataclass(frozen=True)
class NumericSeedExpectation:
    coordinate: str
    value: Decimal
    source: str
    comparison: str
    mismatch_classification: str


@dataclass(frozen=True)
class ExpectedComponent:
    component: str
    policy: PresencePolicy
    value: str | None


@dataclass(frozen=True)
class FixtureCell:
    coordinate: str
    authored_state: AuthoredState
    user_entered_value: ValueContract
    numeric_expectation: NumericExpectationContract | None
    formula: ValueContract
    number_format: NumberFormatContract
    expected_components: tuple[ExpectedComponent, ...]
    visibility_policy: PresencePolicy
    derived_state: Mapping[str, Any]
    merge_semantics: Mapping[str, Any]
    sparse_semantics: Mapping[str, Any]
    component_specific_metadata: Mapping[str, Mapping[str, str]]


@dataclass(frozen=True)
class StructuralAssertion:
    assertion_id: str
    assertion_type: str
    migration_class: MigrationClass
    coordinate: str | None = None
    component: str | None = None
    expected_count: int | None = None
    expected_targets: tuple[str, ...] = ()
    expected_semantics: str | None = None
    related_coordinate: str | None = None


@dataclass(frozen=True)
class FixtureSpec:
    path: Path
    spec_schema_version: int
    fixture_contract_version: int
    fixture_alias: str
    target_sheet_ordinal: int
    locale: str
    time_zone: str
    cells: tuple[FixtureCell, ...]
    structures: tuple[Mapping[str, Any], ...]
    direct_expectations: tuple[tuple[str, str, str], ...]
    numeric_expectations: tuple[NumericSeedExpectation, ...]
    structural_assertions: tuple[StructuralAssertion, ...]
    assertion_ids: tuple[str, ...]
    migration_counts: Mapping[str, int]
    operational_ranges: tuple[str, ...]
    locale_mismatch_classification: str
    time_zone_mismatch_classification: str
    display_semantics: str
    acceptance_semantics_changed: bool
    repair_safety: Mapping[str, bool | str]

    def cell(self, coordinate: str) -> FixtureCell:
        for cell in self.cells:
            if cell.coordinate == coordinate:
                return cell
        raise KeyError(coordinate)

    def expected_component(self, coordinate: str, component: str) -> str:
        cell = self.cell(coordinate)
        for expected in cell.expected_components:
            if expected.component == component and expected.policy is PresencePolicy.REQUIRED:
                assert expected.value is not None
                return expected.value
        raise KeyError((coordinate, component))

    @property
    def content_assertion_ids(self) -> tuple[str, ...]:
        """Assertions observable through the content component stream."""
        direct = tuple(f"{coordinate}/{component}" for coordinate, component, _ in self.direct_expectations)
        structural = tuple(item.assertion_id for item in self.structural_assertions)
        return direct + structural


def _fail(code: str) -> None:
    raise FixtureContractError(code)


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("DUPLICATE_JSON_FIELD")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    _fail("NONFINITE_NUMBER")


def _reject_nulls(value: Any) -> None:
    if value is None:
        _fail("NULL_NOT_ALLOWED")
    if type(value) is dict:
        for nested in value.values():
            _reject_nulls(nested)
    elif type(value) is list:
        for nested in value:
            _reject_nulls(nested)


def _object(value: Any, required: set[str], optional: set[str] = frozenset()) -> dict[str, Any]:
    if type(value) is not dict:
        _fail("OBJECT_REQUIRED")
    keys = set(value)
    if not required <= keys or keys - required - optional:
        _fail("UNKNOWN_OR_MISSING_FIELD")
    return value


def _string(value: Any, *, nonempty: bool = True) -> str:
    if type(value) is not str or (nonempty and not value):
        _fail("STRING_REQUIRED")
    return value


def _freeze(value: Any) -> Any:
    if type(value) is dict:
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if type(value) is list:
        return tuple(_freeze(item) for item in value)
    return value


def _bool(value: Any) -> bool:
    if type(value) is not bool:
        _fail("BOOLEAN_REQUIRED")
    return value


def _int(value: Any, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        _fail("INTEGER_REQUIRED")
    return value


def _coordinate(value: Any) -> str:
    coordinate = _string(value)
    if not _COORDINATE_RE.fullmatch(coordinate):
        _fail("COORDINATE_INVALID")
    return coordinate


def _range(value: Any) -> str:
    raw = _string(value)
    match = _RANGE_RE.fullmatch(raw)
    if not match:
        _fail("RANGE_INVALID")
    if _coordinate(match.group(1)) != match.group(1) or _coordinate(match.group(2)) != match.group(2):
        _fail("RANGE_INVALID")
    return raw


def _policy(value: Any) -> PresencePolicy:
    try:
        return PresencePolicy(_string(value))
    except ValueError:
        _fail("PRESENCE_POLICY_INVALID")


def _value_contract(value: Any, field: str) -> ValueContract:
    if type(value) is not dict or "policy" not in value:
        _fail("VALUE_CONTRACT_INVALID")
    policy = _policy(value["policy"])
    if policy is not PresencePolicy.REQUIRED:
        _object(value, {"policy"})
        return ValueContract(policy)
    _object(value, {"policy", "type", "value"})
    value_type = _string(value["type"])
    raw_value = value["value"]
    if field == "user_entered_value" and value_type == "NUMBER":
        if type(raw_value) is not Decimal:
            _fail("DECIMAL_NUMBER_REQUIRED")
        parsed: str | Decimal | bool = raw_value
    elif field == "user_entered_value" and value_type == "BOOLEAN":
        if type(raw_value) is not bool:
            _fail("BOOLEAN_REQUIRED")
        parsed = raw_value
    else:
        parsed = _string(raw_value)
    if field == "formula" and (value_type != "FORMULA" or not str(parsed).startswith("=")):
        _fail("FORMULA_CONTRACT_INVALID")
    if field == "user_entered_value" and value_type not in {"STRING", "NUMBER", "BOOLEAN"}:
        _fail("USER_ENTERED_VALUE_TYPE_INVALID")
    return ValueContract(policy, value_type, parsed)


def _formula_contract(value: Any) -> ValueContract:
    if type(value) is not dict or "policy" not in value:
        _fail("FORMULA_CONTRACT_INVALID")
    policy = _policy(value["policy"])
    if policy is not PresencePolicy.REQUIRED:
        _object(value, {"policy"})
        return ValueContract(policy)
    _object(value, {"policy", "value"})
    formula = _string(value["value"])
    if not formula.startswith("="):
        _fail("FORMULA_CONTRACT_INVALID")
    return ValueContract(policy, "FORMULA", formula)


def _number_format(value: Any) -> NumberFormatContract:
    if type(value) is not dict or "policy" not in value:
        _fail("NUMBER_FORMAT_INVALID")
    policy = _policy(value["policy"])
    if policy is not PresencePolicy.REQUIRED:
        _object(value, {"policy"})
        return NumberFormatContract(policy)
    _object(value, {"policy", "type", "pattern"})
    format_type = _string(value["type"])
    if format_type not in {"NUMBER", "PERCENT", "DATE", "TEXT", "CURRENCY"}:
        _fail("NUMBER_FORMAT_TYPE_INVALID")
    return NumberFormatContract(policy, format_type, _string(value["pattern"], nonempty=False))


def _numeric_expectation(
    value: Any,
    user_value: ValueContract,
) -> NumericExpectationContract | None:
    if value is None:
        return None
    if type(value) is not dict or "policy" not in value:
        _fail("NUMERIC_EXPECTATION_INVALID")
    policy = _policy(value["policy"])
    if policy is PresencePolicy.UNSPECIFIED:
        _object(value, {"policy"})
        return None
    if policy is not PresencePolicy.REQUIRED:
        _fail("NUMERIC_EXPECTATION_INVALID")
    _object(value, {"policy", "source", "comparison", "mismatch_classification"})
    source = _string(value["source"])
    comparison = _string(value["comparison"])
    mismatch = _string(value["mismatch_classification"])
    if (
        source != "CANONICAL_AUTHORED_SEED"
        or comparison != "EXACT_FINITE_EFFECTIVE_NUMBER_VALUE"
        or mismatch != "CANONICAL_FIXTURE_SOURCE_DRIFT"
        or user_value.policy is not PresencePolicy.REQUIRED
        or user_value.value_type != "NUMBER"
        or type(user_value.value) is not Decimal
    ):
        _fail("NUMERIC_EXPECTATION_INVALID")
    return NumericExpectationContract(source, comparison, mismatch)


def _simple_policy_object(value: Any, allowed_required_fields: Mapping[str, set[str]]) -> Mapping[str, Any]:
    if type(value) is not dict or "policy" not in value:
        _fail("POLICY_OBJECT_INVALID")
    policy = _policy(value["policy"])
    fields = allowed_required_fields.get(policy.value)
    if fields is None:
        _fail("POLICY_OBJECT_INVALID")
    _object(value, {"policy"} | fields)
    return MappingProxyType(dict(value))


def _cell(value: Any) -> FixtureCell:
    raw = _object(
        value,
        {
            "coordinate", "authored_state", "user_entered_value", "formula", "number_format",
            "expected_components", "presence_policies", "derived_state", "merge_semantics",
            "sparse_semantics", "component_specific_metadata",
        },
        {"numeric_expectation"},
    )
    coordinate = _coordinate(raw["coordinate"])
    try:
        authored_state = AuthoredState(_string(raw["authored_state"]))
    except ValueError:
        _fail("AUTHORED_STATE_INVALID")
    user_value = _value_contract(raw["user_entered_value"], "user_entered_value")
    numeric_expectation = _numeric_expectation(raw.get("numeric_expectation"), user_value)
    formula = _formula_contract(raw["formula"])
    number_format = _number_format(raw["number_format"])

    if type(raw["expected_components"]) is not list:
        _fail("EXPECTED_COMPONENTS_INVALID")
    components: list[ExpectedComponent] = []
    seen: set[str] = set()
    for item in raw["expected_components"]:
        item = _object(item, {"component", "policy"}, {"value"})
        component = _string(item["component"])
        if component not in _COMPONENTS or component in seen:
            _fail("DUPLICATE_OR_UNKNOWN_COMPONENT")
        seen.add(component)
        policy = _policy(item["policy"])
        if policy is PresencePolicy.REQUIRED:
            _object(item, {"component", "policy", "value"})
            component_value = _string(item["value"], nonempty=False)
        else:
            _object(item, {"component", "policy"})
            component_value = None
        components.append(ExpectedComponent(component, policy, component_value))

    policies = _object(raw["presence_policies"], {"visibility"})
    visibility_policy = _policy(policies["visibility"])
    derived = _simple_policy_object(
        raw["derived_state"],
        {"UNSPECIFIED": set(), "PROHIBITED": set(), "REQUIRED": {"expectation", "host_coordinate", "host_formula", "relationship", "api_proves_spill_linkage"}},
    )
    if derived["policy"] == "REQUIRED":
        if _string(derived["expectation"]) != "NON_AUTHORED_DYNAMIC_RESULT_AT_EXPECTED_COORDINATE":
            _fail("DERIVED_STATE_INVALID")
        if (
            _coordinate(derived["host_coordinate"]) != "O1"
            or _string(derived["host_formula"]) != "=SEQUENCE(1,2)"
            or _string(derived["relationship"]) != "RIGHT_ADJACENT_DYNAMIC_SPILL_NEIGHBOR"
            or _bool(derived["api_proves_spill_linkage"]) is not False
        ):
            _fail("DERIVED_STATE_INVALID")
    merge = _simple_policy_object(
        raw["merge_semantics"],
        {"UNSPECIFIED": set(), "PROHIBITED": set(), "REQUIRED": {"expectation"}},
    )
    sparse_raw = raw["sparse_semantics"]
    if type(sparse_raw) is not dict or "policy" not in sparse_raw:
        _fail("POLICY_OBJECT_INVALID")
    sparse_policy = _policy(sparse_raw["policy"])
    if sparse_policy is PresencePolicy.REQUIRED and sparse_raw.get("expectation") == "TRAILING_DYNAMIC_SPILL_NEIGHBOR_MAY_BE_OMITTED":
        _object(
            sparse_raw,
            {"policy", "expectation", "host_coordinate", "omission_classification", "synthesize_missing_cell_data", "omission_means_authored_absence"},
        )
        sparse = MappingProxyType(dict(sparse_raw))
        if (
            _coordinate(sparse["host_coordinate"]) != "O1"
            or _string(sparse["omission_classification"]) != "EXPECTED_TRAILING_OMISSION"
            or _bool(sparse["synthesize_missing_cell_data"]) is not False
            or _bool(sparse["omission_means_authored_absence"]) is not False
        ):
            _fail("SPARSE_SEMANTICS_INVALID")
    else:
        sparse = _simple_policy_object(
            sparse_raw,
            {"UNSPECIFIED": set(), "PROHIBITED": set(), "REQUIRED": {"expectation", "omitted_intermediate_cells_are_not_failures"}},
        )
    if merge["policy"] == "REQUIRED" and _string(merge["expectation"]) != "MERGED_RANGE_HOST":
        _fail("MERGE_SEMANTICS_INVALID")
    if sparse["policy"] == "REQUIRED" and sparse.get("expectation") == "LARGE_COORDINATE_SENTINEL":
        _bool(sparse["omitted_intermediate_cells_are_not_failures"])
    elif sparse["policy"] == "REQUIRED" and sparse.get("expectation") != "TRAILING_DYNAMIC_SPILL_NEIGHBOR_MAY_BE_OMITTED":
        _fail("SPARSE_SEMANTICS_INVALID")

    metadata_raw = _object(raw["component_specific_metadata"], set(), set(_COMPONENTS))
    metadata: dict[str, Mapping[str, str]] = {}
    for component, item in metadata_raw.items():
        if component != "CELL_RICH_TEXT_LINK":
            _fail("COMPONENT_METADATA_INVALID")
        item = _object(item, {"structure_ref"})
        metadata[component] = MappingProxyType({"structure_ref": _string(item["structure_ref"])})

    if authored_state is AuthoredState.UNAUTHORED:
        if user_value.policy is not PresencePolicy.PROHIBITED or formula.policy is not PresencePolicy.PROHIBITED:
            _fail("UNAUTHORED_VALUE_POLICY_INVALID")
    elif authored_state is AuthoredState.AUTHORED:
        if user_value.policy is not PresencePolicy.REQUIRED and formula.policy is not PresencePolicy.REQUIRED:
            _fail("AUTHORED_STATE_WITHOUT_AUTHORED_VALUE")

    return FixtureCell(
        coordinate, authored_state, user_value, numeric_expectation, formula, number_format, tuple(components),
        visibility_policy, derived, merge, sparse, MappingProxyType(metadata),
    )


def _structure(value: Any) -> tuple[Mapping[str, Any], list[StructuralAssertion], set[str]]:
    if type(value) is not dict or "kind" not in value or "structure_id" not in value:
        _fail("STRUCTURE_INVALID")
    kind = _string(value["kind"])
    structure_id = _string(value["structure_id"])
    assertions: list[StructuralAssertion] = []
    if kind == "RICH_TEXT_LINKS":
        raw = _object(value, {"kind", "structure_id", "coordinate", "assertions", "runs"})
        coordinate = _coordinate(raw["coordinate"])
        if raw["structure_id"] != "E1/RICH_TEXT_LINKS" or coordinate != "E1":
            _fail("STRUCTURE_ID_INVALID")
        if type(raw["assertions"]) is not list or type(raw["runs"]) is not list:
            _fail("STRUCTURE_INVALID")
        local_ids: set[str] = set()
        for item in raw["assertions"]:
            item = _object(item, {"id", "assertion_type"}, {"expected_count", "expected_targets"})
            assertion_id = _string(item["id"])
            assertion_type = _string(item["assertion_type"])
            if assertion_type == "RICH_TEXT_LINK_COUNT":
                _object(item, {"id", "assertion_type", "expected_count"})
                expected_count = _int(item["expected_count"], minimum=1)
                assertion = StructuralAssertion(assertion_id, assertion_type, MigrationClass.SPEC_BACKED_STRUCTURALLY, coordinate=coordinate, expected_count=expected_count)
            elif assertion_type == "RICH_TEXT_LINK_ORDER":
                _object(item, {"id", "assertion_type", "expected_targets"})
                targets = item["expected_targets"]
                if type(targets) is not list or not targets:
                    _fail("RICH_TEXT_EXPECTATION_INVALID")
                parsed_targets = tuple(_string(target) for target in targets)
                assertion = StructuralAssertion(assertion_id, assertion_type, MigrationClass.SPEC_BACKED_STRUCTURALLY, coordinate=coordinate, expected_targets=parsed_targets)
            else:
                _fail("STRUCTURAL_ASSERTION_TYPE_INVALID")
            if assertion_id in local_ids:
                _fail("DUPLICATE_ASSERTION_ID")
            local_ids.add(assertion_id)
            assertions.append(assertion)
        if len(raw["runs"]) != 2:
            _fail("RICH_TEXT_RUNS_INVALID")
        run_ids: set[int] = set()
        for run in raw["runs"]:
            run = _object(run, {"run_ordinal", "utf16_start", "utf16_end", "target"})
            ordinal = _int(run["run_ordinal"])
            start = _int(run["utf16_start"])
            end = _int(run["utf16_end"], minimum=1)
            _string(run["target"])
            if ordinal in run_ids or end <= start:
                _fail("RICH_TEXT_RUNS_INVALID")
            run_ids.add(ordinal)
    elif kind == "MERGED_RANGE":
        raw = _object(value, {"kind", "structure_id", "range", "assertion", "host_coordinate", "prohibited_component_at"})
        range_value = _range(raw["range"])
        assertion_raw = _object(raw["assertion"], {"id", "assertion_type", "expected_semantics"})
        if assertion_raw["assertion_type"] != "MERGED_RANGE" or assertion_raw["expected_semantics"] != "MERGED":
            _fail("MERGE_ASSERTION_INVALID")
        assertion_id = _string(assertion_raw["id"])
        host = _coordinate(raw["host_coordinate"])
        prohibited = _object(raw["prohibited_component_at"], {"coordinate", "component"})
        prohibited_coord = _coordinate(prohibited["coordinate"])
        prohibited_component = _string(prohibited["component"])
        if prohibited_component not in _COMPONENTS or structure_id != assertion_id or range_value != "A6:B6" or host != "A6" or prohibited_coord != "B6":
            _fail("MERGE_ASSERTION_INVALID")
        assertions.append(StructuralAssertion(assertion_id, "MERGED_RANGE", MigrationClass.SPEC_BACKED_STRUCTURALLY, coordinate=host, component=prohibited_component, expected_semantics="MERGED", related_coordinate=prohibited_coord))
    elif kind == "DERIVED_RESULT":
        raw = _object(value, {"kind", "structure_id", "coordinate", "assertion", "expected_derived_state", "host_coordinate", "api_proves_spill_linkage"})
        assertion_raw = _object(raw["assertion"], {"id", "assertion_type", "component"})
        assertion_id = _string(assertion_raw["id"])
        coordinate = _coordinate(raw["coordinate"])
        component = _string(assertion_raw["component"])
        if (
            raw["structure_id"] != assertion_id
            or assertion_raw["assertion_type"] != "COMPONENT_PROHIBITED"
            or coordinate != "P1"
            or component != "CELL_FORMULA"
            or raw["expected_derived_state"] != "NON_AUTHORED_DYNAMIC_RESULT_AT_EXPECTED_COORDINATE"
            or _coordinate(raw["host_coordinate"]) != "O1"
            or _bool(raw["api_proves_spill_linkage"]) is not False
        ):
            _fail("DERIVED_RESULT_INVALID")
        assertions.append(StructuralAssertion(assertion_id, "COMPONENT_PROHIBITED", MigrationClass.SPEC_BACKED_STRUCTURALLY, coordinate=coordinate, component=component))
    elif kind == "COMPONENT_TYPE_COVERAGE":
        raw = _object(value, {"kind", "structure_id", "assertions"})
        if structure_id != "TYPE_COVERAGE" or type(raw["assertions"]) is not list:
            _fail("TYPE_COVERAGE_INVALID")
        seen_components: set[str] = set()
        for item in raw["assertions"]:
            item = _object(item, {"id", "assertion_type", "component"})
            assertion_id = _string(item["id"])
            component = _string(item["component"])
            if item["assertion_type"] != "COMPONENT_TYPE_PRESENT" or component not in _COMPONENTS or component in seen_components or assertion_id != "TYPE/" + component:
                _fail("TYPE_COVERAGE_INVALID")
            seen_components.add(component)
            assertions.append(StructuralAssertion(assertion_id, "COMPONENT_TYPE_PRESENT", MigrationClass.SPEC_BACKED_STRUCTURALLY, component=component))
        if seen_components != set(_COMPONENTS):
            _fail("TYPE_COVERAGE_INVALID")
    else:
        _fail("STRUCTURE_KIND_UNSUPPORTED")
    return _freeze(raw), assertions, {a.assertion_id for a in assertions}


def load_fixture_spec(path: str | Path | None = None) -> FixtureSpec:
    """Load and validate the single canonical spec; never contacts a service."""
    spec_path = Path(path).resolve() if path is not None else DEFAULT_SPEC_PATH.resolve()
    try:
        raw_text = spec_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        _fail("SPEC_UNAVAILABLE")
    try:
        raw = json.loads(
            raw_text,
            parse_float=Decimal,
            parse_int=int,
            parse_constant=_reject_constant,
            object_pairs_hook=_pairs_no_duplicates,
        )
    except FixtureContractError:
        raise
    except (json.JSONDecodeError, ValueError, TypeError):
        _fail("JSON_INVALID")
    _reject_nulls(raw)
    raw = _object(
        raw,
        {
            "spec_schema_version", "fixture_contract_version", "fixture_alias", "target_sheet_ordinal",
            "spreadsheet", "cells", "structures", "validation_policies",
        },
    )
    schema_version = _int(raw["spec_schema_version"], minimum=1)
    contract_version = _int(raw["fixture_contract_version"], minimum=1)
    if schema_version != 1:
        _fail("SCHEMA_VERSION_UNSUPPORTED")
    if contract_version != 2:
        _fail("CONTRACT_VERSION_UNSUPPORTED")
    alias = _string(raw["fixture_alias"])
    if alias != "GSHEETS_VALIDATION_V1":
        _fail("FIXTURE_ALIAS_INVALID")
    sheet_ordinal = _int(raw["target_sheet_ordinal"])
    if sheet_ordinal != 0:
        _fail("SHEET_ORDINAL_INVALID")
    spreadsheet = _object(raw["spreadsheet"], {"locale", "timeZone"})
    locale = _string(spreadsheet["locale"])
    time_zone = _string(spreadsheet["timeZone"])
    if locale != "pt_BR" or time_zone != "America/Sao_Paulo":
        _fail("CANONICAL_LOCALE_INVALID")

    if type(raw["cells"]) is not list or not raw["cells"]:
        _fail("CELLS_INVALID")
    cells = tuple(_cell(item) for item in raw["cells"])
    cell_coordinates = [cell.coordinate for cell in cells]
    if len(set(cell_coordinates)) != len(cell_coordinates):
        _fail("DUPLICATE_COORDINATE")
    if cell_coordinates != sorted(cell_coordinates, key=_coordinate_sort_key):
        _fail("CELL_ORDER_INVALID")
    if set(cell_coordinates) != {
        "A1", "B1", "C1", "D1", "E1", "F1", "G1", "H1", "I1", "J1", "K1", "L1",
        "M1", "N1", "O1", "P1", "A4", "A6", "Z900",
    }:
        _fail("CANONICAL_CELL_SET_INVALID")

    if type(raw["structures"]) is not list:
        _fail("STRUCTURES_INVALID")
    structures: list[Mapping[str, Any]] = []
    structural: list[StructuralAssertion] = []
    structure_ids: set[str] = set()
    assertion_ids: set[str] = set()
    for item in raw["structures"]:
        parsed, current_assertions, current_ids = _structure(item)
        structure_id = _string(parsed["structure_id"])
        if structure_id in structure_ids or current_ids & assertion_ids:
            _fail("DUPLICATE_STRUCTURE_OR_ASSERTION_ID")
        structure_ids.add(structure_id)
        assertion_ids |= current_ids
        structures.append(parsed)
        structural.extend(current_assertions)
    for cell in cells:
        for metadata in cell.component_specific_metadata.values():
            if metadata["structure_ref"] not in structure_ids:
                _fail("COMPONENT_METADATA_REFERENCE_INVALID")

    direct: list[tuple[str, str, str]] = []
    direct_ids: set[str] = set()
    for cell in cells:
        for expected in cell.expected_components:
            if expected.policy is PresencePolicy.REQUIRED:
                assert expected.value is not None
                assertion_id = f"{cell.coordinate}/{expected.component}"
                if assertion_id in direct_ids:
                    _fail("DUPLICATE_ASSERTION_ID")
                direct_ids.add(assertion_id)
                direct.append((cell.coordinate, expected.component, expected.value))
    numeric_expectations: list[NumericSeedExpectation] = []
    numeric_ids: set[str] = set()
    for cell in cells:
        if cell.numeric_expectation is None:
            continue
        seed = cell.user_entered_value.value
        assert type(seed) is Decimal
        numeric_id = f"{cell.coordinate}/NUMERIC_EXPECTATION"
        if numeric_id in numeric_ids:
            _fail("DUPLICATE_ASSERTION_ID")
        numeric_ids.add(numeric_id)
        numeric_expectations.append(
            NumericSeedExpectation(
                cell.coordinate,
                seed,
                cell.numeric_expectation.source,
                cell.numeric_expectation.comparison,
                cell.numeric_expectation.mismatch_classification,
            )
        )
    if direct_ids & assertion_ids or numeric_ids & (direct_ids | assertion_ids):
        _fail("DUPLICATE_ASSERTION_ID")
    all_ids = tuple(
        [f"{coordinate}/{component}" for coordinate, component, _ in direct]
        + [f"{item.coordinate}/NUMERIC_EXPECTATION" for item in numeric_expectations]
        + [a.assertion_id for a in structural]
    )
    if len(all_ids) != len(set(all_ids)):
        _fail("DUPLICATE_ASSERTION_ID")

    policies = _object(raw["validation_policies"], {"display_semantics", "acceptance_semantics_changed", "numeric_expectation_semantics", "assertion_migration", "locale_precondition", "operational_ranges", "repair_safety"})
    display_semantics = _string(policies["display_semantics"])
    acceptance_changed = _bool(policies["acceptance_semantics_changed"])
    numeric_semantics = _string(policies["numeric_expectation_semantics"])
    if (
        display_semantics != "EXACT_ONLY_WHERE_CONTRACTED_NUMERIC_DISPLAY_OBSERVATION_ONLY"
        or numeric_semantics != "CANONICAL_AUTHORED_SEED_EQUALS_EXACT_FINITE_EFFECTIVE_NUMBER_VALUE"
        or acceptance_changed
    ):
        _fail("DISPLAY_SEMANTICS_INVALID")
    migration = _object(policies["assertion_migration"], {"expected_total", "classification_counts"})
    expected_total = _int(migration["expected_total"], minimum=1)
    counts_raw = _object(migration["classification_counts"], {"SPEC_BACKED_DIRECTLY", "SPEC_BACKED_STRUCTURALLY", "CANONICAL_NUMERIC_SEED", "HARNESS_BEHAVIOR_ONLY", "NEEDS_CONTRACT_COMPLETION"})
    counts = {key: _int(value) for key, value in counts_raw.items()}
    actual_counts = {
        "SPEC_BACKED_DIRECTLY": len(direct),
        "SPEC_BACKED_STRUCTURALLY": len(structural),
        "CANONICAL_NUMERIC_SEED": len(numeric_expectations),
        "HARNESS_BEHAVIOR_ONLY": 0,
        "NEEDS_CONTRACT_COMPLETION": 0,
    }
    if (
        expected_total != len(all_ids)
        or counts != actual_counts
        or len(all_ids) != 33
        or len(direct) != 22
        or len(structural) != 9
        or len(numeric_expectations) != 2
    ):
        _fail("ASSERTION_MIGRATION_INVALID")

    locale_policy = _object(
        policies["locale_precondition"],
        {"assertion_id", "expected_locale", "expected_time_zone", "mismatch_classification", "time_zone_mismatch_classification", "real_validation_requires_verified_state", "preflight_may_mutate_locale", "production_reader_locale_agnostic"},
    )
    locale_id = _string(locale_policy["assertion_id"])
    mismatch = _string(locale_policy["mismatch_classification"])
    time_zone_mismatch = _string(locale_policy["time_zone_mismatch_classification"])
    if (
        locale_id != "FIXTURE_LOCALE_PRECONDITION"
        or locale_policy["expected_locale"] != locale
        or locale_policy["expected_time_zone"] != time_zone
        or mismatch != "FIXTURE_LOCALE_MISMATCH"
        or time_zone_mismatch != "FIXTURE_TIME_ZONE_MISMATCH"
        or not _bool(locale_policy["real_validation_requires_verified_state"])
        or _bool(locale_policy["preflight_may_mutate_locale"])
        or not _bool(locale_policy["production_reader_locale_agnostic"])
    ):
        _fail("LOCALE_PRECONDITION_INVALID")
    if type(policies["operational_ranges"]) is not list:
        _fail("OPERATIONAL_RANGES_INVALID")
    ranges = tuple(_string(item) for item in policies["operational_ranges"])
    if ranges != ("A1:P1", "A4", "A6:B6", "Z900"):
        _fail("OPERATIONAL_RANGES_INVALID")
    repair = _object(policies["repair_safety"], {"K1_L1_preserve_number_formats", "P1_direct_write", "O1_same_formula_rewrite", "locale_mutation"})
    if (
        not _bool(repair["K1_L1_preserve_number_formats"])
        or repair["P1_direct_write"] != "PROHIBITED"
        or repair["O1_same_formula_rewrite"] != "REQUIRES_CONTROLLED_REAL_TEST"
        or repair["locale_mutation"] != "REQUIRES_FUTURE_EXPLICIT_REPAIR_AUTHORIZATION"
    ):
        _fail("REPAIR_SAFETY_INVALID")

    _validate_canonical_cells(cells)
    return FixtureSpec(
        path=spec_path,
        spec_schema_version=schema_version,
        fixture_contract_version=contract_version,
        fixture_alias=alias,
        target_sheet_ordinal=sheet_ordinal,
        locale=locale,
        time_zone=time_zone,
        cells=cells,
        structures=tuple(structures),
        direct_expectations=tuple(direct),
        numeric_expectations=tuple(numeric_expectations),
        structural_assertions=tuple(structural),
        assertion_ids=all_ids,
        migration_counts=MappingProxyType(counts),
        operational_ranges=ranges,
        locale_mismatch_classification=mismatch,
        time_zone_mismatch_classification=time_zone_mismatch,
        display_semantics=display_semantics,
        acceptance_semantics_changed=acceptance_changed,
        repair_safety=MappingProxyType(dict(repair)),
    )


def _coordinate_sort_key(coordinate: str) -> tuple[int, int]:
    match = _COORDINATE_RE.fullmatch(coordinate)
    assert match is not None
    column = 0
    for char in match.group(1):
        column = column * 26 + ord(char) - 64
    return int(match.group(2)), column


def _has_expected(cell: FixtureCell, component: str, value: str) -> bool:
    return any(
        item.component == component
        and item.policy is PresencePolicy.REQUIRED
        and item.value == value
        for item in cell.expected_components
    )


def _validate_canonical_cells(cells: tuple[FixtureCell, ...]) -> None:
    by_coordinate = {cell.coordinate: cell for cell in cells}
    for cell in cells:
        formula_components = [item for item in cell.expected_components if item.component == "CELL_FORMULA"]
        if cell.formula.policy is PresencePolicy.REQUIRED:
            if len(formula_components) != 1 or formula_components[0].policy is not PresencePolicy.REQUIRED or formula_components[0].value != cell.formula.value:
                _fail("FORMULA_COMPONENT_CONTRACT_INVALID")
        elif cell.formula.policy is PresencePolicy.PROHIBITED:
            if any(item.policy is PresencePolicy.REQUIRED for item in formula_components):
                _fail("FORMULA_COMPONENT_CONTRACT_INVALID")
    for coordinate in ("A4", "J1"):
        if by_coordinate[coordinate].visibility_policy is not PresencePolicy.UNSPECIFIED:
            _fail("VISIBILITY_ASSERTION_NOT_ALLOWED")
    for coordinate in ("M1", "N1"):
        cell = by_coordinate[coordinate]
        if cell.user_entered_value.policy is not PresencePolicy.UNSPECIFIED or cell.number_format.policy is not PresencePolicy.UNSPECIFIED:
            _fail("UNDECLARED_SEED_CONTRACT")

    k1 = by_coordinate["K1"]
    if (
        k1.user_entered_value.policy is not PresencePolicy.REQUIRED
        or k1.user_entered_value.value_type != "NUMBER"
        or k1.user_entered_value.value != Decimal("1234.5")
        or k1.numeric_expectation is None
        or k1.numeric_expectation.source != "CANONICAL_AUTHORED_SEED"
        or k1.numeric_expectation.comparison != "EXACT_FINITE_EFFECTIVE_NUMBER_VALUE"
        or k1.numeric_expectation.mismatch_classification != "CANONICAL_FIXTURE_SOURCE_DRIFT"
        or k1.number_format.policy is not PresencePolicy.REQUIRED
        or k1.number_format.format_type != "NUMBER"
        or k1.number_format.pattern != "0.00"
        or any(item.policy is PresencePolicy.REQUIRED for item in k1.expected_components if item.component == "CELL_DISPLAY")
    ):
        _fail("K1_CONTRACT_INVALID")
    l1 = by_coordinate["L1"]
    if (
        l1.user_entered_value.policy is not PresencePolicy.REQUIRED
        or l1.user_entered_value.value_type != "NUMBER"
        or l1.user_entered_value.value != Decimal("0.125")
        or l1.numeric_expectation is None
        or l1.numeric_expectation.source != "CANONICAL_AUTHORED_SEED"
        or l1.numeric_expectation.comparison != "EXACT_FINITE_EFFECTIVE_NUMBER_VALUE"
        or l1.numeric_expectation.mismatch_classification != "CANONICAL_FIXTURE_SOURCE_DRIFT"
        or l1.number_format.policy is not PresencePolicy.REQUIRED
        or l1.number_format.format_type != "PERCENT"
        or l1.number_format.pattern != "0.0%"
        or any(item.policy is PresencePolicy.REQUIRED for item in l1.expected_components if item.component == "CELL_DISPLAY")
    ):
        _fail("L1_CONTRACT_INVALID")
    o1 = by_coordinate["O1"]
    if o1.formula.policy is not PresencePolicy.REQUIRED or o1.formula.value != "=SEQUENCE(1,2)":
        _fail("O1_CONTRACT_INVALID")
    p1 = by_coordinate["P1"]
    if (
        p1.authored_state is not AuthoredState.UNAUTHORED
        or p1.user_entered_value.policy is not PresencePolicy.PROHIBITED
        or p1.formula.policy is not PresencePolicy.PROHIBITED
        or p1.derived_state.get("expectation") != "NON_AUTHORED_DYNAMIC_RESULT_AT_EXPECTED_COORDINATE"
        or p1.derived_state.get("host_coordinate") != "O1"
        or p1.derived_state.get("host_formula") != "=SEQUENCE(1,2)"
        or p1.derived_state.get("relationship") != "RIGHT_ADJACENT_DYNAMIC_SPILL_NEIGHBOR"
        or p1.derived_state.get("api_proves_spill_linkage") is not False
        or p1.sparse_semantics.get("expectation") != "TRAILING_DYNAMIC_SPILL_NEIGHBOR_MAY_BE_OMITTED"
        or p1.sparse_semantics.get("omission_classification") != "EXPECTED_TRAILING_OMISSION"
        or p1.sparse_semantics.get("synthesize_missing_cell_data") is not False
        or p1.sparse_semantics.get("omission_means_authored_absence") is not False
        or not _has_expected(p1, "CELL_DISPLAY", "2")
    ):
        _fail("P1_CONTRACT_INVALID")


def locale_precondition_classification(
    verified_locale: str | None,
    *,
    verified: bool,
    verified_time_zone: str | None,
) -> str:
    """Classify regional metadata without accessing or mutating a spreadsheet."""
    spec = load_fixture_spec()
    if (
        type(verified) is not bool
        or not verified
        or type(verified_locale) is not str
        or type(verified_time_zone) is not str
    ):
        return "FIXTURE_LOCALE_UNVERIFIED"
    if verified_locale != spec.locale:
        return spec.locale_mismatch_classification
    if verified_time_zone != spec.time_zone:
        return spec.time_zone_mismatch_classification
    return "PASS"
