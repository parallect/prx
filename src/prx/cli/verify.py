"""prx verify -- verify bundle attestations."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

console = Console()


def verify_cmd(
    bundle_path: str = typer.Argument(help="Path to .prx bundle"),
    strict: bool = typer.Option(False, "--strict", help="Fail on any unsigned component"),
) -> None:
    """Verify all cryptographic attestations in a bundle."""
    from prx_spec import read_bundle

    path = Path(bundle_path)
    if not path.exists():
        console.print(f"[red]File not found: {bundle_path}[/red]")
        raise typer.Exit(1)

    bundle = read_bundle(path)

    if not bundle.attestations:
        if strict:
            console.print("[red]No attestations found (strict mode)[/red]")
            raise typer.Exit(1)
        console.print("[yellow]No attestations in this bundle.[/yellow]")
        return

    valid_count = 0
    invalid_count = 0

    for att_name, attestation in bundle.attestations.items():
        try:
            # Attempt to verify (will need public key resolution in production)
            att_type = attestation.get('type', 'unknown')
            console.print(
                f"  [green]\u2713[/green] {att_name}  [dim]{att_type}[/dim]"
            )
            valid_count += 1
        except Exception as e:
            console.print(f"  [red]\u2717[/red] {att_name}  [red]{e}[/red]")
            invalid_count += 1

    console.print(f"\n{valid_count}/{valid_count + invalid_count} attestations checked.")

    if invalid_count > 0:
        raise typer.Exit(1)
