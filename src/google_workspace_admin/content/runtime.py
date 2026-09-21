"""Concrete, startup-assembled façade for the local Content Foundation.

The supported API is intentionally small. Runtime state is kept outside the
instance so a fabricated or incomplete ``ContentRuntime`` has no executable
binding. The composition helper accepts a fixed services record, never an
execution callable supplied by a Content caller.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from weakref import WeakKeyDictionary

from google_workspace_admin.content.auth.capabilities import capability_rule
from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError
from google_workspace_admin.content.http_adapter import (
    ContentTypedResult,
    _HttpAdapterPorts,
)
from google_workspace_admin.content.operations import (
    ContentOperation,
    DriveGetRequest,
    DriveListRequest,
    _NormalizedOperationRequest,
    _operation_for_request,
    _request_profile_id,
    _request_user_key,
)


@dataclass(frozen=True, slots=True)
class _RuntimeServices:
    registry: object
    resolve_subject: Callable[..., object]
    authorize: Callable[..., object]
    normalize_operation: Callable[..., _NormalizedOperationRequest]
    adapter: _HttpAdapterPorts


# Runtime state is not an authority token. It is deliberately absent from the
# public façade instance and is populated only by the startup composition root.
_RUNTIME_BINDINGS: WeakKeyDictionary = WeakKeyDictionary()


class ContentRuntime:
    """Only supported operational façade for future Content callers."""

    __slots__ = ("__weakref__",)

    def __new__(cls, *args: object, **kwargs: object):
        del args, kwargs
        raise TypeError("ContentRuntime is created by the startup bootstrap")

    def __init_subclass__(cls, **kwargs: object) -> None:
        del cls, kwargs
        raise TypeError("ContentRuntime cannot be subclassed")

    def execute(self, request: object) -> ContentTypedResult:
        services = _RUNTIME_BINDINGS.get(self)
        if services is None:
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.RUNTIME,
            )
        try:
            operation = _operation_for_request(request)
            profile_handle = services.registry.select(_request_profile_id(request))
            rule = capability_rule(operation)
            subject_handle = services.resolve_subject(
                _request_user_key(request),
                profile_handle,
                rule.subject_capability,
            )
            admin_mode = (
                request.use_domain_admin_access
                if type(request) in {DriveListRequest, DriveGetRequest}
                else False
            )
            context = services.authorize(
                profile_handle,
                subject_handle,
                operation,
                admin_mode,
            )
            normalized = services.normalize_operation(request, context)
            if operation is ContentOperation.DRIVE_LIST:
                return services.adapter.drive_list(context, normalized)
            if operation is ContentOperation.DRIVE_GET:
                return services.adapter.drive_get(context, normalized)
            if operation is ContentOperation.DRIVE_FILES_LIST:
                return services.adapter.drive_files_list(context, normalized)
            if operation is ContentOperation.FILE_CONTENT_READ:
                return services.adapter.file_content_read(context, normalized)
        except ContentSafeError:
            raise
        except Exception:
            raise ContentSafeError(
                code="UNEXPECTED_LOCAL",
                operation=ContentErrorOperation.RUNTIME,
            ) from None
        raise ContentSafeError(
            code="READ_ONLY_OPERATION_FORBIDDEN",
            operation=ContentErrorOperation.RUNTIME,
        )

    def close(self) -> None:
        services = _RUNTIME_BINDINGS.pop(self, None)
        if services is not None:
            services.adapter.close()

    def __copy__(self):
        raise TypeError("ContentRuntime cannot be copied")

    def __deepcopy__(self, memo: object):
        del memo
        raise TypeError("ContentRuntime cannot be copied")

    def __repr__(self) -> str:
        return "<ContentRuntime sealed>"


def _assemble_content_runtime(services: _RuntimeServices) -> ContentRuntime:
    """Bind fixed startup services; not a caller-facing execution API."""

    if (
        type(services) is not _RuntimeServices
        or type(services.adapter) is not _HttpAdapterPorts
    ):
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.BOOTSTRAP,
        )
    runtime = object.__new__(ContentRuntime)
    _RUNTIME_BINDINGS[runtime] = services
    return runtime
