"""Closed, typed scope registry for Content Research.

Only officially verified read-only profiles are represented here.  A caller
cannot provide an arbitrary runtime scope list to this registry.
"""

from __future__ import annotations

from enum import Enum
from types import MappingProxyType

from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError


class ApprovedScopeProfile(str, Enum):
    DRIVE_DISCOVERY = "drive_discovery"
    DRIVE_METADATA = "drive_metadata"
    DOCS_CONTENT = "docs_content"
    SHEETS_CONTENT = "sheets_content"
    SLIDES_CONTENT = "slides_content"
    GMAIL_METADATA = "gmail_metadata"
    GMAIL_CONTENT = "gmail_content"


_SCOPE_REGISTRY = MappingProxyType(
    {
        ApprovedScopeProfile.DRIVE_DISCOVERY: (
            "https://www.googleapis.com/auth/drive.readonly",
        ),
        ApprovedScopeProfile.DRIVE_METADATA: (
            "https://www.googleapis.com/auth/drive.metadata.readonly",
        ),
        ApprovedScopeProfile.DOCS_CONTENT: (
            "https://www.googleapis.com/auth/documents.readonly",
        ),
        ApprovedScopeProfile.SHEETS_CONTENT: (
            "https://www.googleapis.com/auth/spreadsheets.readonly",
        ),
        ApprovedScopeProfile.SLIDES_CONTENT: (
            "https://www.googleapis.com/auth/presentations.readonly",
        ),
        ApprovedScopeProfile.GMAIL_METADATA: (
            "https://www.googleapis.com/auth/gmail.metadata",
        ),
        ApprovedScopeProfile.GMAIL_CONTENT: (
            "https://www.googleapis.com/auth/gmail.readonly",
        ),
    }
)


def scopes_for(profile: ApprovedScopeProfile) -> tuple[str, ...]:
    """Return the immutable scope tuple for an approved profile."""

    if not isinstance(profile, ApprovedScopeProfile):
        raise ContentSafeError(
            code="LOCAL_VALIDATION",
            operation=ContentErrorOperation.SCOPE_REGISTRY,
        )

    return _SCOPE_REGISTRY[profile]


def all_approved_scopes() -> frozenset[str]:
    """Return the complete closed set for negative security assertions."""

    return frozenset(
        scope
        for scopes in _SCOPE_REGISTRY.values()
        for scope in scopes
    )
