from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import re

import httpx
import pytest

from validation.fixtures import canonical_state_repair as repair


_FILE_ID = "synthetic-canonical-fixture-0001"
_MODIFIED_A_B = "2026-09-30T10:00:00.000Z"
_DUMMY_TOKEN = "offline-test-token-only"


def _drive(
    *,
    file_id: str = _FILE_ID,
    mime_type: str = repair.SPREADSHEET_MIME_TYPE,
    modified_time: str | None = _MODIFIED_A_B,
    trashed: bool = False,
) -> repair.DriveMetadataObservation:
    return repair.DriveMetadataObservation(file_id, mime_type, modified_time, trashed)


def _cell(
    target: repair.RepairTarget,
    value: object,
    *,
    value_type: str = "NUMBER",
    effective_value: object | None = None,
    effective_type: str = "NUMBER",
    format_type: str | None = None,
    format_pattern: str | None = None,
    display: str | None = None,
    present: bool = True,
    effective_present: bool = True,
    mapping_established: bool = True,
) -> repair.CellObservation:
    row, column = repair._GRID_ORIGIN[target]
    canonical_format_type, canonical_format_pattern = repair._CANONICAL_FORMATS[target]
    return repair.CellObservation(
        coordinate=target,
        user_entered_value_present=present,
        user_entered_value_type=value_type,
        user_entered_number_value=value,
        effective_value_present=effective_present,
        effective_value_type=effective_type,
        effective_number_value=value if effective_value is None else effective_value,
        number_format_type=canonical_format_type if format_type is None else format_type,
        number_format_pattern=canonical_format_pattern if format_pattern is None else format_pattern,
        sheet_title=repair.CANONICAL_SHEET_TITLE,
        sheet_id=17,
        start_row_index=row,
        start_column_index=column,
        coordinate_mapping_established=mapping_established,
        formatted_display=display,
    )


def _read(
    k1: object = 1234.5,
    l1: object = 0.125,
    *,
    k1_options: dict[str, object] | None = None,
    l1_options: dict[str, object] | None = None,
    file_id: str = _FILE_ID,
    sheet_title: str = repair.CANONICAL_SHEET_TITLE,
    sheet_id: int = 17,
    cells: tuple[repair.CellObservation, ...] | None = None,
) -> repair.SpreadsheetReadObservation:
    if cells is None:
        cells = (
            _cell(repair.RepairTarget.K1, k1, **(k1_options or {})),
            _cell(repair.RepairTarget.L1, l1, **(l1_options or {})),
        )
    return repair.SpreadsheetReadObservation(file_id, sheet_title, sheet_id, cells)


def _plan(
    k1: object = 1234.5,
    l1: object = 0.125,
    *,
    k1_options: dict[str, object] | None = None,
    l1_options: dict[str, object] | None = None,
    drive_a: repair.DriveMetadataObservation | None = None,
    drive_b: repair.DriveMetadataObservation | None = None,
    requested_file_id: str = _FILE_ID,
    spreadsheet_read: repair.SpreadsheetReadObservation | None = None,
) -> repair.CanonicalRepairPlan:
    return repair.build_canonical_repair_plan(
        requested_file_id=requested_file_id,
        drive_a=drive_a or _drive(),
        spreadsheet_read=spreadsheet_read or _read(k1, l1, k1_options=k1_options, l1_options=l1_options),
        drive_b=drive_b or _drive(),
    )


def _transport(
    plan: repair.CanonicalRepairPlan,
    handler,
) -> repair.CanonicalStateRepairTransport:
    return repair.CanonicalStateRepairTransport(
        plan,
        access_token=_DUMMY_TOKEN,
        http_transport=httpx.MockTransport(handler),
    )


def _canonical_readback(
    k1: object = 1234.5,
    l1: object = 0.125,
    *,
    k1_options: dict[str, object] | None = None,
    l1_options: dict[str, object] | None = None,
) -> repair.SpreadsheetReadObservation:
    return _read(k1, l1, k1_options=k1_options, l1_options=l1_options)


def test_both_canonical_cells_build_noop_plan():
    plan = _plan()
    assert plan.status is repair.RepairStatus.NO_OP_ALREADY_CANONICAL
    assert plan.targets == ()
    assert tuple(item.state for item in plan.assessments) == (
        repair.RepairStatus.CANONICAL,
        repair.RepairStatus.CANONICAL,
    )


def test_noop_executor_sends_zero_writes():
    plan = _plan()
    transport = _transport(plan, lambda request: pytest.fail("NO-OP sent an HTTP request"))
    try:
        result = repair.CanonicalStateRepairExecutor(transport).execute(plan)
        assert result.status is repair.RepairStatus.NO_OP_ALREADY_CANONICAL
        assert result.writes_attempted == 0
        assert transport.write_sends_attempted == 0
    finally:
        transport.close()


def test_only_k1_drifted_plan_contains_only_k1():
    plan = _plan(k1=9.25)
    assert plan.status is repair.RepairStatus.WRITE_REQUIRED
    assert plan.target_coordinates == ("K1",)
    assert plan.numeric_updates == ((repair.RepairTarget.K1, 1234.5),)


def test_only_l1_drifted_plan_contains_only_l1():
    plan = _plan(l1=0.5)
    assert plan.status is repair.RepairStatus.WRITE_REQUIRED
    assert plan.target_coordinates == ("L1",)
    assert plan.numeric_updates == ((repair.RepairTarget.L1, 0.125),)


@pytest.mark.parametrize(
    ("k1", "l1", "expected_coordinate", "expected_column", "expected_value"),
    [
        (-1.0, 0.125, "K1", 10, 1234.5),
        (1234.5, 2.0, "L1", 11, 0.125),
    ],
)
def test_single_cell_write_contains_only_the_drifted_target(
    k1, l1, expected_coordinate, expected_column, expected_value
):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, request=request, json={})

    plan = _plan(k1, l1)
    transport = _transport(plan, handler)
    try:
        result = repair.CanonicalStateRepairExecutor(transport).execute(plan)
        payload = json.loads(requests[0].content)
        update = payload["requests"][0]["updateCells"]
        assert result.status is repair.RepairStatus.WRITE_COMPLETE
        assert plan.target_coordinates == (expected_coordinate,)
        assert update["range"]["startColumnIndex"] == expected_column
        assert update["range"]["endColumnIndex"] == expected_column + 1
        assert len(update["rows"][0]["values"]) == 1
        assert update["rows"][0]["values"][0]["userEnteredValue"]["numberValue"] == expected_value
        assert len(requests) == 1
    finally:
        transport.close()


def test_both_drifted_plan_contains_both_canonical_targets():
    plan = _plan(k1=-8.0, l1=2.5)
    assert plan.status is repair.RepairStatus.WRITE_REQUIRED
    assert plan.target_coordinates == ("K1", "L1")
    assert plan.max_targets == 2
    assert plan.numeric_updates == (
        (repair.RepairTarget.K1, 1234.5),
        (repair.RepairTarget.L1, 0.125),
    )


def test_both_drifted_cells_use_one_write_transaction():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, request=request, json={"replies": [{"updateCells": {}}]})

    plan = _plan(k1=1.0, l1=3.0)
    transport = _transport(plan, handler)
    try:
        result = repair.CanonicalStateRepairExecutor(transport).execute(plan)
        assert result.status is repair.RepairStatus.WRITE_COMPLETE
        assert result.writes_attempted == 1
        assert result.retries == 0
        assert result.rollback_writes == 0
        assert len(requests) == 1
        assert transport.write_sends_attempted == 1
    finally:
        transport.close()


def test_canonical_numeric_values_are_exact_numbers():
    plan = _plan(k1=4.0, l1=0.75)
    assert plan.numeric_updates == (
        (repair.RepairTarget.K1, 1234.5),
        (repair.RepairTarget.L1, 0.125),
    )
    assert all(type(value) is float for _, value in plan.numeric_updates)


def test_localized_display_is_never_used_as_a_write_value():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, request=request, json={})

    plan = _plan(k1=-2.0, k1_options={"display": "1234,50"})
    transport = _transport(plan, handler)
    try:
        result = repair.CanonicalStateRepairExecutor(transport).execute(plan)
        payload = json.loads(requests[0].content)
        assert result.status is repair.RepairStatus.WRITE_COMPLETE
        value = payload["requests"][0]["updateCells"]["rows"][0]["values"][0]["userEnteredValue"]["numberValue"]
        assert value == 1234.5
        assert type(value) is float
        assert "1234,50" not in requests[0].content.decode("utf-8")
    finally:
        transport.close()


def test_request_field_mask_is_user_entered_value_only():
    plan = _plan(k1=-1.0)
    request = repair._payload_for_plan(plan)["requests"][0]["updateCells"]
    assert request["fields"] == "userEnteredValue"
    assert set(request) == {"range", "rows", "fields"}
    assert set(request["rows"][0]["values"][0]) == {"userEnteredValue"}


def test_number_format_and_other_cell_fields_are_never_written():
    request = repair._payload_for_plan(_plan(k1=-1.0))["requests"][0]["updateCells"]
    encoded = json.dumps(request)
    for forbidden in ("userEnteredFormat", "numberFormat", "formulaValue", "note", "hyperlink", "dataValidation"):
        assert forbidden not in encoded


@pytest.mark.parametrize("coordinate", ["O1", "P1", "M1", "K2"])
def test_noncanonical_coordinate_is_rejected(coordinate):
    extra = repair.CellObservation(
        coordinate=coordinate,
        user_entered_value_present=True,
        user_entered_value_type="NUMBER",
        user_entered_number_value=99.0,
        number_format_type="NUMBER",
        number_format_pattern="0.00",
        sheet_title=repair.CANONICAL_SHEET_TITLE,
        sheet_id=17,
        start_row_index=0,
        start_column_index=14,
        coordinate_mapping_established=True,
    )
    with pytest.raises(repair.PlanningFailure) as exc:
        _plan(spreadsheet_read=_read(cells=(_cell(repair.RepairTarget.K1, -1.0), extra)))
    assert exc.value.status is repair.RepairStatus.IDENTITY_ORIGIN_FAILURE


def test_plan_cannot_be_constructed_or_replaced_with_arbitrary_target_or_value():
    plan = _plan(k1=-1.0)
    with pytest.raises(TypeError):
        repair.CanonicalRepairPlan()
    with pytest.raises(TypeError):
        replace(plan, _targets=(repair.RepairTarget.L1,))
    request = repair._payload_for_plan(plan)
    request["requests"][0]["updateCells"]["rows"][0]["values"][0]["userEnteredValue"]["numberValue"] = 6.0
    with pytest.raises(repair.ControlledTransportError):
        repair.validate_http_boundary(
            method="POST",
            url=f"{repair.SHEETS_API_ROOT}/v4/spreadsheets/{_FILE_ID}:batchUpdate",
            body=json.dumps(request, separators=(",", ":")).encode("utf-8"),
            plan=plan,
        )


def test_arbitrary_coordinate_and_arbitrary_value_are_rejected_at_http_boundary():
    plan = _plan(k1=-1.0)
    valid_url = f"{repair.SHEETS_API_ROOT}/v4/spreadsheets/{_FILE_ID}:batchUpdate"
    original = repair._payload_for_plan(plan)
    coordinate_payload = json.loads(json.dumps(original))
    coordinate_payload["requests"][0]["updateCells"]["range"]["startColumnIndex"] = 14
    value_payload = json.loads(json.dumps(original))
    value_payload["requests"][0]["updateCells"]["rows"][0]["values"][0]["userEnteredValue"]["numberValue"] = 1234.6
    for payload in (coordinate_payload, value_payload):
        with pytest.raises(repair.ControlledTransportError):
            repair.validate_http_boundary(
                method="POST",
                url=valid_url,
                body=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
                plan=plan,
            )


def test_modified_time_a_b_mismatch_blocks_write_plan():
    with pytest.raises(repair.PlanningFailure) as exc:
        _plan(
            k1=-1.0,
            drive_a=_drive(modified_time=_MODIFIED_A_B),
            drive_b=_drive(modified_time="2026-09-30T10:01:00.000Z"),
        )
    assert exc.value.status is repair.RepairStatus.PRE_WRITE_TOCTOU_FAILURE


def test_drive_file_id_a_b_mismatch_blocks_write_plan():
    with pytest.raises(repair.PlanningFailure) as exc:
        _plan(
            k1=-1.0,
            drive_a=_drive(),
            drive_b=_drive(file_id="different-synthetic-id-0001"),
        )
    assert exc.value.status is repair.RepairStatus.PRE_WRITE_TOCTOU_FAILURE


def test_drive_identity_mismatch_blocks_plan():
    with pytest.raises(repair.PlanningFailure) as exc:
        _plan(k1=-1.0, requested_file_id="a-different-synthetic-id-0001")
    assert exc.value.status is repair.RepairStatus.IDENTITY_ORIGIN_FAILURE


def test_drive_mime_mismatch_blocks_plan():
    with pytest.raises(repair.PlanningFailure) as exc:
        _plan(k1=-1.0, drive_b=_drive(mime_type="application/pdf"))
    assert exc.value.status is repair.RepairStatus.IDENTITY_ORIGIN_FAILURE


def test_trashed_drive_metadata_blocks_plan():
    with pytest.raises(repair.PlanningFailure) as exc:
        _plan(k1=-1.0, drive_a=_drive(trashed=True))
    assert exc.value.status is repair.RepairStatus.IDENTITY_ORIGIN_FAILURE


def test_drive_b_trashed_metadata_blocks_plan():
    with pytest.raises(repair.PlanningFailure) as exc:
        _plan(k1=-1.0, drive_b=_drive(trashed=True))
    assert exc.value.status is repair.RepairStatus.IDENTITY_ORIGIN_FAILURE


def test_unestablished_coordinate_mapping_blocks_plan():
    with pytest.raises(repair.PlanningFailure) as exc:
        _plan(k1=-1.0, k1_options={"mapping_established": False})
    assert exc.value.status is repair.RepairStatus.IDENTITY_ORIGIN_FAILURE


@pytest.mark.parametrize(
    ("target", "options"),
    [
        (repair.RepairTarget.K1, {"format_type": "CURRENCY"}),
        (repair.RepairTarget.L1, {"format_pattern": "0.00%"}),
    ],
)
def test_format_mismatch_blocks_write(target, options):
    kwargs = {"k1_options": options} if target is repair.RepairTarget.K1 else {"l1_options": options}
    with pytest.raises(repair.PlanningFailure) as exc:
        _plan(k1=-1.0, **kwargs)
    assert exc.value.status is repair.RepairStatus.FORMAT_MISMATCH


@pytest.mark.parametrize(
    ("target", "options", "expected"),
    [
        (repair.RepairTarget.K1, {"value_type": "STRING"}, repair.RepairStatus.INVALID_K1_STATE),
        (repair.RepairTarget.L1, {"effective_type": "STRING"}, repair.RepairStatus.INVALID_L1_STATE),
    ],
)
def test_nonnumeric_cell_state_blocks_write(target, options, expected):
    kwargs = {"k1_options": options} if target is repair.RepairTarget.K1 else {"l1_options": options}
    with pytest.raises(repair.PlanningFailure) as exc:
        _plan(k1=-1.0, **kwargs)
    assert exc.value.status is expected


def test_missing_effective_value_blocks_write():
    with pytest.raises(repair.PlanningFailure) as exc:
        _plan(k1=-1.0, k1_options={"effective_present": False})
    assert exc.value.status is repair.RepairStatus.INVALID_K1_STATE


def test_inconsistent_user_entered_and_effective_numeric_values_block_write():
    with pytest.raises(repair.PlanningFailure) as exc:
        _plan(k1=4.0, k1_options={"effective_value": 5.0})
    assert exc.value.status is repair.RepairStatus.INVALID_K1_STATE


def test_one_write_transport_failure_does_not_retry():
    sent = []

    def handler(request):
        sent.append(request)
        raise httpx.ConnectError("synthetic offline transport failure", request=request)

    plan = _plan(k1=-1.0)
    transport = _transport(plan, handler)
    try:
        result = repair.CanonicalStateRepairExecutor(transport).execute(plan)
        assert result.status is repair.RepairStatus.WRITE_FAILURE
        assert result.writes_attempted == 1
        assert result.retries == 0
        assert transport.write_sends_attempted == 1
        assert len(sent) == 1
    finally:
        transport.close()


def test_one_write_transport_failure_does_not_rollback():
    sent = []

    def handler(request):
        sent.append(request)
        return httpx.Response(503, request=request, text="bounded offline fixture")

    plan = _plan(l1=-1.0)
    transport = _transport(plan, handler)
    try:
        result = repair.CanonicalStateRepairExecutor(transport).execute(plan)
        assert result.status is repair.RepairStatus.WRITE_FAILURE
        assert result.rollback_writes == 0
        assert len(sent) == 1
        assert transport.write_budget_remaining == 0
    finally:
        transport.close()


def test_write_contract_has_redirects_disabled_and_bounded_response():
    plan = _plan(k1=-1.0)
    transport = _transport(plan, lambda request: httpx.Response(302, request=request))
    try:
        assert transport._client.follow_redirects is False
        assert transport._client.timeout.read == repair.HTTP_TIMEOUT_SECONDS
        assert repair.MAX_RESPONSE_BODY_BYTES == 262144
        result = repair.CanonicalStateRepairExecutor(transport).execute(plan)
        assert result.status is repair.RepairStatus.WRITE_FAILURE
    finally:
        transport.close()


def test_oversized_write_response_fails_closed_with_one_send():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(
            200,
            request=request,
            content=b"x" * (repair.MAX_RESPONSE_BODY_BYTES + 1),
        )

    plan = _plan(k1=-1.0)
    transport = _transport(plan, handler)
    try:
        result = repair.CanonicalStateRepairExecutor(transport).execute(plan)
        assert result.status is repair.RepairStatus.WRITE_FAILURE
        assert result.writes_attempted == 1
        assert transport.write_sends_attempted == 1
        assert len(seen) == 1
    finally:
        transport.close()


def test_post_write_verification_failure_does_not_trigger_another_write():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, request=request, json={})

    plan = _plan(k1=-1.0, l1=-3.0)
    transport = _transport(plan, handler)
    try:
        result = repair.CanonicalStateRepairExecutor(transport).execute(plan)
        assert result.status is repair.RepairStatus.WRITE_COMPLETE
        verification = repair.verify_post_write(
            plan,
            drive_c=_drive(modified_time="2026-09-30T10:02:00.000Z"),
            spreadsheet_readback=_canonical_readback(l1=99.0),
        )
        assert verification.status is repair.RepairStatus.VERIFY_FAILURE
        assert len(requests) == 1
        assert transport.write_sends_attempted == 1
    finally:
        transport.close()


def test_post_write_contract_accepts_changed_drive_modified_time_and_preserves_origin():
    plan = _plan(k1=-1.0, l1=-3.0)
    result = repair.verify_post_write(
        plan,
        drive_c=_drive(modified_time="2026-09-30T10:02:00.000Z"),
        spreadsheet_readback=_canonical_readback(),
    )
    assert result.status is repair.RepairStatus.WRITE_COMPLETE
    assert result.modified_time_change is repair.ModifiedTimeChange.CHANGED_AFTER_WRITE


def test_post_write_contract_accepts_unchanged_drive_modified_time():
    plan = _plan(k1=-1.0)
    result = repair.verify_post_write(
        plan,
        drive_c=_drive(modified_time=_MODIFIED_A_B),
        spreadsheet_readback=_canonical_readback(),
    )
    assert result.status is repair.RepairStatus.WRITE_COMPLETE
    assert result.modified_time_change is repair.ModifiedTimeChange.UNCHANGED


@pytest.mark.parametrize(
    "drive_c",
    [
        _drive(file_id="different-synthetic-id-0001"),
        _drive(mime_type="application/pdf"),
        _drive(trashed=True),
    ],
)
def test_drive_c_identity_mime_and_trashed_are_required(drive_c):
    plan = _plan(k1=-1.0)
    result = repair.verify_post_write(
        plan,
        drive_c=drive_c,
        spreadsheet_readback=_canonical_readback(),
    )
    assert result.status is repair.RepairStatus.VERIFY_FAILURE


def test_post_write_requires_both_numeric_values_formats_and_expected_origin():
    plan = _plan(k1=-1.0)
    invalid_reads = (
        _canonical_readback(k1=9.0),
        _canonical_readback(l1=8.0),
        _canonical_readback(l1_options={"format_type": "NUMBER"}),
        _read(file_id="different-synthetic-id-0001"),
        _read(sheet_title="Other tab"),
    )
    for readback in invalid_reads:
        result = repair.verify_post_write(plan, drive_c=_drive(), spreadsheet_readback=readback)
        assert result.status is repair.RepairStatus.VERIFY_FAILURE


def test_transport_rejects_a_plan_other_than_the_one_it_was_bound_to():
    plan = _plan(k1=-1.0)
    other_plan = _plan(l1=-1.0)
    transport = _transport(plan, lambda request: pytest.fail("unbound plan reached transport"))
    try:
        with pytest.raises(repair.ControlledTransportError):
            repair.CanonicalStateRepairExecutor(transport).execute(other_plan)
    finally:
        transport.close()


def test_public_mcp_tool_count_remains_24_and_validation_repair_is_not_registered():
    root = Path(__file__).resolve().parents[1]
    server_source = (root / "src/google_workspace_admin/server.py").read_text(encoding="utf-8")
    repair_source = Path(repair.__file__).read_text(encoding="utf-8")
    public_tools = re.findall(r"@mcp\.tool\(\)\s*\ndef\s+([A-Za-z_][A-Za-z0-9_]*)", server_source)
    assert len(public_tools) == 24
    assert len(set(public_tools)) == 24
    content_tools = {
        "workspace_drives_list",
        "workspace_drive_get",
        "workspace_drive_files_list",
        "workspace_file_content_read",
    }
    assert len(content_tools & set(public_tools)) == 4
    assert len(set(public_tools) - content_tools) == 20
    assert not any(re.search(r"(?:write|create|update|delete|remove)", name, re.IGNORECASE) for name in public_tools)
    assert "@mcp.tool()" not in repair_source


def test_future_sequence_is_explicit_and_repair_runner_is_not_created():
    root = Path(__file__).resolve().parents[1]
    assert repair.FUTURE_RUNNER_SEQUENCE == (
        "Drive A exact-ID metadata",
        "Sheets K1/L1 pre-read",
        "Drive B exact-ID metadata",
        "validate Drive A/B, identity, MIME, modifiedTime, trashed, sheet origin and cell mapping",
        "build sealed canonical repair plan",
        "NO_OP_ALREADY_CANONICAL: zero writes and finish",
        "WRITE_REQUIRED: exactly one controlled batchUpdate",
        "Sheets K1/L1 read-back",
        "Drive C metadata",
        "verify numeric values, formats, origin, identity, MIME and trashed; allow modifiedTime change",
    )
    assert not (root / "validation/fixtures/gworkspace_gsheets_canonical_fixture_state_repair_v1.py").exists()
