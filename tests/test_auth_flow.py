"""Tests for the device-code login flow, token storage, and key registration."""

from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from typer.testing import CliRunner

from prx import auth
from prx.auth import (
    AuthError,
    StoredToken,
    clear_token,
    load_token,
    poll_for_token,
    save_token,
    start_device_flow,
)
from prx.cli import prx_app

runner = CliRunner()


@pytest.fixture
def tmp_auth(tmp_path, monkeypatch):
    """Redirect auth.json to a tmp path for all tests."""
    auth_file = tmp_path / "auth.json"
    monkeypatch.setattr(auth, "auth_path", lambda: auth_file)
    yield auth_file


# ---------------------------------------------------------------------------
# Token store
# ---------------------------------------------------------------------------


class TestTokenStore:
    def test_save_and_load_roundtrip(self, tmp_auth):
        tok = StoredToken(
            access_token="abc",
            token_type="Bearer",
            expires_at=time.time() + 60,
            scope="read write",
            api_url="https://prxhub.com",
            username="alice",
        )
        save_token(tok)
        loaded = load_token()
        assert loaded is not None
        assert loaded.access_token == "abc"
        assert loaded.username == "alice"

    def test_load_token_missing_returns_none(self, tmp_auth):
        assert load_token() is None

    def test_load_corrupt_file_returns_none(self, tmp_auth):
        tmp_auth.parent.mkdir(parents=True, exist_ok=True)
        tmp_auth.write_text("not json")
        assert load_token() is None

    def test_clear_token(self, tmp_auth):
        save_token(
            StoredToken(
                access_token="x",
                token_type="Bearer",
                expires_at=time.time() + 60,
                scope="",
                api_url="https://prxhub.com",
            )
        )
        assert clear_token() is True
        assert load_token() is None
        # second clear: no token to remove
        assert clear_token() is False

    def test_is_expired(self):
        past = StoredToken("t", "Bearer", time.time() - 10, "", "https://x")
        future = StoredToken("t", "Bearer", time.time() + 3600, "", "https://x")
        assert past.is_expired() is True
        assert future.is_expired() is False


# ---------------------------------------------------------------------------
# Device-code flow (unit tests around poll_for_token)
# ---------------------------------------------------------------------------


def _mock_response(status: int, body: dict) -> MagicMock:
    r = MagicMock(spec=httpx.Response)
    r.status_code = status
    r.json.return_value = body
    r.text = json.dumps(body)
    return r


class TestStartDeviceFlow:
    def test_start_returns_payload(self):
        http = MagicMock()
        http.post.return_value = _mock_response(
            200,
            {
                "device_code": "dev",
                "user_code": "ABCD-1234",
                "verification_uri_complete": "https://prxhub.com/cli/device?code=ABCD-1234",
                "interval": 5,
            },
        )
        result = start_device_flow("https://prxhub.com", http)
        assert result["device_code"] == "dev"
        assert result["user_code"] == "ABCD-1234"


class TestPollForToken:
    def test_happy_path(self):
        http = MagicMock()
        pending = _mock_response(400, {"error": "authorization_pending"})
        success = _mock_response(
            200,
            {
                "access_token": "tok-xyz",
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "read write",
                "username": "alice",
            },
        )
        http.post.side_effect = [pending, success]
        sleeps: list[int] = []
        result = poll_for_token(
            "https://prxhub.com", "dev", 1, http, sleep=sleeps.append
        )
        assert result["access_token"] == "tok-xyz"
        # slept twice (once before each poll)
        assert sleeps == [1, 1]

    def test_slow_down_increments_interval(self):
        http = MagicMock()
        http.post.side_effect = [
            _mock_response(400, {"error": "slow_down"}),
            _mock_response(
                200,
                {
                    "access_token": "tok",
                    "token_type": "Bearer",
                    "expires_in": 60,
                    "scope": "",
                },
            ),
        ]
        sleeps: list[int] = []
        poll_for_token(
            "https://prxhub.com", "dev", 5, http, sleep=sleeps.append
        )
        # first sleep uses initial interval, second uses +5
        assert sleeps == [5, 10]

    def test_access_denied_raises(self):
        http = MagicMock()
        http.post.return_value = _mock_response(400, {"error": "access_denied"})
        with pytest.raises(AuthError, match="denied"):
            poll_for_token(
                "https://prxhub.com", "dev", 1, http, sleep=lambda _s: None
            )

    def test_expired_raises(self):
        http = MagicMock()
        http.post.return_value = _mock_response(400, {"error": "expired_token"})
        with pytest.raises(AuthError, match="expired"):
            poll_for_token(
                "https://prxhub.com", "dev", 1, http, sleep=lambda _s: None
            )

    def test_timeout_raises(self):
        http = MagicMock()
        http.post.return_value = _mock_response(400, {"error": "authorization_pending"})
        # Deadline will be reached immediately because now starts past it.
        times = iter([0.0, 100.0, 200.0, 300.0])

        def fake_now():
            return next(times)

        with pytest.raises(AuthError, match="Timed out"):
            poll_for_token(
                "https://prxhub.com",
                "dev",
                1,
                http,
                max_seconds=10,
                sleep=lambda _s: None,
                now=fake_now,
            )


# ---------------------------------------------------------------------------
# `prx login` CLI
# ---------------------------------------------------------------------------


class TestLoginCmd:
    @patch("prx.cli.login.open_browser", return_value=True)
    @patch("prx.cli.login.poll_for_token")
    @patch("prx.cli.login.start_device_flow")
    def test_login_happy_path(
        self, mock_start, mock_poll, mock_open, tmp_auth
    ):
        mock_start.return_value = {
            "device_code": "dev",
            "user_code": "ABCD-1234",
            "verification_uri_complete": "https://prxhub.com/cli/device?code=ABCD-1234",
            "interval": 5,
        }
        mock_poll.return_value = {
            "access_token": "tok",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "read write",
            "username": "alice",
        }
        result = runner.invoke(prx_app, ["login"])
        assert result.exit_code == 0, result.output
        assert "Authenticated as alice" in result.output
        mock_open.assert_called_once()
        assert load_token() is not None

    @patch("prx.cli.login.open_browser", return_value=True)
    @patch("prx.cli.login.poll_for_token")
    @patch("prx.cli.login.start_device_flow")
    def test_login_denied(self, mock_start, mock_poll, mock_open, tmp_auth):
        mock_start.return_value = {
            "device_code": "dev",
            "user_code": "X",
            "verification_uri_complete": "https://prxhub.com/cli/device?code=X",
            "interval": 1,
        }
        mock_poll.side_effect = AuthError("Authorization denied.")
        result = runner.invoke(prx_app, ["login"])
        assert result.exit_code == 1
        assert "denied" in result.output.lower()
        assert load_token() is None


class TestLogoutCmd:
    def test_logout_when_logged_in(self, tmp_auth):
        save_token(
            StoredToken("t", "Bearer", time.time() + 60, "", "https://prxhub.com")
        )
        result = runner.invoke(prx_app, ["logout"])
        assert result.exit_code == 0
        assert "Logged out" in result.output
        assert load_token() is None

    def test_logout_when_not_logged_in(self, tmp_auth):
        result = runner.invoke(prx_app, ["logout"])
        assert result.exit_code == 0
        assert "Not logged in" in result.output


# ---------------------------------------------------------------------------
# API client bearer-header injection + auth errors
# ---------------------------------------------------------------------------


class TestApiAuth:
    def test_auth_headers_uses_stored_token(self, tmp_auth):
        from prx.api import _auth_headers

        save_token(
            StoredToken("stored-tok", "Bearer", time.time() + 60, "", "https://x")
        )
        headers = _auth_headers(None)
        assert headers == {"Authorization": "Bearer stored-tok"}

    def test_auth_headers_explicit_token_wins(self, tmp_auth):
        from prx.api import _auth_headers

        save_token(
            StoredToken("stored-tok", "Bearer", time.time() + 60, "", "https://x")
        )
        headers = _auth_headers("override")
        assert headers == {"Authorization": "Bearer override"}

    def test_auth_headers_missing_token_raises(self, tmp_auth):
        from prx.api import AuthRequired, _auth_headers

        with pytest.raises(AuthRequired, match="Not logged in"):
            _auth_headers(None)

    def test_auth_headers_expired_token_raises(self, tmp_auth):
        from prx.api import AuthRequired, _auth_headers

        save_token(
            StoredToken("old", "Bearer", time.time() - 10, "", "https://x")
        )
        with pytest.raises(AuthRequired, match="expired"):
            _auth_headers(None)

    def test_auth_headers_optional_returns_empty_when_missing(self, tmp_auth):
        from prx.api import _auth_headers

        assert _auth_headers(None, required=False) == {}


# ---------------------------------------------------------------------------
# `prx keys register` CLI
# ---------------------------------------------------------------------------


class TestKeysRegisterCmd:
    def test_requires_login(self, tmp_auth):
        result = runner.invoke(prx_app, ["keys", "register"])
        assert result.exit_code == 1
        assert "Run `prx login`" in result.output

    def test_errors_when_no_public_key(self, tmp_auth, tmp_path, monkeypatch):
        save_token(
            StoredToken("tok", "Bearer", time.time() + 60, "", "https://prxhub.com")
        )
        # Point key_dir at an empty tmp dir
        monkeypatch.setattr("prx.cli.keys._key_dir", lambda: tmp_path / "empty")
        result = runner.invoke(prx_app, ["keys", "register"])
        assert result.exit_code == 1
        assert "No public key" in result.output

    @patch("prx.api.register_public_key", new_callable=AsyncMock)
    def test_happy_path(self, mock_register, tmp_auth, tmp_path, monkeypatch):
        from prx.api import KeyRegistration

        save_token(
            StoredToken(
                "tok",
                "Bearer",
                time.time() + 60,
                "",
                "https://prxhub.com",
                username="alice",
            )
        )
        key_dir = tmp_path / "keys"
        key_dir.mkdir()
        # 32 bytes of fake pubkey
        (key_dir / "prx_signing.pub").write_bytes(b"\x01" * 32)
        monkeypatch.setattr("prx.cli.keys._key_dir", lambda: key_dir)

        mock_register.return_value = KeyRegistration(
            key_id="prx_pub_0101010101010101",
            url="https://prxhub.com/settings/keys",
        )
        result = runner.invoke(prx_app, ["keys", "register"])
        assert result.exit_code == 0, result.output
        assert "Key registered" in result.output
        mock_register.assert_called_once()
        kwargs = mock_register.call_args.kwargs
        assert kwargs["key_id"].startswith("prx_pub_")
        assert kwargs["public_key_jwk"]["kty"] == "OKP"
        assert kwargs["public_key_jwk"]["crv"] == "Ed25519"


# ---------------------------------------------------------------------------
# `prx publish` CLI — token plumbing
# ---------------------------------------------------------------------------


class TestPublishCmd:
    def test_requires_login(self, tmp_auth, tmp_path):
        bundle = tmp_path / "b.prx"
        bundle.write_bytes(b"PK\x03\x04dummy")
        result = runner.invoke(prx_app, ["publish", str(bundle)])
        assert result.exit_code == 1
        assert "Run `prx login`" in result.output

    def test_rejects_non_zip(self, tmp_auth, tmp_path):
        bundle = tmp_path / "b.prx"
        bundle.write_bytes(b"not-zip")
        save_token(
            StoredToken("tok", "Bearer", time.time() + 60, "", "https://prxhub.com")
        )
        result = runner.invoke(prx_app, ["publish", str(bundle)])
        assert result.exit_code == 1
        assert "valid" in result.output.lower()

    @patch("prx.api.publish_bundle", new_callable=AsyncMock)
    def test_happy_path_attaches_bearer(self, mock_publish, tmp_auth, tmp_path):
        from prx.api import PublishResult

        bundle = tmp_path / "b.prx"
        bundle.write_bytes(b"PK\x03\x04dummy")
        save_token(
            StoredToken("tok", "Bearer", time.time() + 60, "", "https://prxhub.com")
        )
        mock_publish.return_value = PublishResult(
            bundle_url="https://prxhub.com/alice/bundle-123",
            bundle_id="bundle-123",
        )
        result = runner.invoke(prx_app, ["publish", str(bundle)])
        assert result.exit_code == 0, result.output
        assert "prxhub.com/alice/bundle-123" in result.output
        mock_publish.assert_called_once()
