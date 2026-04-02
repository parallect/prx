"""Diff viewer screen: side-by-side bundle comparison."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

if TYPE_CHECKING:
    from prx_spec import BundleData


class DiffViewerScreen(Screen):
    """Compare two bundles side by side."""

    def __init__(
        self,
        bundle_a: BundleData | None = None,
        bundle_b: BundleData | None = None,
    ) -> None:
        super().__init__()
        self.bundle_a = bundle_a
        self.bundle_b = bundle_b

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Bundle Diff", classes="panel-title")
        yield DataTable(id="diff-table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Field", "Bundle A", "Bundle B")

        if not self.bundle_a or not self.bundle_b:
            table.add_row("", "No bundles loaded", "Load two bundles to compare")
            return

        self._populate_diff(table)

    def _populate_diff(self, table: DataTable) -> None:
        a = self.bundle_a
        b = self.bundle_b
        assert a is not None and b is not None

        ma, mb = a.manifest, b.manifest

        # Metadata comparison
        table.add_row("ID", ma.id, mb.id)
        table.add_row("Query", _trunc(ma.query, 50), _trunc(mb.query, 50))
        table.add_row("Created", str(ma.created_at or "")[:19], str(mb.created_at or "")[:19])
        table.add_row(
            "Producer",
            f"{ma.producer.name} {ma.producer.version}" if ma.producer else "",
            f"{mb.producer.name} {mb.producer.version}" if mb.producer else "",
        )

        # Provider comparison
        prov_a = set(ma.providers_used)
        prov_b = set(mb.providers_used)
        table.add_row("Providers", ", ".join(sorted(prov_a)), ", ".join(sorted(prov_b)))

        only_a = prov_a - prov_b
        only_b = prov_b - prov_a
        if only_a or only_b:
            table.add_row(
                "  Unique",
                ", ".join(sorted(only_a)) if only_a else "—",
                ", ".join(sorted(only_b)) if only_b else "—",
            )

        # Synthesis
        table.add_row(
            "Synthesis",
            "yes" if ma.has_synthesis else "no",
            "yes" if mb.has_synthesis else "no",
        )

        # Cost
        table.add_row(
            "Cost",
            f"${ma.total_cost_usd:.4f}" if ma.total_cost_usd else "—",
            f"${mb.total_cost_usd:.4f}" if mb.total_cost_usd else "—",
        )

        # Duration
        table.add_row(
            "Duration",
            f"{ma.total_duration_seconds:.1f}s" if ma.total_duration_seconds else "—",
            f"{mb.total_duration_seconds:.1f}s" if mb.total_duration_seconds else "—",
        )

        # Claims
        claims_a = len(a.claims.claims) if a.claims else 0
        claims_b = len(b.claims.claims) if b.claims else 0
        table.add_row("Claims", str(claims_a), str(claims_b))

        # Sources
        sources_a = len(a.sources.sources) if a.sources else 0
        sources_b = len(b.sources.sources) if b.sources else 0
        table.add_row("Sources", str(sources_a), str(sources_b))

        # Attestations
        table.add_row("Attestations", str(len(a.attestations)), str(len(b.attestations)))

        # Report lengths
        for provider_a in a.providers:
            match_b = next((p for p in b.providers if p.name == provider_a.name), None)
            len_a = len(provider_a.report_md)
            len_b = len(match_b.report_md) if match_b else 0
            table.add_row(
                f"  {provider_a.name} report",
                f"{len_a:,} chars",
                f"{len_b:,} chars" if match_b else "—",
            )

        # Providers only in B
        for provider_b in b.providers:
            if not any(p.name == provider_b.name for p in a.providers):
                table.add_row(
                    f"  {provider_b.name} report",
                    "—",
                    f"{len(provider_b.report_md):,} chars",
                )


def _trunc(text: str, length: int) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= length:
        return text
    return text[:length - 3] + "..."
