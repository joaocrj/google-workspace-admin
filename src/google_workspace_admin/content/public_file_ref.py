"""Customer-bound pseudonyms for public Drive-backed content references."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import re

from google_workspace_admin.content.errors import ContentErrorOperation, ContentSafeError


PUBLIC_FILE_REF_PREFIX = "gdrv_v1_"
_PUBLIC_FILE_REF_PATTERN = re.compile(
    r"^gdrv_v1_[A-Za-z0-9_-]{42}[AEIMQUYcgkosw048]$"
)
_CUSTOMER_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_PUBLIC_FILE_REF_DOMAIN = b"google-workspace-admin\x00public-file-ref\x00gdrv_v1\x00"
_MAX_DRIVE_FILE_ID_LENGTH = 256


def _invalid(operation: ContentErrorOperation) -> ContentSafeError:
    return ContentSafeError(code="LOCAL_VALIDATION", operation=operation)


def decode_public_file_ref_hmac_key(value: object) -> bytes:
    """Parse canonical standard Base64 for one 256-bit key without echoing it."""

    if type(value) is not str or not value:
        raise _invalid(ContentErrorOperation.BOOTSTRAP)
    try:
        key = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        raise _invalid(ContentErrorOperation.BOOTSTRAP) from None
    if len(key) != 32 or base64.b64encode(key).decode("ascii") != value:
        raise _invalid(ContentErrorOperation.BOOTSTRAP)
    return key


def is_public_file_ref(value: object) -> bool:
    """Return whether a value is the canonical unpadded SHA-256 base64url form."""

    return type(value) is str and _PUBLIC_FILE_REF_PATTERN.fullmatch(value) is not None


class PublicFileRefProvider:
    """Compute stable, tenant-bound public references without retaining file IDs."""

    __slots__ = ("_customer_id", "_key")

    def __init__(self, customer_id: str, key: bytes) -> None:
        if (
            type(customer_id) is not str
            or not _CUSTOMER_ID_PATTERN.fullmatch(customer_id)
            or customer_id.casefold() == "my_customer"
            or type(key) is not bytes
            or len(key) != 32
        ):
            raise _invalid(ContentErrorOperation.BOOTSTRAP)
        self._customer_id = customer_id
        self._key = key

    def __call__(self, drive_file_id: str) -> str:
        if (
            type(drive_file_id) is not str
            or not drive_file_id
            or len(drive_file_id) > _MAX_DRIVE_FILE_ID_LENGTH
            or drive_file_id.startswith(PUBLIC_FILE_REF_PREFIX)
            or any(
                character.isspace()
                or ord(character) < 32
                or 0x7F <= ord(character) <= 0x9F
                for character in drive_file_id
            )
            or any(character in drive_file_id for character in ("/", "\\", "?", "#"))
        ):
            raise _invalid(ContentErrorOperation.OPERATION_NORMALIZATION)
        try:
            customer_bytes = self._customer_id.encode("utf-8", "strict")
            file_id_bytes = drive_file_id.encode("utf-8", "strict")
        except UnicodeError:
            raise _invalid(ContentErrorOperation.OPERATION_NORMALIZATION) from None

        message = (
            _PUBLIC_FILE_REF_DOMAIN
            + len(customer_bytes).to_bytes(4, "big")
            + customer_bytes
            + len(file_id_bytes).to_bytes(4, "big")
            + file_id_bytes
        )
        digest = hmac.new(self._key, message, hashlib.sha256).digest()
        encoded = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        return f"{PUBLIC_FILE_REF_PREFIX}{encoded}"

    def __repr__(self) -> str:
        return "<PublicFileRefProvider sealed>"
