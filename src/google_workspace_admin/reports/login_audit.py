"""Leitura de atividades de Login Audit pela Reports API."""

import re
from datetime import datetime
from urllib.parse import quote

import httpx

from google_workspace_admin.auth.dwd import get_workspace_access_token


LOGIN_REPORTS_AUDIT_READONLY_SCOPE = (
    "https://www.googleapis.com/auth/admin.reports.audit.readonly"
)

LOGIN_AUDIT_ACTIVITIES_URL = (
    "https://admin.googleapis.com/admin/reports/v1/activity/"
    "users/{user_key}/applications/login"
)

_RFC3339_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


def _authorization_headers() -> dict[str, str]:
    token, _ = get_workspace_access_token(
        scopes=[LOGIN_REPORTS_AUDIT_READONLY_SCOPE]
    )
    return {"Authorization": f"Bearer {token}"}


def _validate_optional_string(
    value: str | None,
    parameter_name: str,
) -> None:
    if value is not None and not value.strip():
        raise ValueError(f"{parameter_name} não pode estar vazio.")


def _parse_rfc3339(value: str, parameter_name: str) -> datetime:
    if not _RFC3339_PATTERN.fullmatch(value):
        raise ValueError(
            f"{parameter_name} deve estar no formato RFC 3339."
        )

    normalized_value = (
        f"{value[:-1]}+00:00"
        if value.endswith("Z")
        else value
    )

    try:
        return datetime.fromisoformat(normalized_value)
    except ValueError as error:
        raise ValueError(
            f"{parameter_name} deve estar no formato RFC 3339."
        ) from error


def _validate_login_audit_arguments(
    *,
    max_results: int,
    page_token: str | None,
    user_key: str,
    event_name: str | None,
    filters: str | None,
    start_time: str | None,
    end_time: str | None,
    actor_ip_address: str | None,
    org_unit_id: str | None,
) -> None:
    if max_results < 1 or max_results > 100:
        raise ValueError("max_results deve estar entre 1 e 100.")

    if not user_key.strip():
        raise ValueError("user_key não pode estar vazio.")

    for parameter_name, value in (
        ("page_token", page_token),
        ("event_name", event_name),
        ("filters", filters),
        ("start_time", start_time),
        ("end_time", end_time),
        ("actor_ip_address", actor_ip_address),
        ("org_unit_id", org_unit_id),
    ):
        _validate_optional_string(value, parameter_name)

    parsed_start_time = (
        _parse_rfc3339(start_time, "start_time")
        if start_time is not None
        else None
    )
    parsed_end_time = (
        _parse_rfc3339(end_time, "end_time")
        if end_time is not None
        else None
    )

    if (
        parsed_start_time is not None
        and parsed_end_time is not None
        and parsed_start_time >= parsed_end_time
    ):
        raise ValueError("start_time deve ser anterior a end_time.")


def list_login_audit_activities(
    max_results: int = 25,
    page_token: str | None = None,
    user_key: str = "all",
    event_name: str | None = None,
    filters: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    actor_ip_address: str | None = None,
    org_unit_id: str | None = None,
) -> dict:
    """Lista uma página de atividades de Login Audit do Workspace."""
    _validate_login_audit_arguments(
        max_results=max_results,
        page_token=page_token,
        user_key=user_key,
        event_name=event_name,
        filters=filters,
        start_time=start_time,
        end_time=end_time,
        actor_ip_address=actor_ip_address,
        org_unit_id=org_unit_id,
    )

    params = {"maxResults": max_results}
    optional_parameters = {
        "pageToken": page_token,
        "eventName": event_name,
        "filters": filters,
        "startTime": start_time,
        "endTime": end_time,
        "actorIpAddress": actor_ip_address,
        "orgUnitID": org_unit_id,
    }
    params.update(
        {
            parameter_name: value
            for parameter_name, value in optional_parameters.items()
            if value is not None
        }
    )

    url = LOGIN_AUDIT_ACTIVITIES_URL.format(
        user_key=quote(user_key, safe=""),
    )

    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            url,
            headers=_authorization_headers(),
            params=params,
        )
        response.raise_for_status()
        payload = response.json()

    return {
        "activities": payload.get("items", []),
        "next_page_token": payload.get("nextPageToken"),
    }
