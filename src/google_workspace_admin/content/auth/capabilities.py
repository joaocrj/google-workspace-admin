"""Closed Content operation and subject capability matrix."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from google_workspace_admin.content.auth.scopes import ApprovedScopeProfile
from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError


class SubjectCapability(str, Enum):
    DRIVE = "drive"
    GMAIL = "gmail"


class ContentCapability(str, Enum):
    DRIVE_DISCOVERY = "drive_discovery"
    DRIVE_METADATA = "drive_metadata"
    GMAIL_METADATA = "gmail_metadata"
    GMAIL_CONTENT = "gmail_content"
    GOOGLE_DOCS_CONTENT = "google_docs_content"


class AdminCapability(str, Enum):
    NONE = "none"
    SHARED_DRIVE_DISCOVERY = "shared_drive_discovery"


@dataclass(frozen=True, slots=True)
class OperationCapabilityRule:
    operation: str
    capability: ContentCapability
    scope_profile: ApprovedScopeProfile
    subject_capability: SubjectCapability
    admin_capability: AdminCapability


_RULES = MappingProxyType(
    {
        "drive.list": OperationCapabilityRule(
            operation="drive.list",
            capability=ContentCapability.DRIVE_DISCOVERY,
            scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
            subject_capability=SubjectCapability.DRIVE,
            admin_capability=AdminCapability.SHARED_DRIVE_DISCOVERY,
        ),
        "drive.get": OperationCapabilityRule(
            operation="drive.get",
            capability=ContentCapability.DRIVE_DISCOVERY,
            scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
            subject_capability=SubjectCapability.DRIVE,
            admin_capability=AdminCapability.SHARED_DRIVE_DISCOVERY,
        ),
        "drive.files.list": OperationCapabilityRule(
            operation="drive.files.list",
            capability=ContentCapability.DRIVE_DISCOVERY,
            scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
            subject_capability=SubjectCapability.DRIVE,
            admin_capability=AdminCapability.NONE,
        ),
        "content.file.read": OperationCapabilityRule(
            operation="content.file.read",
            capability=ContentCapability.GOOGLE_DOCS_CONTENT,
            scope_profile=ApprovedScopeProfile.DRIVE_DISCOVERY,
            subject_capability=SubjectCapability.DRIVE,
            admin_capability=AdminCapability.NONE,
        ),
    }
)


_SCOPE_SUBJECT_CAPABILITIES = MappingProxyType(
    {
        ApprovedScopeProfile.DRIVE_DISCOVERY: SubjectCapability.DRIVE,
        ApprovedScopeProfile.DRIVE_METADATA: SubjectCapability.DRIVE,
        ApprovedScopeProfile.GMAIL_METADATA: SubjectCapability.GMAIL,
        ApprovedScopeProfile.GMAIL_CONTENT: SubjectCapability.GMAIL,
        ApprovedScopeProfile.DOCS_CONTENT: SubjectCapability.DRIVE,
        ApprovedScopeProfile.SHEETS_CONTENT: SubjectCapability.DRIVE,
        ApprovedScopeProfile.SLIDES_CONTENT: SubjectCapability.DRIVE,
    }
)


def capability_rule(operation: object) -> OperationCapabilityRule:
    # Import lazily to keep the operation table free of an import cycle.
    from google_workspace_admin.content.operations import ContentOperation

    if type(operation) is not ContentOperation:
        raise ContentSafeError(
            code="READ_ONLY_OPERATION_FORBIDDEN",
            operation=ContentErrorOperation.CAPABILITY_MATRIX,
        )
    return _RULES[operation.value]


def subject_capability_for_scope(
    scope_profile: object,
) -> SubjectCapability:
    if not isinstance(scope_profile, ApprovedScopeProfile):
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.CAPABILITY_MATRIX,
        )
    return _SCOPE_SUBJECT_CAPABILITIES[scope_profile]
