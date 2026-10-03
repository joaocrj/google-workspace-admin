"""Process-local opaque continuation handles for structured Content readers."""

from __future__ import annotations

from dataclasses import dataclass
import base64
import hashlib
import hmac
import secrets
import threading
import time
from typing import Callable

from google_workspace_admin.content.budgets import DEFAULT_CONTENT_READING_BUDGETS
from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError
from google_workspace_admin.content.google_sheets import (
    GOOGLE_SHEET_MIME_TYPE,
    SheetsCoverageGap,
)
from google_workspace_admin.content.inventory import InventorySnapshot
from google_workspace_admin.content.provenance import SheetsContentComponent


_PURPOSE = b"google-workspace-admin/content/docs-continuation/v1\x00"
_DEFAULT_TTL_SECONDS = 15 * 60
_MAX_STATES = 1_000


def _invalid() -> ContentSafeError:
    return ContentSafeError(
        code="LOCAL_VALIDATION",
        operation=ContentErrorOperation.READING_CONTINUATION,
    )


@dataclass(frozen=True, slots=True)
class DocsContinuationState:
    snapshot: InventorySnapshot
    reader_version: int
    unit_index: int
    character_offset: int
    tab_ordinal: int
    structural_cursor: tuple[int, ...]
    revision_id: str | None = None

    def __post_init__(self) -> None:
        if type(self.snapshot) is not InventorySnapshot:
            raise _invalid()
        for value in (
            self.reader_version,
            self.unit_index,
            self.character_offset,
            self.tab_ordinal,
        ):
            if isinstance(value, bool) or type(value) is not int or value < 0:
                raise _invalid()
        if type(self.structural_cursor) not in (tuple, list) or len(self.structural_cursor) > 64:
            raise _invalid()
        cursor = tuple(self.structural_cursor)
        if any(isinstance(value, bool) or type(value) is not int or value < 0 for value in cursor):
            raise _invalid()
        if self.revision_id is not None and (
            type(self.revision_id) is not str
            or not self.revision_id
            or len(self.revision_id) > 1024
            or any(ord(character) < 32 for character in self.revision_id)
        ):
            raise _invalid()
        object.__setattr__(self, "structural_cursor", cursor)


@dataclass(frozen=True, slots=True)
class SheetsContinuationState:
    """Private next-unread cursor retained only behind an authenticated handle."""

    snapshot: InventorySnapshot
    reader_version: int
    metadata_fingerprint: tuple[tuple[int, int, str, str, int | None, int | None, bool], ...]
    sheet_ordinal: int
    sheet_id: int
    row: int
    column: int
    component: SheetsContentComponent | None
    rich_text_run_ordinal: int | None
    rich_text_start_utf16: int | None
    logical_cells_completed: int
    coverage_gaps: tuple[SheetsCoverageGap, ...] = ()

    def __post_init__(self) -> None:
        if type(self.snapshot) is not InventorySnapshot:
            raise _invalid()
        if self.snapshot.expected_mime_type != GOOGLE_SHEET_MIME_TYPE:
            raise _invalid()
        if type(self.reader_version) is not int or self.reader_version < 1:
            raise _invalid()
        if type(self.metadata_fingerprint) is not tuple or not self.metadata_fingerprint:
            raise _invalid()
        if len(self.metadata_fingerprint) > DEFAULT_CONTENT_READING_BUDGETS.max_sheets_tabs:
            raise _invalid()
        previous_index = -1
        sheet_ids: set[int] = set()
        for record in self.metadata_fingerprint:
            if type(record) is not tuple or len(record) != 7:
                raise _invalid()
            sheet_id, sheet_index, title, sheet_type, rows, columns, hidden = record
            if (
                type(sheet_id) is not int
                or sheet_id < 0
                or type(sheet_index) is not int
                or sheet_index <= previous_index
                or type(title) is not str
                or not title
                or len(title) > 100
                or type(sheet_type) is not str
                or sheet_type not in {"GRID", "OBJECT", "DATA_SOURCE"}
                or type(hidden) is not bool
                or (rows is not None and (type(rows) is not int or rows < 0))
                or (columns is not None and (type(columns) is not int or columns < 0))
                or (sheet_type == "GRID" and (rows is None or columns is None))
                or sheet_id in sheet_ids
            ):
                raise _invalid()
            try:
                title.encode("utf-8", "strict")
            except UnicodeEncodeError:
                raise _invalid() from None
            previous_index = sheet_index
            sheet_ids.add(sheet_id)
        for value in (self.sheet_ordinal, self.sheet_id, self.row, self.column):
            if type(value) is not int or value < 0:
                raise _invalid()
        if self.component is not None and type(self.component) is not SheetsContentComponent:
            raise _invalid()
        if type(self.logical_cells_completed) is not int or not (
            0 <= self.logical_cells_completed <= DEFAULT_CONTENT_READING_BUDGETS.max_sheets_cells_per_file
        ):
            raise _invalid()
        if self.sheet_ordinal >= len(self.metadata_fingerprint):
            raise _invalid()
        cursor_sheet = self.metadata_fingerprint[self.sheet_ordinal]
        if (
            cursor_sheet[0] != self.sheet_id
            or cursor_sheet[3] != "GRID"
            or cursor_sheet[4] == 0
            or cursor_sheet[5] == 0
            or self.row >= cursor_sheet[4]
            or self.column >= cursor_sheet[5]
        ):
            raise _invalid()
        if self.component is SheetsContentComponent.CELL_RICH_TEXT_LINK:
            if (
                type(self.rich_text_run_ordinal) is not int
                or self.rich_text_run_ordinal < 0
                or type(self.rich_text_start_utf16) is not int
                or self.rich_text_start_utf16 < 0
            ):
                raise _invalid()
        elif self.rich_text_run_ordinal is not None or self.rich_text_start_utf16 is not None:
            raise _invalid()
        if type(self.coverage_gaps) is not tuple or any(
            type(gap) is not SheetsCoverageGap for gap in self.coverage_gaps
        ) or len(set(self.coverage_gaps)) != len(self.coverage_gaps):
            raise _invalid()


class DocsContinuationManager:
    """Bounded RAM-only state store with purpose-separated HMAC handles."""

    __slots__ = ("_clock", "_key", "_lock", "_max_states", "_states", "_ttl_seconds")

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.time,
        key: bytes | None = None,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
        max_states: int = _MAX_STATES,
    ) -> None:
        if not callable(clock):
            raise _invalid()
        secret = secrets.token_bytes(32) if key is None else key
        if type(secret) is not bytes or len(secret) < 32:
            raise _invalid()
        if isinstance(ttl_seconds, bool) or type(ttl_seconds) is not int or not 1 <= ttl_seconds <= 3600:
            raise _invalid()
        if (
            isinstance(max_states, bool)
            or type(max_states) is not int
            or not 1 <= max_states <= _MAX_STATES
        ):
            raise _invalid()
        self._clock = clock
        self._key = hmac.new(secret, _PURPOSE, hashlib.sha256).digest()
        self._lock = threading.Lock()
        self._max_states = max_states
        self._states: dict[str, tuple[int, DocsContinuationState | SheetsContinuationState]] = {}
        self._ttl_seconds = ttl_seconds

    def _mac(self, handle: str, expires_at: int) -> str:
        message = _PURPOSE + handle.encode("ascii") + b"." + str(expires_at).encode("ascii")
        digest = hmac.new(self._key, message, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    def _purge(self, now: int) -> None:
        expired = [handle for handle, (expiry, _) in self._states.items() if expiry < now]
        for handle in expired:
            self._states.pop(handle, None)

    def issue(self, state: DocsContinuationState) -> str:
        if type(state) is not DocsContinuationState:
            raise _invalid()
        return self._issue_state(state)

    def _issue_state(self, state: DocsContinuationState | SheetsContinuationState) -> str:
        now = int(self._clock())
        with self._lock:
            self._purge(now)
            if len(self._states) >= self._max_states:
                raise ContentSafeError(
                    code="CONTEXT_LIMIT_EXCEEDED",
                    operation=ContentErrorOperation.READING_CONTINUATION,
                )
            while True:
                handle = base64.urlsafe_b64encode(secrets.token_bytes(24)).rstrip(b"=").decode("ascii")
                if handle not in self._states:
                    break
            expires_at = now + self._ttl_seconds
            self._states[handle] = (expires_at, state)
        return f"v1.{handle}.{expires_at}.{self._mac(handle, expires_at)}"

    def issue_sheets(
        self,
        state: SheetsContinuationState,
    ) -> str:
        """Issue one-use Sheets state with the shared opaque HMAC handle store."""

        if type(state) is not SheetsContinuationState:
            raise _invalid()
        return self._issue_state(state)

    def _verified_handle(self, token: object) -> tuple[str, int]:
        if type(token) is not str or len(token) > 4096:
            raise _invalid()
        parts = token.split(".")
        if (
            len(parts) != 4
            or parts[0] != "v1"
            or not parts[1]
            or not parts[1].isascii()
            or not parts[2].isascii()
            or not parts[2].isdigit()
        ):
            raise _invalid()
        handle, expiry_text, supplied_mac = parts[1], parts[2], parts[3]
        expires_at = int(expiry_text)
        if not hmac.compare_digest(supplied_mac, self._mac(handle, expires_at)):
            raise _invalid()
        return handle, expires_at

    def resolve(
        self,
        token: object,
        *,
        snapshot: InventorySnapshot,
        reader_version: int,
    ) -> DocsContinuationState:
        handle, expires_at = self._verified_handle(token)
        now = int(self._clock())
        with self._lock:
            self._purge(now)
            record = self._states.get(handle)
            if record is None or record[0] != expires_at or expires_at < now:
                raise _invalid()
            state = record[1]
        if (
            type(state) is not DocsContinuationState
            or
            type(snapshot) is not InventorySnapshot
            or not state.snapshot.same_version(snapshot)
            or state.reader_version != reader_version
        ):
            raise _invalid()
        return state

    def resolve_sheets(
        self,
        token: object,
        *,
        snapshot: InventorySnapshot,
        reader_version: int,
    ) -> SheetsContinuationState:
        handle, expires_at = self._verified_handle(token)
        now = int(self._clock())
        with self._lock:
            self._purge(now)
            record = self._states.get(handle)
            if record is None or record[0] != expires_at or expires_at < now:
                raise _invalid()
            state = record[1]
            if (
                type(state) is not SheetsContinuationState
                or type(snapshot) is not InventorySnapshot
                or not state.snapshot.same_version(snapshot)
                or state.reader_version != reader_version
            ):
                raise _invalid()
            # Claim atomically before network work. A replay or concurrent use
            # cannot release the same logical tail twice.
            self._states.pop(handle, None)
        return state

    def discard_sheets(self, token: object) -> None:
        """Remove one authenticated Sheets handle after invalidation/completion."""

        handle, expires_at = self._verified_handle(token)
        now = int(self._clock())
        with self._lock:
            self._purge(now)
            record = self._states.get(handle)
            if record is not None and record[0] == expires_at and type(record[1]) is SheetsContinuationState:
                self._states.pop(handle, None)
