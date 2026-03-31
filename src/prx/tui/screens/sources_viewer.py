"""Sources viewer screen: source registry browser."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Header, Static


class SourcesViewerScreen(Screen):
    """Source registry browser with quality indicators."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Sources", classes="panel-title")
        yield DataTable(id="sources-table")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("URL", "Title", "Quality", "Providers", "Citations")

        bundle = self.app._bundle
        if not bundle or not bundle.sources:
            return

        for source in bundle.sources:
            table.add_row(
                source.get("url", "")[:40],
                source.get("title", "")[:30],
                source.get("quality_tier", ""),
                ", ".join(source.get("cited_by_providers", [])),
                str(source.get("citation_count", 0)),
            )
