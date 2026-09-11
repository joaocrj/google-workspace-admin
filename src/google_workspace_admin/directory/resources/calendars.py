"""Leitura de recursos corporativos de Calendar na Directory API."""

import httpx

from google_workspace_admin.auth.dwd import get_workspace_access_token


DIRECTORY_RESOURCE_CALENDAR_READONLY_SCOPE = (
    "https://www.googleapis.com/auth/"
    "admin.directory.resource.calendar.readonly"
)

CALENDAR_RESOURCES_URL = (
    "https://admin.googleapis.com/admin/directory/v1/"
    "customer/my_customer/resources/calendars"
)


def _authorization_headers() -> dict[str, str]:
    token, _ = get_workspace_access_token(
        scopes=[DIRECTORY_RESOURCE_CALENDAR_READONLY_SCOPE]
    )
    return {"Authorization": f"Bearer {token}"}


def _validate_optional_string(
    value: str | None,
    parameter_name: str,
) -> None:
    if value is not None and not value.strip():
        raise ValueError(f"{parameter_name} não pode estar vazio.")


def list_calendar_resources(
    max_results: int = 100,
    page_token: str | None = None,
    order_by: str | None = None,
    query: str | None = None,
) -> dict:
    """Lista uma página de recursos corporativos de Calendar."""
    if max_results < 1 or max_results > 500:
        raise ValueError("max_results deve estar entre 1 e 500.")

    _validate_optional_string(page_token, "page_token")
    _validate_optional_string(order_by, "order_by")
    _validate_optional_string(query, "query")

    params = {
        "maxResults": max_results,
    }

    if page_token is not None:
        params["pageToken"] = page_token

    if order_by is not None:
        params["orderBy"] = order_by

    if query is not None:
        params["query"] = query

    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            CALENDAR_RESOURCES_URL,
            headers=_authorization_headers(),
            params=params,
        )
        response.raise_for_status()

        payload = response.json()

    return {
        "resources": payload.get("items", []),
        "next_page_token": payload.get("nextPageToken"),
    }
