"""prx validate -- validate a .prx bundle."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

console = Console()


def validate_cmd(
    bundle_path: str = typer.Argument(help="Path to .prx bundle"),
    level: int = typer.Option(2, "--level", "-l", help="Validation level (0, 1, or 2)"),
) -> None:
    """Validate a .prx bundle at the specified level."""
    from prx_spec import validate_archive

    path = Path(bundle_path)
    if not path.exists():
        console.print(f"[red]File not found: {bundle_path}[/red]")
        raise typer.Exit(1)

    result = validate_archive(path, level=level)

    all_passed = True
    for key, level_result in sorted(result.levels.items()):
        lvl_num = int(key.replace("l", ""))
        if lvl_num > level:
            continue

        status = "[green]PASS[/green]" if level_result.passed else "[red]FAIL[/red]"
        console.print(f"  L{lvl_num}: {status}")

        if not level_result.passed:
            all_passed = False

        for error in level_result.errors:
            console.print(f"    [red]error:[/red] {error}")
        for warning in level_result.warnings:
            console.print(f"    [yellow]warning:[/yellow] {warning}")

    if all_passed:
        console.print(f"\n[green]Bundle is valid up to L{result.highest_passing_level}[/green]")
    else:
        console.print("\n[red]Bundle validation failed[/red]")
        raise typer.Exit(1)
