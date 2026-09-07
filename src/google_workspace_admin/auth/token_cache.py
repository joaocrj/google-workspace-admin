import threading
import time
from dataclasses import dataclass
from typing import Iterable


TOKEN_REFRESH_MARGIN_SECONDS = 300


@dataclass
class CachedToken:
    access_token: str
    expires_at: float


_cache: dict[tuple[str, tuple[str, ...]], CachedToken] = {}
_lock = threading.Lock()


def _cache_key(
    subject: str,
    scopes: Iterable[str],
) -> tuple[str, tuple[str, ...]]:
    normalized_scopes = tuple(sorted(set(scopes)))
    return subject, normalized_scopes


def get_cached_token(
    subject: str,
    scopes: Iterable[str],
) -> str | None:
    key = _cache_key(subject, scopes)

    with _lock:
        cached = _cache.get(key)

        if cached is None:
            return None

        remaining = cached.expires_at - time.time()

        if remaining <= TOKEN_REFRESH_MARGIN_SECONDS:
            _cache.pop(key, None)
            return None

        return cached.access_token


def store_token(
    subject: str,
    scopes: Iterable[str],
    access_token: str,
    expires_in: int,
) -> None:
    key = _cache_key(subject, scopes)

    with _lock:
        _cache[key] = CachedToken(
            access_token=access_token,
            expires_at=time.time() + expires_in,
        )


def clear_token_cache() -> None:
    with _lock:
        _cache.clear()
