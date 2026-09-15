"""Helpers for bounded, safe Workspace API responses."""

from __future__ import annotations

from collections.abc import Iterable
import re

import httpx
from mcp.server.mcpserver.exceptions import ToolError


SAFE_ERROR_CODES = frozenset(
    {
        "ADC_REFRESH",
        "IAM_SIGN_JWT",
        "DWD_TOKEN_EXCHANGE",
        "WORKSPACE_HTTP",
        "RESPONSE_VALIDATION",
        "LOCAL_VALIDATION",
        "UNEXPECTED_LOCAL",
        "TARGET_SUBJECT_INVALID",
        "MAILBOX_NOT_ALLOWED",
        "READ_ONLY_OPERATION_FORBIDDEN",
        "CONTEXT_LIMIT_EXCEEDED",
        "QUOTA_EXCEEDED",
        "CONTENT_NOT_SUPPORTED",
        "CONTENT_TOO_LARGE",
        "CONTENT_PARSE_FAILED",
        "ATTACHMENT_NOT_SUPPORTED",
        "AMBIGUOUS_RESOURCE",
        "CONFIRMATION_REQUIRED",
    }
)

_SAFE_LAYERS = frozenset(
    {
        "adc",
        "iam",
        "dwd",
        "workspace",
        "response",
        "validation",
        "local",
        "content",
    }
)

_SAFE_OPERATION_ALIASES = {
    "Directory users.list": "users.list",
    "Directory users.get": "users.get",
    "Directory groups.list": "groups.list",
    "Directory group members.list": "group_members.list",
    "Directory orgunits.list": "orgunits.list",
    "Directory mobile devices.list": "mobile_devices.list",
    "Directory chromeos devices.list": "chromeos_devices.list",
    "Directory roles.list": "roles.list",
    "Directory role assignments.list": "role_assignments.list",
    "Directory domains.list": "domains.list",
    "Directory domain aliases.list": "domain_aliases.list",
    "Directory resources.buildings.list": "buildings.list",
    "Directory resources.calendars.list": "calendar_resources.list",
    "Directory resources.features.list": "calendar_features.list",
    "IAM signJwt": "signJwt",
    "OAuth DWD": "token_exchange",
}
_SAFE_OPERATION_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_SAFE_HTTP_CATEGORIES = frozenset(
    {
        "authentication",
        "authorization",
        "client_error",
        "upstream_error",
        "http_error",
        "timeout",
        "transport_error",
        "malformed_response",
    }
)


def _safe_operation(operation: object) -> str:
    if isinstance(operation, str) and operation in _SAFE_OPERATION_ALIASES:
        return _SAFE_OPERATION_ALIASES[operation]
    if isinstance(operation, str) and _SAFE_OPERATION_PATTERN.fullmatch(
        operation
    ):
        return operation
    return "unknown"


def _safe_status_code(status_code: object) -> int | None:
    if (
        isinstance(status_code, int)
        and not isinstance(status_code, bool)
        and 100 <= status_code <= 599
    ):
        return status_code
    return None


def _response_status(response: object) -> int | None:
    return _safe_status_code(getattr(response, "status_code", None))


class SafeOperationError(ValueError, ToolError):
    """Erro estruturado com metadados internos determinísticos e seguros."""

    def __init__(
        self,
        *,
        code: str,
        layer: str,
        operation: str,
        http_status: int | None = None,
    ) -> None:
        self.code = code if code in SAFE_ERROR_CODES else "UNEXPECTED_LOCAL"
        self.layer = layer if layer in _SAFE_LAYERS else "local"
        self.operation = _safe_operation(operation)
        self.http_status = _safe_status_code(http_status)
        # Compatibilidade com os consumidores internos anteriores.
        self.status_code = self.http_status

        status = (
            str(self.http_status)
            if self.http_status is not None
            else "none"
        )
        super().__init__(
            f"code={self.code}; layer={self.layer}; "
            f"operation={self.operation}; http_status={status}"
        )


class WorkspaceApiError(SafeOperationError):
    """Erro seguro de transporte ou de shape da API Workspace."""

    def __init__(
        self,
        operation: str,
        category: str,
        status_code: int | None = None,
        *,
        code: str = "WORKSPACE_HTTP",
        layer: str = "workspace",
    ) -> None:
        self.category = (
            category
            if isinstance(category, str) and category in _SAFE_HTTP_CATEGORIES
            else "http_error"
        )
        super().__init__(
            code=code,
            layer=layer,
            operation=operation,
            http_status=status_code,
        )


class PageResult(list[dict]):
    """Lista de itens com o token opaco da página atual.

    A herança de list preserva a compatibilidade dos helpers internos antigos;
    as tools MCP convertem o resultado para um objeto explícito de página.
    """

    def __init__(
        self,
        items: Iterable[dict],
        next_page_token: str | None,
    ) -> None:
        super().__init__(items)
        self.next_page_token = next_page_token


def validate_max_results(value: object, maximum: int) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 1
        or value > maximum
    ):
        raise ValueError(
            f"max_results deve estar entre 1 e {maximum}."
        )


def validate_page_token(value: object) -> None:
    if value is not None and (
        not isinstance(value, str) or not value.strip()
    ):
        raise ValueError(
            "page_token não pode estar vazio e deve ser uma string não vazia."
        )


def validate_optional_string(value: object, parameter_name: str) -> None:
    if value is not None and (
        not isinstance(value, str) or not value.strip()
    ):
        raise ValueError(f"{parameter_name} não pode estar vazio.")


def _http_error_category(status_code: int) -> str:
    if status_code == 401:
        return "authentication"
    if status_code == 403:
        return "authorization"
    if 400 <= status_code < 500:
        return "client_error"
    if status_code >= 500:
        return "upstream_error"
    return "http_error"


def raise_for_status_safe(response: httpx.Response, operation: str) -> None:
    """Converte HTTPStatusError em erro sem body, headers ou query."""
    safe_error = None
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError:
        status_code = _response_status(response)
        safe_error = WorkspaceApiError(
            operation=operation,
            category=(
                _http_error_category(status_code)
                if status_code is not None
                else "http_error"
            ),
            status_code=status_code,
        )

    if safe_error is not None:
        raise safe_error


def request_safe(
    client: httpx.Client,
    method: str,
    url: str,
    operation: str,
    **kwargs: object,
) -> httpx.Response:
    """Executa uma chamada HTTP sem retransmitir detalhes sensíveis."""
    safe_error = None
    try:
        response = getattr(client, method)(url, **kwargs)
    except httpx.TimeoutException:
        safe_error = WorkspaceApiError(
            operation=operation,
            category="timeout",
        )
    except httpx.RequestError:
        safe_error = WorkspaceApiError(
            operation=operation,
            category="transport_error",
        )

    if safe_error is not None:
        raise safe_error

    raise_for_status_safe(response, operation)
    return response


def parse_json_object(response: httpx.Response, operation: str) -> dict:
    malformed_response = False
    try:
        payload = response.json()
    except (TypeError, ValueError):
        malformed_response = True

    if malformed_response:
        raise WorkspaceApiError(
            operation=operation,
            category="malformed_response",
            code="RESPONSE_VALIDATION",
            layer="response",
            status_code=_response_status(response),
        )

    if not isinstance(payload, dict):
        raise WorkspaceApiError(
            operation=operation,
            category="malformed_response",
            code="RESPONSE_VALIDATION",
            layer="response",
            status_code=_response_status(response),
        )

    return payload


def require_dict_list(
    payload: dict,
    field_name: str,
    operation: str,
) -> list[dict]:
    if field_name not in payload:
        return []

    items = payload[field_name]
    if not isinstance(items, list) or any(
        not isinstance(item, dict) for item in items
    ):
        raise WorkspaceApiError(
            operation=operation,
            category="malformed_response",
            code="RESPONSE_VALIDATION",
            layer="response",
        )

    return items


def get_next_page_token(payload: dict, operation: str) -> str | None:
    if "nextPageToken" not in payload or payload["nextPageToken"] is None:
        return None

    token = payload["nextPageToken"]
    if not isinstance(token, str) or not token.strip():
        raise WorkspaceApiError(
            operation=operation,
            category="malformed_response",
            code="RESPONSE_VALIDATION",
            layer="response",
        )

    return token


def validate_next_page_token(
    value: object,
    operation: str,
) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str) or not value.strip():
        raise WorkspaceApiError(
            operation=operation,
            category="malformed_response",
            code="RESPONSE_VALIDATION",
            layer="response",
        )

    return value
