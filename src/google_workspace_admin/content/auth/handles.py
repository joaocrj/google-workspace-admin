"""Opaque, issuer-bound authorities for the in-process Content runtime.

Handles carry no authority metadata. Authority lives in a per-runtime closure
and is established solely by weak identity membership. Fabricating an instance
with ``object.__new__`` therefore creates an inert object.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from google_workspace_admin.content.auth.profile import ContentAuthProfile
from google_workspace_admin.content.auth.scopes import ApprovedScopeProfile
from google_workspace_admin.content.auth.subject import WorkspaceSubject
from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError


class _OpaqueAuthority:
    __slots__ = ("__weakref__",)

    def __new__(cls, *args: object, **kwargs: object):
        del args, kwargs
        raise TypeError("Content authority handles are issuer-created")

    def __copy__(self):
        raise TypeError("Content authority handles cannot be copied")

    def __deepcopy__(self, memo: object):
        del memo
        raise TypeError("Content authority handles cannot be copied")

    def __repr__(self) -> str:
        return f"<{type(self).__name__} opaque>"


class RegisteredProfileHandle(_OpaqueAuthority):
    __slots__ = ()

    def __init_subclass__(cls, **kwargs: object) -> None:
        del cls, kwargs
        raise TypeError("RegisteredProfileHandle cannot be subclassed")


class AuthorizedSubjectHandle(_OpaqueAuthority):
    __slots__ = ()

    def __init_subclass__(cls, **kwargs: object) -> None:
        del cls, kwargs
        raise TypeError("AuthorizedSubjectHandle cannot be subclassed")


class AuthorizedOperationContext(_OpaqueAuthority):
    __slots__ = ()

    def __init_subclass__(cls, **kwargs: object) -> None:
        del cls, kwargs
        raise TypeError("AuthorizedOperationContext cannot be subclassed")


@dataclass(frozen=True, slots=True)
class _ProfileAuthority:
    profile: ContentAuthProfile


@dataclass(frozen=True, slots=True)
class _SubjectAuthority:
    profile_handle: RegisteredProfileHandle
    subject: WorkspaceSubject
    capability: object


@dataclass(frozen=True, slots=True)
class _OperationAuthority:
    profile_handle: RegisteredProfileHandle
    subject_handle: AuthorizedSubjectHandle
    operation: object
    approved_scope_profile: ApprovedScopeProfile
    admin_mode_authorized: bool


class _AuthorityKernel(Protocol):
    def issue_profile(self, profile: ContentAuthProfile) -> RegisteredProfileHandle: ...
    def require_profile(self, handle: object) -> _ProfileAuthority: ...
    def issue_subject(
        self,
        profile_handle: RegisteredProfileHandle,
        subject: WorkspaceSubject,
        capability: object,
    ) -> AuthorizedSubjectHandle: ...
    def require_subject(self, handle: object) -> _SubjectAuthority: ...
    def issue_context(
        self,
        profile_handle: RegisteredProfileHandle,
        subject_handle: AuthorizedSubjectHandle,
        operation: object,
        approved_scope_profile: ApprovedScopeProfile,
        admin_mode_authorized: bool,
    ) -> AuthorizedOperationContext: ...
    def require_context(self, handle: object) -> _OperationAuthority: ...
