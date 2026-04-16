"""prx keys -- key management subcommands.

Keys are stored in the same location as the parallect CLI —
``prx_spec.attestation.keys.DEFAULT_KEY_DIR`` (``~/.config/parallect/keys/``).
This is the single source of truth so bundles signed by parallect can be
registered and used by prx without migration.
"""

from __future__ import annotations

import asyncio
import base64
import socket
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()

keys_app = typer.Typer(help="Manage Ed25519 signing keys.", no_args_is_help=True)


def _key_dir() -> Path:
    """Canonical, shared-with-parallect key directory."""
    from prx_spec.attestation.keys import DEFAULT_KEY_DIR

    return DEFAULT_KEY_DIR


def _b64url_nopad(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def public_key_jwk(public_key_bytes: bytes) -> dict:
    """Build an RFC 8037 Ed25519 public-key JWK from raw 32-byte public key."""
    return {
        "kty": "OKP",
        "crv": "Ed25519",
        "x": _b64url_nopad(public_key_bytes),
    }


@keys_app.command("generate")
def generate_cmd(
    label: str = typer.Option(
        "default", "--label", help="Display label for the key (metadata only)"
    ),
) -> None:
    """Generate a new Ed25519 signing keypair."""
    from prx_spec import generate_keypair
    from prx_spec.errors import KeyManagementError

    try:
        signing_key, verify_key, key_id = generate_keypair()
    except KeyManagementError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)
    except ValueError as exc:  # unexpected, but don't crash
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    key_dir = _key_dir()
    console.print("[green]Generated Ed25519 signing key:[/green]")
    console.print(f"  Key ID:      {key_id}")
    console.print(f"  Label:       {label}")
    console.print(f"  Private key: {key_dir / 'prx_signing.key'}")
    console.print(f"  Public key:  {key_dir / 'prx_signing.pub'}")
    console.print("\nRegister on prxhub.com:  [bold]prx keys register[/bold]")


@keys_app.command("list")
def list_cmd() -> None:
    """List local signing keys."""
    from prx_spec.attestation.keys import PRIVATE_KEY_NAME, PUBLIC_KEY_NAME, get_key_id
    from nacl.signing import VerifyKey

    key_dir = _key_dir()
    public_path = key_dir / PUBLIC_KEY_NAME
    private_path = key_dir / PRIVATE_KEY_NAME

    if not public_path.exists():
        console.print(
            f"[yellow]No keys found at {key_dir}. "
            f"Run 'prx keys generate' first.[/yellow]"
        )
        return

    pub_bytes = public_path.read_bytes()
    key_id = get_key_id(VerifyKey(pub_bytes))

    table = Table(title="Signing Keys")
    table.add_column("Key ID")
    table.add_column("Public Key File")
    table.add_column("Private Key")

    table.add_row(
        key_id,
        str(public_path),
        "present" if private_path.exists() else "[red]missing[/red]",
    )

    console.print(table)


@keys_app.command("register")
def register_cmd(
    label: str | None = typer.Option(
        None, "--label", help="Human-readable label shown on prxhub (default: <hostname> via prx CLI)"
    ),
    api_url: str | None = typer.Option(
        None, "--api-url", help="Override prxhub API URL"
    ),
) -> None:
    """Register your public key on prxhub."""
    from prx.api import AuthRequired, PRXHUB_API_URL, register_public_key
    from prx.auth import load_token
    from prx_spec.attestation.keys import PUBLIC_KEY_NAME, get_key_id
    from nacl.signing import VerifyKey

    token = load_token()
    if token is None:
        console.print("[red]Not logged in. Run `prx login` first.[/red]")
        raise typer.Exit(1)
    if token.is_expired():
        console.print("[red]Your session expired. Run `prx login` again.[/red]")
        raise typer.Exit(1)

    public_path = _key_dir() / PUBLIC_KEY_NAME
    if not public_path.exists():
        console.print(
            f"[red]No public key found at {public_path}. "
            f"Run `prx keys generate` first.[/red]"
        )
        raise typer.Exit(1)

    pub_bytes = public_path.read_bytes()
    key_id = get_key_id(VerifyKey(pub_bytes))
    jwk = public_key_jwk(pub_bytes)
    registration_label = label or f"{socket.gethostname()} via prx CLI"

    resolved_api_url = api_url or token.api_url or PRXHUB_API_URL
    console.print(f"[dim]Registering {key_id} on {resolved_api_url}...[/dim]")

    try:
        result = asyncio.run(
            register_public_key(
                public_key_jwk=jwk,
                key_id=key_id,
                label=registration_label,
                api_url=resolved_api_url,
            )
        )
    except AuthRequired as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)
    except Exception as exc:
        console.print(f"[red]Key registration failed: {exc}[/red]")
        raise typer.Exit(1)

    where = result.url or f"{resolved_api_url}/settings/keys"
    who = token.username or "your account"
    console.print(f"[green]Key registered on {who} -> {where}[/green]")


@keys_app.command("revoke")
def revoke_cmd(
    key_id: str = typer.Argument(help="Key ID to revoke (prx_pub_...)"),
    api_url: str | None = typer.Option(None, "--api-url", help="Override prxhub API URL"),
) -> None:
    """Revoke a public key on prxhub."""
    from prx.api import AuthRequired, PRXHUB_API_URL, revoke_public_key
    from prx.auth import load_token

    token = load_token()
    if token is None:
        console.print("[red]Not logged in. Run `prx login` first.[/red]")
        raise typer.Exit(1)
    if token.is_expired():
        console.print("[red]Your session expired. Run `prx login` again.[/red]")
        raise typer.Exit(1)

    resolved_api_url = api_url or token.api_url or PRXHUB_API_URL

    try:
        asyncio.run(revoke_public_key(key_id=key_id, api_url=resolved_api_url))
    except AuthRequired as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)
    except Exception as exc:
        console.print(f"[red]Revoke failed: {exc}[/red]")
        raise typer.Exit(1)

    console.print(f"[green]Revoked {key_id}[/green]")
