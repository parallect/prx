"""prx fork -- fork a bundle on prxhub.com."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console

console = Console()


def fork_cmd(
    bundle_id: str = typer.Argument(help="Bundle ID to fork"),
    api_key: str | None = typer.Option(None, "--api-key", help="prxhub API key"),
) -> None:
    """Fork a research bundle on prxhub.com."""
    asyncio.run(_fork_async(bundle_id, api_key))


async def _fork_async(bundle_id: str, api_key: str | None) -> None:
    from prx.api import fork_bundle
    from prx.config_mod.settings import PrxSettings

    settings = PrxSettings.load()
    key = api_key or settings.prxhub_api_key or settings.parallect_api_key

    if not key:
        console.print(
            "[red]API key required for forking. "
            "Set via --api-key or in config.[/red]"
        )
        raise typer.Exit(1)

    console.print(f"[bold]Forking bundle:[/bold] {bundle_id[:8]}...")

    try:
        result = await fork_bundle(bundle_id, key)
        console.print("[green]Forked![/green]")
        console.print(f"  New ID: {result.id}")
        console.print(f"  Slug: {result.slug}")
    except Exception as e:
        console.print(f"[red]Fork failed: {e}[/red]")
        raise typer.Exit(1)
