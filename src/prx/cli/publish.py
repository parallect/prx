"""prx publish -- upload to prxhub.com."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console

console = Console()


def publish_cmd(
    bundle_path: str = typer.Argument(help="Path to .prx bundle"),
    visibility: str | None = typer.Option(None, "--visibility", help="public, unlisted, or private (default: from config)"),
    tags: str | None = typer.Option(None, "--tags", help="Comma-separated tags"),
    org: str | None = typer.Option(None, "--org", help="Publish under an organization (slug)"),
    collection: str | None = typer.Option(
        None, "--collection", "-c",
        help="Target collection slug. Created automatically if it doesn't exist.",
    ),
    no_create_collection: bool = typer.Option(
        False, "--no-create-collection",
        help="Fail if the --collection slug doesn't exist (don't auto-create).",
    ),
) -> None:
    """Upload a .prx bundle to prxhub.com."""
    asyncio.run(
        _publish_async(
            bundle_path,
            visibility,
            tags,
            org,
            collection,
            not no_create_collection,
        )
    )


async def _publish_async(
    bundle_path: str,
    visibility: str | None,
    tags: str | None,
    org: str | None,
    collection: str | None,
    create_collection_if_missing: bool,
) -> None:
    import httpx
    from prx.api import PRXHUB_API_URL, publish_bundle, resolve_org_id
    from prx.api.signing import has_signing_key, sign_request  # noqa: F401 -- sign_request used in _link_to_collection
    from prx.config_mod.settings import PrxSettings

    settings = PrxSettings.load()
    vis = visibility or settings.default_visibility
    hub_url = settings.prxhub_url or None
    resolved_api_url = hub_url or PRXHUB_API_URL

    if not has_signing_key():
        console.print(
            "[red]No signing key found. "
            "Run 'prx keys generate' and register the key on prxhub.[/red]"
        )
        raise typer.Exit(1)

    path = Path(bundle_path)
    if not path.exists():
        console.print(f"[red]File not found: {bundle_path}[/red]")
        raise typer.Exit(1)

    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    api_url = hub_url or "https://prxhub.com"

    org_id: str | None = None
    if org:
        try:
            org_id = await resolve_org_id(org, api_url=api_url)
        except ValueError as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(1)

    console.print(f"[bold]Publishing:[/bold] {path.name}")
    console.print(f"[dim]Visibility: {vis}[/dim]")
    if org:
        console.print(f"[dim]Organization: {org}[/dim]")
    if hub_url:
        console.print(f"[dim]Hub: {hub_url}[/dim]")
    if tag_list:
        console.print(f"[dim]Tags: {', '.join(tag_list)}[/dim]")
    if collection:
        console.print(f"[dim]Collection: {collection}[/dim]")

    try:
        kwargs: dict = {"visibility": vis, "tags": tag_list}
        if org_id:
            kwargs["org_id"] = org_id
        if hub_url:
            kwargs["api_url"] = hub_url
        result = await publish_bundle(path, **kwargs)
    except Exception as e:
        console.print(f"[red]Publish failed: {e}[/red]")
        raise typer.Exit(1)

    console.print("[green]Published![/green]")
    console.print(f"  URL: {result.bundle_url}")

    if collection:
        try:
            coll_url = await _link_to_collection(
                api_url=resolved_api_url,
                bundle_id=result.bundle_id,
                collection_slug=collection,
                create_if_missing=create_collection_if_missing,
                visibility=vis,
            )
            if coll_url:
                console.print(f"  Collection: {coll_url}")
        except httpx.HTTPStatusError as e:
            console.print(
                f"[yellow]Published, but couldn't link to collection '{collection}': "
                f"HTTP {e.response.status_code} {e.response.text[:100]}[/yellow]"
            )
        except Exception as e:
            console.print(f"[yellow]Published, but collection link failed: {e}[/yellow]")


async def _link_to_collection(
    *,
    api_url: str,
    bundle_id: str,
    collection_slug: str,
    create_if_missing: bool,
    visibility: str,
) -> str | None:
    """Find or optionally create a collection by slug, then link the bundle."""
    import httpx
    from prx.api.signing import sign_request

    async with httpx.AsyncClient(timeout=30.0) as client:
        # List owned collections to find by slug
        list_url = f"{api_url}/api/collections?per_page=200"
        headers = sign_request("GET", list_url)
        lookup = await client.get(list_url, headers=headers)
        lookup.raise_for_status()
        owned = lookup.json().get("collections", [])
        match = next((c for c in owned if c.get("slug") == collection_slug), None)

        if not match:
            if not create_if_missing:
                raise RuntimeError(
                    f"Collection '{collection_slug}' not found and --no-create-collection set."
                )
            create_url = f"{api_url}/api/collections"
            create_body = {"name": collection_slug, "visibility": visibility}
            import json as _json
            body_bytes = _json.dumps(create_body, separators=(",", ":")).encode()
            headers = sign_request("POST", create_url, body_bytes)
            headers["Content-Type"] = "application/json"
            created = await client.post(create_url, headers=headers, content=body_bytes)
            created.raise_for_status()
            match = created.json()

        link_url = f"{api_url}/api/collections/{match['id']}/bundles"
        link_body = {"bundleId": bundle_id}
        import json as _json
        body_bytes = _json.dumps(link_body, separators=(",", ":")).encode()
        headers = sign_request("POST", link_url, body_bytes)
        headers["Content-Type"] = "application/json"
        link = await client.post(link_url, headers=headers, content=body_bytes)
        link.raise_for_status()

        owner = (match.get("owner") or {}).get("username") or match.get("ownerUsername")
        slug = match.get("slug", collection_slug)
        if owner:
            return f"{api_url}/{owner}/collections/{slug}"
        return None
