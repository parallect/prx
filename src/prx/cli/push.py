"""prx push -- push a bundle to a prxhub repo branch."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console

from prx.api import push_bundle
from prx.config_mod.settings import PrxSettings

console = Console()


def push_cmd(
    repo_id: str = typer.Option(..., "--repo", "-r", help="Repo ID"),
    bundle_id: str = typer.Option(..., "--bundle", "-b", help="Bundle ID (already published)"),
    branch: str = typer.Option(None, "--branch", help="Target branch (default: repo default)"),
    message: str = typer.Option(None, "--message", "-m", help="Version message"),
    api_key: str = typer.Option(None, "--api-key", help="prxhub API key"),
) -> None:
    """Push a published bundle to a repo branch."""
    settings = PrxSettings.load()
    key = api_key or settings.prxhub_api_key

    if not key:
        console.print("[red]API key required. Set via config or --api-key[/red]")
        raise typer.Exit(1)

    result = asyncio.run(
        push_bundle(repo_id, bundle_id, key, branch=branch, message=message)
    )
    console.print(f"[green]Pushed to {result.branch}[/green]")
    console.print(f"  Version: {result.version_id}")
