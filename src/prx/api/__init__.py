"""prxhub API client — publish, search, clone, fork, star, repo, branch, push, MR.

Authentication
--------------
Writes to prxhub require a bearer token obtained via ``prx login`` (device-code
OAuth). The token is stored at ``~/.config/prx/auth.json`` (platform-specific)
and attached as ``Authorization: Bearer <token>``.

Advanced users may additionally register their Ed25519 public key via
``prx keys register`` and have bundles signature-authenticated; see the prxhub
API docs. Bearer auth is the default and is what the CLI commands in this
package use.

Every helper accepts an optional ``token`` argument. For backwards compatibility
the older name ``api_key`` is still accepted on the write helpers -- it's
treated as a bearer token (which is what newly-issued prxhub credentials are).
If no token is provided and none is stored, write helpers raise ``AuthRequired``
with a clear message.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import httpx

from prx.auth import DEFAULT_API_URL, load_token

PRXHUB_API_URL = DEFAULT_API_URL


class AuthRequired(RuntimeError):
    """Raised when a write helper is called without an available bearer token."""

    def __init__(self, message: str = "Not logged in. Run `prx login` first.") -> None:
        super().__init__(message)


def _resolve_token(token: str | None) -> str:
    """Return a bearer token, preferring the caller-supplied one."""
    if token:
        return token
    stored = load_token()
    if stored is None:
        raise AuthRequired()
    if stored.is_expired():
        raise AuthRequired("Your session expired. Run `prx login` again.")
    return stored.access_token


def _auth_headers(token: str | None, *, required: bool = True) -> dict[str, str]:
    """Build the Authorization header dict.

    If ``required`` is False and no token is available, returns an empty dict
    (used for public read endpoints).
    """
    if token:
        return {"Authorization": f"Bearer {token}"}
    stored = load_token()
    if stored is None or stored.is_expired():
        if required:
            raise AuthRequired(
                "Your session expired. Run `prx login` again."
                if stored is not None
                else "Not logged in. Run `prx login` first."
            )
        return {}
    return {"Authorization": f"Bearer {stored.access_token}"}


@dataclass
class PublishResult:
    bundle_url: str
    bundle_id: str
    collection_url: str | None = None


@dataclass
class BundleSummary:
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
    bundles: list[BundleSummary]
    page: int
    per_page: int


@dataclass
class ForkResult:
    id: str
    slug: str
    forked_from_id: str


@dataclass
class RepoInfo:
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
    id: str
    name: str
    head_bundle_id: str | None


@dataclass
class PushResult:
    version_id: str
    branch: str


@dataclass
class MergeRequestInfo:
    id: str
    title: str
    status: str
    source_branch_id: str
    target_branch_id: str
    author_id: str


@dataclass
class KeyRegistration:
    key_id: str
    url: str | None = None


# ---------------------------------------------------------------------------
# Bundle operations
# ---------------------------------------------------------------------------


def _make_bundle_summary(data: dict) -> BundleSummary:
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
    api_key: str | None = None,
    visibility: str = "public",
    tags: list[str] | None = None,
    api_url: str = PRXHUB_API_URL,
    *,
    token: str | None = None,
    collection: str | None = None,
    create_collection_if_missing: bool = True,
) -> PublishResult:
    """Upload a .prx bundle to prxhub, optionally adding to a collection."""
    headers = _auth_headers(token or api_key)
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{api_url}/api/bundles/upload",
            headers=headers,
            json={"visibility": visibility, "tags": tags or []},
        )
        response.raise_for_status()
        upload_data = response.json()

        with open(bundle_path, "rb") as f:
            await client.put(upload_data["upload_url"], content=f.read())

        confirm = await client.post(
            f"{api_url}/api/bundles/confirm",
            headers=headers,
            json={"upload_id": upload_data["upload_id"]},
        )
        confirm.raise_for_status()
        result = confirm.json()

        collection_url: str | None = None
        if collection:
            collection_url = await _link_to_collection(
                client=client,
                api_url=api_url,
                headers=headers,
                bundle_id=result["bundle_id"],
                collection_slug=collection,
                create_if_missing=create_collection_if_missing,
                visibility=visibility,
            )

        return PublishResult(
            bundle_url=result["bundle_url"],
            bundle_id=result["bundle_id"],
            collection_url=collection_url,
        )


async def _link_to_collection(
    *,
    client: httpx.AsyncClient,
    api_url: str,
    headers: dict,
    bundle_id: str,
    collection_slug: str,
    create_if_missing: bool,
    visibility: str,
) -> str | None:
    """Find or (optionally) create a collection by slug, then link the bundle.
    Returns the collection URL on success, None on failure."""
    # Look up by slug via the authed user's collections
    lookup = await client.get(
        f"{api_url}/api/collections?per_page=200",
        headers=headers,
    )
    lookup.raise_for_status()
    owned = lookup.json().get("collections", [])
    match = next((c for c in owned if c.get("slug") == collection_slug), None)

    if not match:
        if not create_if_missing:
            raise RuntimeError(
                f"Collection '{collection_slug}' not found and --no-create-collection set."
            )
        created = await client.post(
            f"{api_url}/api/collections",
            headers=headers,
            json={"name": collection_slug, "visibility": visibility},
        )
        created.raise_for_status()
        match = created.json()

    link = await client.post(
        f"{api_url}/api/collections/{match['id']}/bundles",
        headers=headers,
        json={"bundleId": bundle_id},
    )
    link.raise_for_status()

    owner = match.get("owner", {}).get("username") or match.get("ownerUsername")
    if owner:
        return f"{api_url}/{owner}/collections/{match.get('slug', collection_slug)}"
    return None


async def search_bundles(
    query: str | None = None,
    provider: str | None = None,
    tag: str | None = None,
    sort: str = "recent",
    page: int = 1,
    per_page: int = 20,
    api_url: str = PRXHUB_API_URL,
) -> SearchResult:
    """Search public bundles (no auth required)."""
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
    """Fetch bundle metadata (public read, no auth required)."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{api_url}/api/bundles/{bundle_id}")
        response.raise_for_status()
        return _make_bundle_summary(response.json())


async def download_bundle(
    bundle_id: str,
    output_path: Path,
    api_key: str | None = None,
    api_url: str = PRXHUB_API_URL,
    *,
    token: str | None = None,
) -> Path:
    """Download a .prx bundle. Token only required for private bundles."""
    headers = _auth_headers(token or api_key, required=False)

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
    api_key: str | None = None,
    api_url: str = PRXHUB_API_URL,
    *,
    token: str | None = None,
) -> ForkResult:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{api_url}/api/bundles/{bundle_id}/fork",
            headers=_auth_headers(token or api_key),
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
    api_key: str | None = None,
    api_url: str = PRXHUB_API_URL,
    *,
    token: str | None = None,
) -> bool:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{api_url}/api/bundles/{bundle_id}/star",
            headers=_auth_headers(token or api_key),
        )
        response.raise_for_status()
        return response.json().get("starred", True)


async def unstar_bundle(
    bundle_id: str,
    api_key: str | None = None,
    api_url: str = PRXHUB_API_URL,
    *,
    token: str | None = None,
) -> bool:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.delete(
            f"{api_url}/api/bundles/{bundle_id}/star",
            headers=_auth_headers(token or api_key),
        )
        response.raise_for_status()
        return response.json().get("starred", False)


# ---------------------------------------------------------------------------
# Keys
# ---------------------------------------------------------------------------


async def register_public_key(
    public_key_jwk: dict,
    key_id: str,
    label: str,
    api_key: str | None = None,
    api_url: str = PRXHUB_API_URL,
    *,
    token: str | None = None,
) -> KeyRegistration:
    """Register an Ed25519 public key on prxhub. Requires login."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{api_url}/api/keys",
            headers=_auth_headers(token or api_key),
            json={
                "public_key_jwk": public_key_jwk,
                "key_id": key_id,
                "label": label,
            },
        )
        response.raise_for_status()
        data = response.json()
        return KeyRegistration(
            key_id=data.get("key_id", key_id),
            url=data.get("url"),
        )


async def revoke_public_key(
    key_id: str,
    api_key: str | None = None,
    api_url: str = PRXHUB_API_URL,
    *,
    token: str | None = None,
) -> bool:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.delete(
            f"{api_url}/api/keys/{key_id}",
            headers=_auth_headers(token or api_key),
        )
        response.raise_for_status()
        return True


# ---------------------------------------------------------------------------
# Repo / branch / push / MR
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
    api_key: str | None = None,
    description: str | None = None,
    visibility: str = "public",
    api_url: str = PRXHUB_API_URL,
    *,
    token: str | None = None,
) -> RepoInfo:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{api_url}/api/repos",
            headers=_auth_headers(token or api_key),
            json={"name": name, "description": description, "visibility": visibility},
        )
        response.raise_for_status()
        return _make_repo_info(response.json())


async def list_repos(
    owner: str | None = None,
    api_key: str | None = None,
    api_url: str = PRXHUB_API_URL,
    *,
    token: str | None = None,
) -> list[RepoInfo]:
    headers = _auth_headers(token or api_key, required=False)
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
    *,
    token: str | None = None,
) -> list[BranchInfo]:
    headers = _auth_headers(token or api_key, required=False)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{api_url}/api/repos/{repo_id}/branches", headers=headers)
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
    api_key: str | None = None,
    from_branch: str | None = None,
    api_url: str = PRXHUB_API_URL,
    *,
    token: str | None = None,
) -> BranchInfo:
    body: dict[str, str] = {"name": name}
    if from_branch:
        body["fromBranch"] = from_branch

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{api_url}/api/repos/{repo_id}/branches",
            headers=_auth_headers(token or api_key),
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
    api_key: str | None = None,
    branch: str | None = None,
    message: str | None = None,
    api_url: str = PRXHUB_API_URL,
    *,
    token: str | None = None,
) -> PushResult:
    body: dict[str, str] = {"bundleId": bundle_id}
    if branch:
        body["branch"] = branch
    if message:
        body["message"] = message

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{api_url}/api/repos/{repo_id}/push",
            headers=_auth_headers(token or api_key),
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
    api_key: str | None = None,
    target_branch: str | None = None,
    description: str | None = None,
    api_url: str = PRXHUB_API_URL,
    *,
    token: str | None = None,
) -> MergeRequestInfo:
    body: dict[str, str] = {"sourceBranch": source_branch, "title": title}
    if target_branch:
        body["targetBranch"] = target_branch
    if description:
        body["description"] = description

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{api_url}/api/repos/{repo_id}/mrs",
            headers=_auth_headers(token or api_key),
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
    api_key: str | None = None,
    api_url: str = PRXHUB_API_URL,
    *,
    token: str | None = None,
) -> dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{api_url}/api/repos/{repo_id}/mrs/{mr_id}",
            headers=_auth_headers(token or api_key),
        )
        response.raise_for_status()
        return response.json()
