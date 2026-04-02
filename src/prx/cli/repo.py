"""prx repo -- manage repos on prxhub."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.table import Table

from prx.api import create_repo, list_repos
from prx.api.signing import has_signing_key

console = Console()


def repo_cmd(
    action: str = typer.Argument(
        help="Action: create, list"
    ),
    name: str = typer.Option(None, "--name", "-n", help="Repo name (for create)"),
    description: str = typer.Option(None, "--desc", "-d", help="Description"),
    visibility: str = typer.Option("public", "--visibility", "-v", help="public or private"),
    owner: str = typer.Option(None, "--owner", help="Owner ID (for list)"),
) -> None:
    """Manage research repos on prxhub."""
    if action == "create":
        if not name:
            console.print("[red]--name is required for create[/red]")
            raise typer.Exit(1)
        if not has_signing_key():
            console.print(
                "[red]No signing key found. "
                "Run 'prx keys generate' and register the key on prxhub.[/red]"
            )
            raise typer.Exit(1)
        result = asyncio.run(
            create_repo(name, description=description, visibility=visibility)
        )
        console.print(f"[green]Created repo:[/green] {result.name} ({result.slug})")
        console.print(f"  ID: {result.id}")
        console.print(f"  Visibility: {result.visibility}")

    elif action == "list":
        repos = asyncio.run(list_repos(owner=owner))
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
