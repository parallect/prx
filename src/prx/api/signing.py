"""HTTP request signing for prxhub API authentication.

Signs requests using the local Ed25519 private key so that prxhub
can verify the caller's identity via the registered public key.
"""

from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse

from nacl.signing import SigningKey

from prx_spec.attestation.keys import (
    DEFAULT_KEY_DIR,
    get_key_id,
    load_private_key,
)


def sign_request(
    method: str,
    url: str,
    body: bytes | str = b"",
    *,
    signing_key: SigningKey | None = None,
) -> dict[str, str]:
    """Produce authentication headers for a prxhub API request.

    Returns a dict with X-PRX-Key-Id, X-PRX-Timestamp, X-PRX-Signature.
    """
    if signing_key is None:
        signing_key = load_private_key(DEFAULT_KEY_DIR)

    verify_key = signing_key.verify_key
    key_id = get_key_id(verify_key)

    timestamp = datetime.now(timezone.utc).isoformat()

    if isinstance(body, str):
        body = body.encode("utf-8")

    body_sha256 = hashlib.sha256(body).hexdigest()
    pathname = urlparse(url).path

    canonical = f"{method.upper()}\n{pathname}\n{timestamp}\n{body_sha256}"
    signed = signing_key.sign(canonical.encode("utf-8"))
    signature = base64.urlsafe_b64encode(signed.signature).decode("ascii")

    return {
        "X-PRX-Key-Id": key_id,
        "X-PRX-Timestamp": timestamp,
        "X-PRX-Signature": signature,
    }


def has_signing_key() -> bool:
    """Check whether a signing key exists on disk."""
    return (DEFAULT_KEY_DIR / "prx_signing.key").exists()
