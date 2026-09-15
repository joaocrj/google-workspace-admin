"""Strict bounded retrieval and context-limit primitives."""

from __future__ import annotations

from dataclasses import dataclass

from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError


GLOBAL_CONTENT_CEILING = 500
GLOBAL_API_PAGE_SIZE_CEILING = 1000
ABSOLUTE_CONTEXT_BYTES = 10_000_000
ABSOLUTE_CONTEXT_CHARACTERS = 2_000_000
ABSOLUTE_CONTEXT_CHUNKS = 500


def validate_positive_int(
    value: object,
    *,
    name: ContentErrorOperation,
    maximum: int | None = None,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=name)
    if maximum is not None and value > maximum:
        raise ContentSafeError(code="CONTEXT_LIMIT_EXCEEDED", operation=name)
    return value


def validate_optional_page_token(
    value: object, *, name: ContentErrorOperation
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ContentSafeError(code="LOCAL_VALIDATION", operation=name)
    return value.strip()


@dataclass(frozen=True, slots=True)
class PaginationBounds:
    """Application bounds separate from documented API page-size maxima."""

    api_max_page_size: int
    content_hard_cap: int
    default_page_size: int
    max_items_per_invocation: int

    def __post_init__(self) -> None:
        for value, is_api_max in (
            (self.api_max_page_size, True),
            (self.content_hard_cap, False),
            (self.default_page_size, False),
            (self.max_items_per_invocation, False),
        ):
            validate_positive_int(
                value,
                name=ContentErrorOperation.PAGINATION,
                maximum=(
                    GLOBAL_API_PAGE_SIZE_CEILING
                    if is_api_max
                    else GLOBAL_CONTENT_CEILING
                ),
            )
        if self.content_hard_cap > self.api_max_page_size:
            raise ContentSafeError(
                code="CONTEXT_LIMIT_EXCEEDED",
                operation=ContentErrorOperation.PAGINATION,
            )
        if self.default_page_size > self.content_hard_cap:
            raise ContentSafeError(
                code="CONTEXT_LIMIT_EXCEEDED",
                operation=ContentErrorOperation.PAGINATION,
            )
        if self.max_items_per_invocation > self.content_hard_cap:
            raise ContentSafeError(
                code="CONTEXT_LIMIT_EXCEEDED",
                operation=ContentErrorOperation.PAGINATION,
            )

    def validate_page_size(
        self, value: object, *, name: ContentErrorOperation
    ) -> int:
        if type(self) is not PaginationBounds:
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.PAGINATION,
            )
        return validate_positive_int(
            value,
            name=name,
            maximum=self.content_hard_cap,
        )

    def validate_max_items(
        self, value: object, *, name: ContentErrorOperation
    ) -> int:
        if type(self) is not PaginationBounds:
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.PAGINATION,
            )
        return validate_positive_int(
            value,
            name=name,
            maximum=self.max_items_per_invocation,
        )


DEFAULT_PAGINATION_BOUNDS = PaginationBounds(
    api_max_page_size=GLOBAL_CONTENT_CEILING,
    content_hard_cap=GLOBAL_CONTENT_CEILING,
    default_page_size=100,
    max_items_per_invocation=GLOBAL_CONTENT_CEILING,
)


@dataclass(frozen=True, slots=True)
class PaginationRequest:
    page_size: int
    page_token: str | None = None
    max_items: int | None = None
    bounds: PaginationBounds = DEFAULT_PAGINATION_BOUNDS

    def __post_init__(self) -> None:
        if type(self.bounds) is not PaginationBounds:
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.PAGINATION,
            )
        self.bounds.validate_page_size(
            self.page_size,
            name=ContentErrorOperation.PAGINATION,
        )
        if self.max_items is not None:
            self.bounds.validate_max_items(
                self.max_items,
                name=ContentErrorOperation.PAGINATION,
            )
        token = validate_optional_page_token(
            self.page_token,
            name=ContentErrorOperation.PAGINATION,
        )
        object.__setattr__(self, "page_token", token)

    @property
    def effective_page_size(self) -> int:
        """Apply the explicit item bound to the requested API page size."""

        if type(self.bounds) is not PaginationBounds:
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.PAGINATION,
            )
        for value, maximum in (
            (self.bounds.api_max_page_size, GLOBAL_API_PAGE_SIZE_CEILING),
            (self.bounds.content_hard_cap, GLOBAL_CONTENT_CEILING),
            (self.bounds.default_page_size, GLOBAL_CONTENT_CEILING),
            (self.bounds.max_items_per_invocation, GLOBAL_CONTENT_CEILING),
        ):
            validate_positive_int(
                value,
                name=ContentErrorOperation.PAGINATION,
                maximum=maximum,
            )
        if self.bounds.content_hard_cap > self.bounds.api_max_page_size:
            raise ContentSafeError(
                code="CONTEXT_LIMIT_EXCEEDED",
                operation=ContentErrorOperation.PAGINATION,
            )
        item_limit = self.max_items or self.bounds.max_items_per_invocation
        effective = min(
            self.page_size,
            item_limit,
            self.bounds.content_hard_cap,
            self.bounds.api_max_page_size,
        )
        return validate_positive_int(
            effective,
            name=ContentErrorOperation.PAGINATION,
            maximum=GLOBAL_CONTENT_CEILING,
        )


@dataclass(frozen=True, slots=True)
class PaginationState:
    next_page_token: str | None
    truncated: bool

    def __post_init__(self) -> None:
        token = validate_optional_page_token(
            self.next_page_token,
            name=ContentErrorOperation.PAGINATION,
        )
        if not isinstance(self.truncated, bool):
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.PAGINATION,
            )
        object.__setattr__(self, "next_page_token", token)


@dataclass(frozen=True, slots=True)
class ContextLimits:
    max_bytes: int
    max_characters: int
    max_chunks: int

    def __post_init__(self) -> None:
        validate_positive_int(
            self.max_bytes,
            name=ContentErrorOperation.CONTEXT_LIMIT,
            maximum=ABSOLUTE_CONTEXT_BYTES,
        )
        validate_positive_int(
            self.max_characters,
            name=ContentErrorOperation.CONTEXT_LIMIT,
            maximum=ABSOLUTE_CONTEXT_CHARACTERS,
        )
        validate_positive_int(
            self.max_chunks,
            name=ContentErrorOperation.CONTEXT_LIMIT,
            maximum=ABSOLUTE_CONTEXT_CHUNKS,
        )


@dataclass(frozen=True, slots=True)
class ContentLimitPolicy:
    """Separates configured safe defaults from operation hard caps."""

    safe_defaults: ContextLimits
    hard_caps: ContextLimits

    def __post_init__(self) -> None:
        if not isinstance(self.safe_defaults, ContextLimits) or not isinstance(
            self.hard_caps,
            ContextLimits,
        ):
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.CONTEXT_LIMIT,
            )
        for safe, hard in (
            (self.safe_defaults.max_bytes, self.hard_caps.max_bytes),
            (
                self.safe_defaults.max_characters,
                self.hard_caps.max_characters,
            ),
            (self.safe_defaults.max_chunks, self.hard_caps.max_chunks),
        ):
            if safe > hard:
                raise ContentSafeError(
                    code="CONTEXT_LIMIT_EXCEEDED",
                    operation=ContentErrorOperation.CONTEXT_LIMIT,
                )

    def resolve(self, requested: ContextLimits | None = None) -> ContextLimits:
        if type(self) is not ContentLimitPolicy:
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.CONTEXT_LIMIT,
            )
        if type(self.safe_defaults) is not ContextLimits or type(self.hard_caps) is not ContextLimits:
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.CONTEXT_LIMIT,
            )
        resolved = requested or self.safe_defaults
        if type(resolved) is not ContextLimits:
            raise ContentSafeError(
                code="LOCAL_VALIDATION",
                operation=ContentErrorOperation.CONTEXT_LIMIT,
            )
        for value, maximum in (
            (resolved.max_bytes, ABSOLUTE_CONTEXT_BYTES),
            (resolved.max_characters, ABSOLUTE_CONTEXT_CHARACTERS),
            (resolved.max_chunks, ABSOLUTE_CONTEXT_CHUNKS),
        ):
            validate_positive_int(
                value,
                name=ContentErrorOperation.CONTEXT_LIMIT,
                maximum=maximum,
            )
        if (
            resolved.max_bytes > self.hard_caps.max_bytes
            or resolved.max_characters > self.hard_caps.max_characters
            or resolved.max_chunks > self.hard_caps.max_chunks
        ):
            raise ContentSafeError(
                code="CONTEXT_LIMIT_EXCEEDED",
                operation=ContentErrorOperation.CONTEXT_LIMIT,
            )
        return resolved
