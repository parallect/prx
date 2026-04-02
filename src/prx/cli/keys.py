"""prx keys -- key management subcommands."""

from __future__ import annotations

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

    from prx_spec.attestation.keys import DEFAULT_KEY_DIR, PRIVATE_KEY_NAME, PUBLIC_KEY_NAME

    _signing_key, _verify_key, key_id = generate_keypair()
    key_dir = DEFAULT_KEY_DIR
    console.print("[green]Generated Ed25519 signing key:[/green]")
    console.print(f"  Key ID:      {key_id}")
    console.print(f"  Private key: {key_dir / PRIVATE_KEY_NAME}")
    console.print(f"  Public key:  {key_dir / PUBLIC_KEY_NAME}")
    console.print("\nRegister on prxhub:  go to Settings > Signing keys on prxhub")


@keys_app.command("list")
def list_cmd() -> None:
    """List local signing keys."""
    from prx_spec.attestation.keys import DEFAULT_KEY_DIR, get_key_id

    key_dir = DEFAULT_KEY_DIR

    if not key_dir.exists():
        console.print("[yellow]No keys found. Run 'prx keys generate' first.[/yellow]")
        return

    pub_files = sorted(key_dir.glob("*.pub"))
    if not pub_files:
        console.print("[yellow]No keys found.[/yellow]")
        return

    import base64

    from nacl.signing import VerifyKey

    table = Table(title="Signing Keys")
    table.add_column("Key ID")
    table.add_column("Public Key (base64)")
    table.add_column("Private Key")

    for pub_path in pub_files:
        priv_path = pub_path.with_suffix(".key")
        verify_key = VerifyKey(pub_path.read_bytes())
        key_id = get_key_id(verify_key)
        pub_b64 = base64.b64encode(verify_key.encode()).decode()

        table.add_row(
            key_id,
            pub_b64,
            "present" if priv_path.exists() else "[red]missing[/red]",
        )

    console.print(table)


@keys_app.command("register")
def register_cmd() -> None:
    """Register your public key on prxhub."""
    console.print(
        "[yellow]To register a signing key, go to your prxhub Settings page "
        "and paste the public key (base64) from 'prx keys list'.[/yellow]"
    )


@keys_app.command("revoke")
def revoke_cmd(
    key_id: str = typer.Argument(help="Key ID to revoke (prx_pub_...)"),
) -> None:
    """Revoke a public key on prxhub."""
    console.print(
        "[yellow]To revoke a signing key, go to your prxhub Settings page "
        "and click 'Revoke' on the key you want to disable.[/yellow]"
    )
