"""Diff viewer screen: side-by-side bundle comparison."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Header, Static


class DiffViewerScreen(Screen):
    """Compare two bundles side by side."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Bundle Diff", classes="panel-title")
        yield DataTable(id="diff-table")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Field", "Bundle A", "Bundle B")
        # Populated when two bundles are loaded for comparison
