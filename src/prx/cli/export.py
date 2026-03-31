"""prx export -- export bundle to other formats."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

console = Console()


def export_cmd(
    bundle_path: str = typer.Argument(help="Path to .prx bundle"),
    format: str = typer.Option("markdown", "--format", "-f", help="Output format: markdown, json"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path"),
) -> None:
    """Export bundle to other formats (markdown, json)."""

    from prx_spec import read_bundle

    path = Path(bundle_path)
    if not path.exists():
        console.print(f"[red]File not found: {bundle_path}[/red]")
        raise typer.Exit(1)

    bundle = read_bundle(path)

    if format == "markdown":
        content = _export_markdown(bundle)
    elif format == "json":
        content = _export_json(bundle)
    else:
        console.print(f"[red]Unknown format: {format}. Supported: markdown, json[/red]")
        raise typer.Exit(1)

    if output:
        Path(output).write_text(content)
        console.print(f"[green]Exported to {output}[/green]")
    else:
        console.print(content)


def _export_markdown(bundle) -> str:
    """Export bundle as a single markdown document."""
    parts = [f"# {bundle.manifest.query}\n"]

    if bundle.synthesis_md:
        parts.append("## Synthesis\n")
        parts.append(bundle.synthesis_md)
        parts.append("\n")

    for provider in bundle.providers:
        parts.append(f"## {provider.name}\n")
        parts.append(provider.report_md)
        parts.append("\n")

    return "\n".join(parts)


def _export_json(bundle) -> str:
    """Export bundle metadata and content as JSON."""
    import json

    data = {
        "manifest": bundle.manifest.model_dump(mode="json"),
        "query": bundle.query_md,
        "providers": {
            p.name: {
                "report": p.report_md,
                "citations": [c.model_dump(mode="json") for c in p.citations] if p.citations else None,
                "meta": p.meta.model_dump(mode="json") if p.meta else None,
            }
            for p in bundle.providers
        },
    }
    if bundle.synthesis_md:
        data["synthesis"] = bundle.synthesis_md

    return json.dumps(data, indent=2)
