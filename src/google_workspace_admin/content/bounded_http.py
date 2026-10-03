"""Incremental response-body bounds shared by native Google readers."""

from __future__ import annotations

from dataclasses import dataclass
import zlib

import httpx


_RAW_STREAM_CHUNK_BYTES = 64 * 1024
_SUPPORTED_CONTENT_ENCODINGS = frozenset({"identity", "gzip", "deflate"})


@dataclass(frozen=True, slots=True)
class BoundedBodyFailure:
    """Closed, content-free outcome from a bounded streaming read."""

    kind: str

    def __post_init__(self) -> None:
        if type(self) is not BoundedBodyFailure or self.kind not in {
            "response_malformed",
            "unsupported_encoding",
            "too_large",
        }:
            raise ValueError("invalid bounded body failure")


def read_bounded_response_body(
    response: httpx.Response,
    *,
    raw_cap: int,
    decoded_cap: int,
) -> bytes | BoundedBodyFailure:
    """Read encoded bytes incrementally and cap decoded bytes before JSON parse."""

    if (
        type(response) is not httpx.Response
        or type(raw_cap) is not int
        or type(decoded_cap) is not int
        or raw_cap < 1
        or decoded_cap < 1
    ):
        return BoundedBodyFailure("response_malformed")

    content_length = response.headers.get("content-length")
    if content_length is not None:
        if not content_length.isascii() or not content_length.isdigit():
            return BoundedBodyFailure("response_malformed")
        if int(content_length) > raw_cap:
            return BoundedBodyFailure("too_large")

    raw_encoding = response.headers.get("content-encoding")
    encoding = "identity" if raw_encoding is None else raw_encoding.strip().lower()
    if encoding not in _SUPPORTED_CONTENT_ENCODINGS:
        return BoundedBodyFailure("unsupported_encoding")

    if encoding == "gzip":
        decoder: zlib.Decompress | None = zlib.decompressobj(16 + zlib.MAX_WBITS)
    elif encoding == "deflate":
        decoder = zlib.decompressobj(zlib.MAX_WBITS)
    else:
        decoder = None

    raw_count = 0
    decoded = bytearray()
    try:
        for raw_chunk in response.iter_raw(chunk_size=_RAW_STREAM_CHUNK_BYTES):
            raw_count += len(raw_chunk)
            if raw_count > raw_cap:
                return BoundedBodyFailure("too_large")

            remaining = decoded_cap + 1 - len(decoded)
            if remaining <= 0:
                return BoundedBodyFailure("too_large")
            if decoder is None:
                decoded.extend(raw_chunk[:remaining])
            else:
                decoded.extend(decoder.decompress(raw_chunk, remaining))
            if len(decoded) > decoded_cap:
                return BoundedBodyFailure("too_large")
            if decoder is not None and decoder.unconsumed_tail:
                return BoundedBodyFailure("too_large")
    except (httpx.StreamError, zlib.error):
        return BoundedBodyFailure("response_malformed")

    if decoder is not None and (
        not decoder.eof or decoder.unconsumed_tail or decoder.unused_data
    ):
        return BoundedBodyFailure("response_malformed")
    return bytes(decoded)
