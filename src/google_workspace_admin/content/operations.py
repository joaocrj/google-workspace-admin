"""Closed request and operation contracts for the future Drive vertical."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from google_workspace_admin.content.auth.handles import _OperationAuthority
from google_workspace_admin.content.auth.scopes import ApprovedScopeProfile
from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError
from google_workspace_admin.content.limits import PaginationBounds, PaginationRequest


class ContentOperation(str, Enum):
    DRIVE_LIST = "drive.list"
    DRIVE_GET = "drive.get"
    DRIVE_FILES_LIST = "drive.files.list"


@dataclass(frozen=True, slots=True)
class DriveListRequest:
    profile_id: str
    user_key: str
    page_size: object | None = None
    page_token: object | None = None
    max_items: object | None = None
    use_domain_admin_access: object = False


@dataclass(frozen=True, slots=True)
class DriveGetRequest:
    profile_id: str
    user_key: str
    drive_id: object
    use_domain_admin_access: object = False


@dataclass(frozen=True, slots=True)
class DriveFilesListRequest:
    profile_id: str
    user_key: str
    drive_id: object
    page_size: object | None = None
    page_token: object | None = None
    max_items: object | None = None


DRIVE_LIST_FIELDS = "nextPageToken,drives(id,name)"
DRIVE_GET_FIELDS = "id,name"
DRIVE_FILES_LIST_FIELDS = (
    "nextPageToken,files(id,name,mimeType,modifiedTime,size,parents,trashed)"
)

DRIVE_LIST_PAGINATION = PaginationBounds(
    api_max_page_size=100,
    content_hard_cap=100,
    default_page_size=25,
    max_items_per_invocation=100,
)
DRIVE_FILES_LIST_PAGINATION = PaginationBounds(
    api_max_page_size=1000,
    content_hard_cap=500,
    default_page_size=100,
    max_items_per_invocation=500,
)


@dataclass(frozen=True, slots=True)
class ContentOperationContract:
    operation: ContentOperation
    method: str
    endpoint_template: str
    scope_profile: ApprovedScopeProfile
    endpoint_family: str
    supports_admin_access: bool
    pagination: PaginationBounds | None
    default_fields: str
    idempotent_read: bool


@dataclass(frozen=True, slots=True)
class _NormalizedOperationRequest:
    """Validated operation data, never an executable HTTP capability."""

    operation: ContentOperation
    drive_id: str | None
    page_size: int | None
    page_token: str | None
    response_item_limit: int | None
    admin_mode: bool


_DRIVE_API_ROOT = "https://www.googleapis.com/drive/v3"

_CONTRACTS = MappingProxyType(
    {
        ContentOperation.DRIVE_LIST: ContentOperationContract(
            ContentOperation.DRIVE_LIST,
            "GET",
            f"{_DRIVE_API_ROOT}/drives",
            ApprovedScopeProfile.DRIVE_DISCOVERY,
            "drive.drives.list",
            True,
            DRIVE_LIST_PAGINATION,
            DRIVE_LIST_FIELDS,
            True,
        ),
        ContentOperation.DRIVE_GET: ContentOperationContract(
            ContentOperation.DRIVE_GET,
            "GET",
            f"{_DRIVE_API_ROOT}/drives/{{drive_id}}",
            ApprovedScopeProfile.DRIVE_DISCOVERY,
            "drive.drives.get",
            True,
            None,
            DRIVE_GET_FIELDS,
            True,
        ),
        ContentOperation.DRIVE_FILES_LIST: ContentOperationContract(
            ContentOperation.DRIVE_FILES_LIST,
            "GET",
            f"{_DRIVE_API_ROOT}/files",
            ApprovedScopeProfile.DRIVE_DISCOVERY,
            "drive.files.list",
            False,
            DRIVE_FILES_LIST_PAGINATION,
            DRIVE_FILES_LIST_FIELDS,
            True,
        ),
    }
)


def get_operation_contract(operation: ContentOperation) -> ContentOperationContract:
    if type(operation) is not ContentOperation:
        raise ContentSafeError(
            code="READ_ONLY_OPERATION_FORBIDDEN",
            operation=ContentErrorOperation.OPERATION_RESOLUTION,
        )
    return _CONTRACTS[operation]


def _operation_for_request(request: object) -> ContentOperation:
    request_types = {
        DriveListRequest: ContentOperation.DRIVE_LIST,
        DriveGetRequest: ContentOperation.DRIVE_GET,
        DriveFilesListRequest: ContentOperation.DRIVE_FILES_LIST,
    }
    try:
        return request_types[type(request)]
    except KeyError:
        raise ContentSafeError(
            code="READ_ONLY_OPERATION_FORBIDDEN",
            operation=ContentErrorOperation.OPERATION_RESOLUTION,
        ) from None


def _request_profile_id(request: object) -> object:
    return request.profile_id  # type: ignore[attr-defined]


def _request_user_key(request: object) -> object:
    return request.user_key  # type: ignore[attr-defined]


def _require_nonempty_string(
    value: object,
    *,
    max_length: int | None = None,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.OPERATION_NORMALIZATION,
        )
    normalized = value.strip()
    if any(
        character.isspace()
        or ord(character) < 32
        or 0x7F <= ord(character) <= 0x9F
        for character in normalized
    ):
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.OPERATION_NORMALIZATION,
        )
    if max_length is not None and len(normalized) > max_length:
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.OPERATION_NORMALIZATION,
        )
    return normalized


def _require_drive_id(value: object) -> str:
    normalized = _require_nonempty_string(value, max_length=256)
    folded = normalized.casefold()
    if (
        "://" in normalized
        or folded.startswith(
            ("http:", "https:", "drive.google.com/", "www.googleapis.com/")
        )
    ):
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.OPERATION_NORMALIZATION,
        )
    return normalized


def _require_bool(value: object) -> bool:
    if type(value) is not bool:
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.OPERATION_NORMALIZATION,
        )
    return value


def _require_opaque_page_token(value: object) -> str | None:
    if value is None:
        return None
    if type(value) is not str or not value:
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.PAGINATION,
        )
    if any(
        character.isspace()
        or ord(character) < 32
        or 0x7F <= ord(character) <= 0x9F
        for character in value
    ):
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.PAGINATION,
        )
    return value


def _pagination(
    contract: ContentOperationContract,
    *,
    page_size: object | None,
    page_token: object | None,
    max_items: object | None,
) -> PaginationRequest:
    assert contract.pagination is not None
    return PaginationRequest(
        page_size=(contract.pagination.default_page_size if page_size is None else page_size),
        page_token=page_token,
        max_items=(
            contract.pagination.max_items_per_invocation
            if max_items is None
            else max_items
        ),
        bounds=contract.pagination,
    )


def _normalize_verified_operation_request(
    request: object,
    authority: _OperationAuthority,
) -> _NormalizedOperationRequest:
    operation = _operation_for_request(request)
    contract = get_operation_contract(operation)
    if authority.operation is not operation or authority.approved_scope_profile is not contract.scope_profile:
        raise ContentSafeError(
            code="READ_ONLY_OPERATION_FORBIDDEN",
            operation=ContentErrorOperation.OPERATION_NORMALIZATION,
        )
    use_admin = _require_bool(
        getattr(request, "use_domain_admin_access", False)
    )
    if use_admin and (
        not contract.supports_admin_access or not authority.admin_mode_authorized
    ):
        raise ContentSafeError(
            code="READ_ONLY_OPERATION_FORBIDDEN",
            operation=ContentErrorOperation.OPERATION_NORMALIZATION,
        )

    response_item_limit: int | None = None
    drive_id: str | None = None
    page_size: int | None = None
    page_token: str | None = None

    if operation is ContentOperation.DRIVE_LIST:
        pagination = _pagination(
            contract,
            page_size=request.page_size,
            page_token=request.page_token,
            max_items=request.max_items,
        )
        page_size = pagination.effective_page_size
        page_token = pagination.page_token
        response_item_limit = pagination.effective_page_size
    elif operation is ContentOperation.DRIVE_GET:
        drive_id = _require_nonempty_string(request.drive_id, max_length=256)
    elif operation is ContentOperation.DRIVE_FILES_LIST:
        drive_id = _require_drive_id(request.drive_id)
        page_token = _require_opaque_page_token(request.page_token)
        pagination = _pagination(
            contract,
            page_size=request.page_size,
            page_token=page_token,
            max_items=request.max_items,
        )
        page_size = pagination.effective_page_size
        page_token = pagination.page_token
        response_item_limit = pagination.effective_page_size

    return _NormalizedOperationRequest(
        operation=operation,
        drive_id=drive_id,
        page_size=page_size,
        page_token=page_token,
        response_item_limit=response_item_limit,
        admin_mode=use_admin,
    )
