"""prx list -- list local bundles."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()


def list_cmd(
    directory: str | None = typer.Option(
        ".", "--dir", "-d", help="Directory to search for .prx files"
    ),
) -> None:
    """List local .prx bundles."""
    from prx_spec import read_bundle

    search_dir = Path(directory)
    if not search_dir.is_dir():
        console.print(f"[red]Not a directory: {directory}[/red]")
        raise typer.Exit(1)

    prx_files = sorted(search_dir.glob("**/*.prx"))

    if not prx_files:
        console.print("[yellow]No .prx bundles found.[/yellow]")
        return

    table = Table(title=f"Bundles in {search_dir}")
    table.add_column("File", style="blue")
    table.add_column("ID", style="dim")
    table.add_column("Query")
    table.add_column("Providers")
    table.add_column("Synth")
    table.add_column("Created")

    for prx_path in prx_files:
        try:
            bundle = read_bundle(prx_path)
            m = bundle.manifest
            table.add_row(
                str(prx_path.relative_to(search_dir)),
                m.id,
                m.query[:50] + ("..." if len(m.query) > 50 else ""),
                ", ".join(m.providers_used),
                "yes" if m.has_synthesis else "no",
                str(m.created_at)[:10] if m.created_at else "",
            )
        except Exception as e:
            rel = str(prx_path.relative_to(search_dir))
            table.add_row(rel, "", f"[red]Error: {e}[/red]", "", "", "")

    console.print(table)
