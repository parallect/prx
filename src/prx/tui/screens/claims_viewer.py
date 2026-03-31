"""Claims viewer screen: DataTable of extracted claims."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Header, Static


class ClaimsViewerScreen(Screen):
    """Claims table with sorting and filtering."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Claims", classes="panel-title")
        yield DataTable(id="claims-table")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("#", "Claim", "Supporting", "Contradicting", "Category")

        bundle = self.app._bundle
        if not bundle or not bundle.claims:
            return

        for i, claim in enumerate(bundle.claims, 1):
            table.add_row(
                str(i),
                claim.get("content", "")[:60],
                ", ".join(claim.get("providers_supporting", [])),
                ", ".join(claim.get("providers_contradicting", [])),
                claim.get("category", ""),
            )
