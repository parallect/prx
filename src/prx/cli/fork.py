"""prx fork -- fork a bundle on prxhub.com."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console

console = Console()


def fork_cmd(
    bundle_id: str = typer.Argument(help="Bundle ID to fork"),
) -> None:
    """Fork a research bundle on prxhub.com."""
    asyncio.run(_fork_async(bundle_id))


async def _fork_async(bundle_id: str) -> None:
    from prx.api import fork_bundle
    from prx.api.signing import has_signing_key

    if not has_signing_key():
        console.print(
            "[red]No signing key found. "
            "Run 'prx keys generate' and register the key on prxhub.[/red]"
        )
        raise typer.Exit(1)

    console.print(f"[bold]Forking bundle:[/bold] {bundle_id[:8]}...")

    try:
        result = await fork_bundle(bundle_id)
        console.print("[green]Forked![/green]")
        console.print(f"  New ID: {result.id}")
        console.print(f"  Slug: {result.slug}")
    except Exception as e:
        console.print(f"[red]Fork failed: {e}[/red]")
        raise typer.Exit(1)
