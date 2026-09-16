"""Immutable coverage ledger enforcing one terminal outcome per file."""

from __future__ import annotations

from dataclasses import dataclass

from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError
from google_workspace_admin.content.inventory import MAX_FILE_ID_LENGTH
from google_workspace_admin.content.outcomes import ProcessingOutcome


MAX_COVERAGE_RECORDS = 100_000


def _file_id(value: object) -> str:
    if type(value) is not str or not value or len(value) > MAX_FILE_ID_LENGTH:
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_OUTCOME)
    if any(
        character.isspace()
        or ord(character) < 32
        or 0x7F <= ord(character) <= 0x9F
        or character in "/\\?#"
        for character in value
    ):
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_OUTCOME)
    return value


@dataclass(frozen=True, slots=True)
class CoverageRecord:
    file_id: str
    outcome: ProcessingOutcome

    def __post_init__(self) -> None:
        if type(self) is not CoverageRecord:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_OUTCOME)
        _file_id(self.file_id)
        if type(self.outcome) is not ProcessingOutcome or not self.outcome.is_terminal:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_OUTCOME)


@dataclass(frozen=True, slots=True)
class CoverageLedger:
    """A bounded immutable set of exactly-one terminal outcome records."""

    records: tuple[CoverageRecord, ...] = ()

    def __post_init__(self) -> None:
        if type(self) is not CoverageLedger:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_OUTCOME)
        if type(self.records) not in (tuple, list) or len(self.records) > MAX_COVERAGE_RECORDS:
            raise ContentSafeError(code="CONTEXT_LIMIT_EXCEEDED", operation=ContentErrorOperation.READING_OUTCOME)
        records = tuple(self.records)
        if any(type(record) is not CoverageRecord for record in records):
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_OUTCOME)
        ids = tuple(record.file_id for record in records)
        if len(set(ids)) != len(ids):
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_OUTCOME)
        object.__setattr__(self, "records", records)

    def record(self, file_id: object, outcome: ProcessingOutcome) -> "CoverageLedger":
        file_id_value = _file_id(file_id)
        if type(outcome) is not ProcessingOutcome:
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_OUTCOME)
        if any(record.file_id == file_id_value for record in self.records):
            raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_OUTCOME)
        if len(self.records) >= MAX_COVERAGE_RECORDS:
            raise ContentSafeError(code="CONTEXT_LIMIT_EXCEEDED", operation=ContentErrorOperation.READING_OUTCOME)
        return CoverageLedger(self.records + (CoverageRecord(file_id_value, outcome),))

    @property
    def total_inventoried(self) -> int:
        return len(self.records)

    @property
    def analyzed(self) -> int:
        return sum(record.outcome.is_success or record.outcome.is_partial for record in self.records)

    @property
    def failures(self) -> int:
        return sum(record.outcome.is_failure for record in self.records)


def validate_coverage_complete(
    inventory_file_ids: object,
    ledger: CoverageLedger,
) -> None:
    """Fail closed unless every inventoried ID has exactly one outcome."""

    if type(ledger) is not CoverageLedger or type(inventory_file_ids) not in (tuple, list):
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_OUTCOME)
    if len(inventory_file_ids) > MAX_COVERAGE_RECORDS:
        raise ContentSafeError(code="CONTEXT_LIMIT_EXCEEDED", operation=ContentErrorOperation.READING_OUTCOME)
    expected = tuple(_file_id(value) for value in inventory_file_ids)
    if len(set(expected)) != len(expected) or set(expected) != {record.file_id for record in ledger.records}:
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=ContentErrorOperation.READING_OUTCOME)
