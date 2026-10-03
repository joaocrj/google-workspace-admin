import base64
import hashlib
import hmac
import re

import pytest

from google_workspace_admin.content.errors import ContentSafeError
from google_workspace_admin.content.public_file_ref import (
    PUBLIC_FILE_REF_PREFIX,
    PublicFileRefProvider,
    decode_public_file_ref_hmac_key,
    is_public_file_ref,
)


def _provider(customer_id: str = "customer-123") -> PublicFileRefProvider:
    return PublicFileRefProvider(customer_id, bytes(range(32)))


def test_public_file_ref_is_deterministic_canonical_and_customer_bound():
    provider = _provider()
    first = provider("drive-File-ID-123")

    assert first == provider("drive-File-ID-123")
    assert re.fullmatch(r"gdrv_v1_[A-Za-z0-9_-]{43}", first)
    assert "=" not in first
    assert is_public_file_ref(first)
    assert "drive-File-ID-123" not in first
    assert "customer-123" not in first
    assert first != provider("drive-file-id-123")
    assert first != _provider("customer-456")("drive-File-ID-123")
    assert first != _provider("Customer-123")("drive-File-ID-123")
    assert not is_public_file_ref(PUBLIC_FILE_REF_PREFIX + "A" * 42 + "B")
    assert not is_public_file_ref(first + "=")


def test_provider_requires_a_concrete_customer_id():
    with pytest.raises(ContentSafeError):
        PublicFileRefProvider("my_customer", bytes(range(32)))


def test_public_file_ref_matches_domain_separated_hmac_sha256_contract():
    customer_id = "customer-123"
    file_id = "drive-File-ID-123"
    key = bytes(range(32))
    message = (
        b"google-workspace-admin\x00public-file-ref\x00gdrv_v1\x00"
        + len(customer_id.encode()).to_bytes(4, "big")
        + customer_id.encode()
        + len(file_id.encode()).to_bytes(4, "big")
        + file_id.encode()
    )
    expected = PUBLIC_FILE_REF_PREFIX + base64.urlsafe_b64encode(
        hmac.new(key, message, hashlib.sha256).digest()
    ).rstrip(b"=").decode("ascii")

    assert _provider()(file_id) == expected


@pytest.mark.parametrize(
    "file_id",
    ["", "gdrv_v1_" + "A" * 43, "a/b", "a\\b", "a?b", "a#b", "a b", "a\n", "x" * 257, "bad\ud800"],
)
def test_provider_rejects_invalid_or_pseudonymous_input_without_normalizing(file_id):
    with pytest.raises(ContentSafeError) as error:
        _provider()(file_id)

    assert error.value.code == "LOCAL_VALIDATION"
    assert not file_id or file_id not in str(error.value)


def test_provider_representation_does_not_disclose_customer_or_key():
    key = bytes(range(32))
    provider = PublicFileRefProvider("private-customer", key)

    assert repr(provider) == "<PublicFileRefProvider sealed>"
    assert "private-customer" not in repr(provider)
    assert base64.b64encode(key).decode("ascii") not in repr(provider)


def test_configured_hmac_key_requires_canonical_standard_base64_and_32_bytes():
    key = bytes(range(32))
    encoded = base64.b64encode(key).decode("ascii")

    assert decode_public_file_ref_hmac_key(encoded) == key
    for malformed in (encoded.rstrip("="), "!" + encoded[1:], base64.b64encode(b"short").decode("ascii")):
        with pytest.raises(ContentSafeError) as error:
            decode_public_file_ref_hmac_key(malformed)
        assert error.value.code == "LOCAL_VALIDATION"
        assert malformed not in str(error.value)
