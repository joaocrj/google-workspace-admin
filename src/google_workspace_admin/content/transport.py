"""Bounded retry and cancellation policy for Content read operations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import math
import threading
import time

from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError
from google_workspace_admin.http_errors import WorkspaceApiError


MAX_ATTEMPTS = 3
DEFAULT_RETRYABLE_STATUSES = frozenset({408, 429, 500, 502, 503, 504})


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Bounded retry policy; one attempt is the safe default."""

    max_attempts: int = 1
    initial_delay_seconds: float = 0.5
    max_delay_seconds: float = 8.0
    retryable_statuses: frozenset[int] = DEFAULT_RETRYABLE_STATUSES

    def __post_init__(self) -> None:
        if (
            isinstance(self.max_attempts, bool)
            or not isinstance(self.max_attempts, int)
            or not 1 <= self.max_attempts <= MAX_ATTEMPTS
        ):
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.RETRY_POLICY,
            )
        for value in (self.initial_delay_seconds, self.max_delay_seconds):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ContentSafeError(
                    code="LOCAL_VALIDATION",
                    operation=ContentErrorOperation.RETRY_POLICY,
                )
            if not math.isfinite(float(value)) or value < 0:
                raise ContentSafeError(
                    code="LOCAL_VALIDATION",
                    operation=ContentErrorOperation.RETRY_POLICY,
                )
        if self.max_delay_seconds < self.initial_delay_seconds:
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.RETRY_POLICY,
            )
        if not isinstance(self.retryable_statuses, frozenset) or any(
            isinstance(status, bool)
            or not isinstance(status, int)
            or status not in DEFAULT_RETRYABLE_STATUSES
            for status in self.retryable_statuses
        ):
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.RETRY_POLICY,
            )

    def _can_retry(
        self,
        *,
        idempotent_read: bool,
        attempt_number: int,
        error: WorkspaceApiError,
    ) -> bool:
        if type(self) is not RetryPolicy:
            return False
        if (
            isinstance(self.max_attempts, bool)
            or not isinstance(self.max_attempts, int)
            or not 1 <= self.max_attempts <= MAX_ATTEMPTS
        ):
            return False
        if not idempotent_read or attempt_number + 1 >= self.max_attempts:
            return False
        status = error.http_status
        if status in {400, 401, 403, 404}:
            return False
        if status in self.retryable_statuses:
            return True
        return status is None and error.category in {"timeout", "transport_error"}

    def delay_for(self, retry_number: int) -> float:
        delay = self.initial_delay_seconds * (2 ** max(retry_number - 1, 0))
        return min(delay, self.max_delay_seconds)


def _sleep_with_cancellation(
    delay: float,
    cancel_event: threading.Event | None,
    sleeper: Callable[[float], None],
) -> None:
    if cancel_event is None:
        sleeper(delay)
        return
    if delay <= 0:
        sleeper(0)
        if cancel_event.is_set():
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.TRANSPORT,
            )
        return
    deadline = time.monotonic() + delay
    while True:
        if cancel_event.is_set():
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.TRANSPORT,
            )
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        sleeper(min(remaining, 0.05))
