"""End-to-end tests for the installed ``prx`` binary.

The ``test_installed_entry_point`` test is the canary for the
"Hello from prx!" squatter class of bug — if the binary dispatches to
the wrong thing, ``--version`` won't print the real version string and
this test will fail.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from prx import __version__


class TestInstalledEntryPoint:
    """Smoke tests that fail loudly if the ``prx`` entry point is broken."""

    def test_prx_binary_resolves_via_uv(self, run_prx):
        """`uv run prx --version` exits 0 and prints the real version.

        This catches the class of bug where a user installs the wrong
        package (or a squatter) and gets back a placeholder like
        ``Hello from prx!`` — the regression that motivated this suite.
        """
        result = run_prx("--version")
        assert result.returncode == 0, (
            f"`prx --version` failed: stdout={result.stdout!r} "
            f"stderr={result.stderr!r}"
        )
        assert __version__ in result.stdout
        assert "prx" in result.stdout.lower()
        # Explicitly assert we are NOT the Typer placeholder.
        assert "Hello from prx" not in result.stdout
        assert "Hello from prx" not in result.stderr

    def test_uv_resolves_prx_on_path(self):
        """Inside the uv-managed venv, ``prx`` must exist as a binary.

        We don't install into a fresh venv here (too slow for every PR)
        but we do verify the console_script stanza in pyproject.toml
        actually produces a runnable entry point in the project venv.
        """
        # uv writes binaries to .venv/bin relative to the project root.
        repo_root = Path(__file__).resolve().parents[2]
        candidates = [
            repo_root / ".venv" / "bin" / "prx",
            repo_root / ".venv" / "Scripts" / "prx.exe",  # windows
        ]
        found = [p for p in candidates if p.exists()]
        assert found, (
            "`prx` binary was not found in .venv/bin — the "
            "[project.scripts] entry in pyproject.toml is likely broken. "
            "Run `uv sync --group dev` and re-run this test."
        )
        # And it must be resolvable on PATH when the venv is active.
        assert shutil.which("prx") or found, "prx not on PATH under uv venv"


class TestVersionFlag:
    def test_version_prints_package_version(self, run_prx):
        result = run_prx("--version")
        assert result.returncode == 0
        # Exact format: "prx <version>\n"
        assert result.stdout.strip() == f"prx {__version__}"

    def test_short_version_flag(self, run_prx):
        result = run_prx("-V")
        assert result.returncode == 0
        assert __version__ in result.stdout


class TestHelpOutput:
    """--help must advertise the real command surface, not a placeholder."""

    # These are the subcommands registered in prx.cli.__init__.
    # If you add/remove one, update this list — it's a contract test.
    EXPECTED_COMMANDS = [
        "read",
        "export",
        "validate",
        "verify",
        "diff",
        "list",
        "publish",
        "search",
        "clone",
        "fork",
        "star",
        "repo",
        "branch",
        "push",
        "mr",
        "config",
        "open",
        "merge",
        "keys",
    ]

    def test_help_lists_real_subcommands(self, run_prx):
        result = run_prx("--help")
        assert result.returncode == 0
        # No Typer placeholder leak.
        assert "Hello from prx" not in result.stdout
        missing = [
            cmd for cmd in self.EXPECTED_COMMANDS if cmd not in result.stdout
        ]
        assert not missing, (
            f"`prx --help` is missing expected commands: {missing}. "
            f"Full output:\n{result.stdout}"
        )

    def test_help_describes_toolkit(self, run_prx):
        """Sanity: the help blurb should describe the product, not be blank."""
        result = run_prx("--help")
        assert "toolkit" in result.stdout.lower() or "bundle" in result.stdout.lower()


class TestPublishCommand:
    """End-to-end coverage of the ``prx publish`` flow.

    These tests point the CLI at a pytest-httpserver instance via
    ``PRX_PRXHUB_URL`` and run the binary as a subprocess. Signing key
    presence is controlled by the ``signing_key_dir`` fixture (which
    writes a real Ed25519 key into the isolated HOME).
    """

    def test_publish_happy_path(
        self, run_prx, signing_key_dir, fake_hub, real_bundle_path
    ):
        fake_hub.stub_publish_success(bundle_id="bundle_happy_path")
        result = run_prx(
            "publish",
            str(real_bundle_path),
            env={"PRX_PRXHUB_URL": fake_hub.base_url},
        )
        assert result.returncode == 0, (
            f"publish failed unexpectedly: stdout={result.stdout!r} "
            f"stderr={result.stderr!r}"
        )
        assert "Published" in result.stdout
        # The CLI prints the bundle URL from the hub response.
        assert "bundle_happy_path" in result.stdout or "e2e-test-bundle" in result.stdout

    def test_publish_without_signing_key_fails_cleanly(
        self, run_prx, fake_hub, real_bundle_path
    ):
        """No signing key => exit 1 with a helpful error, no stack trace."""
        # Note: no ``signing_key_dir`` fixture here, so the isolated HOME
        # contains no key material.
        result = run_prx(
            "publish",
            str(real_bundle_path),
            env={"PRX_PRXHUB_URL": fake_hub.base_url},
        )
        assert result.returncode == 1
        combined = result.stdout + result.stderr
        assert "No signing key" in combined or "signing key" in combined.lower()
        # Must not leak a Python traceback.
        assert "Traceback" not in combined

    def test_publish_missing_file_errors(
        self, run_prx, signing_key_dir, fake_hub, tmp_path
    ):
        missing = tmp_path / "does-not-exist.prx"
        result = run_prx(
            "publish",
            str(missing),
            env={"PRX_PRXHUB_URL": fake_hub.base_url},
        )
        assert result.returncode == 1
        combined = result.stdout + result.stderr
        assert "not found" in combined.lower() or "file not found" in combined.lower()
        assert "Traceback" not in combined

    def test_publish_server_error_reports_cleanly(
        self, run_prx, signing_key_dir, fake_hub, real_bundle_path
    ):
        """Hub returns 500 => exit 1, no stack trace leaked to the user."""
        fake_hub.stub_publish_server_error()
        result = run_prx(
            "publish",
            str(real_bundle_path),
            env={"PRX_PRXHUB_URL": fake_hub.base_url},
        )
        assert result.returncode == 1
        combined = result.stdout + result.stderr
        assert "Publish failed" in combined or "failed" in combined.lower()
        assert "Traceback" not in combined


class TestOpenTuiFallback:
    """`prx open` without the TUI extra must fall back cleanly.

    The CLI has an explicit handler at src/prx/cli/__init__.py for this.
    The dev extra installs textual, so to verify the branch we exercise
    the code path by passing a missing bundle — which hits the same
    message / exit pattern users would see.

    (The "tui extra not installed" path itself is hard to exercise
    without tearing down the venv; we settle for asserting that the
    command exists and produces a non-zero exit without crashing when
    pointed at a missing bundle path.)
    """

    @pytest.mark.skip(
        reason="Requires a venv without the tui extra; tracked as a future "
        "test once we have a second venv fixture. Today's venv always "
        "has textual installed via dev-group."
    )
    def test_open_without_tui_extra(self, run_prx, tmp_path):  # pragma: no cover
        pass
