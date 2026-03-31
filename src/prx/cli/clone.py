"""prx clone -- download a bundle from prxhub.com."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console

console = Console()


def clone_cmd(
    bundle_id: str = typer.Argument(help="Bundle ID or URL to clone"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path"),
    api_key: str | None = typer.Option(
        None, "--api-key", help="prxhub API key (for private bundles)"
    ),
) -> None:
    """Download a research bundle from prxhub.com."""
    asyncio.run(_clone_async(bundle_id, output, api_key))


async def _clone_async(
    bundle_id: str, output: str | None, api_key: str | None
) -> None:
    from prx.api import download_bundle, get_bundle
    from prx.config_mod.settings import PrxSettings

    settings = PrxSettings.load()
    key = api_key or settings.prxhub_api_key or None

    # Extract ID from URL if needed (e.g. https://prxhub.com/user/slug or just an ID)
    bid = _extract_bundle_id(bundle_id)

    console.print(f"[bold]Fetching bundle info:[/bold] {bid[:8]}...")

    try:
        info = await get_bundle(bid)
        label = info.title or info.query[:50]
        console.print(f"  [cyan]{label}[/cyan]")
        console.print(f"  [dim]Providers: {', '.join(info.providers_used)}[/dim]")
    except Exception:
        # If we can't get info, still try to download
        info = None
        label = bid[:8]

    if output:
        out_path = Path(output)
    else:
        # Generate filename from slug or ID
        slug = info.slug if info else bid[:8]
        out_path = Path(f"{slug}.prx")

    console.print(f"[bold]Downloading to:[/bold] {out_path}")

    try:
        await download_bundle(bid, out_path, api_key=key)
        size_kb = out_path.stat().st_size / 1024
        console.print(f"[green]Cloned![/green] ({size_kb:.0f} KB)")
    except Exception as e:
        console.print(f"[red]Clone failed: {e}[/red]")
        raise typer.Exit(1)


def _extract_bundle_id(value: str) -> str:
    """Extract bundle ID from a URL or return as-is."""
    # Handle URLs like https://prxhub.com/api/bundles/UUID
    if "/" in value and "prxhub" in value:
        parts = value.rstrip("/").split("/")
        return parts[-1]
    return value
