"""prxhub API client — publish, search, clone, fork, star, repo, branch, push, MR."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import httpx

from prx.api.signing import sign_request

PRXHUB_API_URL = os.environ.get("PRXHUB_API_URL", "https://prxhub.com")


def _signed_headers(
    method: str, url: str, body: bytes | str = b""
) -> dict[str, str]:
    """Build auth headers by signing the request with the local key."""
    return sign_request(method, url, body)


def _auth_headers_for_json(
    method: str, url: str, json_body: dict | None = None
) -> dict[str, str]:
    """Sign a request whose body is JSON-serialized."""
    body = json.dumps(json_body, separators=(",", ":")).encode() if json_body else b""
    return _signed_headers(method, url, body)


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


async def resolve_org_id(
    org_slug: str,
    api_url: str = PRXHUB_API_URL,
) -> str:
    """Resolve an org slug to its ID by listing the user's orgs.

    Raises ValueError if the user is not a member of an org with that slug.
    """
    url = f"{api_url}/api/orgs"
    headers = _signed_headers("GET", url)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        orgs = response.json().get("orgs", [])
    for org in orgs:
        if org.get("slug") == org_slug:
            return org["id"]
    available = [o.get("slug") for o in orgs]
    raise ValueError(
        f"Organization '{org_slug}' not found. Your orgs: {', '.join(available) or '(none)'}"
    )


async def publish_bundle(
    bundle_path: Path,
    visibility: str = "public",
    tags: list[str] | None = None,
    org_id: str | None = None,
    api_url: str = PRXHUB_API_URL,
) -> PublishResult:
    """Upload a .prx bundle to prxhub.com."""
    file_size = bundle_path.stat().st_size

    async with httpx.AsyncClient(timeout=120.0) as client:
        # Step 1: Initiate upload
        upload_url = f"{api_url}/api/bundles/upload"
        upload_body = {"filename": bundle_path.name, "size_bytes": file_size}
        response = await client.post(
            upload_url,
            headers=_auth_headers_for_json("POST", upload_url, upload_body),
            json=upload_body,
        )
        response.raise_for_status()
        upload_data = response.json()

        # Step 2: Upload file to presigned URL
        with open(bundle_path, "rb") as f:
            await client.put(upload_data["upload_url"], content=f.read())

        # Step 3: Confirm upload
        confirm_url = f"{api_url}/api/bundles/confirm"
        confirm_body: dict = {
            "upload_id": upload_data["upload_id"],
            "storage_key": upload_data["storage_key"],
            "visibility": visibility,
            "tags": tags or [],
        }
        if org_id:
            confirm_body["org_id"] = org_id
        confirm = await client.post(
            confirm_url,
            headers=_auth_headers_for_json("POST", confirm_url, confirm_body),
            json=confirm_body,
        )
        confirm.raise_for_status()
        result = confirm.json()

        bundle_url = result.get("bundle_url") or result.get("url", "")
        if bundle_url and not bundle_url.startswith("http"):
            bundle_url = f"{api_url}{bundle_url}"

        return PublishResult(
            bundle_url=bundle_url,
            bundle_id=result.get("bundle_id", result.get("id", "")),
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
    api_url: str = PRXHUB_API_URL,
) -> Path:
    """Download a .prx bundle from prxhub.com."""
    url = f"{api_url}/api/bundles/{bundle_id}/download"
    headers = _signed_headers("GET", url)

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        download_url = response.json()["download_url"]

        download = await client.get(download_url)
        download.raise_for_status()
        output_path.write_bytes(download.content)
        return output_path


async def fork_bundle(
    bundle_id: str,
    api_url: str = PRXHUB_API_URL,
) -> ForkResult:
    """Fork a bundle on prxhub.com."""
    url = f"{api_url}/api/bundles/{bundle_id}/fork"
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            url,
            headers=_signed_headers("POST", url),
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
    api_url: str = PRXHUB_API_URL,
) -> bool:
    """Star a bundle on prxhub.com. Returns True if starred."""
    url = f"{api_url}/api/bundles/{bundle_id}/star"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            headers=_signed_headers("POST", url),
        )
        response.raise_for_status()
        return response.json().get("starred", True)


async def unstar_bundle(
    bundle_id: str,
    api_url: str = PRXHUB_API_URL,
) -> bool:
    """Unstar a bundle on prxhub.com. Returns False if unstarred."""
    url = f"{api_url}/api/bundles/{bundle_id}/star"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.delete(
            url,
            headers=_signed_headers("DELETE", url),
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
    description: str | None = None,
    visibility: str = "public",
    api_url: str = PRXHUB_API_URL,
) -> RepoInfo:
    """Create a new repo on prxhub."""
    url = f"{api_url}/api/repos"
    body = {"name": name, "description": description, "visibility": visibility}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            headers=_auth_headers_for_json("POST", url, body),
            json=body,
        )
        response.raise_for_status()
        return _make_repo_info(response.json())


async def list_repos(
    owner: str | None = None,
    api_url: str = PRXHUB_API_URL,
) -> list[RepoInfo]:
    """List repos."""
    url = f"{api_url}/api/repos"
    params: dict[str, str] = {}
    if owner:
        params["owner"] = owner

    headers = _signed_headers("GET", url)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        return [_make_repo_info(r) for r in response.json().get("repos", [])]


async def list_branches(
    repo_id: str,
    api_url: str = PRXHUB_API_URL,
) -> list[BranchInfo]:
    """List branches for a repo."""
    url = f"{api_url}/api/repos/{repo_id}/branches"
    headers = _signed_headers("GET", url)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers=headers)
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
    from_branch: str | None = None,
    api_url: str = PRXHUB_API_URL,
) -> BranchInfo:
    """Create a new branch."""
    url = f"{api_url}/api/repos/{repo_id}/branches"
    body: dict[str, str] = {"name": name}
    if from_branch:
        body["fromBranch"] = from_branch

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            headers=_auth_headers_for_json("POST", url, body),
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
    branch: str | None = None,
    message: str | None = None,
    api_url: str = PRXHUB_API_URL,
) -> PushResult:
    """Push a bundle to a repo branch."""
    url = f"{api_url}/api/repos/{repo_id}/push"
    body: dict[str, str] = {"bundleId": bundle_id}
    if branch:
        body["branch"] = branch
    if message:
        body["message"] = message

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            url,
            headers=_auth_headers_for_json("POST", url, body),
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
    target_branch: str | None = None,
    description: str | None = None,
    api_url: str = PRXHUB_API_URL,
) -> MergeRequestInfo:
    """Create a merge request."""
    url = f"{api_url}/api/repos/{repo_id}/mrs"
    body: dict[str, str] = {"sourceBranch": source_branch, "title": title}
    if target_branch:
        body["targetBranch"] = target_branch
    if description:
        body["description"] = description

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            headers=_auth_headers_for_json("POST", url, body),
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
    api_url: str = PRXHUB_API_URL,
) -> dict:
    """Merge a merge request."""
    url = f"{api_url}/api/repos/{repo_id}/mrs/{mr_id}"
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            url,
            headers=_signed_headers("POST", url),
        )
        response.raise_for_status()
        return response.json()
