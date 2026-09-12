"""Leitura de User Usage Reports pela Admin SDK Reports API."""

import re
from datetime import datetime
from urllib.parse import quote

import httpx

from google_workspace_admin.auth.dwd import get_workspace_access_token


USER_USAGE_REPORTS_USAGE_READONLY_SCOPE = (
    "https://www.googleapis.com/auth/admin.reports.usage.readonly"
)
USER_USAGE_READONLY_SCOPE = USER_USAGE_REPORTS_USAGE_READONLY_SCOPE

USER_USAGE_REPORT_URL = (
    "https://admin.googleapis.com/admin/reports/v1/usage/"
    "users/{user_key}/dates/{date}"
)

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _authorization_headers() -> dict[str, str]:
    token, _ = get_workspace_access_token(
        scopes=[USER_USAGE_REPORTS_USAGE_READONLY_SCOPE]
    )

    return {"Authorization": f"Bearer {token}"}


def _validate_optional_string(
    value: str | None,
    parameter_name: str,
) -> None:
    if value is not None and (
        not isinstance(value, str) or not value.strip()
    ):
        raise ValueError(f"{parameter_name} não pode estar vazio.")


def _validate_date(value: str) -> None:
    if not isinstance(value, str) or not _DATE_PATTERN.fullmatch(value):
        raise ValueError("date deve estar no formato YYYY-MM-DD.")

    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as error:
        raise ValueError("date deve ser uma data válida.") from error


def _validate_user_usage_arguments(
    *,
    date: str,
    max_results: int,
    page_token: str | None,
    user_key: str,
    parameters: str | None,
    filters: str | None,
    org_unit_id: str | None,
) -> None:
    _validate_date(date)

    if (
        isinstance(max_results, bool)
        or not isinstance(max_results, int)
        or max_results < 1
        or max_results > 100
    ):
        raise ValueError("max_results deve estar entre 1 e 100.")

    if not isinstance(user_key, str) or not user_key.strip():
        raise ValueError("user_key não pode estar vazio.")

    for parameter_name, value in (
        ("page_token", page_token),
        ("parameters", parameters),
        ("filters", filters),
        ("org_unit_id", org_unit_id),
    ):
        _validate_optional_string(value, parameter_name)


def get_user_usage_report(
    date: str,
    max_results: int = 25,
    page_token: str | None = None,
    user_key: str = "all",
    parameters: str | None = None,
    filters: str | None = None,
    org_unit_id: str | None = None,
) -> dict:
    """Obtém exatamente uma página de User Usage Report."""
    _validate_user_usage_arguments(
        date=date,
        max_results=max_results,
        page_token=page_token,
        user_key=user_key,
        parameters=parameters,
        filters=filters,
        org_unit_id=org_unit_id,
    )

    params = {"maxResults": max_results}
    optional_parameters = {
        "pageToken": page_token,
        "parameters": parameters,
        "filters": filters,
        "orgUnitID": org_unit_id,
    }
    params.update(
        {
            parameter_name: value
            for parameter_name, value in optional_parameters.items()
            if value is not None
        }
    )

    url = USER_USAGE_REPORT_URL.format(
        user_key=quote(user_key, safe=""),
        date=quote(date, safe=""),
    )

    headers = _authorization_headers()

    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            url,
            headers=headers,
            params=params,
        )
        response.raise_for_status()

        payload = response.json()
        warnings = payload.get("warnings")
        warnings_count = len(warnings) if isinstance(warnings, list) else 0

        return {
            "usage_reports": payload.get("usageReports", []),
            "next_page_token": payload.get("nextPageToken"),
            "warnings_present": warnings_count > 0,
            "warnings_count": warnings_count,
        }
