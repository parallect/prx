"""prx diff -- compare two bundles."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()


def diff_cmd(
    bundle_a: str = typer.Argument(help="Path to first .prx bundle"),
    bundle_b: str = typer.Argument(help="Path to second .prx bundle"),
) -> None:
    """Compare two .prx bundles side by side."""
    from prx_spec import read_bundle

    path_a = Path(bundle_a)
    path_b = Path(bundle_b)

    for p in (path_a, path_b):
        if not p.exists():
            console.print(f"[red]File not found: {p}[/red]")
            raise typer.Exit(1)

    a = read_bundle(path_a)
    b = read_bundle(path_b)

    # Metadata comparison
    table = Table(title="Bundle Comparison")
    table.add_column("Field", style="bold")
    table.add_column(path_a.name, style="blue")
    table.add_column(path_b.name, style="green")

    table.add_row("ID", a.manifest.id, b.manifest.id)
    table.add_row("Query", a.manifest.query, b.manifest.query)
    table.add_row(
        "Providers",
        ", ".join(a.manifest.providers_used),
        ", ".join(b.manifest.providers_used),
    )
    table.add_row(
        "Synthesis",
        "yes" if a.manifest.has_synthesis else "no",
        "yes" if b.manifest.has_synthesis else "no",
    )
    table.add_row(
        "Claims",
        "yes" if a.manifest.has_claims else "no",
        "yes" if b.manifest.has_claims else "no",
    )
    table.add_row("Created", str(a.manifest.created_at), str(b.manifest.created_at))

    cost_a = f"${a.manifest.total_cost_usd:.4f}" if a.manifest.total_cost_usd else "n/a"
    cost_b = f"${b.manifest.total_cost_usd:.4f}" if b.manifest.total_cost_usd else "n/a"
    table.add_row("Cost", cost_a, cost_b)

    console.print(table)

    # Provider diff
    providers_a = {p.name for p in a.providers}
    providers_b = {p.name for p in b.providers}

    added = providers_b - providers_a
    removed = providers_a - providers_b

    if added:
        console.print(f"\n[green]+ Providers added in {path_b.name}: {', '.join(added)}[/green]")
    if removed:
        console.print(f"\n[red]- Providers removed in {path_b.name}: {', '.join(removed)}[/red]")

    shared = providers_a & providers_b
    prov_map_a = {p.name: p for p in a.providers}
    prov_map_b = {p.name: p for p in b.providers}
    for name in sorted(shared):
        len_a = len(prov_map_a[name].report_md)
        len_b = len(prov_map_b[name].report_md)
        if len_a != len_b:
            delta = len_b - len_a
            sign = "+" if delta > 0 else ""
            console.print(f"  [dim]{name}: {len_a} -> {len_b} chars ({sign}{delta})[/dim]")
