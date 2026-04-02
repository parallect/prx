"""prx branch -- manage branches on a prxhub repo."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.table import Table

from prx.api import create_branch, list_branches
from prx.api.signing import has_signing_key

console = Console()


def branch_cmd(
    action: str = typer.Argument(help="Action: create, list"),
    repo_id: str = typer.Option(..., "--repo", "-r", help="Repo ID"),
    name: str = typer.Option(None, "--name", "-n", help="Branch name (for create)"),
    from_branch: str = typer.Option(None, "--from", help="Source branch to copy head from"),
) -> None:
    """Manage branches on a prxhub repo."""
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
            create_branch(repo_id, name, from_branch=from_branch)
        )
        console.print(f"[green]Created branch:[/green] {result.name}")
        console.print(f"  ID: {result.id}")
        if result.head_bundle_id:
            console.print(f"  Head: {result.head_bundle_id}")

    elif action == "list":
        branches = asyncio.run(list_branches(repo_id))
        if not branches:
            console.print("[dim]No branches found.[/dim]")
            return
        table = Table(title="Branches")
        table.add_column("Name", style="bold")
        table.add_column("Head Bundle", style="dim")
        table.add_column("ID", style="dim")
        for b in branches:
            table.add_row(b.name, b.head_bundle_id or "-", b.id)
        console.print(table)

    else:
        console.print(f"[red]Unknown action: {action}. Use 'create' or 'list'.[/red]")
        raise typer.Exit(1)
