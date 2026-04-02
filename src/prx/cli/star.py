"""prx star -- star/unstar a bundle on prxhub.com."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console

console = Console()


def star_cmd(
    bundle_id: str = typer.Argument(help="Bundle ID to star"),
    unstar: bool = typer.Option(False, "--unstar", "-u", help="Remove star instead"),
) -> None:
    """Star or unstar a research bundle on prxhub.com."""
    asyncio.run(_star_async(bundle_id, unstar))


async def _star_async(bundle_id: str, unstar: bool) -> None:
    from prx.api import star_bundle, unstar_bundle
    from prx.api.signing import has_signing_key

    if not has_signing_key():
        console.print(
            "[red]No signing key found. "
            "Run 'prx keys generate' and register the key on prxhub.[/red]"
        )
        raise typer.Exit(1)

    try:
        if unstar:
            await unstar_bundle(bundle_id)
            console.print(f"[yellow]Unstarred[/yellow] {bundle_id[:8]}")
        else:
            await star_bundle(bundle_id)
            console.print(f"[green]Starred[/green] {bundle_id[:8]}")
    except Exception as e:
        console.print(f"[red]Failed: {e}[/red]")
        raise typer.Exit(1)
