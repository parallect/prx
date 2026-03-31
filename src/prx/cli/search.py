"""prx search -- search prxhub.com for bundles."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.table import Table

console = Console()


def search_cmd(
    query: str = typer.Argument(None, help="Search query"),
    provider: str | None = typer.Option(None, "--provider", "-p", help="Filter by provider"),
    tag: str | None = typer.Option(None, "--tag", "-t", help="Filter by tag"),
    sort: str = typer.Option("recent", "--sort", "-s", help="Sort: recent, stars, downloads"),
    page: int = typer.Option(1, "--page", help="Page number"),
    per_page: int = typer.Option(20, "--per-page", help="Results per page"),
) -> None:
    """Search for research bundles on prxhub.com."""
    asyncio.run(_search_async(query, provider, tag, sort, page, per_page))


async def _search_async(
    query: str | None,
    provider: str | None,
    tag: str | None,
    sort: str,
    page: int,
    per_page: int,
) -> None:
    from prx.api import search_bundles

    try:
        result = await search_bundles(
            query=query,
            provider=provider,
            tag=tag,
            sort=sort,
            page=page,
            per_page=per_page,
        )
    except Exception as e:
        console.print(f"[red]Search failed: {e}[/red]")
        raise typer.Exit(1)

    if not result.bundles:
        console.print("[dim]No bundles found.[/dim]")
        return

    table = Table(title=f"Search Results (page {result.page})")
    table.add_column("Title / Query", style="bold", max_width=50)
    table.add_column("Providers", style="cyan")
    table.add_column("Stars", justify="right")
    table.add_column("Forks", justify="right")
    table.add_column("ID", style="dim")

    for b in result.bundles:
        label = b.title or b.query[:50]
        providers = ", ".join(b.providers_used[:3])
        if len(b.providers_used) > 3:
            providers += f" +{len(b.providers_used) - 3}"
        table.add_row(
            label,
            providers,
            str(b.star_count),
            str(b.fork_count),
            b.id[:8],
        )

    console.print(table)
    console.print(
        f"[dim]Showing {len(result.bundles)} of page {result.page} "
        f"({result.per_page}/page)[/dim]"
    )
