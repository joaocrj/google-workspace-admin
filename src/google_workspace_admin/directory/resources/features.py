"""Leitura de features de recursos corporativos na Directory API."""

import httpx

from google_workspace_admin.auth.dwd import get_workspace_access_token


DIRECTORY_RESOURCE_CALENDAR_READONLY_SCOPE = (
    "https://www.googleapis.com/auth/"
    "admin.directory.resource.calendar.readonly"
)

CALENDAR_FEATURES_URL = (
    "https://admin.googleapis.com/admin/directory/v1/"
    "customer/my_customer/resources/features"
)


def _authorization_headers() -> dict[str, str]:
    token, _ = get_workspace_access_token(
        scopes=[DIRECTORY_RESOURCE_CALENDAR_READONLY_SCOPE]
    )
    return {"Authorization": f"Bearer {token}"}


def list_calendar_features(
    max_results: int = 100,
    page_token: str | None = None,
) -> dict:
    """Lista uma página de features dos recursos corporativos de Calendar."""
    if max_results < 1 or max_results > 500:
        raise ValueError("max_results deve estar entre 1 e 500.")

    if page_token is not None and not page_token.strip():
        raise ValueError("page_token não pode estar vazio.")

    params = {
        "maxResults": max_results,
    }

    if page_token is not None:
        params["pageToken"] = page_token

    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            CALENDAR_FEATURES_URL,
            headers=_authorization_headers(),
            params=params,
        )
        response.raise_for_status()

        payload = response.json()

    return {
        "features": payload.get("features", []),
        "next_page_token": payload.get("nextPageToken"),
    }
