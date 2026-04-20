"""Tests for hub commands: search, clone, fork, star, repo, branch, push, mr."""

from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from prx.cli import prx_app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fake dataclasses matching the api module
# ---------------------------------------------------------------------------


@dataclass
class FakeBundleSummary:
    id: str = "uuid-1234"
    bundle_id: str = "prx_test0001"
    slug: str = "test-research"
    query: str = "What is quantum computing?"
    title: str | None = "Test Research"
    providers_used: list[str] = field(default_factory=lambda: ["perplexity"])
    star_count: int = 5
    fork_count: int = 1
    download_count: int = 10
    created_at: str = "2025-01-01T00:00:00Z"
    has_synthesis: bool = True
    has_claims: bool = False
    enhanced_by: str | None = None


@dataclass
class FakeSearchResult:
    bundles: list = field(default_factory=lambda: [FakeBundleSummary()])
    page: int = 1
    per_page: int = 20


@dataclass
class FakeForkResult:
    id: str = "uuid-fork"
    slug: str = "test-research-fork"
    forked_from_id: str = "uuid-1234"


@dataclass
class FakeRepoInfo:
    id: str = "repo-uuid"
    name: str = "my-research"
    slug: str = "my-research"
    description: str | None = "Test repo"
    visibility: str = "public"
    default_branch: str = "main"
    star_count: int = 0
    fork_count: int = 0


@dataclass
class FakeBranchInfo:
    id: str = "branch-uuid"
    name: str = "feature-1"
    head_bundle_id: str | None = None


@dataclass
class FakePushResult:
    version_id: str = "version-uuid"
    branch: str = "main"


@dataclass
class FakeMRInfo:
    id: str = "mr-uuid"
    title: str = "Test MR"
    status: str = "open"
    source_branch_id: str = "src-branch"
    target_branch_id: str = "tgt-branch"
    author_id: str = "user-uuid"


# ---------------------------------------------------------------------------
# search — patches the api function used inside the async helper
# ---------------------------------------------------------------------------


class TestSearchCmd:
    @patch("prx.api.search_bundles", new_callable=AsyncMock)
    def test_search_basic(self, mock_search):
        mock_search.return_value = FakeSearchResult()
        result = runner.invoke(prx_app, ["search", "quantum"])
        assert result.exit_code == 0

    @patch("prx.api.search_bundles", new_callable=AsyncMock)
    def test_search_empty_results(self, mock_search):
        mock_search.return_value = FakeSearchResult(bundles=[])
        result = runner.invoke(prx_app, ["search", "nonexistent"])
        assert result.exit_code == 0
        assert "No bundles" in result.output


# ---------------------------------------------------------------------------
# clone
# ---------------------------------------------------------------------------


class TestCloneCmd:
    @patch("prx.api.download_bundle", new_callable=AsyncMock)
    @patch("prx.api.get_bundle", new_callable=AsyncMock)
    def test_clone_basic(self, mock_get, mock_download):
        mock_get.return_value = FakeBundleSummary()

        async def fake_download(bid, path, **kwargs):
            path.write_bytes(b"fake content")
            return path

        mock_download.side_effect = fake_download
        result = runner.invoke(prx_app, ["clone", "uuid-1234"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# fork
# ---------------------------------------------------------------------------


class TestForkCmd:
    @patch("prx.api.fork_bundle", new_callable=AsyncMock)
    @patch("prx.api.signing.has_signing_key", return_value=True)
    def test_fork_with_signing_key(self, mock_has_key, mock_fork):
        mock_fork.return_value = FakeForkResult()
        result = runner.invoke(prx_app, ["fork", "uuid-1234"])
        assert result.exit_code == 0
        assert "Forked" in result.output

    @patch("prx.api.signing.has_signing_key", return_value=False)
    def test_fork_no_signing_key_errors(self, mock_has_key):
        result = runner.invoke(prx_app, ["fork", "uuid-1234"])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# star
# ---------------------------------------------------------------------------


class TestStarCmd:
    @patch("prx.api.star_bundle", new_callable=AsyncMock)
    @patch("prx.api.signing.has_signing_key", return_value=True)
    def test_star_basic(self, mock_has_key, mock_star):
        mock_star.return_value = True
        result = runner.invoke(prx_app, ["star", "uuid-1234"])
        assert result.exit_code == 0
        assert "Starred" in result.output

    @patch("prx.api.unstar_bundle", new_callable=AsyncMock)
    @patch("prx.api.signing.has_signing_key", return_value=True)
    def test_unstar(self, mock_has_key, mock_unstar):
        mock_unstar.return_value = False
        result = runner.invoke(prx_app, ["star", "uuid-1234", "--unstar"])
        assert result.exit_code == 0
        assert "Unstarred" in result.output


# ---------------------------------------------------------------------------
# repo
# ---------------------------------------------------------------------------


class TestRepoCmd:
    @patch("prx.cli.repo.create_repo", new_callable=AsyncMock)
    @patch("prx.cli.repo.has_signing_key", return_value=True)
    def test_repo_create(self, mock_has_key, mock_create):
        mock_create.return_value = FakeRepoInfo()
        result = runner.invoke(prx_app, [
            "repo", "create", "--name", "my-research",
        ])
        assert result.exit_code == 0
        assert "my-research" in result.output

    @patch("prx.cli.repo.list_repos", new_callable=AsyncMock)
    def test_repo_list(self, mock_list):
        mock_list.return_value = [FakeRepoInfo()]
        result = runner.invoke(prx_app, ["repo", "list"])
        assert result.exit_code == 0
        assert "my-research" in result.output

    @patch("prx.cli.repo.list_repos", new_callable=AsyncMock)
    def test_repo_list_empty(self, mock_list):
        mock_list.return_value = []
        result = runner.invoke(prx_app, ["repo", "list"])
        assert result.exit_code == 0
        assert "No repos" in result.output

    @patch("prx.cli.repo.has_signing_key", return_value=True)
    def test_repo_create_no_name(self, mock_has_key):
        result = runner.invoke(prx_app, ["repo", "create"])
        assert result.exit_code == 1

    def test_repo_unknown_action(self):
        result = runner.invoke(prx_app, ["repo", "unknown"])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# branch
# ---------------------------------------------------------------------------


class TestBranchCmd:
    @patch("prx.cli.branch.create_branch", new_callable=AsyncMock)
    @patch("prx.cli.branch.has_signing_key", return_value=True)
    def test_branch_create(self, mock_has_key, mock_create):
        mock_create.return_value = FakeBranchInfo()
        result = runner.invoke(prx_app, [
            "branch", "create", "--repo", "repo-uuid", "--name", "feature-1",
        ])
        assert result.exit_code == 0
        assert "feature-1" in result.output

    @patch("prx.cli.branch.list_branches", new_callable=AsyncMock)
    def test_branch_list(self, mock_list):
        mock_list.return_value = [FakeBranchInfo(name="main"), FakeBranchInfo(name="feature-1")]
        result = runner.invoke(prx_app, ["branch", "list", "--repo", "repo-uuid"])
        assert result.exit_code == 0
        assert "main" in result.output

    @patch("prx.cli.branch.has_signing_key", return_value=True)
    def test_branch_create_no_name(self, mock_has_key):
        result = runner.invoke(prx_app, [
            "branch", "create", "--repo", "repo-uuid",
        ])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# push
# ---------------------------------------------------------------------------


class TestPushCmd:
    @patch("prx.cli.push.push_bundle", new_callable=AsyncMock)
    @patch("prx.cli.push.has_signing_key", return_value=True)
    @patch("prx.cli.push.PrxSettings")
    def test_push_basic(self, mock_settings, mock_has_key, mock_push):
        mock_settings.load.return_value = MagicMock(prxhub_url="")
        mock_push.return_value = FakePushResult()
        result = runner.invoke(prx_app, [
            "push", "--repo", "repo-uuid", "--bundle", "bundle-uuid",
        ])
        assert result.exit_code == 0
        assert "main" in result.output

    @patch("prx.cli.push.has_signing_key", return_value=False)
    @patch("prx.cli.push.PrxSettings")
    def test_push_no_signing_key(self, mock_settings, mock_has_key):
        mock_settings.load.return_value = MagicMock(prxhub_url="")
        result = runner.invoke(prx_app, [
            "push", "--repo", "repo-uuid", "--bundle", "bundle-uuid",
        ])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# mr
# ---------------------------------------------------------------------------


class TestMrCmd:
    @patch("prx.cli.mr.create_merge_request", new_callable=AsyncMock)
    @patch("prx.cli.mr.has_signing_key", return_value=True)
    def test_mr_create(self, mock_has_key, mock_create):
        mock_create.return_value = FakeMRInfo()
        result = runner.invoke(prx_app, [
            "mr", "create", "--repo", "repo-uuid",
            "--source", "feature-1", "--title", "Test MR",
        ])
        assert result.exit_code == 0
        assert "Test MR" in result.output

    @patch("prx.cli.mr.merge_mr", new_callable=AsyncMock)
    @patch("prx.cli.mr.has_signing_key", return_value=True)
    def test_mr_merge(self, mock_has_key, mock_merge):
        mock_merge.return_value = {"merged": True, "targetBranch": "main"}
        result = runner.invoke(prx_app, [
            "mr", "merge", "--repo", "repo-uuid", "--mr-id", "mr-uuid",
        ])
        assert result.exit_code == 0
        assert "Merged" in result.output

    @patch("prx.cli.mr.has_signing_key", return_value=True)
    def test_mr_create_missing_source(self, mock_has_key):
        result = runner.invoke(prx_app, [
            "mr", "create", "--repo", "repo-uuid", "--title", "No Source",
        ])
        assert result.exit_code == 1

    @patch("prx.cli.mr.has_signing_key", return_value=False)
    def test_mr_no_signing_key(self, mock_has_key):
        result = runner.invoke(prx_app, ["mr", "create", "--repo", "r"])
        assert result.exit_code == 1
