"""Tests for the HTTP request signing utility."""

from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pytest
from nacl.signing import SigningKey, VerifyKey

from prx.api.signing import has_signing_key, sign_request


@pytest.fixture
def tmp_keypair(tmp_path: Path):
    """Generate a temporary keypair and return (signing_key, verify_key, key_dir)."""
    sk = SigningKey.generate()
    vk = sk.verify_key
    key_dir = tmp_path / "keys"
    key_dir.mkdir()
    (key_dir / "prx_signing.key").write_bytes(sk.encode())
    (key_dir / "prx_signing.pub").write_bytes(vk.encode())
    return sk, vk, key_dir


class TestSignRequest:
    def test_returns_required_headers(self, tmp_keypair):
        sk, vk, _key_dir = tmp_keypair
        headers = sign_request("POST", "https://prxhub.com/api/bundles/upload", b'{"test": true}', signing_key=sk)

        assert "X-PRX-Key-Id" in headers
        assert "X-PRX-Timestamp" in headers
        assert "X-PRX-Signature" in headers

    def test_key_id_matches_public_key(self, tmp_keypair):
        sk, vk, _key_dir = tmp_keypair
        headers = sign_request("GET", "https://prxhub.com/api/test", signing_key=sk)

        expected_key_id = "prx_pub_" + vk.encode().hex()[:16]
        assert headers["X-PRX-Key-Id"] == expected_key_id

    def test_signature_is_valid(self, tmp_keypair):
        sk, vk, _key_dir = tmp_keypair
        body = b'{"hello":"world"}'
        url = "https://prxhub.com/api/bundles/upload"
        headers = sign_request("POST", url, body, signing_key=sk)

        timestamp = headers["X-PRX-Timestamp"]
        body_sha256 = hashlib.sha256(body).hexdigest()
        canonical = f"POST\n/api/bundles/upload\n{timestamp}\n{body_sha256}"

        sig_bytes = base64.urlsafe_b64decode(headers["X-PRX-Signature"] + "==")
        vk.verify(canonical.encode("utf-8"), sig_bytes)

    def test_empty_body_signing(self, tmp_keypair):
        sk, vk, _key_dir = tmp_keypair
        headers = sign_request("GET", "https://prxhub.com/api/test", b"", signing_key=sk)

        timestamp = headers["X-PRX-Timestamp"]
        body_sha256 = hashlib.sha256(b"").hexdigest()
        canonical = f"GET\n/api/test\n{timestamp}\n{body_sha256}"

        sig_bytes = base64.urlsafe_b64decode(headers["X-PRX-Signature"] + "==")
        vk.verify(canonical.encode("utf-8"), sig_bytes)

    def test_string_body_treated_as_utf8(self, tmp_keypair):
        sk, vk, _key_dir = tmp_keypair
        body_str = '{"data":"value"}'
        headers = sign_request("POST", "https://prxhub.com/api/test", body_str, signing_key=sk)

        timestamp = headers["X-PRX-Timestamp"]
        body_sha256 = hashlib.sha256(body_str.encode("utf-8")).hexdigest()
        canonical = f"POST\n/api/test\n{timestamp}\n{body_sha256}"

        sig_bytes = base64.urlsafe_b64decode(headers["X-PRX-Signature"] + "==")
        vk.verify(canonical.encode("utf-8"), sig_bytes)

    def test_timestamp_is_recent_utc(self, tmp_keypair):
        sk, _vk, _key_dir = tmp_keypair
        headers = sign_request("GET", "https://prxhub.com/api/test", signing_key=sk)

        ts = datetime.fromisoformat(headers["X-PRX-Timestamp"])
        now = datetime.now(timezone.utc)
        assert abs((now - ts).total_seconds()) < 5


class TestHasSigningKey:
    def test_returns_false_when_no_key(self, tmp_path, monkeypatch):
        monkeypatch.setattr("prx.api.signing.DEFAULT_KEY_DIR", tmp_path / "nonexistent")
        assert has_signing_key() is False

    def test_returns_true_when_key_exists(self, tmp_keypair, monkeypatch):
        _sk, _vk, key_dir = tmp_keypair
        monkeypatch.setattr("prx.api.signing.DEFAULT_KEY_DIR", key_dir)
        assert has_signing_key() is True
