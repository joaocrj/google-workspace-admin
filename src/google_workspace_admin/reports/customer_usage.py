"""Leitura de Customer Usage Reports pela Admin SDK Reports API."""

import re
from datetime import datetime
from urllib.parse import quote

import httpx

from google_workspace_admin.auth.dwd import get_workspace_access_token


CUSTOMER_USAGE_REPORTS_USAGE_READONLY_SCOPE = (
    "https://www.googleapis.com/auth/admin.reports.usage.readonly"
)

CUSTOMER_USAGE_REPORT_URL = (
    "https://admin.googleapis.com/admin/reports/v1/usage/dates/{date}"
)

CUSTOMER_USAGE_ALLOWED_PARAMETERS = frozenset(
    {
        "accounts:num_users",
        "accounts:num_archived_users",
        "accounts:num_disabled_accounts",
        "accounts:num_suspended_users",
        "accounts:customer_used_quota_in_mb",
        "accounts:drive_used_quota_in_mb",
        "accounts:gmail_used_quota_in_mb",
        "accounts:team_drive_used_quota_in_mb",
        "accounts:total_quota_in_mb",
        "accounts:used_quota_in_mb",
    }
)

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_date(value: str) -> None:
    if not isinstance(value, str) or not _DATE_PATTERN.fullmatch(value):
        raise ValueError("date deve estar no formato YYYY-MM-DD.")

    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as error:
        raise ValueError("date deve ser uma data válida.") from error


def _validate_page_token(value: str | None) -> None:
    if value is not None and (
        not isinstance(value, str) or not value.strip()
    ):
        raise ValueError("page_token não pode estar vazio.")


def _normalize_parameters(parameters: str) -> str:
    if not isinstance(parameters, str) or not parameters.strip():
        raise ValueError("parameters é obrigatório e não pode estar vazio.")

    normalized_parameters = []
    seen_parameters = set()

    for raw_parameter in parameters.split(","):
        parameter = raw_parameter.strip()
        if not parameter:
            raise ValueError("parameters deve conter métricas não vazias.")
        if ":" not in parameter or parameter.count(":") != 1:
            raise ValueError(
                "parameters deve conter métricas no formato application:metric."
            )
        if parameter not in CUSTOMER_USAGE_ALLOWED_PARAMETERS:
            raise ValueError(
                f"parameters contém métrica não allowlisted: {parameter}."
            )
        if parameter in seen_parameters:
            raise ValueError(f"parameters contém métrica duplicada: {parameter}.")

        seen_parameters.add(parameter)
        normalized_parameters.append(parameter)

    return ",".join(normalized_parameters)


def _validate_customer_usage_arguments(
    *,
    date: str,
    parameters: str,
    page_token: str | None,
) -> str:
    _validate_date(date)
    normalized_parameters = _normalize_parameters(parameters)
    _validate_page_token(page_token)
    return normalized_parameters


def _authorization_headers() -> dict[str, str]:
    token, _ = get_workspace_access_token(
        scopes=[CUSTOMER_USAGE_REPORTS_USAGE_READONLY_SCOPE]
    )
    return {"Authorization": f"Bearer {token}"}


def get_customer_usage_report(
    date: str,
    parameters: str,
    page_token: str | None = None,
) -> dict:
    """Obtém exatamente uma página de Customer Usage Report."""
    normalized_parameters = _validate_customer_usage_arguments(
        date=date,
        parameters=parameters,
        page_token=page_token,
    )

    params = {"parameters": normalized_parameters}
    if page_token is not None:
        params["pageToken"] = page_token

    url = CUSTOMER_USAGE_REPORT_URL.format(
        date=quote(date, safe=""),
    )

    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            url,
            headers=_authorization_headers(),
            params=params,
        )
        response.raise_for_status()
        payload = response.json()

    warnings = payload.get("warnings")
    warnings_count = len(warnings) if isinstance(warnings, list) else 0
    usage_reports = payload.get("usageReports", [])
    if not isinstance(usage_reports, list):
        usage_reports = []

    next_page_token = payload.get("nextPageToken")
    if not isinstance(next_page_token, str) or not next_page_token:
        next_page_token = None

    return {
        "usage_reports": usage_reports,
        "next_page_token": next_page_token,
        "warnings_present": warnings_count > 0,
        "warnings_count": warnings_count,
    }
