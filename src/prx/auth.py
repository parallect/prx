"""Device-code OAuth flow + token storage for prxhub.

Tokens are stored at the platform-standard prx config dir (e.g.
``~/.config/prx/auth.json`` on Linux, ``~/Library/Application Support/prx/auth.json``
on macOS) with file mode 0600.

The server contract is documented in ``CLI-AUTH-CONTRACT.md`` at the prxhub
repo root. Endpoints used here:

- ``POST /api/auth/cli/start`` -> ``{device_code, user_code, verification_uri,
  verification_uri_complete, expires_in, interval}``
- ``POST /api/auth/cli/poll`` with ``{device_code}`` -> 400
  ``{error: "authorization_pending" | "slow_down" | "access_denied" |
  "expired_token"}`` or 200
  ``{access_token, token_type, expires_in, scope, username?}``
"""

from __future__ import annotations

import json
import os
import platform
import stat
import time
import webbrowser
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx
import platformdirs

DEFAULT_API_URL = "https://prxhub.com"
DEFAULT_POLL_INTERVAL = 5  # seconds
MAX_POLL_SECONDS = 10 * 60  # 10 minutes


def auth_path() -> Path:
    """Path to the prx CLI auth token file."""
    return Path(platformdirs.user_config_dir("prx")) / "auth.json"


@dataclass
class StoredToken:
    access_token: str
    token_type: str
    expires_at: float  # unix timestamp
    scope: str
    api_url: str
    username: str | None = None

    def is_expired(self, leeway: int = 30) -> bool:
        return time.time() + leeway >= self.expires_at


class AuthError(Exception):
    """Raised for auth flow failures the user should see."""


def save_token(token: StoredToken) -> Path:
    """Write the token to disk with 0600 permissions."""
    path = auth_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(token), indent=2))
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        # Windows / unusual FS — best effort
        pass
    return path


def load_token() -> StoredToken | None:
    """Read the token from disk, or None if not logged in."""
    path = auth_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return StoredToken(**data)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def clear_token() -> bool:
    """Delete the stored token. Returns True if a token was removed."""
    path = auth_path()
    if path.exists():
        path.unlink()
        return True
    return False


def client_name(prx_version: str | None = None) -> str:
    version = prx_version or _prx_version()
    return f"prx CLI v{version} ({platform.platform()})"


def _prx_version() -> str:
    try:
        from importlib.metadata import version

        return version("prx")
    except Exception:
        return "0.0.0"


def start_device_flow(api_url: str, http: httpx.Client) -> dict:
    """Call POST /api/auth/cli/start and return the raw payload."""
    response = http.post(
        f"{api_url}/api/auth/cli/start",
        json={"client_name": client_name()},
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()


def poll_for_token(
    api_url: str,
    device_code: str,
    interval: int,
    http: httpx.Client,
    max_seconds: int = MAX_POLL_SECONDS,
    sleep: "callable" = time.sleep,
    now: "callable" = time.time,
) -> dict:
    """Poll POST /api/auth/cli/poll until success, denial, or timeout.

    Returns the 200 success body. Raises AuthError on denial/expiry/timeout.
    """
    deadline = now() + max_seconds
    current_interval = max(int(interval), 1)

    while now() < deadline:
        sleep(current_interval)
        response = http.post(
            f"{api_url}/api/auth/cli/poll",
            json={"device_code": device_code},
            timeout=30.0,
        )
        if response.status_code == 200:
            return response.json()

        body: dict = {}
        try:
            body = response.json()
        except Exception:
            pass

        err = body.get("error") if isinstance(body, dict) else None
        if err == "authorization_pending":
            continue
        if err == "slow_down":
            current_interval += 5
            continue
        if err == "access_denied":
            raise AuthError("Authorization denied. You can run `prx login` again to retry.")
        if err == "expired_token":
            raise AuthError(
                "The device code expired before you approved it. Run `prx login` again."
            )
        # Unknown non-200
        raise AuthError(
            f"Login failed ({response.status_code}): {body or response.text or 'no body'}"
        )

    raise AuthError("Timed out waiting for approval. Run `prx login` again.")


def open_browser(url: str) -> bool:
    """Open ``url`` in the user's browser. Returns True on success."""
    try:
        return webbrowser.open(url)
    except Exception:
        return False
