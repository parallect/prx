"""prx read -- display bundle contents in terminal."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

console = Console()


def read_cmd(
    bundle_path: str = typer.Argument(help="Path to .prx bundle"),
    claims: bool = typer.Option(False, "--claims", help="Show claims table"),
    providers_only: bool = typer.Option(False, "--providers", help="Show provider reports only"),
    synthesis_only: bool = typer.Option(False, "--synthesis", help="Show synthesis report only"),
    meta: bool = typer.Option(False, "--meta", help="Show bundle metadata"),
) -> None:
    """Display bundle contents in the terminal."""
    from prx_spec import read_bundle

    path = Path(bundle_path)
    if not path.exists():
        console.print(f"[red]File not found: {bundle_path}[/red]")
        raise typer.Exit(1)

    bundle = read_bundle(path)
    manifest = bundle.manifest

    if meta or not (claims or providers_only or synthesis_only):
        _show_metadata(manifest)

    if providers_only or not (claims or synthesis_only or meta):
        _show_providers(bundle)

    if synthesis_only or not (claims or providers_only or meta):
        if bundle.synthesis_md:
            console.print(Panel(Markdown(bundle.synthesis_md), title="Synthesis Report"))

    if claims:
        _show_claims(bundle)


def _show_metadata(manifest) -> None:
    """Display bundle metadata."""
    table = Table(title="Bundle Metadata", show_header=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")

    table.add_row("ID", manifest.id)
    table.add_row("Query", manifest.query)
    table.add_row("Spec Version", manifest.spec_version)
    table.add_row("Created", str(manifest.created_at))
    table.add_row("Providers", ", ".join(manifest.providers_used))
    table.add_row("Synthesis", "yes" if manifest.has_synthesis else "no")
    table.add_row("Claims", "yes" if manifest.has_claims else "no")
    table.add_row("Sources", "yes" if manifest.has_sources else "no")
    table.add_row("Evidence Graph", "yes" if manifest.has_evidence_graph else "no")
    if manifest.total_cost_usd:
        table.add_row("Cost", f"${manifest.total_cost_usd:.4f}")
    if manifest.total_duration_seconds:
        table.add_row("Duration", f"{manifest.total_duration_seconds:.1f}s")
    if manifest.producer:
        table.add_row("Producer", f"{manifest.producer.name}/{manifest.producer.version}")

    console.print(table)
    console.print()


def _show_providers(bundle) -> None:
    """Display provider reports."""
    for provider in bundle.providers:
        console.print(Panel(
            Markdown(provider.report_md),
            title=f"Provider: {provider.name}",
            border_style="blue",
        ))


def _show_claims(bundle) -> None:
    """Display claims table."""
    if not bundle.claims or not bundle.claims.claims:
        console.print("[yellow]No claims in this bundle.[/yellow]")
        return

    table = Table(title="Claims")
    table.add_column("#", style="dim")
    table.add_column("Claim")
    table.add_column("Supporting", style="green")
    table.add_column("Contradicting", style="red")

    for i, claim in enumerate(bundle.claims.claims, 1):
        table.add_row(
            str(i),
            claim.content,
            ", ".join(claim.providers_supporting),
            ", ".join(claim.providers_contradicting),
        )

    console.print(table)
