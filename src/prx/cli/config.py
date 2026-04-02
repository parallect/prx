"""prx config -- interactive configuration setup."""

from __future__ import annotations

from pathlib import Path

import platformdirs
import typer
from rich.console import Console

console = Console()


def config_cmd() -> None:
    """Interactive setup for prxhub URL and signing preferences."""
    config_dir = Path(platformdirs.user_config_dir("prx"))
    config_path = config_dir / "config.toml"

    console.print("[bold]prx Configuration[/bold]\n")
    console.print(f"Config file: {config_path}\n")

    if config_path.exists():
        console.print("[dim]Existing config found. Values shown as defaults.[/dim]\n")

    lines = ["# prx CLI configuration\n"]

    # prxhub settings
    prxhub_url = typer.prompt(
        "prxhub URL (leave empty for https://prxhub.com)",
        default="",
        show_default=False,
    )
    if prxhub_url:
        lines.append("[prxhub]")
        lines.append(f'url = "{prxhub_url.rstrip("/")}"')
        lines.append("")

    visibility = typer.prompt(
        "Default bundle visibility (public/unlisted/private)",
        default="public",
    )
    lines.append("[defaults]")
    lines.append(f'visibility = "{visibility}"')
    lines.append("")

    # Signing
    identity = typer.prompt("Signing identity (name or email)", default="", show_default=False)
    if identity:
        lines.append("[signing]")
        lines.append(f'identity = "{identity}"')
        lines.append("auto_sign = true")
        lines.append("")

    config_dir.mkdir(parents=True, exist_ok=True)
    config_path.write_text("\n".join(lines))
    console.print(f"\n[green]Config saved to {config_path}[/green]")
