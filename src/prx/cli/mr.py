"""prx mr -- manage merge requests on prxhub repos."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console

from prx.api import create_merge_request, merge_mr
from prx.config_mod.settings import PrxSettings

console = Console()


def mr_cmd(
    action: str = typer.Argument(help="Action: create, merge"),
    repo_id: str = typer.Option(..., "--repo", "-r", help="Repo ID"),
    source: str = typer.Option(None, "--source", "-s", help="Source branch name (for create)"),
    target: str = typer.Option(None, "--target", "-t", help="Target branch (default: main)"),
    title: str = typer.Option(None, "--title", help="MR title (for create)"),
    description: str = typer.Option(None, "--desc", "-d", help="MR description"),
    mr_id: str = typer.Option(None, "--mr-id", help="Merge request ID (for merge)"),
    api_key: str = typer.Option(None, "--api-key", help="prxhub API key"),
) -> None:
    """Manage merge requests on prxhub repos."""
    settings = PrxSettings.load()
    key = api_key or settings.prxhub_api_key

    if not key:
        console.print("[red]API key required.[/red]")
        raise typer.Exit(1)

    if action == "create":
        if not source or not title:
            console.print("[red]--source and --title required for create[/red]")
            raise typer.Exit(1)
        result = asyncio.run(
            create_merge_request(
                repo_id, source, title, key,
                target_branch=target, description=description,
            )
        )
        console.print(f"[green]Created MR:[/green] {result.title}")
        console.print(f"  ID: {result.id}")
        console.print(f"  Status: {result.status}")

    elif action == "merge":
        if not mr_id:
            console.print("[red]--mr-id required for merge[/red]")
            raise typer.Exit(1)
        result = asyncio.run(merge_mr(repo_id, mr_id, key))
        if result.get("merged"):
            console.print(
                f"[green]Merged![/green] Target: {result.get('targetBranch', 'main')}"
            )
        else:
            console.print(f"[yellow]Merge response:[/yellow] {result}")

    else:
        console.print(f"[red]Unknown action: {action}. Use 'create' or 'merge'.[/red]")
        raise typer.Exit(1)
