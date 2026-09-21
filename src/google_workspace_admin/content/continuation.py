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

from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError
from google_workspace_admin.content.inventory import InventorySnapshot


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
        self._states: dict[str, tuple[int, DocsContinuationState]] = {}
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

    def resolve(
        self,
        token: object,
        *,
        snapshot: InventorySnapshot,
        reader_version: int,
    ) -> DocsContinuationState:
        if type(token) is not str or len(token) > 4096:
            raise _invalid()
        parts = token.split(".")
        if len(parts) != 4 or parts[0] != "v1" or not parts[1] or not parts[2].isascii() or not parts[2].isdigit():
            raise _invalid()
        handle, expiry_text, supplied_mac = parts[1], parts[2], parts[3]
        expires_at = int(expiry_text)
        if not hmac.compare_digest(supplied_mac, self._mac(handle, expires_at)):
            raise _invalid()
        now = int(self._clock())
        with self._lock:
            self._purge(now)
            record = self._states.get(handle)
            if record is None or record[0] != expires_at or expires_at < now:
                raise _invalid()
            state = record[1]
        if (
            type(snapshot) is not InventorySnapshot
            or not state.snapshot.same_version(snapshot)
            or state.reader_version != reader_version
        ):
            raise _invalid()
        return state
