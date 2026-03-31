"""Tests for CLI commands — export, validate, read, verify."""

from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import MagicMock, patch

from prx.cli.export import _export_json, _export_markdown

# ---------------------------------------------------------------------------
# Helpers: lightweight fakes for prx_spec objects
# ---------------------------------------------------------------------------


@dataclass
class FakeManifest:
    id: str = "prx_test0001"
    query: str = "What is quantum computing?"
    spec_version: str = "1.0"
    created_at: str = "2025-01-01T00:00:00Z"
    providers_used: list[str] = field(default_factory=lambda: ["fast", "slow"])
    has_synthesis: bool = True
    has_claims: bool = False
    has_sources: bool = False
    has_evidence_graph: bool = False
    total_cost_usd: float | None = 0.05
    total_duration_seconds: float | None = 2.5
    producer: MagicMock = field(default_factory=lambda: MagicMock(name="test", version="0.1"))

    def model_dump(self, mode="python"):
        return {
            "id": self.id,
            "query": self.query,
            "spec_version": self.spec_version,
            "created_at": self.created_at,
            "providers_used": self.providers_used,
            "has_synthesis": self.has_synthesis,
            "total_cost_usd": self.total_cost_usd,
        }


@dataclass
class FakeProvider:
    name: str = "fast"
    report_md: str = "# Fast Report\n\nSome content."
    citations: list | None = None
    meta: dict | None = None


@dataclass
class FakeBundle:
    manifest: FakeManifest = field(default_factory=FakeManifest)
    query_md: str = "What is quantum computing?"
    synthesis_md: str | None = "# Synthesis\n\nCombined report."
    providers: list[FakeProvider] = field(
        default_factory=lambda: [FakeProvider(name="fast"), FakeProvider(name="slow")]
    )
    claims: object | None = None
    attestations: dict | None = None


# ---------------------------------------------------------------------------
# export helper tests
# ---------------------------------------------------------------------------


class TestExportMarkdown:
    def test_includes_query_heading(self):
        bundle = FakeBundle()
        md = _export_markdown(bundle)
        assert "What is quantum computing?" in md

    def test_includes_synthesis(self):
        bundle = FakeBundle()
        md = _export_markdown(bundle)
        assert "Synthesis" in md
        assert "Combined report." in md

    def test_includes_provider_sections(self):
        bundle = FakeBundle()
        md = _export_markdown(bundle)
        assert "## fast" in md
        assert "## slow" in md

    def test_no_synthesis_when_absent(self):
        bundle = FakeBundle(synthesis_md=None)
        md = _export_markdown(bundle)
        assert "Synthesis" not in md


class TestExportJson:
    def test_returns_valid_json(self):
        import json

        bundle = FakeBundle()
        result = _export_json(bundle)
        data = json.loads(result)
        assert "manifest" in data
        assert data["manifest"]["id"] == "prx_test0001"

    def test_includes_providers(self):
        import json

        bundle = FakeBundle()
        data = json.loads(_export_json(bundle))
        assert "fast" in data["providers"]
        assert "slow" in data["providers"]

    def test_includes_synthesis_when_present(self):
        import json

        bundle = FakeBundle()
        data = json.loads(_export_json(bundle))
        assert "synthesis" in data

    def test_no_synthesis_key_when_absent(self):
        import json

        bundle = FakeBundle(synthesis_md=None)
        data = json.loads(_export_json(bundle))
        assert "synthesis" not in data


# ---------------------------------------------------------------------------
# CLI export_cmd via Typer CliRunner
# ---------------------------------------------------------------------------


class TestExportCmd:
    def _run_export(self, args: list[str]):
        from typer.testing import CliRunner

        from prx.cli import prx_app

        runner = CliRunner()
        return runner.invoke(prx_app, ["export", *args])

    def test_export_missing_file_exits(self):
        result = self._run_export(["/nonexistent/bundle.prx"])
        assert result.exit_code != 0

    @patch("prx_spec.read_bundle")
    def test_export_markdown_to_stdout(self, mock_read, tmp_path):
        # Create a real dummy file for the exists check
        dummy = tmp_path / "test.prx"
        dummy.write_bytes(b"dummy")
        mock_read.return_value = FakeBundle()
        result = self._run_export([str(dummy), "--format", "markdown"])
        assert result.exit_code == 0
        assert "quantum computing" in result.output.lower()

    @patch("prx_spec.read_bundle")
    def test_export_json_to_stdout(self, mock_read, tmp_path):
        dummy = tmp_path / "test.prx"
        dummy.write_bytes(b"dummy")
        mock_read.return_value = FakeBundle()
        result = self._run_export([str(dummy), "--format", "json"])
        assert result.exit_code == 0
        assert "prx_test0001" in result.output

    @patch("prx_spec.read_bundle")
    def test_export_to_file(self, mock_read, tmp_path):
        dummy = tmp_path / "test.prx"
        dummy.write_bytes(b"dummy")
        out_file = tmp_path / "output.md"
        mock_read.return_value = FakeBundle()
        result = self._run_export([str(dummy), "-f", "markdown", "-o", str(out_file)])
        assert result.exit_code == 0
        assert out_file.exists()
        assert "quantum computing" in out_file.read_text().lower()

    @patch("prx_spec.read_bundle")
    def test_export_unknown_format(self, mock_read, tmp_path):
        dummy = tmp_path / "test.prx"
        dummy.write_bytes(b"dummy")
        mock_read.return_value = FakeBundle()
        result = self._run_export([str(dummy), "--format", "csv"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# CLI validate_cmd via Typer CliRunner
# ---------------------------------------------------------------------------


class TestValidateCmd:
    def _run_validate(self, args: list[str]):
        from typer.testing import CliRunner

        from prx.cli import prx_app

        runner = CliRunner()
        return runner.invoke(prx_app, ["validate", *args])

    def test_missing_file_exits(self):
        result = self._run_validate(["/nonexistent/bundle.prx"])
        assert result.exit_code != 0

    @patch("prx_spec.validate_archive")
    def test_valid_bundle(self, mock_validate, tmp_path):
        dummy = tmp_path / "test.prx"
        dummy.write_bytes(b"dummy")

        # Create a ValidationResult-like mock with dict levels
        level_result = MagicMock()
        level_result.passed = True
        level_result.errors = []
        level_result.warnings = []
        mock_result = MagicMock()
        mock_result.levels = {"l0": level_result, "l1": level_result}
        mock_result.highest_passing_level = 1
        mock_validate.return_value = mock_result

        result = self._run_validate([str(dummy)])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# CLI read_cmd via Typer CliRunner
# ---------------------------------------------------------------------------


class TestReadCmd:
    def _run_read(self, args: list[str]):
        from typer.testing import CliRunner

        from prx.cli import prx_app

        runner = CliRunner()
        return runner.invoke(prx_app, ["read", *args])

    def test_missing_file_exits(self):
        result = self._run_read(["/nonexistent/bundle.prx"])
        assert result.exit_code != 0

    @patch("prx_spec.read_bundle")
    def test_read_default(self, mock_read, tmp_path):
        dummy = tmp_path / "test.prx"
        dummy.write_bytes(b"dummy")
        mock_read.return_value = FakeBundle()
        result = self._run_read([str(dummy)])
        assert result.exit_code == 0

    @patch("prx_spec.read_bundle")
    def test_read_meta_flag(self, mock_read, tmp_path):
        dummy = tmp_path / "test.prx"
        dummy.write_bytes(b"dummy")
        mock_read.return_value = FakeBundle()
        result = self._run_read([str(dummy), "--meta"])
        assert result.exit_code == 0

    @patch("prx_spec.read_bundle")
    def test_read_claims_flag(self, mock_read, tmp_path):
        dummy = tmp_path / "test.prx"
        dummy.write_bytes(b"dummy")

        # Mimic ClaimsFile with a .claims list of Pydantic-like objects
        class FakeClaim:
            content = "Quantum is fast"
            providers_supporting = ["fast"]
            providers_contradicting = []

        class FakeClaimsFile:
            claims = [FakeClaim()]

        bundle = FakeBundle(claims=FakeClaimsFile())
        mock_read.return_value = bundle
        result = self._run_read([str(dummy), "--claims"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# CLI verify_cmd via Typer CliRunner
# ---------------------------------------------------------------------------


class TestVerifyCmd:
    def _run_verify(self, args: list[str]):
        from typer.testing import CliRunner

        from prx.cli import prx_app

        runner = CliRunner()
        return runner.invoke(prx_app, ["verify", *args])

    def test_verify_missing_file_exits(self):
        result = self._run_verify(["/nonexistent/bundle.prx"])
        assert result.exit_code != 0

    @patch("prx_spec.read_bundle")
    def test_verify_no_attestations(self, mock_read, tmp_path):
        dummy = tmp_path / "test.prx"
        dummy.write_bytes(b"dummy")
        bundle = FakeBundle(attestations=None)
        mock_read.return_value = bundle
        result = self._run_verify([str(dummy)])
        assert result.exit_code == 0

    @patch("prx_spec.read_bundle")
    def test_verify_no_attestations_strict(self, mock_read, tmp_path):
        dummy = tmp_path / "test.prx"
        dummy.write_bytes(b"dummy")
        bundle = FakeBundle(attestations=None)
        mock_read.return_value = bundle
        result = self._run_verify([str(dummy), "--strict"])
        assert result.exit_code != 0

    @patch("prx_spec.read_bundle")
    def test_verify_with_attestations(self, mock_read, tmp_path):
        dummy = tmp_path / "test.prx"
        dummy.write_bytes(b"dummy")
        bundle = FakeBundle(attestations={"sig_1": {"type": "ed25519", "signer": "test"}})
        mock_read.return_value = bundle
        result = self._run_verify([str(dummy)])
        assert result.exit_code == 0
