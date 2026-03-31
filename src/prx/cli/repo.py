"""prx repo -- manage repos on prxhub."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.table import Table

from prx.api import create_repo, list_repos
from prx.config_mod.settings import PrxSettings

console = Console()


def repo_cmd(
    action: str = typer.Argument(
        help="Action: create, list"
    ),
    name: str = typer.Option(None, "--name", "-n", help="Repo name (for create)"),
    description: str = typer.Option(None, "--desc", "-d", help="Description"),
    visibility: str = typer.Option("public", "--visibility", "-v", help="public or private"),
    owner: str = typer.Option(None, "--owner", help="Owner ID (for list)"),
    api_key: str = typer.Option(None, "--api-key", help="prxhub API key"),
) -> None:
    """Manage research repos on prxhub."""
    settings = PrxSettings.load()
    key = api_key or settings.prxhub_api_key

    if action == "create":
        if not name:
            console.print("[red]--name is required for create[/red]")
            raise typer.Exit(1)
        if not key:
            console.print("[red]API key required. Set via config or --api-key[/red]")
            raise typer.Exit(1)
        result = asyncio.run(
            create_repo(name, key, description=description, visibility=visibility)
        )
        console.print(f"[green]Created repo:[/green] {result.name} ({result.slug})")
        console.print(f"  ID: {result.id}")
        console.print(f"  Visibility: {result.visibility}")

    elif action == "list":
        repos = asyncio.run(list_repos(owner=owner, api_key=key or None))
        if not repos:
            console.print("[dim]No repos found.[/dim]")
            return
        table = Table(title="Repos")
        table.add_column("Name", style="bold")
        table.add_column("Slug")
        table.add_column("Visibility")
        table.add_column("Stars", justify="right")
        table.add_column("ID", style="dim")
        for r in repos:
            table.add_row(r.name, r.slug, r.visibility, str(r.star_count), r.id)
        console.print(table)

    else:
        console.print(f"[red]Unknown action: {action}. Use 'create' or 'list'.[/red]")
        raise typer.Exit(1)
