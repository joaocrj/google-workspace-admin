"""Internal reader protocol; no concrete readers are implemented here."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from google_workspace_admin.content.budgets import ContentReadingBudgets
from google_workspace_admin.content.chunks import ContentChunk
from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError
from google_workspace_admin.content.inventory import InventorySnapshot
from google_workspace_admin.content.outcomes import ProcessingOutcome
from google_workspace_admin.content.routing import ContentClass


def validate_reader_continuation(value: object) -> str | None:
    if value is None:
        return None
    if type(value) is not str or not value or len(value) > 4096 or any(
        character.isspace() or ord(character) < 32 or 0x7F <= ord(character) <= 0x9F
        for character in value
    ):
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_READER)
    return value


@dataclass(frozen=True, slots=True)
class BoundedReadResult:
    chunks: tuple[ContentChunk, ...]
    outcome: ProcessingOutcome

    def __post_init__(self) -> None:
        if type(self.chunks) not in (tuple, list) or any(type(chunk) is not ContentChunk for chunk in self.chunks):
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_READER)
        chunks = tuple(self.chunks)
        if type(self.outcome) is not ProcessingOutcome:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_READER)
        if self.outcome.chunk_count != len(chunks):
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_READER)
        if any(chunk.content_class is not self.outcome.content_class for chunk in chunks):
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_READER)
        if self.outcome.is_success and any(chunk.truncated or chunk.continuation is not None for chunk in chunks):
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_READER)
        if self.outcome.is_partial and (
            not chunks or not chunks[-1].truncated or chunks[-1].continuation != self.outcome.continuation
        ):
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_READER)
        if self.outcome.continuation is not None and (
            not chunks or chunks[-1].continuation != self.outcome.continuation
        ):
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_READER)
        object.__setattr__(self, "chunks", chunks)


@runtime_checkable
class ContentReader(Protocol):
    """Closed interface for a specialized future reader."""

    @property
    def content_class(self) -> ContentClass:
        ...

    def read(
        self,
        snapshot: InventorySnapshot,
        budgets: ContentReadingBudgets,
        continuation: str | None = None,
    ) -> BoundedReadResult:
        ...
