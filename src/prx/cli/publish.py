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
) -> None:
    """Upload a .prx bundle to prxhub.com."""
    asyncio.run(_publish_async(bundle_path, visibility, tags))


async def _publish_async(
    bundle_path: str, visibility: str | None, tags: str | None
) -> None:
    from prx.api import publish_bundle
    from prx.api.signing import has_signing_key
    from prx.config_mod.settings import PrxSettings

    settings = PrxSettings.load()
    vis = visibility or settings.default_visibility
    hub_url = settings.prxhub_url or None

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

    console.print(f"[bold]Publishing:[/bold] {path.name}")
    console.print(f"[dim]Visibility: {vis}[/dim]")
    if hub_url:
        console.print(f"[dim]Hub: {hub_url}[/dim]")
    if tag_list:
        console.print(f"[dim]Tags: {', '.join(tag_list)}[/dim]")

    try:
        kwargs: dict = {"visibility": vis, "tags": tag_list}
        if hub_url:
            kwargs["api_url"] = hub_url
        result = await publish_bundle(path, **kwargs)
        console.print("[green]Published![/green]")
        console.print(f"  URL: {result.bundle_url}")
    except Exception as e:
        console.print(f"[red]Publish failed: {e}[/red]")
        raise typer.Exit(1)
