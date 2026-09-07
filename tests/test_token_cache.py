import time

from google_workspace_admin.auth.token_cache import (
    clear_token_cache,
    get_cached_token,
    store_token,
)


SUBJECT = "teste@example.com"
SCOPES = [
    "https://www.googleapis.com/auth/admin.directory.user",
]


def setup_function():
    clear_token_cache()


def teardown_function():
    clear_token_cache()


def test_token_is_cached():
    store_token(
        subject=SUBJECT,
        scopes=SCOPES,
        access_token="fake-token",
        expires_in=3600,
    )

    token = get_cached_token(
        subject=SUBJECT,
        scopes=SCOPES,
    )

    assert token == "fake-token"


def test_cache_separates_subjects():
    store_token(
        subject="user1@example.com",
        scopes=SCOPES,
        access_token="token-user-1",
        expires_in=3600,
    )

    token = get_cached_token(
        subject="user2@example.com",
        scopes=SCOPES,
    )

    assert token is None


def test_cache_separates_scopes():
    store_token(
        subject=SUBJECT,
        scopes=["scope-a"],
        access_token="token-a",
        expires_in=3600,
    )

    token = get_cached_token(
        subject=SUBJECT,
        scopes=["scope-b"],
    )

    assert token is None


def test_scope_order_does_not_change_cache_key():
    store_token(
        subject=SUBJECT,
        scopes=["scope-b", "scope-a"],
        access_token="ordered-token",
        expires_in=3600,
    )

    token = get_cached_token(
        subject=SUBJECT,
        scopes=["scope-a", "scope-b"],
    )

    assert token == "ordered-token"


def test_token_inside_refresh_margin_is_not_reused():
    store_token(
        subject=SUBJECT,
        scopes=SCOPES,
        access_token="almost-expired",
        expires_in=60,
    )

    token = get_cached_token(
        subject=SUBJECT,
        scopes=SCOPES,
    )

    assert token is None