"""Typer CLI application for the prx format toolkit."""

import typer

from prx.cli.branch import branch_cmd
from prx.cli.clone import clone_cmd
from prx.cli.config import config_cmd
from prx.cli.diff import diff_cmd
from prx.cli.export import export_cmd
from prx.cli.fork import fork_cmd
from prx.cli.keys import keys_app
from prx.cli.list_cmd import list_cmd
from prx.cli.mr import mr_cmd
from prx.cli.publish import publish_cmd
from prx.cli.push import push_cmd
from prx.cli.read import read_cmd
from prx.cli.repo import repo_cmd
from prx.cli.search import search_cmd
from prx.cli.star import star_cmd
from prx.cli.validate import validate_cmd
from prx.cli.verify import verify_cmd

app = typer.Typer(
    name="prx",
    help="The .prx format toolkit — read, validate, merge, and share research bundles.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# Format operations
app.command("read")(read_cmd)
app.command("export")(export_cmd)
app.command("validate")(validate_cmd)
app.command("verify")(verify_cmd)
app.command("diff")(diff_cmd)
app.command("list")(list_cmd)

# Hub operations
app.command("publish")(publish_cmd)
app.command("search")(search_cmd)
app.command("clone")(clone_cmd)
app.command("fork")(fork_cmd)
app.command("star")(star_cmd)
app.command("repo")(repo_cmd)
app.command("branch")(branch_cmd)
app.command("push")(push_cmd)
app.command("mr")(mr_cmd)

# Shared
app.command("config")(config_cmd)
app.add_typer(keys_app, name="keys")


def _open_cmd(
    bundle: str = typer.Argument(help="Path to .prx bundle"),
) -> None:
    """Launch TUI to browse a bundle."""
    try:
        from prx.tui.app import PrxApp

        tui_app = PrxApp(bundle_path=bundle)
        tui_app.run()
    except ImportError:
        typer.echo("TUI requires the 'tui' extra: pip install prx[tui]", err=True)
        raise typer.Exit(1)


app.command("open")(_open_cmd)


def _merge_cmd(
    bundle_a: str = typer.Argument(help="Path to target .prx bundle"),
    bundle_b: str = typer.Argument(help="Path to source .prx bundle to merge in"),
    output: str = typer.Option(None, "--output", "-o", help="Output path for merged bundle"),
    threshold: float = typer.Option(
        0.85, "--threshold", "-t", help="Similarity threshold for claim dedup (0.0-1.0)"
    ),
) -> None:
    """Merge two .prx bundles — dedup claims, detect conflicts, combine sources."""
    from pathlib import Path

    from rich.console import Console
    from rich.table import Table

    from prx_spec.bundle.reader import read_bundle
    from prx_spec.bundle.writer import write_bundle
    from prx_spec.merge import apply_merge, merge_bundles

    console = Console()

    path_a, path_b = Path(bundle_a), Path(bundle_b)
    if not path_a.exists():
        console.print(f"[red]Bundle not found: {bundle_a}[/red]")
        raise typer.Exit(1)
    if not path_b.exists():
        console.print(f"[red]Bundle not found: {bundle_b}[/red]")
        raise typer.Exit(1)

    with console.status("Reading bundles..."):
        target = read_bundle(str(path_a))
        source = read_bundle(str(path_b))

    with console.status("Merging bundles..."):
        result = merge_bundles(target, source, similarity_threshold=threshold)

    table = Table(title="Merge Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Target claims", str(result.stats.total_claims_a))
    table.add_row("Source claims", str(result.stats.total_claims_b))
    table.add_row("Deduplicated", str(result.stats.deduplicated))
    table.add_row("Conflicts", str(result.stats.conflicts_detected))
    table.add_row("Merged total", str(result.stats.merged_total))
    console.print(table)

    if result.conflicts:
        console.print(f"\n[yellow]⚠ {len(result.conflicts)} conflicts detected:[/yellow]")
        for c in result.conflicts:
            console.print(f"  [{c.conflict_type}] {c.claim_a_content[:80]}...")

    merged = apply_merge(target, result)
    out_path = output or str(path_a.with_stem(f"{path_a.stem}_merged"))
    write_bundle(merged, out_path)
    console.print(f"\n[green]✓ Merged bundle written to {out_path}[/green]")


app.command("merge")(_merge_cmd)

# Alias for test compatibility
prx_app = app


if __name__ == "__main__":
    app()
