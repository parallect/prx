"""prx keys -- key management subcommands."""

from __future__ import annotations

from pathlib import Path

import platformdirs
import typer
from rich.console import Console
from rich.table import Table

console = Console()

keys_app = typer.Typer(help="Manage Ed25519 signing keys.", no_args_is_help=True)


@keys_app.command("generate")
def generate_cmd(
    label: str = typer.Option("default", "--label", help="Key label (e.g. 'work', 'personal')"),
) -> None:
    """Generate a new Ed25519 signing keypair."""
    from prx_spec import generate_keypair

    keypair = generate_keypair()
    console.print("[green]Generated Ed25519 signing key:[/green]")
    console.print(f"  Key ID:      {keypair.key_id}")
    console.print(f"  Private key: {keypair.private_path}")
    console.print(f"  Public key:  {keypair.public_path}")
    console.print("\nRegister on prxhub.com:  [bold]prx keys register[/bold]")


@keys_app.command("list")
def list_cmd() -> None:
    """List local signing keys."""
    key_dir = Path(platformdirs.user_config_dir("prx")) / "keys"

    if not key_dir.exists():
        console.print("[yellow]No keys found. Run 'prx keys generate' first.[/yellow]")
        return

    pub_files = sorted(key_dir.glob("*.pub"))
    if not pub_files:
        console.print("[yellow]No keys found.[/yellow]")
        return

    table = Table(title="Signing Keys")
    table.add_column("Key ID")
    table.add_column("Public Key File")
    table.add_column("Private Key")

    for pub_path in pub_files:
        priv_path = pub_path.with_suffix(".key")
        key_bytes = pub_path.read_bytes()
        key_id = f"prx_pub_{key_bytes.hex()[:16]}"

        table.add_row(
            key_id,
            str(pub_path),
            "present" if priv_path.exists() else "[red]missing[/red]",
        )

    console.print(table)


@keys_app.command("register")
def register_cmd(
    api_key: str = typer.Option(None, "--api-key", help="prxhub API key"),
) -> None:
    """Register your public key on prxhub.com."""
    console.print(
        "[yellow]Key registration requires a prxhub.com account. "
        "This feature is available once prxhub.com is live.[/yellow]"
    )


@keys_app.command("revoke")
def revoke_cmd(
    key_id: str = typer.Argument(help="Key ID to revoke (prx_pub_...)"),
    api_key: str = typer.Option(None, "--api-key", help="prxhub API key"),
) -> None:
    """Revoke a public key on prxhub.com."""
    console.print(
        "[yellow]Key revocation requires a prxhub.com account. "
        "This feature is available once prxhub.com is live.[/yellow]"
    )
