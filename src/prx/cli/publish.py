"""prx publish -- upload to prxhub.com."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console

console = Console()


def publish_cmd(
    bundle_path: str = typer.Argument(help="Path to .prx bundle"),
    visibility: str = typer.Option("public", "--visibility", help="public, unlisted, or private"),
    tags: str | None = typer.Option(None, "--tags", help="Comma-separated tags"),
    api_key: str | None = typer.Option(None, "--api-key", help="prxhub API key"),
) -> None:
    """Upload a .prx bundle to prxhub.com."""
    asyncio.run(_publish_async(bundle_path, visibility, tags, api_key))


async def _publish_async(
    bundle_path: str, visibility: str, tags: str | None, api_key: str | None
) -> None:
    from prx.api import publish_bundle
    from prx.config_mod.settings import PrxSettings

    settings = PrxSettings.load()
    key = api_key or settings.prxhub_api_key or settings.parallect_api_key

    if not key:
        console.print(
            "[red]API key required for publishing. "
            "Set via --api-key or in config.[/red]"
        )
        raise typer.Exit(1)

    path = Path(bundle_path)
    if not path.exists():
        console.print(f"[red]File not found: {bundle_path}[/red]")
        raise typer.Exit(1)

    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    console.print(f"[bold]Publishing:[/bold] {path.name}")
    console.print(f"[dim]Visibility: {visibility}[/dim]")
    if tag_list:
        console.print(f"[dim]Tags: {', '.join(tag_list)}[/dim]")

    try:
        result = await publish_bundle(path, key, visibility=visibility, tags=tag_list)
        console.print("[green]Published![/green]")
        console.print(f"  URL: {result.bundle_url}")
    except Exception as e:
        console.print(f"[red]Publish failed: {e}[/red]")
        raise typer.Exit(1)
