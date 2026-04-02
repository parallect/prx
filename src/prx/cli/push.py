"""prx push -- push a bundle to a prxhub repo branch."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console

from prx.api import push_bundle
from prx.api.signing import has_signing_key
from prx.config_mod.settings import PrxSettings

console = Console()


def push_cmd(
    repo_id: str = typer.Option(..., "--repo", "-r", help="Repo ID"),
    bundle_id: str = typer.Option(..., "--bundle", "-b", help="Bundle ID (already published)"),
    branch: str = typer.Option(None, "--branch", help="Target branch (default: repo default)"),
    message: str = typer.Option(None, "--message", "-m", help="Version message"),
) -> None:
    """Push a published bundle to a repo branch."""
    settings = PrxSettings.load()
    hub_url = settings.prxhub_url or None

    if not has_signing_key():
        console.print(
            "[red]No signing key found. "
            "Run 'prx keys generate' and register the key on prxhub.[/red]"
        )
        raise typer.Exit(1)

    kwargs: dict = {"branch": branch, "message": message}
    if hub_url:
        kwargs["api_url"] = hub_url

    result = asyncio.run(
        push_bundle(repo_id, bundle_id, **kwargs)
    )
    console.print(f"[green]Pushed to {result.branch}[/green]")
    console.print(f"  Version: {result.version_id}")
