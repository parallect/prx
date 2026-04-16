"""prx publish -- upload a .prx bundle to prxhub."""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import typer
from rich.console import Console

console = Console()


def publish_cmd(
    bundle_path: str = typer.Argument(help="Path to .prx bundle"),
    visibility: str = typer.Option("public", "--visibility", help="public, unlisted, or private"),
    tags: str | None = typer.Option(None, "--tags", help="Comma-separated tags"),
    api_url: str | None = typer.Option(
        None, "--api-url", help="Override prxhub API URL"
    ),
) -> None:
    """Upload a .prx bundle to prxhub."""
    asyncio.run(_publish_async(bundle_path, visibility, tags, api_url))


async def _publish_async(
    bundle_path: str, visibility: str, tags: str | None, api_url: str | None
) -> None:
    from prx.api import AuthRequired, PRXHUB_API_URL, publish_bundle
    from prx.auth import load_token

    path = Path(bundle_path)
    if not path.exists():
        console.print(f"[red]File not found: {bundle_path}[/red]")
        raise typer.Exit(1)

    # Basic sanity: .prx bundles are zip-format. Peek first bytes.
    try:
        with open(path, "rb") as f:
            head = f.read(4)
        if not head.startswith(b"PK"):
            console.print(
                f"[red]{path} doesn't look like a valid .prx bundle (missing zip magic).[/red]"
            )
            raise typer.Exit(1)
    except OSError as exc:
        console.print(f"[red]Could not read bundle: {exc}[/red]")
        raise typer.Exit(1)

    token = load_token()
    if token is None:
        console.print("[red]Not logged in. Run `prx login` first.[/red]")
        raise typer.Exit(1)
    if token.is_expired():
        console.print("[red]Your session expired. Run `prx login` again.[/red]")
        raise typer.Exit(1)

    resolved_api_url = api_url or token.api_url or PRXHUB_API_URL
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    console.print(f"[bold]Publishing:[/bold] {path.name}")
    console.print(f"[dim]Visibility: {visibility}[/dim]")
    console.print(f"[dim]Target: {resolved_api_url}[/dim]")
    if tag_list:
        console.print(f"[dim]Tags: {', '.join(tag_list)}[/dim]")

    try:
        result = await publish_bundle(
            path,
            visibility=visibility,
            tags=tag_list,
            api_url=resolved_api_url,
        )
    except AuthRequired as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)
    except httpx.HTTPStatusError as exc:
        _handle_http_error(exc)
        raise typer.Exit(1)
    except Exception as exc:
        console.print(f"[red]Publish failed: {exc}[/red]")
        raise typer.Exit(1)

    console.print("[green]Published![/green]")
    console.print(f"  URL: {result.bundle_url}")


def _handle_http_error(exc: httpx.HTTPStatusError) -> None:
    status = exc.response.status_code
    body: dict = {}
    try:
        body = exc.response.json()
    except Exception:
        pass
    message = body.get("error") or body.get("message") or exc.response.text

    if status == 401:
        console.print("[red]Your session expired. Run `prx login` again.[/red]")
        return
    if status == 403 and (
        "signature" in str(message).lower() or "key" in str(message).lower()
    ):
        console.print(
            "[red]The bundle was signed by a key not registered on prxhub. "
            "Run `prx keys register` to register this key.[/red]"
        )
        return
    console.print(f"[red]Publish failed ({status}): {message}[/red]")
