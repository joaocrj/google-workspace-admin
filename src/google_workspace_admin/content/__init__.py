"""Sealed, read-only local foundation for future Workspace Content tools.

No MCP tool or Google authentication is registered here.  Operational access
is limited to a startup-assembled :class:`ContentRuntime` and closed requests.
"""

from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError
from google_workspace_admin.content.operations import (
    DriveFilesListRequest,
    DriveGetRequest,
    DriveListRequest,
)
from google_workspace_admin.content.results import (
    DriveFileListPage,
    DriveFileSummary,
    DriveGetResult,
    DriveListPage,
    DriveSummary,
)
from google_workspace_admin.content.runtime import ContentRuntime

__all__ = [
    "ContentErrorOperation",
    "ContentRuntime",
    "DriveFileListPage",
    "DriveFileSummary",
    "DriveFilesListRequest",
    "DriveGetRequest",
    "DriveGetResult",
    "DriveListPage",
    "DriveListRequest",
    "DriveSummary",
    "ContentSafeError",
]
