"""Integration tests for previously untested CLI commands.

Covers: list, diff, merge, publish, config, keys (generate/list/register/revoke), open.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from prx.cli import prx_app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Shared fakes
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
# list command
# ---------------------------------------------------------------------------


class TestListCmd:
    def test_list_nonexistent_directory(self):
        result = runner.invoke(prx_app, ["list", "--dir", "/nonexistent/path"])
        assert result.exit_code != 0

    @patch("prx_spec.read_bundle")
    def test_list_empty_directory(self, mock_read, tmp_path):
        result = runner.invoke(prx_app, ["list", "--dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "No .prx bundles found" in result.output
        mock_read.assert_not_called()

    @patch("prx_spec.read_bundle")
    def test_list_with_bundles(self, mock_read, tmp_path):
        (tmp_path / "test.prx").write_bytes(b"dummy")
        (tmp_path / "other.prx").write_bytes(b"dummy")
        mock_read.return_value = FakeBundle()

        result = runner.invoke(prx_app, ["list", "--dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "prx_test0001" in result.output
        assert mock_read.call_count == 2

    @patch("prx_spec.read_bundle")
    def test_list_corrupt_bundle_shows_error(self, mock_read, tmp_path):
        (tmp_path / "bad.prx").write_bytes(b"corrupt")
        mock_read.side_effect = ValueError("Invalid bundle format")

        result = runner.invoke(prx_app, ["list", "--dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "Error" in result.output

    @patch("prx_spec.read_bundle")
    def test_list_nested_bundles(self, mock_read, tmp_path):
        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "nested.prx").write_bytes(b"dummy")
        mock_read.return_value = FakeBundle()

        result = runner.invoke(prx_app, ["list", "--dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "prx_test0001" in result.output


# ---------------------------------------------------------------------------
# diff command
# ---------------------------------------------------------------------------


class TestDiffCmd:
    def test_diff_missing_first_file(self):
        result = runner.invoke(prx_app, ["diff", "/nonexistent/a.prx", "/nonexistent/b.prx"])
        assert result.exit_code != 0

    def test_diff_missing_second_file(self, tmp_path):
        a = tmp_path / "a.prx"
        a.write_bytes(b"dummy")
        result = runner.invoke(prx_app, ["diff", str(a), "/nonexistent/b.prx"])
        assert result.exit_code != 0

    @patch("prx_spec.read_bundle")
    def test_diff_comparison_table(self, mock_read, tmp_path):
        a = tmp_path / "a.prx"
        b = tmp_path / "b.prx"
        a.write_bytes(b"dummy")
        b.write_bytes(b"dummy")

        bundle_a = FakeBundle(manifest=FakeManifest(id="prx_aaa"))
        bundle_b = FakeBundle(manifest=FakeManifest(id="prx_bbb"))
        mock_read.side_effect = [bundle_a, bundle_b]

        result = runner.invoke(prx_app, ["diff", str(a), str(b)])
        assert result.exit_code == 0
        assert "prx_aaa" in result.output
        assert "prx_bbb" in result.output

    @patch("prx_spec.read_bundle")
    def test_diff_shows_added_removed_providers(self, mock_read, tmp_path):
        a = tmp_path / "a.prx"
        b = tmp_path / "b.prx"
        a.write_bytes(b"dummy")
        b.write_bytes(b"dummy")

        bundle_a = FakeBundle(providers=[FakeProvider(name="alpha")])
        bundle_b = FakeBundle(providers=[FakeProvider(name="beta")])
        mock_read.side_effect = [bundle_a, bundle_b]

        result = runner.invoke(prx_app, ["diff", str(a), str(b)])
        assert result.exit_code == 0
        assert "beta" in result.output
        assert "alpha" in result.output

    @patch("prx_spec.read_bundle")
    def test_diff_shared_provider_length_change(self, mock_read, tmp_path):
        a = tmp_path / "a.prx"
        b = tmp_path / "b.prx"
        a.write_bytes(b"dummy")
        b.write_bytes(b"dummy")

        bundle_a = FakeBundle(providers=[FakeProvider(name="gpt4", report_md="short")])
        bundle_b = FakeBundle(
            providers=[FakeProvider(name="gpt4", report_md="a much longer report with more text")]
        )
        mock_read.side_effect = [bundle_a, bundle_b]

        result = runner.invoke(prx_app, ["diff", str(a), str(b)])
        assert result.exit_code == 0
        assert "gpt4" in result.output


# ---------------------------------------------------------------------------
# merge command
# ---------------------------------------------------------------------------


@dataclass
class FakeMergeStats:
    total_claims_a: int = 5
    total_claims_b: int = 3
    deduplicated: int = 1
    conflicts_detected: int = 0
    merged_total: int = 7


@dataclass
class FakeMergeConflict:
    conflict_type: str = "contradiction"
    claim_a_content: str = "Claim A says one thing that is quite different from claim B's assertion"


@dataclass
class FakeMergeResult:
    stats: FakeMergeStats = field(default_factory=FakeMergeStats)
    conflicts: list = field(default_factory=list)


class TestMergeCmd:
    def test_merge_missing_first_bundle(self):
        result = runner.invoke(prx_app, ["merge", "/nonexistent/a.prx", "/nonexistent/b.prx"])
        assert result.exit_code != 0

    def test_merge_missing_second_bundle(self, tmp_path):
        a = tmp_path / "a.prx"
        a.write_bytes(b"dummy")
        result = runner.invoke(prx_app, ["merge", str(a), "/nonexistent/b.prx"])
        assert result.exit_code != 0

    @patch("prx_spec.bundle.writer.write_bundle")
    @patch("prx_spec.merge.apply_merge")
    @patch("prx_spec.merge.merge_bundles")
    @patch("prx_spec.bundle.reader.read_bundle")
    def test_merge_success(self, mock_read, mock_merge, mock_apply, mock_write, tmp_path):
        a = tmp_path / "a.prx"
        b = tmp_path / "b.prx"
        a.write_bytes(b"dummy")
        b.write_bytes(b"dummy")

        mock_read.side_effect = [FakeBundle(), FakeBundle()]
        mock_merge.return_value = FakeMergeResult()
        mock_apply.return_value = FakeBundle()

        result = runner.invoke(prx_app, ["merge", str(a), str(b)])
        assert result.exit_code == 0
        assert "Merge Results" in result.output
        mock_write.assert_called_once()

    @patch("prx_spec.bundle.writer.write_bundle")
    @patch("prx_spec.merge.apply_merge")
    @patch("prx_spec.merge.merge_bundles")
    @patch("prx_spec.bundle.reader.read_bundle")
    def test_merge_with_conflicts(self, mock_read, mock_merge, mock_apply, mock_write, tmp_path):
        a = tmp_path / "a.prx"
        b = tmp_path / "b.prx"
        a.write_bytes(b"dummy")
        b.write_bytes(b"dummy")

        mock_read.side_effect = [FakeBundle(), FakeBundle()]
        conflicts = [FakeMergeConflict()]
        mock_merge.return_value = FakeMergeResult(
            stats=FakeMergeStats(conflicts_detected=1),
            conflicts=conflicts,
        )
        mock_apply.return_value = FakeBundle()

        result = runner.invoke(prx_app, ["merge", str(a), str(b)])
        assert result.exit_code == 0
        assert "conflict" in result.output.lower()

    @patch("prx_spec.bundle.writer.write_bundle")
    @patch("prx_spec.merge.apply_merge")
    @patch("prx_spec.merge.merge_bundles")
    @patch("prx_spec.bundle.reader.read_bundle")
    def test_merge_custom_output(self, mock_read, mock_merge, mock_apply, mock_write, tmp_path):
        a = tmp_path / "a.prx"
        b = tmp_path / "b.prx"
        out = tmp_path / "merged.prx"
        a.write_bytes(b"dummy")
        b.write_bytes(b"dummy")

        mock_read.side_effect = [FakeBundle(), FakeBundle()]
        mock_merge.return_value = FakeMergeResult()
        mock_apply.return_value = FakeBundle()

        result = runner.invoke(prx_app, ["merge", str(a), str(b), "-o", str(out)])
        assert result.exit_code == 0
        mock_write.assert_called_once()
        call_args = mock_write.call_args
        assert str(call_args[0][1]) == str(out)

    @patch("prx_spec.bundle.writer.write_bundle")
    @patch("prx_spec.merge.apply_merge")
    @patch("prx_spec.merge.merge_bundles")
    @patch("prx_spec.bundle.reader.read_bundle")
    def test_merge_custom_threshold(self, mock_read, mock_merge, mock_apply, mock_write, tmp_path):
        a = tmp_path / "a.prx"
        b = tmp_path / "b.prx"
        a.write_bytes(b"dummy")
        b.write_bytes(b"dummy")

        mock_read.side_effect = [FakeBundle(), FakeBundle()]
        mock_merge.return_value = FakeMergeResult()
        mock_apply.return_value = FakeBundle()

        result = runner.invoke(prx_app, ["merge", str(a), str(b), "-t", "0.5"])
        assert result.exit_code == 0
        mock_merge.assert_called_once()
        _, kwargs = mock_merge.call_args
        assert kwargs["similarity_threshold"] == 0.5


# ---------------------------------------------------------------------------
# publish command
# ---------------------------------------------------------------------------


@dataclass
class FakePublishResult:
    bundle_url: str = "https://prxhub.com/bundles/test-slug"
    bundle_id: str = "prx_test0001"


class TestPublishCmd:
    def test_publish_missing_file(self):
        result = runner.invoke(prx_app, ["publish", "/nonexistent/bundle.prx"])
        assert result.exit_code != 0

    @patch("prx.api.signing.has_signing_key", return_value=False)
    @patch("prx.config_mod.settings.PrxSettings.load")
    def test_publish_no_signing_key(self, mock_load, mock_has_key, tmp_path):
        dummy = tmp_path / "test.prx"
        dummy.write_bytes(b"dummy")
        mock_load.return_value = MagicMock(default_visibility="public", prxhub_url="")
        result = runner.invoke(prx_app, ["publish", str(dummy)])
        assert result.exit_code != 0
        assert "signing key" in result.output.lower()

    @patch("prx.api.publish_bundle", new_callable=AsyncMock)
    @patch("prx.api.signing.has_signing_key", return_value=True)
    @patch("prx.config_mod.settings.PrxSettings.load")
    def test_publish_success(self, mock_load, mock_has_key, mock_publish, tmp_path):
        dummy = tmp_path / "test.prx"
        dummy.write_bytes(b"dummy")
        mock_load.return_value = MagicMock(default_visibility="public", prxhub_url="")
        mock_publish.return_value = FakePublishResult()

        result = runner.invoke(prx_app, ["publish", str(dummy)])
        assert result.exit_code == 0
        assert "Published" in result.output
        assert "prxhub.com" in result.output

    @patch("prx.api.publish_bundle", new_callable=AsyncMock)
    @patch("prx.api.signing.has_signing_key", return_value=True)
    @patch("prx.config_mod.settings.PrxSettings.load")
    def test_publish_with_tags(self, mock_load, mock_has_key, mock_publish, tmp_path):
        dummy = tmp_path / "test.prx"
        dummy.write_bytes(b"dummy")
        mock_load.return_value = MagicMock(default_visibility="public", prxhub_url="")
        mock_publish.return_value = FakePublishResult()

        result = runner.invoke(prx_app, [
            "publish", str(dummy), "--tags", "quantum,physics",
        ])
        assert result.exit_code == 0
        assert "quantum, physics" in result.output

    @patch("prx.api.publish_bundle", new_callable=AsyncMock)
    @patch("prx.api.signing.has_signing_key", return_value=True)
    @patch("prx.config_mod.settings.PrxSettings.load")
    def test_publish_with_visibility(self, mock_load, mock_has_key, mock_publish, tmp_path):
        dummy = tmp_path / "test.prx"
        dummy.write_bytes(b"dummy")
        mock_load.return_value = MagicMock(default_visibility="public", prxhub_url="")
        mock_publish.return_value = FakePublishResult()

        result = runner.invoke(prx_app, [
            "publish", str(dummy), "--visibility", "private",
        ])
        assert result.exit_code == 0
        assert "private" in result.output

    @patch("prx.api.publish_bundle", new_callable=AsyncMock)
    @patch("prx.api.signing.has_signing_key", return_value=True)
    @patch("prx.config_mod.settings.PrxSettings.load")
    def test_publish_api_error(self, mock_load, mock_has_key, mock_publish, tmp_path):
        dummy = tmp_path / "test.prx"
        dummy.write_bytes(b"dummy")
        mock_load.return_value = MagicMock(default_visibility="public", prxhub_url="")
        mock_publish.side_effect = Exception("Connection refused")

        result = runner.invoke(prx_app, ["publish", str(dummy)])
        assert result.exit_code != 0
        assert "failed" in result.output.lower()


# ---------------------------------------------------------------------------
# config command
# ---------------------------------------------------------------------------


class TestConfigCmd:
    @patch("prx.cli.config.platformdirs.user_config_dir")
    def test_config_writes_file(self, mock_config_dir, tmp_path):
        mock_config_dir.return_value = str(tmp_path)
        # Config now prompts: URL, visibility, signing identity
        input_text = "https://prxhub.example.com\npublic\njohn@example.com\n"
        result = runner.invoke(prx_app, ["config"], input=input_text)
        assert result.exit_code == 0

        config_file = tmp_path / "config.toml"
        assert config_file.exists()
        content = config_file.read_text()
        assert "prxhub.example.com" in content
        assert "public" in content
        assert "john@example.com" in content

    @patch("prx.cli.config.platformdirs.user_config_dir")
    def test_config_skips_empty_url(self, mock_config_dir, tmp_path):
        mock_config_dir.return_value = str(tmp_path)
        # Empty URL, default visibility, no signing identity
        input_text = "\npublic\n\n"
        result = runner.invoke(prx_app, ["config"], input=input_text)
        assert result.exit_code == 0

        config_file = tmp_path / "config.toml"
        assert config_file.exists()
        content = config_file.read_text()
        assert "[prxhub]" not in content
        assert "[signing]" not in content
        assert "[defaults]" in content

    @patch("prx.cli.config.platformdirs.user_config_dir")
    def test_config_shows_path(self, mock_config_dir, tmp_path):
        mock_config_dir.return_value = str(tmp_path)
        input_text = "\npublic\n\n"
        result = runner.invoke(prx_app, ["config"], input=input_text)
        assert result.exit_code == 0
        assert "Config" in result.output


# ---------------------------------------------------------------------------
# keys generate
# ---------------------------------------------------------------------------


class TestKeysGenerateCmd:
    @patch("prx_spec.generate_keypair")
    def test_generate_default_label(self, mock_gen):
        mock_gen.return_value = (MagicMock(), MagicMock(), "prx_pub_abc123def456")
        result = runner.invoke(prx_app, ["keys", "generate"])
        assert result.exit_code == 0
        assert "prx_pub_abc123def456" in result.output

    @patch("prx_spec.generate_keypair")
    def test_generate_custom_label(self, mock_gen):
        mock_gen.return_value = (MagicMock(), MagicMock(), "prx_pub_abc123def456")
        result = runner.invoke(prx_app, ["keys", "generate", "--label", "work"])
        assert result.exit_code == 0
        assert "prx_pub_abc123def456" in result.output


# ---------------------------------------------------------------------------
# keys list
# ---------------------------------------------------------------------------


class TestKeysListCmd:
    def test_list_no_key_directory(self, tmp_path):
        with patch("prx_spec.attestation.keys.DEFAULT_KEY_DIR", tmp_path / "nonexistent"):
            result = runner.invoke(prx_app, ["keys", "list"])
            assert result.exit_code == 0
            assert "No keys found" in result.output

    def test_list_empty_key_directory(self, tmp_path):
        key_dir = tmp_path / "keys"
        key_dir.mkdir()
        with patch("prx_spec.attestation.keys.DEFAULT_KEY_DIR", key_dir):
            result = runner.invoke(prx_app, ["keys", "list"])
            assert result.exit_code == 0
            assert "No keys found" in result.output

    def test_list_with_keys(self, tmp_path):
        from nacl.signing import SigningKey
        key_dir = tmp_path / "keys"
        key_dir.mkdir()
        sk = SigningKey.generate()
        (key_dir / "prx_signing.pub").write_bytes(sk.verify_key.encode())
        (key_dir / "prx_signing.key").write_bytes(sk.encode())
        with patch("prx_spec.attestation.keys.DEFAULT_KEY_DIR", key_dir):
            result = runner.invoke(prx_app, ["keys", "list"])
            assert result.exit_code == 0
            assert "prx_pub_" in result.output
            assert "present" in result.output

    def test_list_missing_private_key(self, tmp_path):
        from nacl.signing import SigningKey
        key_dir = tmp_path / "keys"
        key_dir.mkdir()
        sk = SigningKey.generate()
        (key_dir / "prx_signing.pub").write_bytes(sk.verify_key.encode())
        with patch("prx_spec.attestation.keys.DEFAULT_KEY_DIR", key_dir):
            result = runner.invoke(prx_app, ["keys", "list"])
            assert result.exit_code == 0
            assert "missing" in result.output


# ---------------------------------------------------------------------------
# keys register / revoke (stub commands)
# ---------------------------------------------------------------------------


class TestKeysRegisterCmd:
    def test_register_shows_message(self):
        result = runner.invoke(prx_app, ["keys", "register"])
        assert result.exit_code == 0
        assert "prxhub" in result.output.lower()


class TestKeysRevokeCmd:
    def test_revoke_shows_message(self):
        result = runner.invoke(prx_app, ["keys", "revoke", "prx_pub_abc123"])
        assert result.exit_code == 0
        assert "prxhub" in result.output.lower()


# ---------------------------------------------------------------------------
# open command (TUI)
# ---------------------------------------------------------------------------


class TestOpenCmd:
    def test_open_no_textual_shows_error(self):
        with patch.dict(sys.modules, {"prx.tui.app": None, "prx.tui": None}):
            result = runner.invoke(prx_app, ["open", "test.prx"])
            assert result.exit_code != 0

    @patch("prx.tui.app.PrxApp")
    def test_open_launches_tui(self, mock_app_cls, tmp_path):
        dummy = tmp_path / "test.prx"
        dummy.write_bytes(b"dummy")
        mock_instance = MagicMock()
        mock_app_cls.return_value = mock_instance

        result = runner.invoke(prx_app, ["open", str(dummy)])
        assert result.exit_code == 0
        mock_app_cls.assert_called_once_with(bundle_path=str(dummy))
        mock_instance.run.assert_called_once()
