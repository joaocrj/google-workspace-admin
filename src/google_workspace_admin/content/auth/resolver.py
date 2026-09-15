"""Subject lookup and authority issuance inside the sealed Content runtime."""

from __future__ import annotations

from typing import Protocol

from google_workspace_admin.content.auth.subject import WorkspaceSubject


class SubjectLookup(Protocol):
    def __call__(self, user_key: str) -> WorkspaceSubject | None: ...
