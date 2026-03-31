"""prx star -- star/unstar a bundle on prxhub.com."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console

console = Console()


def star_cmd(
    bundle_id: str = typer.Argument(help="Bundle ID to star"),
    unstar: bool = typer.Option(False, "--unstar", "-u", help="Remove star instead"),
    api_key: str | None = typer.Option(None, "--api-key", help="prxhub API key"),
) -> None:
    """Star or unstar a research bundle on prxhub.com."""
    asyncio.run(_star_async(bundle_id, unstar, api_key))


async def _star_async(bundle_id: str, unstar: bool, api_key: str | None) -> None:
    from prx.api import star_bundle, unstar_bundle
    from prx.config_mod.settings import PrxSettings

    settings = PrxSettings.load()
    key = api_key or settings.prxhub_api_key or settings.parallect_api_key

    if not key:
        console.print(
            "[red]API key required. Set via --api-key or in config.[/red]"
        )
        raise typer.Exit(1)

    try:
        if unstar:
            await unstar_bundle(bundle_id, key)
            console.print(f"[yellow]Unstarred[/yellow] {bundle_id[:8]}")
        else:
            await star_bundle(bundle_id, key)
            console.print(f"[green]Starred[/green] {bundle_id[:8]}")
    except Exception as e:
        console.print(f"[red]Failed: {e}[/red]")
        raise typer.Exit(1)
