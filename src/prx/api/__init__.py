"""prxhub API client — publish, search, clone, fork, star, repo, branch, push, MR."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import httpx

PRXHUB_API_URL = "https://prxhub.com"


@dataclass
class PublishResult:
    """Result of a publish request."""

    bundle_url: str
    bundle_id: str


@dataclass
class BundleSummary:
    """Summary of a bundle from search/list results."""

    id: str
    bundle_id: str
    slug: str
    query: str
    title: str | None
    providers_used: list[str]
    star_count: int
    fork_count: int
    download_count: int
    created_at: str
    has_synthesis: bool = False
    has_claims: bool = False
    enhanced_by: str | None = None


@dataclass
class SearchResult:
    """Result of a search query."""

    bundles: list[BundleSummary]
    page: int
    per_page: int


@dataclass
class ForkResult:
    """Result of a fork operation."""

    id: str
    slug: str
    forked_from_id: str


@dataclass
class RepoInfo:
    """Summary of a repo from API."""

    id: str
    name: str
    slug: str
    description: str | None
    visibility: str
    default_branch: str
    star_count: int
    fork_count: int


@dataclass
class BranchInfo:
    """Summary of a branch."""

    id: str
    name: str
    head_bundle_id: str | None


@dataclass
class PushResult:
    """Result of a push operation."""

    version_id: str
    branch: str


@dataclass
class MergeRequestInfo:
    """Summary of a merge request."""

    id: str
    title: str
    status: str
    source_branch_id: str
    target_branch_id: str
    author_id: str


# ---------------------------------------------------------------------------
# Bundle operations
# ---------------------------------------------------------------------------


def _make_bundle_summary(data: dict) -> BundleSummary:
    """Convert a raw API response dict to a BundleSummary."""
    return BundleSummary(
        id=data["id"],
        bundle_id=data.get("bundleId", data.get("bundle_id", "")),
        slug=data.get("slug", ""),
        query=data.get("query", ""),
        title=data.get("title"),
        providers_used=data.get("providersUsed", data.get("providers_used", [])),
        star_count=data.get("starCount", data.get("star_count", 0)),
        fork_count=data.get("forkCount", data.get("fork_count", 0)),
        download_count=data.get("downloadCount", data.get("download_count", 0)),
        created_at=data.get("createdAt", data.get("created_at", "")),
        has_synthesis=data.get("hasSynthesis", data.get("has_synthesis", False)),
        has_claims=data.get("hasClaims", data.get("has_claims", False)),
        enhanced_by=data.get("enhancedBy", data.get("enhanced_by")),
    )


async def publish_bundle(
    bundle_path: Path,
    api_key: str,
    visibility: str = "public",
    tags: list[str] | None = None,
    api_url: str = PRXHUB_API_URL,
) -> PublishResult:
    """Upload a .prx bundle to prxhub.com."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{api_url}/api/bundles/upload",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"visibility": visibility, "tags": tags or []},
        )
        response.raise_for_status()
        upload_data = response.json()

        with open(bundle_path, "rb") as f:
            await client.put(upload_data["upload_url"], content=f.read())

        confirm = await client.post(
            f"{api_url}/api/bundles/confirm",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"upload_id": upload_data["upload_id"]},
        )
        confirm.raise_for_status()
        result = confirm.json()

        return PublishResult(
            bundle_url=result["bundle_url"],
            bundle_id=result["bundle_id"],
        )


async def search_bundles(
    query: str | None = None,
    provider: str | None = None,
    tag: str | None = None,
    sort: str = "recent",
    page: int = 1,
    per_page: int = 20,
    api_url: str = PRXHUB_API_URL,
) -> SearchResult:
    """Search public bundles on prxhub.com."""
    params: dict[str, str | int] = {"sort": sort, "page": page, "per_page": per_page}
    if query:
        params["q"] = query
    if provider:
        params["provider"] = provider
    if tag:
        params["tag"] = tag

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{api_url}/api/bundles", params=params)
        response.raise_for_status()
        data = response.json()
        return SearchResult(
            bundles=[_make_bundle_summary(b) for b in data.get("bundles", [])],
            page=data.get("page", page),
            per_page=data.get("per_page", per_page),
        )


async def get_bundle(
    bundle_id: str,
    api_url: str = PRXHUB_API_URL,
) -> BundleSummary:
    """Fetch bundle metadata by ID."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{api_url}/api/bundles/{bundle_id}")
        response.raise_for_status()
        return _make_bundle_summary(response.json())


async def download_bundle(
    bundle_id: str,
    output_path: Path,
    api_key: str | None = None,
    api_url: str = PRXHUB_API_URL,
) -> Path:
    """Download a .prx bundle from prxhub.com."""
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(
            f"{api_url}/api/bundles/{bundle_id}/download",
            headers=headers,
        )
        response.raise_for_status()
        download_url = response.json()["download_url"]

        download = await client.get(download_url)
        download.raise_for_status()
        output_path.write_bytes(download.content)
        return output_path


async def fork_bundle(
    bundle_id: str,
    api_key: str,
    api_url: str = PRXHUB_API_URL,
) -> ForkResult:
    """Fork a bundle on prxhub.com."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{api_url}/api/bundles/{bundle_id}/fork",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        response.raise_for_status()
        data = response.json()
        return ForkResult(
            id=data["id"],
            slug=data["slug"],
            forked_from_id=data.get("forkedFromId", data.get("forked_from_id", "")),
        )


async def star_bundle(
    bundle_id: str,
    api_key: str,
    api_url: str = PRXHUB_API_URL,
) -> bool:
    """Star a bundle on prxhub.com. Returns True if starred."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{api_url}/api/bundles/{bundle_id}/star",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        response.raise_for_status()
        return response.json().get("starred", True)


async def unstar_bundle(
    bundle_id: str,
    api_key: str,
    api_url: str = PRXHUB_API_URL,
) -> bool:
    """Unstar a bundle on prxhub.com. Returns False if unstarred."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.delete(
            f"{api_url}/api/bundles/{bundle_id}/star",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        response.raise_for_status()
        return response.json().get("starred", False)


# ---------------------------------------------------------------------------
# Repo / branch / push / MR API functions
# ---------------------------------------------------------------------------


def _make_repo_info(data: dict) -> RepoInfo:
    return RepoInfo(
        id=data["id"],
        name=data.get("name", ""),
        slug=data.get("slug", ""),
        description=data.get("description"),
        visibility=data.get("visibility", "public"),
        default_branch=data.get("defaultBranch", data.get("default_branch", "main")),
        star_count=data.get("starCount", data.get("star_count", 0)),
        fork_count=data.get("forkCount", data.get("fork_count", 0)),
    )


async def create_repo(
    name: str,
    api_key: str,
    description: str | None = None,
    visibility: str = "public",
    api_url: str = PRXHUB_API_URL,
) -> RepoInfo:
    """Create a new repo on prxhub."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{api_url}/api/repos",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"name": name, "description": description, "visibility": visibility},
        )
        response.raise_for_status()
        return _make_repo_info(response.json())


async def list_repos(
    owner: str | None = None,
    api_key: str | None = None,
    api_url: str = PRXHUB_API_URL,
) -> list[RepoInfo]:
    """List repos."""
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    params: dict[str, str] = {}
    if owner:
        params["owner"] = owner

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{api_url}/api/repos", headers=headers, params=params)
        response.raise_for_status()
        return [_make_repo_info(r) for r in response.json().get("repos", [])]


async def list_branches(
    repo_id: str,
    api_key: str | None = None,
    api_url: str = PRXHUB_API_URL,
) -> list[BranchInfo]:
    """List branches for a repo."""
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{api_url}/api/repos/{repo_id}/branches", headers=headers
        )
        response.raise_for_status()
        data = response.json()
        return [
            BranchInfo(
                id=b["id"],
                name=b["name"],
                head_bundle_id=b.get("headBundleId", b.get("head_bundle_id")),
            )
            for b in data.get("branches", [])
        ]


async def create_branch(
    repo_id: str,
    name: str,
    api_key: str,
    from_branch: str | None = None,
    api_url: str = PRXHUB_API_URL,
) -> BranchInfo:
    """Create a new branch."""
    body: dict[str, str] = {"name": name}
    if from_branch:
        body["fromBranch"] = from_branch

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{api_url}/api/repos/{repo_id}/branches",
            headers={"Authorization": f"Bearer {api_key}"},
            json=body,
        )
        response.raise_for_status()
        data = response.json()
        return BranchInfo(
            id=data["id"],
            name=data["name"],
            head_bundle_id=data.get("headBundleId", data.get("head_bundle_id")),
        )


async def push_bundle(
    repo_id: str,
    bundle_id: str,
    api_key: str,
    branch: str | None = None,
    message: str | None = None,
    api_url: str = PRXHUB_API_URL,
) -> PushResult:
    """Push a bundle to a repo branch."""
    body: dict[str, str] = {"bundleId": bundle_id}
    if branch:
        body["branch"] = branch
    if message:
        body["message"] = message

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{api_url}/api/repos/{repo_id}/push",
            headers={"Authorization": f"Bearer {api_key}"},
            json=body,
        )
        response.raise_for_status()
        data = response.json()
        return PushResult(
            version_id=data["version"]["id"],
            branch=data["branch"],
        )


async def create_merge_request(
    repo_id: str,
    source_branch: str,
    title: str,
    api_key: str,
    target_branch: str | None = None,
    description: str | None = None,
    api_url: str = PRXHUB_API_URL,
) -> MergeRequestInfo:
    """Create a merge request."""
    body: dict[str, str] = {"sourceBranch": source_branch, "title": title}
    if target_branch:
        body["targetBranch"] = target_branch
    if description:
        body["description"] = description

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{api_url}/api/repos/{repo_id}/mrs",
            headers={"Authorization": f"Bearer {api_key}"},
            json=body,
        )
        response.raise_for_status()
        data = response.json()
        return MergeRequestInfo(
            id=data["id"],
            title=data["title"],
            status=data["status"],
            source_branch_id=data["sourceBranchId"],
            target_branch_id=data["targetBranchId"],
            author_id=data["authorId"],
        )


async def merge_mr(
    repo_id: str,
    mr_id: str,
    api_key: str,
    api_url: str = PRXHUB_API_URL,
) -> dict:
    """Merge a merge request."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{api_url}/api/repos/{repo_id}/mrs/{mr_id}",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        response.raise_for_status()
        return response.json()
