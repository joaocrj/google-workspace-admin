"""Trusted startup composition root for the local Content Foundation."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from types import MappingProxyType
import time
from weakref import WeakKeyDictionary

import httpx

from google_workspace_admin.content.auth.capabilities import (
    AdminCapability,
    SubjectCapability,
    capability_rule,
)
from google_workspace_admin.content.auth.handles import (
    AuthorizedOperationContext,
    AuthorizedSubjectHandle,
    RegisteredProfileHandle,
    _OperationAuthority,
    _ProfileAuthority,
    _SubjectAuthority,
)
from google_workspace_admin.content.auth.profile import ContentAuthProfile
from google_workspace_admin.content.auth.registry import ProvisionedContentProfile
from google_workspace_admin.content.auth.resolver import SubjectLookup
from google_workspace_admin.content.auth.subject import WorkspaceSubject
from google_workspace_admin.content.auth.production import build_content_token_provider
from google_workspace_admin.content.config import load_content_config
from google_workspace_admin.content.continuation import DocsContinuationManager
from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError
from google_workspace_admin.content.http_adapter import _build_http_adapter
from google_workspace_admin.content.operations import (
    ContentOperation,
    _normalize_verified_operation_request,
)
from google_workspace_admin.content.policy import validate_subject_for_capability
from google_workspace_admin.content.public_file_ref import PublicFileRefProvider
from google_workspace_admin.content.runtime import (
    ContentRuntime,
    _RuntimeServices,
    _assemble_content_runtime,
)
from google_workspace_admin.content.transport import RetryPolicy


def _load_provisioned_profiles() -> tuple[ProvisionedContentProfile, ...]:
    config = load_content_config()
    return (config.to_provisioned_profile(),)


def _build_subject_lookup() -> SubjectLookup:
    config = load_content_config()
    subject = config.fixed_subject()
    canonical_subject = subject.primary_email.casefold()

    def lookup(user_key: str) -> WorkspaceSubject | None:
        if not isinstance(user_key, str) or user_key.strip().casefold() != canonical_subject:
            return None
        return subject

    return lookup


def _build_http_client() -> httpx.Client:
    return httpx.Client(
        follow_redirects=False,
        timeout=30.0,
    )


def _build_retry_policy() -> RetryPolicy:
    return RetryPolicy()


def _build_sleeper() -> Callable[[float], None]:
    return time.sleep


def _build_token_provider() -> object:
    config = load_content_config()
    return build_content_token_provider(config)


def _build_public_file_ref_provider() -> PublicFileRefProvider | None:
    config = load_content_config()
    key = config.public_file_ref_hmac_key
    if key is None:
        return None
    return PublicFileRefProvider(config.customer_id, key)


def create_content_runtime() -> ContentRuntime:
    """Assemble the only supported Content runtime from startup providers."""

    profiles = _load_provisioned_profiles()
    subject_lookup = _build_subject_lookup()
    client = _build_http_client()
    try:
        # All issuer state and authority issuance remain lexical to this one
        # startup assembly. There is no module-level issuer factory.
        sentinel = object()
        profiles_state: WeakKeyDictionary = WeakKeyDictionary()
        subjects_state: WeakKeyDictionary = WeakKeyDictionary()
        contexts_state: WeakKeyDictionary = WeakKeyDictionary()

        def fail(code: str, operation: ContentErrorOperation) -> ContentSafeError:
            return ContentSafeError(code=code, operation=operation)

        class Kernel:
            __slots__ = ()

            def issue_profile(self, profile: ContentAuthProfile) -> RegisteredProfileHandle:
                if type(profile) is not ContentAuthProfile:
                    raise fail("LOCAL_VALIDATION", ContentErrorOperation.AUTH_PROFILE_PROVENANCE)
                handle = object.__new__(RegisteredProfileHandle)
                profiles_state[handle] = (sentinel, _ProfileAuthority(profile))
                return handle

            def require_profile(self, handle: object) -> _ProfileAuthority:
                if type(handle) is not RegisteredProfileHandle:
                    raise fail("LOCAL_VALIDATION", ContentErrorOperation.AUTH_PROFILE_PROVENANCE)
                record = profiles_state.get(handle)
                if record is None or record[0] is not sentinel:
                    raise fail("LOCAL_VALIDATION", ContentErrorOperation.AUTH_PROFILE_PROVENANCE)
                return record[1]

            def issue_subject(
                self,
                profile_handle: RegisteredProfileHandle,
                subject: WorkspaceSubject,
                capability: SubjectCapability,
            ) -> AuthorizedSubjectHandle:
                self.require_profile(profile_handle)
                if type(subject) is not WorkspaceSubject:
                    raise fail("TARGET_SUBJECT_INVALID", ContentErrorOperation.SUBJECT_PROVENANCE)
                if type(capability) is not SubjectCapability:
                    raise fail("LOCAL_VALIDATION", ContentErrorOperation.CAPABILITY_MATRIX)
                handle = object.__new__(AuthorizedSubjectHandle)
                subjects_state[handle] = (
                    sentinel,
                    _SubjectAuthority(profile_handle, subject, capability),
                )
                return handle

            def require_subject(self, handle: object) -> _SubjectAuthority:
                if type(handle) is not AuthorizedSubjectHandle:
                    raise fail("TARGET_SUBJECT_INVALID", ContentErrorOperation.SUBJECT_PROVENANCE)
                record = subjects_state.get(handle)
                if record is None or record[0] is not sentinel:
                    raise fail("TARGET_SUBJECT_INVALID", ContentErrorOperation.SUBJECT_PROVENANCE)
                self.require_profile(record[1].profile_handle)
                return record[1]

            def issue_context(
                self,
                profile_handle: RegisteredProfileHandle,
                subject_handle: AuthorizedSubjectHandle,
                operation: ContentOperation,
                approved_scope_profile: object,
                admin_mode_authorized: bool,
            ) -> AuthorizedOperationContext:
                self.require_profile(profile_handle)
                subject_record = self.require_subject(subject_handle)
                if subject_record.profile_handle is not profile_handle:
                    raise fail("TARGET_SUBJECT_INVALID", ContentErrorOperation.AUTH_PROFILE_SUBJECT)
                if type(operation) is not ContentOperation or not isinstance(admin_mode_authorized, bool):
                    raise fail("LOCAL_VALIDATION", ContentErrorOperation.AUTH_BROKER)
                handle = object.__new__(AuthorizedOperationContext)
                contexts_state[handle] = (
                    sentinel,
                    _OperationAuthority(
                        profile_handle,
                        subject_handle,
                        operation,
                        approved_scope_profile,
                        admin_mode_authorized,
                    ),
                )
                return handle

            def require_context(self, handle: object) -> _OperationAuthority:
                if type(handle) is not AuthorizedOperationContext:
                    raise fail("READ_ONLY_OPERATION_FORBIDDEN", ContentErrorOperation.AUTH_CONTEXT_PROVENANCE)
                record = contexts_state.get(handle)
                if record is None or record[0] is not sentinel:
                    raise fail("READ_ONLY_OPERATION_FORBIDDEN", ContentErrorOperation.AUTH_CONTEXT_PROVENANCE)
                self.require_profile(record[1].profile_handle)
                self.require_subject(record[1].subject_handle)
                return record[1]

        kernel = Kernel()

        if isinstance(profiles, (str, bytes)):
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.AUTH_PROFILE_PROVISIONING,
            )
        built: dict[str, ContentAuthProfile] = {}
        try:
            for provisioned in profiles:
                if type(provisioned) is not ProvisionedContentProfile:
                    raise ContentSafeError(
                        code="LOCAL_VALIDATION",
                        operation=ContentErrorOperation.AUTH_PROFILE_PROVISIONING,
                    )
                profile = provisioned.build()
                if profile.profile_id in built:
                    raise ContentSafeError(
                        code="LOCAL_VALIDATION",
                        operation=ContentErrorOperation.AUTH_PROFILE_PROVISIONING,
                    )
                built[profile.profile_id] = profile
        except TypeError:
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.AUTH_PROFILE_PROVISIONING,
            ) from None
        if not built:
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.AUTH_PROFILE_PROVISIONING,
            )

        profile_handles = MappingProxyType(
            {
                profile_id: kernel.issue_profile(profile)
                for profile_id, profile in built.items()
            }
        )

        class Registry:
            __slots__ = ()

            def select(self, profile_id: object) -> RegisteredProfileHandle:
                if not isinstance(profile_id, str) or not profile_id.strip():
                    raise ContentSafeError(
                        code="LOCAL_VALIDATION",
                        operation=ContentErrorOperation.AUTH_PROFILE_LOOKUP,
                    )
                try:
                    handle = profile_handles[profile_id.strip()]
                except KeyError:
                    raise ContentSafeError(
                        code="LOCAL_VALIDATION",
                        operation=ContentErrorOperation.AUTH_PROFILE_LOOKUP,
                    ) from None
                kernel.require_profile(handle)
                return handle

        registry = Registry()

        def resolve_subject(
            user_key: object,
            profile_handle: RegisteredProfileHandle,
            capability: SubjectCapability,
        ) -> AuthorizedSubjectHandle:
            if not isinstance(user_key, str) or not user_key.strip():
                raise ContentSafeError(
                    code="TARGET_SUBJECT_INVALID",
                    operation=ContentErrorOperation.SUBJECT_RESOLUTION,
                )
            if type(capability) is not SubjectCapability:
                raise ContentSafeError(
                    code="LOCAL_VALIDATION",
                    operation=ContentErrorOperation.CAPABILITY_MATRIX,
                )
            profile = kernel.require_profile(profile_handle).profile
            try:
                subject = subject_lookup(user_key.strip())
            except ContentSafeError:
                raise
            except Exception:
                raise ContentSafeError(
                    code="TARGET_SUBJECT_INVALID",
                    operation=ContentErrorOperation.SUBJECT_RESOLUTION,
                ) from None
            if type(subject) is not WorkspaceSubject:
                raise ContentSafeError(
                    code="TARGET_SUBJECT_INVALID",
                    operation=ContentErrorOperation.SUBJECT_RESOLUTION,
                )
            validate_subject_for_capability(subject, profile, capability)
            return kernel.issue_subject(profile_handle, subject, capability)

        def authorize(
            profile_handle: RegisteredProfileHandle,
            subject_handle: AuthorizedSubjectHandle,
            operation: ContentOperation,
            admin_mode: bool,
        ) -> AuthorizedOperationContext:
            profile_record = kernel.require_profile(profile_handle)
            subject_record = kernel.require_subject(subject_handle)
            if subject_record.profile_handle is not profile_handle:
                raise ContentSafeError(
                    code="TARGET_SUBJECT_INVALID",
                    operation=ContentErrorOperation.AUTH_PROFILE_SUBJECT,
                )
            if type(admin_mode) is not bool:
                raise ContentSafeError(
                    code="LOCAL_VALIDATION",
                    operation=ContentErrorOperation.AUTH_BROKER,
                )
            rule = capability_rule(operation)
            profile = profile_record.profile
            if rule.scope_profile is not profile.approved_scope_profile:
                raise ContentSafeError(
                    code="READ_ONLY_OPERATION_FORBIDDEN",
                    operation=ContentErrorOperation.CAPABILITY_MATRIX,
                )
            if subject_record.capability is not rule.subject_capability:
                raise ContentSafeError(
                    code="READ_ONLY_OPERATION_FORBIDDEN",
                    operation=ContentErrorOperation.CAPABILITY_MATRIX,
                )
            validate_subject_for_capability(
                subject_record.subject,
                profile,
                rule.subject_capability,
            )
            if admin_mode and (
                rule.admin_capability is AdminCapability.NONE
                or profile.admin_capability is not rule.admin_capability
            ):
                raise ContentSafeError(
                    code="READ_ONLY_OPERATION_FORBIDDEN",
                    operation=ContentErrorOperation.AUTH_BROKER,
                )
            return kernel.issue_context(
                profile_handle,
                subject_handle,
                operation,
                profile.approved_scope_profile,
                admin_mode,
            )

        def normalize_operation(request: object, context: AuthorizedOperationContext):
            authority = kernel.require_context(context)
            return _normalize_verified_operation_request(request, authority)

        token_provider = _build_token_provider()
        if not callable(getattr(token_provider, "get_access_token", None)):
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.AUTH_BROKER,
            )

        def provide_token(
            context: AuthorizedOperationContext,
            scope_profile: object,
        ) -> str:
            authority = kernel.require_context(context)
            profile = kernel.require_profile(authority.profile_handle).profile
            subject = kernel.require_subject(authority.subject_handle).subject
            if scope_profile is not profile.approved_scope_profile:
                raise ContentSafeError(
                    code="READ_ONLY_OPERATION_FORBIDDEN",
                    operation=ContentErrorOperation.CAPABILITY_MATRIX,
                )
            try:
                return token_provider.get_access_token(
                    profile=profile,
                    subject=subject,
                    scope_profile=scope_profile,
                )
            except ContentSafeError:
                raise
            except Exception:
                raise ContentSafeError(
                    code="UNEXPECTED_LOCAL",
                    operation=ContentErrorOperation.AUTH_BROKER,
                ) from None

        adapter = _build_http_adapter(
            client=client,
            require_context=kernel.require_context,
            token_provider=provide_token,
            continuation_manager=DocsContinuationManager(),
            public_file_ref_provider=_build_public_file_ref_provider(),
            retry_policy=_build_retry_policy(),
            sleeper=_build_sleeper(),
        )
        return _assemble_content_runtime(
            _RuntimeServices(
                registry=registry,
                resolve_subject=resolve_subject,
                authorize=authorize,
                normalize_operation=normalize_operation,
                adapter=adapter,
            )
        )
    except Exception:
        client.close()
        raise
