"""Narrow, validation-only Google transport for one O1 spill rewrite.

This module is intentionally outside the public Content adapters. It exposes
only fixed Drive metadata and Sheets metadata/O1:P1 operations. The sole POST
body is assembled here from the canonical fixture formula and the resolved
ordinal-zero sheet ID.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
import math
import re
from typing import Any
from urllib.parse import quote, urlsplit

import httpx


DRIVER_VERSION = "2.1"
HTTP_TIMEOUT_SECONDS = 12.0
MAX_REQUEST_BODY_BYTES = 4096
MAX_RESPONSE_BODY_BYTES = 262144
INITIAL_SHEETS_WRITE_BUDGET = 1

DRIVE_API_HOST = "www.googleapis.com"
SHEETS_API_HOST = "sheets.googleapis.com"
DRIVE_API_ROOT = f"https://{DRIVE_API_HOST}"
SHEETS_API_ROOT = f"https://{SHEETS_API_HOST}"
GOOGLE_SHEETS_MIME = "application/vnd.google-apps.spreadsheet"

OPERATION_REGISTRY = frozenset(
    {
        "drive.read_exact_file_metadata",
        "drive.read_exact_file_metadata_postwrite",
        "sheets.read_workbook_metadata",
        "sheets.read_o1_p1_prewrite",
        "sheets.batch_update_o1_once",
        "sheets.read_o1_p1_postwrite",
    }
)
CLOSED_HTTP_METHODS = frozenset({"GET", "POST"})
CLOSED_HTTP_HOSTS = frozenset({DRIVE_API_HOST, SHEETS_API_HOST})

_FILE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{5,256}$", re.ASCII)
_FORMULA_RE = re.compile(r"^=[^\r\n\x00-\x1f\x7f]{1,512}$", re.ASCII)
_DRIVE_FIELDS = "id,mimeType,trashed,modifiedTime"
_WORKBOOK_FIELDS = "properties(locale,timeZone),sheets(properties(sheetId,index,title))"
_CELL_FIELDS = (
    "sheets(properties(sheetId),data(startRow,startColumn,"
    "rowData(values(userEnteredValue,formattedValue,effectiveValue))))"
)


class ControlledTransportError(RuntimeError):
    """Exception carrying only a fixed safe classification."""

    __slots__ = ("code",)

    def __init__(self, code: str) -> None:
        safe_code = code if code in {
            "LOCAL_TRANSPORT_REJECTED",
            "TRANSPORT_FAILURE",
            "HTTP_FAILURE",
            "RESPONSE_TOO_LARGE",
            "RESPONSE_INVALID",
            "WRITE_BUDGET_EXHAUSTED",
        } else "TRANSPORT_FAILURE"
        self.code = safe_code
        super().__init__(safe_code)

    def __repr__(self) -> str:
        return f"<ControlledTransportError {self.code}>"


@dataclass(frozen=True, slots=True)
class DriveMetadata:
    id_present: bool
    id_matches_requested_exact_id: bool
    mime_type_present: bool
    is_google_sheet: bool
    trashed_present: bool
    not_trashed: bool
    modified_time_present: bool
    modified_time_value: str | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class WorkbookMetadata:
    locale: str | None
    ordinal_zero_sheet_id: int | None
    ordinal_zero_sheet_title: str | None = field(default=None, repr=False)
    sheet_count: int = 0
    time_zone: str | None = None


@dataclass(frozen=True, slots=True)
class CellDataSnapshot:
    cell_data_present: bool
    user_entered_value_present: bool
    authored_formula_present: bool
    canonical_formula_match: bool
    formatted_value_present: bool
    formatted_expectation_match: bool
    effective_value_present: bool
    effective_value_type: str
    effective_expectation_match: bool


def validate_http_boundary(
    *,
    method: str,
    url: str,
    fixture_id: str,
    sheet_title: str | None = None,
    body: bytes | None = None,
) -> str:
    """Validate the fixed HTTP surface; return its operation name.

    This helper is directly unit-testable. Callers cannot supply the mutation
    request through the transport API; a batchUpdate body must match the one
    canonical O1 update assembled by ``ControlledSheetsTransport``.
    """

    try:
        parts = urlsplit(url)
    except Exception:
        raise ControlledTransportError("LOCAL_TRANSPORT_REJECTED") from None
    if (
        method not in CLOSED_HTTP_METHODS
        or parts.scheme != "https"
        or parts.hostname not in CLOSED_HTTP_HOSTS
        or parts.username is not None
        or parts.password is not None
        or parts.port is not None
        or parts.query
        or parts.fragment
        or not _FILE_ID_RE.fullmatch(fixture_id)
    ):
        raise ControlledTransportError("LOCAL_TRANSPORT_REJECTED")

    file_id = quote(fixture_id, safe="")
    drive_path = f"/drive/v3/files/{file_id}"
    sheets_path = f"/v4/spreadsheets/{file_id}"
    if parts.hostname == DRIVE_API_HOST and method == "GET" and parts.path == drive_path:
        return "drive.read_exact_file_metadata"
    if parts.hostname != SHEETS_API_HOST:
        raise ControlledTransportError("LOCAL_TRANSPORT_REJECTED")
    if method == "GET" and parts.path == sheets_path:
        return "sheets.read_metadata_or_o1_p1"
    if method == "POST" and parts.path == f"{sheets_path}:batchUpdate":
        if body is None or len(body) > MAX_REQUEST_BODY_BYTES:
            raise ControlledTransportError("LOCAL_TRANSPORT_REJECTED")
        if not sheet_title:
            raise ControlledTransportError("LOCAL_TRANSPORT_REJECTED")
        try:
            payload = json.loads(body)
        except (TypeError, ValueError):
            raise ControlledTransportError("LOCAL_TRANSPORT_REJECTED") from None
        if not _is_exact_o1_update(payload):
            raise ControlledTransportError("LOCAL_TRANSPORT_REJECTED")
        return "sheets.batch_update_o1_once"
    raise ControlledTransportError("LOCAL_TRANSPORT_REJECTED")


def _is_exact_o1_update(payload: object) -> bool:
    """Recognize the one allowed updateCells shape without accepting extras."""

    if type(payload) is not dict or set(payload) != {"requests"}:
        return False
    requests = payload.get("requests")
    if type(requests) is not list or len(requests) != 1:
        return False
    request = requests[0]
    if type(request) is not dict or set(request) != {"updateCells"}:
        return False
    update = request.get("updateCells")
    if type(update) is not dict or set(update) != {"range", "rows", "fields"}:
        return False
    grid_range = update.get("range")
    if (
        type(grid_range) is not dict
        or set(grid_range)
        != {
            "sheetId",
            "startRowIndex",
            "endRowIndex",
            "startColumnIndex",
            "endColumnIndex",
        }
        or type(grid_range.get("sheetId")) is not int
        or grid_range.get("sheetId") < 0
        or type(grid_range.get("startRowIndex")) is not int
        or grid_range.get("startRowIndex") != 0
        or type(grid_range.get("endRowIndex")) is not int
        or grid_range.get("endRowIndex") != 1
        or type(grid_range.get("startColumnIndex")) is not int
        or grid_range.get("startColumnIndex") != 14
        or type(grid_range.get("endColumnIndex")) is not int
        or grid_range.get("endColumnIndex") != 15
    ):
        return False
    rows = update.get("rows")
    if type(rows) is not list or len(rows) != 1 or type(rows[0]) is not dict:
        return False
    if set(rows[0]) != {"values"}:
        return False
    values = rows[0].get("values")
    if type(values) is not list or len(values) != 1 or type(values[0]) is not dict:
        return False
    if set(values[0]) != {"userEnteredValue"}:
        return False
    user_value = values[0].get("userEnteredValue")
    if type(user_value) is not dict or set(user_value) != {"formulaValue"}:
        return False
    formula = user_value.get("formulaValue")
    if type(formula) is not str or not _FORMULA_RE.fullmatch(formula):
        return False
    return update.get("fields") == "userEnteredValue"


class ControlledSheetsTransport:
    """Exact-ID Drive/Sheets transport with an internal one-write ceiling."""

    __slots__ = (
        "_fixture_id",
        "_formula",
        "_expected_o1_display",
        "_expected_p1_display",
        "_client",
        "_sheet_id",
        "_sheet_title",
        "_write_budget",
        "_sheets_writes_attempted",
        "_sheets_writes_succeeded",
        "_p1_writes",
        "_retries",
        "_write_permit",
        "_closed",
    )

    def __init__(
        self,
        *,
        fixture_identity: object,
        access_token: str,
        formula: str,
        expected_o1_display: str,
        expected_p1_display: str,
        http_transport: httpx.BaseTransport | None = None,
    ) -> None:
        identity_type = type(fixture_identity)
        if (
            identity_type.__name__ != "_ValidatedFixtureIdentity"
            or identity_type.__module__
            not in {
                "validation.fixtures.run_gsheets_spill_restoration_controlled_v1",
                "__main__",
            }
        ):
            raise ControlledTransportError("LOCAL_TRANSPORT_REJECTED")
        fixture_id = getattr(fixture_identity, "value", None)
        if not isinstance(fixture_id, str) or not _FILE_ID_RE.fullmatch(fixture_id):
            raise ControlledTransportError("LOCAL_TRANSPORT_REJECTED")
        if (
            not isinstance(access_token, str)
            or not access_token
            or any(character.isspace() for character in access_token)
        ):
            raise ControlledTransportError("LOCAL_TRANSPORT_REJECTED")
        if not isinstance(formula, str) or not _FORMULA_RE.fullmatch(formula):
            raise ControlledTransportError("LOCAL_TRANSPORT_REJECTED")
        if not _positive_numeric_display(expected_o1_display) or not _positive_numeric_display(expected_p1_display):
            raise ControlledTransportError("LOCAL_TRANSPORT_REJECTED")

        self._fixture_id = fixture_id
        self._formula = formula
        self._expected_o1_display = expected_o1_display
        self._expected_p1_display = expected_p1_display
        self._client = httpx.Client(
            transport=http_transport,
            follow_redirects=False,
            timeout=HTTP_TIMEOUT_SECONDS,
            trust_env=False,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        self._sheet_id: int | None = None
        self._sheet_title: str | None = None
        self._write_budget = INITIAL_SHEETS_WRITE_BUDGET
        self._sheets_writes_attempted = 0
        self._sheets_writes_succeeded = 0
        self._p1_writes = 0
        self._retries = 0
        self._write_permit: object | None = None
        self._closed = False

    def __repr__(self) -> str:
        return "<ControlledSheetsTransport exact-id closed-surface redacted>"

    @property
    def sheets_writes_attempted(self) -> int:
        return self._sheets_writes_attempted

    @property
    def sheets_writes_succeeded(self) -> int:
        return self._sheets_writes_succeeded

    @property
    def p1_writes(self) -> int:
        return self._p1_writes

    @property
    def retries(self) -> int:
        return self._retries

    @property
    def write_budget_remaining(self) -> int:
        return self._write_budget

    def close(self) -> None:
        if not self._closed:
            self._client.close()
            self._closed = True

    def read_drive_metadata(self) -> DriveMetadata:
        payload = self._send_get(
            host=DRIVE_API_HOST,
            path=f"/drive/v3/files/{quote(self._fixture_id, safe='')}",
            params={"fields": _DRIVE_FIELDS, "supportsAllDrives": "true"},
        )
        return _parse_drive_metadata(payload, self._fixture_id)

    def read_workbook_metadata(self) -> WorkbookMetadata:
        payload = self._send_get(
            host=SHEETS_API_HOST,
            path=f"/v4/spreadsheets/{quote(self._fixture_id, safe='')}",
            params={"fields": _WORKBOOK_FIELDS},
        )
        metadata = _parse_workbook_metadata(payload)
        if metadata.ordinal_zero_sheet_id is not None and metadata.ordinal_zero_sheet_title is not None:
            self._sheet_id = metadata.ordinal_zero_sheet_id
            self._sheet_title = metadata.ordinal_zero_sheet_title
        return metadata

    def read_o1_p1_prewrite(self) -> tuple[CellDataSnapshot, CellDataSnapshot]:
        return self._read_o1_p1()

    def read_o1_p1_postwrite(self) -> tuple[CellDataSnapshot, CellDataSnapshot]:
        return self._read_o1_p1()

    def write_o1_once(self) -> None:
        if self._write_budget <= 0:
            raise ControlledTransportError("WRITE_BUDGET_EXHAUSTED")
        self._write_budget = 0
        self._sheets_writes_attempted += 1
        if self._sheet_id is None or self._sheet_title is None:
            raise ControlledTransportError("LOCAL_TRANSPORT_REJECTED")
        payload = {
            "requests": [
                {
                    "updateCells": {
                        "range": {
                            "sheetId": self._sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": 14,
                            "endColumnIndex": 15,
                        },
                        "rows": [
                            {
                                "values": [
                                    {
                                        "userEnteredValue": {
                                            "formulaValue": self._formula
                                        }
                                    }
                                ]
                            }
                        ],
                        "fields": "userEnteredValue",
                    }
                }
            ]
        }
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        permit = object()
        self._write_permit = permit
        try:
            self._send_post_o1_update(body, permit)
        except ControlledTransportError:
            raise
        except Exception:
            raise ControlledTransportError("TRANSPORT_FAILURE") from None
        finally:
            self._write_permit = None
        self._sheets_writes_succeeded += 1

    def _read_o1_p1(self) -> tuple[CellDataSnapshot, CellDataSnapshot]:
        if self._sheet_id is None or self._sheet_title is None:
            raise ControlledTransportError("LOCAL_TRANSPORT_REJECTED")
        escaped_title = self._sheet_title.replace("'", "''")
        exact_range = f"'{escaped_title}'!O1:P1"
        payload = self._send_get(
            host=SHEETS_API_HOST,
            path=f"/v4/spreadsheets/{quote(self._fixture_id, safe='')}",
            params={
                "ranges": exact_range,
                "includeGridData": "true",
                "fields": _CELL_FIELDS,
            },
        )
        return _parse_o1_p1(
            payload,
            sheet_id=self._sheet_id,
            formula=self._formula,
            expected_o1_display=self._expected_o1_display,
            expected_p1_display=self._expected_p1_display,
        )

    def _send_get(self, *, host: str, path: str, params: dict[str, str]) -> dict[str, Any]:
        url = f"https://{host}{path}"
        raw = self._perform_request("GET", url, params=params, body=None)
        return _decode_object(raw)

    def _send_post_o1_update(self, body: bytes, permit: object) -> None:
        if self._sheet_title is None:
            raise ControlledTransportError("LOCAL_TRANSPORT_REJECTED")
        url = (
            f"{SHEETS_API_ROOT}/v4/spreadsheets/"
            f"{quote(self._fixture_id, safe='')}:batchUpdate"
        )
        self._perform_request(
            "POST",
            url,
            params=None,
            body=body,
            _write_permit=permit,
        )

    def _guard_and_send(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, str] | None,
        body: bytes | None,
    ) -> None:
        operation = validate_http_boundary(
            method=method,
            url=url,
            fixture_id=self._fixture_id,
            sheet_title=self._sheet_title,
            body=body,
        )
        if operation == "drive.read_exact_file_metadata":
            if params != {
                "fields": _DRIVE_FIELDS,
                "supportsAllDrives": "true",
            } or body is not None:
                raise ControlledTransportError("LOCAL_TRANSPORT_REJECTED")
        elif operation == "sheets.read_metadata_or_o1_p1":
            if body is not None or params not in (
                {"fields": _WORKBOOK_FIELDS},
                {
                    "ranges": f"'{(self._sheet_title or '').replace(chr(39), chr(39) * 2)}'!O1:P1",
                    "includeGridData": "true",
                    "fields": _CELL_FIELDS,
                },
            ):
                raise ControlledTransportError("LOCAL_TRANSPORT_REJECTED")
        elif operation == "sheets.batch_update_o1_once":
            if params is not None or body is None or self._sheet_id is None:
                raise ControlledTransportError("LOCAL_TRANSPORT_REJECTED")
            try:
                payload = json.loads(body)
            except (TypeError, ValueError):
                raise ControlledTransportError("LOCAL_TRANSPORT_REJECTED") from None
            if not _payload_matches_binding(payload, self._sheet_id, self._formula):
                raise ControlledTransportError("LOCAL_TRANSPORT_REJECTED")
        else:
            raise ControlledTransportError("LOCAL_TRANSPORT_REJECTED")

    def _perform_request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, str] | None,
        body: bytes | None,
        _write_permit: object | None = None,
    ) -> bytes:
        if self._closed:
            raise ControlledTransportError("TRANSPORT_FAILURE")
        self._guard_and_send(method, url, params=params, body=body)
        if method == "POST":
            if _write_permit is None or _write_permit is not self._write_permit:
                raise ControlledTransportError("LOCAL_TRANSPORT_REJECTED")
            self._write_permit = None
        elif _write_permit is not None:
            raise ControlledTransportError("LOCAL_TRANSPORT_REJECTED")
        if body is not None and len(body) > MAX_REQUEST_BODY_BYTES:
            raise ControlledTransportError("LOCAL_TRANSPORT_REJECTED")
        headers = {"Content-Type": "application/json"} if body is not None else None
        try:
            with self._client.stream(
                method,
                url,
                params=params,
                content=body,
                headers=headers,
            ) as response:
                if response.status_code < 200 or response.status_code >= 300:
                    raise ControlledTransportError("HTTP_FAILURE")
                content_length = response.headers.get("content-length")
                if content_length is not None:
                    try:
                        if int(content_length) > MAX_RESPONSE_BODY_BYTES:
                            raise ControlledTransportError("RESPONSE_TOO_LARGE")
                    except ValueError:
                        raise ControlledTransportError("RESPONSE_INVALID") from None
                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_bytes(chunk_size=4096):
                    total += len(chunk)
                    if total > MAX_RESPONSE_BODY_BYTES:
                        raise ControlledTransportError("RESPONSE_TOO_LARGE")
                    chunks.append(chunk)
                return b"".join(chunks)
        except ControlledTransportError:
            raise
        except Exception:
            raise ControlledTransportError("TRANSPORT_FAILURE") from None


def _payload_matches_binding(payload: object, sheet_id: int, formula: str) -> bool:
    if not _is_exact_o1_update(payload):
        return False
    try:
        update = payload["requests"][0]["updateCells"]  # type: ignore[index]
        grid_range = update["range"]
        request_formula = update["rows"][0]["values"][0]["userEnteredValue"]["formulaValue"]
    except (KeyError, IndexError, TypeError):
        return False
    return grid_range.get("sheetId") == sheet_id and request_formula == formula


def _decode_object(raw: bytes) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        raise ControlledTransportError("RESPONSE_INVALID") from None
    if type(parsed) is not dict:
        raise ControlledTransportError("RESPONSE_INVALID")
    return parsed


def _parse_drive_metadata(
    payload: dict[str, Any], requested_file_id: str
) -> DriveMetadata:
    response_id = payload.get("id")
    mime_type = payload.get("mimeType")
    trashed = payload.get("trashed")
    modified_time = payload.get("modifiedTime")
    id_present = type(response_id) is str and bool(response_id)
    mime_type_present = type(mime_type) is str and bool(mime_type)
    trashed_present = type(trashed) is bool
    modified_time_usable = _is_usable_modified_time(modified_time)
    return DriveMetadata(
        id_present=id_present,
        id_matches_requested_exact_id=(
            id_present and response_id == requested_file_id
        ),
        mime_type_present=mime_type_present,
        is_google_sheet=(mime_type_present and mime_type == GOOGLE_SHEETS_MIME),
        trashed_present=trashed_present,
        not_trashed=trashed_present and trashed is False,
        modified_time_present=modified_time_usable,
        modified_time_value=modified_time if modified_time_usable else None,
    )


def _is_usable_modified_time(value: object) -> bool:
    if type(value) is not str or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.tzinfo is not None and parsed.utcoffset() is not None
    except (TypeError, ValueError, OverflowError):
        return False


def _parse_workbook_metadata(payload: dict[str, Any]) -> WorkbookMetadata:
    properties = payload.get("properties")
    locale = properties.get("locale") if type(properties) is dict else None
    time_zone = properties.get("timeZone") if type(properties) is dict else None
    safe_locale = locale if isinstance(locale, str) else None
    safe_time_zone = time_zone if isinstance(time_zone, str) else None
    raw_sheets = payload.get("sheets")
    if type(raw_sheets) is not list:
        return WorkbookMetadata(safe_locale, None, time_zone=safe_time_zone)
    ordered: list[tuple[int, int, str]] = []
    for position, raw_sheet in enumerate(raw_sheets):
        props = raw_sheet.get("properties") if type(raw_sheet) is dict else None
        if type(props) is not dict:
            continue
        sheet_id = props.get("sheetId")
        index = props.get("index")
        title = props.get("title")
        if (
            type(sheet_id) is int
            and sheet_id >= 0
            and type(index) is int
            and index >= 0
            and isinstance(title, str)
            and title
        ):
            ordered.append((index, sheet_id, title))
    ordered.sort(key=lambda item: item[0])
    if (
        not ordered
        or ordered[0][0] != 0
        or len({item[0] for item in ordered}) != len(ordered)
    ):
        return WorkbookMetadata(safe_locale, None, sheet_count=len(raw_sheets), time_zone=safe_time_zone)
    return WorkbookMetadata(
        safe_locale,
        ordered[0][1],
        ordered[0][2],
        sheet_count=len(raw_sheets),
        time_zone=safe_time_zone,
    )


def _parse_o1_p1(
    payload: dict[str, Any],
    *,
    sheet_id: int,
    formula: str,
    expected_o1_display: str,
    expected_p1_display: str,
) -> tuple[CellDataSnapshot, CellDataSnapshot]:
    raw_sheets = payload.get("sheets")
    raw_sheet = raw_sheets[0] if type(raw_sheets) is list and raw_sheets else None
    if type(raw_sheet) is not dict:
        raise ControlledTransportError("RESPONSE_INVALID")
    properties = raw_sheet.get("properties")
    if type(properties) is not dict or properties.get("sheetId") != sheet_id:
        raise ControlledTransportError("RESPONSE_INVALID")
    data = raw_sheet.get("data")
    if type(data) is not list or not data or type(data[0]) is not dict:
        return _empty_snapshot(), _empty_snapshot()
    grid = data[0]
    if grid.get("startRow") not in (None, 0) or grid.get("startColumn") not in (None, 14):
        raise ControlledTransportError("RESPONSE_INVALID")
    row_data = grid.get("rowData")
    if type(row_data) is not list or not row_data or type(row_data[0]) is not dict:
        return _empty_snapshot(), _empty_snapshot()
    values = row_data[0].get("values")
    if type(values) is not list:
        return _empty_snapshot(), _empty_snapshot()
    o1_raw = values[0] if len(values) >= 1 else None
    p1_raw = values[1] if len(values) >= 2 else None
    return (
        _cell_snapshot(o1_raw, formula, expected_o1_display),
        _cell_snapshot(p1_raw, None, expected_p1_display),
    )


def _empty_snapshot() -> CellDataSnapshot:
    return CellDataSnapshot(False, False, False, False, False, False, False, "ABSENT", False)


def _cell_snapshot(
    raw: object,
    canonical_formula: str | None,
    expected_display: str,
) -> CellDataSnapshot:
    if type(raw) is not dict:
        return _empty_snapshot()
    user_value = raw.get("userEnteredValue")
    user_present = "userEnteredValue" in raw
    formula_value = user_value.get("formulaValue") if type(user_value) is dict else None
    formula_present = (
        isinstance(formula_value, str) and bool(formula_value)
    ) or (type(user_value) is dict and "formulaValue" in user_value)
    formatted_value = raw.get("formattedValue")
    formatted_present = isinstance(formatted_value, str)
    effective = raw.get("effectiveValue")
    effective_present, effective_type, effective_matches = _effective_value(
        effective, expected_display
    )
    return CellDataSnapshot(
        cell_data_present=True,
        user_entered_value_present=user_present,
        authored_formula_present=formula_present,
        canonical_formula_match=(
            canonical_formula is not None and formula_value == canonical_formula
        ),
        formatted_value_present=formatted_present,
        formatted_expectation_match=(
            formatted_present and formatted_value == expected_display
        ),
        effective_value_present=effective_present,
        effective_value_type=effective_type,
        effective_expectation_match=effective_matches,
    )


def _effective_value(effective: object, expected_display: str) -> tuple[bool, str, bool]:
    if type(effective) is not dict or not effective:
        return False, "ABSENT", False
    if set(effective) == {"numberValue"}:
        value = effective["numberValue"]
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)):
            try:
                matches = Decimal(str(value)) == Decimal(expected_display)
            except InvalidOperation:
                matches = False
            return True, "NUMBER", matches
        return True, "OTHER", False
    if set(effective) == {"stringValue"} and isinstance(effective["stringValue"], str):
        return True, "STRING", False
    if set(effective) == {"boolValue"} and type(effective["boolValue"]) is bool:
        return True, "BOOL", False
    if set(effective) == {"errorValue"} and type(effective["errorValue"]) is dict:
        return True, "ERROR", False
    return True, "OTHER", False


def _positive_numeric_display(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        number = Decimal(value)
    except InvalidOperation:
        return False
    return number.is_finite() and number >= 0
