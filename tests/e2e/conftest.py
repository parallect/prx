"""Shared fixtures for the prx CLI end-to-end suite.

Every test in this directory invokes the ``prx`` binary as a subprocess.
We deliberately avoid importing the Typer app in-process for assertions —
the whole point of this suite is to exercise the real install-and-run
path that a user hits when they ``pip install prx-cli`` and run ``prx``.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

# The test suite relies on ``uv run prx`` resolving to the binary installed
# from this workspace's pyproject.toml. ``uv run`` re-uses the project's
# locked virtualenv, so the package under test is always the one on disk.
REPO_ROOT = Path(__file__).resolve().parents[2]
PRX_CMD: list[str] = ["uv", "run", "prx"]
DEFAULT_TIMEOUT = 30  # seconds — generous for cold uv runs in CI


# ---------------------------------------------------------------------------
# Isolated HOME so the subprocess never touches the developer's real keys
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_home(tmp_path: Path) -> Path:
    """Return a throwaway HOME directory for the subprocess.

    ``prx_spec.attestation.keys.DEFAULT_KEY_DIR`` is computed from
    ``Path.home()`` at import time, so swapping HOME in the child
    environment reroutes all key lookups to this temp dir.
    """
    home = tmp_path / "home"
    home.mkdir()
    (home / ".config").mkdir()
    return home


@pytest.fixture
def signing_key_dir(isolated_home: Path) -> Path:
    """Generate a real Ed25519 signing key inside the isolated HOME.

    Uses the prx_spec helper rather than shelling out so the fixture is
    cheap. The returned path is where the CLI will look for keys when
    HOME is set to ``isolated_home``.
    """
    from prx_spec.attestation.keys import generate_keypair

    key_dir = isolated_home / ".config" / "parallect" / "keys"
    generate_keypair(key_dir=key_dir)
    return key_dir


# ---------------------------------------------------------------------------
# Subprocess runner
# ---------------------------------------------------------------------------


@pytest.fixture
def run_prx(isolated_home: Path):
    """Factory fixture that runs ``prx`` as a subprocess with a clean env.

    Always sets HOME to the isolated temp dir so key lookups are sandboxed.
    Extra env vars can be passed per-call; they're merged into the
    parent environment so uv / python / PATH still resolve correctly.
    """

    def _run(
        *args: str,
        env: dict[str, str] | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        cwd: str | os.PathLike[str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        child_env = os.environ.copy()
        child_env["HOME"] = str(isolated_home)
        # Force plain output so we can assert on strings deterministically.
        child_env.setdefault("NO_COLOR", "1")
        child_env.setdefault("TERM", "dumb")
        if env:
            child_env.update(env)
        return subprocess.run(
            [*PRX_CMD, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd) if cwd else str(REPO_ROOT),
            env=child_env,
        )

    return _run


# ---------------------------------------------------------------------------
# Fake prxhub — uses pytest-httpserver so tests are fully hermetic
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_hub(httpserver) -> Iterator[object]:
    """Wrap pytest-httpserver with helpers for the prxhub publish flow.

    The real CLI performs three sequential requests when publishing:

    1. ``POST /api/bundles/upload`` — returns a presigned ``upload_url``.
    2. ``PUT  <upload_url>``        — uploads the raw bytes.
    3. ``POST /api/bundles/confirm`` — finalises and returns the bundle URL.

    Tests opt into whichever stage they want to exercise.
    """

    class Hub:
        def __init__(self, server):
            self.server = server
            self.base_url = server.url_for("")
            self.storage_path = "/storage/fake-object"

        def stub_publish_success(
            self,
            *,
            bundle_id: str = "bundle_e2e_0001",
            slug: str = "e2e-test-bundle",
        ) -> None:
            """Happy path: all three steps return 2xx."""
            upload_url = self.server.url_for(self.storage_path)

            self.server.expect_request(
                "/api/bundles/upload", method="POST"
            ).respond_with_json(
                {
                    "upload_id": "upload_e2e_1",
                    "storage_key": "s3://fake-bucket/fake-key",
                    "upload_url": upload_url,
                }
            )
            self.server.expect_request(
                self.storage_path, method="PUT"
            ).respond_with_data("", status=200)
            self.server.expect_request(
                "/api/bundles/confirm", method="POST"
            ).respond_with_json(
                {
                    "bundle_id": bundle_id,
                    "id": bundle_id,
                    "slug": slug,
                    "bundle_url": f"/{slug}",
                }
            )

        def stub_publish_server_error(self) -> None:
            """Simulate prxhub returning a 500 at step 1 (init upload)."""
            self.server.expect_request(
                "/api/bundles/upload", method="POST"
            ).respond_with_data("internal error", status=500)

    yield Hub(httpserver)


# ---------------------------------------------------------------------------
# Real .prx bundle fixture — built on the fly so we're not depending on
# the committed stub ``test-research.prx`` (which is just a placeholder).
# ---------------------------------------------------------------------------


@pytest.fixture
def real_bundle_path(tmp_path: Path) -> Path:
    """Build a minimal but valid .prx bundle using prx-spec's writer.

    We go through the real writer so the publish flow (which only reads
    the file size / bytes off disk) receives a genuinely well-formed
    archive. That keeps the test honest if the publish path starts
    validating the bundle before upload.
    """
    from datetime import datetime, timezone

    from prx_spec import BundleData, ProviderData, write_bundle
    from prx_spec.models.manifest import Manifest, Producer

    manifest = Manifest(
        id="prx_e2e00001",
        query="end-to-end test query",
        created_at=datetime.now(timezone.utc),
        producer=Producer(name="prx-e2e-tests", version="0.0.0"),
        providers_used=["stub"],
        has_synthesis=False,
        has_claims=False,
        has_sources=False,
        has_evidence_graph=False,
        has_follow_ons=False,
    )
    bundle = BundleData(
        manifest=manifest,
        query_md="# end-to-end test query\n",
        providers=[ProviderData(name="stub", report_md="# stub\n\nhello\n")],
    )
    out = tmp_path / "e2e.prx"
    write_bundle(bundle, out)
    return out
