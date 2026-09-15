"""Application policy checks that sit above Google's delegated subject."""

from __future__ import annotations

from google_workspace_admin.content.auth.capabilities import SubjectCapability
from google_workspace_admin.content.auth.profile import ContentAuthProfile
from google_workspace_admin.content.auth.subject import WorkspaceSubject
from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError


def validate_subject_for_profile(
    subject: WorkspaceSubject,
    profile: ContentAuthProfile,
) -> WorkspaceSubject:
    """Validate a resolved subject against fixed Content policy."""

    if not isinstance(subject, WorkspaceSubject):
        raise ContentSafeError(
            code="TARGET_SUBJECT_INVALID",
            operation=ContentErrorOperation.SUBJECT_VALIDATION,
        )
    if not isinstance(profile, ContentAuthProfile):
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.SUBJECT_VALIDATION,
        )
    if subject.domain != profile.allowed_domain:
        raise ContentSafeError(
            code="MAILBOX_NOT_ALLOWED",
            operation=ContentErrorOperation.SUBJECT_VALIDATION,
        )
    if subject.primary_email.rsplit("@", 1)[1] != profile.allowed_domain:
        raise ContentSafeError(
            code="MAILBOX_NOT_ALLOWED",
            operation=ContentErrorOperation.SUBJECT_VALIDATION,
        )
    if subject.customer_id != profile.customer_id:
        raise ContentSafeError(
            code="TARGET_SUBJECT_INVALID",
            operation=ContentErrorOperation.SUBJECT_VALIDATION,
        )
    if subject.suspended or subject.archived:
        raise ContentSafeError(
            code="TARGET_SUBJECT_INVALID",
            operation=ContentErrorOperation.SUBJECT_VALIDATION,
        )
    return subject


def validate_subject_for_capability(
    subject: WorkspaceSubject,
    profile: ContentAuthProfile,
    capability: SubjectCapability,
) -> WorkspaceSubject:
    """Apply capability-specific checks without conflating Drive and Gmail."""

    validated = validate_subject_for_profile(subject, profile)
    if not isinstance(capability, SubjectCapability):
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.CAPABILITY_MATRIX,
        )
    if capability is SubjectCapability.GMAIL and not validated.mailbox_ready:
        raise ContentSafeError(
            code="MAILBOX_NOT_ALLOWED",
            operation=ContentErrorOperation.SUBJECT_MAILBOX,
        )
    return validated
