"""prx login / logout -- device-code OAuth against prxhub."""

from __future__ import annotations

import time

import httpx
import typer
from rich.console import Console

from prx.auth import (
    AuthError,
    DEFAULT_API_URL,
    StoredToken,
    auth_path,
    clear_token,
    load_token,
    open_browser,
    poll_for_token,
    save_token,
    start_device_flow,
)

console = Console()


def login_cmd(
    api_url: str = typer.Option(
        DEFAULT_API_URL, "--api-url", help="prxhub API base URL (self-hosted)"
    ),
    with_parallect: bool = typer.Option(
        False, "--with-parallect", help="Federated login via parallect.ai (server support required)"
    ),
) -> None:
    """Log in to prxhub using the device-code flow."""
    if with_parallect:
        raise NotImplementedError(
            "--with-parallect requires server support; see CLI-AUTH-CONTRACT.md"
        )

    try:
        with httpx.Client() as http:
            try:
                start = start_device_flow(api_url, http)
            except httpx.HTTPError as exc:
                console.print(f"[red]Could not reach {api_url}: {exc}[/red]")
                raise typer.Exit(1)

            device_code = start["device_code"]
            user_code = start.get("user_code", "")
            verification_uri_complete = start.get(
                "verification_uri_complete",
                start.get("verification_uri", f"{api_url}/cli/device"),
            )
            interval = int(start.get("interval", 5))

            console.print(
                f"[cyan]-> Opening {verification_uri_complete} in your browser...[/cyan]"
            )
            console.print(
                f"  (if that doesn't open, visit the URL manually and enter code: "
                f"[bold]{user_code}[/bold])"
            )
            open_browser(verification_uri_complete)
            console.print("[dim]-> Waiting for approval...[/dim]")

            try:
                result = poll_for_token(api_url, device_code, interval, http)
            except AuthError as exc:
                console.print(f"[red]{exc}[/red]")
                raise typer.Exit(1)

        expires_in = int(result.get("expires_in", 60 * 60 * 24 * 30))
        token = StoredToken(
            access_token=result["access_token"],
            token_type=result.get("token_type", "Bearer"),
            expires_at=time.time() + expires_in,
            scope=result.get("scope", ""),
            api_url=api_url,
            username=result.get("username"),
        )
        path = save_token(token)
        who = token.username or "your account"
        console.print(f"[green]Authenticated as {who}[/green]")
        console.print(f"[dim]Token stored at {path}[/dim]")
    except typer.Exit:
        raise
    except Exception as exc:  # defensive — unexpected failures
        console.print(f"[red]Login failed: {exc}[/red]")
        raise typer.Exit(1)


def logout_cmd() -> None:
    """Remove the locally stored prxhub auth token."""
    removed = clear_token()
    if removed:
        console.print("[green]Logged out.[/green]")
    else:
        console.print("[yellow]Not logged in.[/yellow]")


def whoami_cmd() -> None:
    """Show the currently logged-in user, if any."""
    token = load_token()
    if token is None:
        console.print("[yellow]Not logged in. Run `prx login` first.[/yellow]")
        raise typer.Exit(1)
    who = token.username or "(unknown user)"
    console.print(f"[green]{who}[/green] via {token.api_url}")
    console.print(f"[dim]Token file: {auth_path()}[/dim]")
    if token.is_expired():
        console.print("[yellow]Token is expired. Run `prx login` again.[/yellow]")
