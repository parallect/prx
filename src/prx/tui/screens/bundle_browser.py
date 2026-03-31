"""Bundle browser screen: file picker showing local .prx files."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Header, Static


class BundleBrowserScreen(Screen):
    """File picker showing local .prx bundles with metadata preview."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Local Bundles", classes="panel-title")
        yield DataTable(id="bundle-table")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("File", "ID", "Query", "Providers", "Created")
        self._load_bundles(table)

    def _load_bundles(self, table: DataTable) -> None:
        from prx_spec import read_bundle

        cwd = Path.cwd()
        for prx_path in sorted(cwd.glob("**/*.prx")):
            try:
                bundle = read_bundle(prx_path)
                m = bundle.manifest
                table.add_row(
                    str(prx_path.relative_to(cwd)),
                    m.id,
                    m.query[:40] + ("..." if len(m.query) > 40 else ""),
                    ", ".join(m.providers_used),
                    str(m.created_at)[:10] if m.created_at else "",
                )
            except Exception:
                table.add_row(str(prx_path.relative_to(cwd)), "error", "", "", "")
