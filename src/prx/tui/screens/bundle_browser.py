"""Bundle browser screen: file picker showing local .prx files."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static


class BundleBrowserScreen(Screen):
    """File picker showing local .prx bundles with metadata preview."""

    BINDINGS = [
        Binding("enter", "select_bundle", "Open Bundle"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._row_paths: dict[str, Path] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Local Bundles", classes="panel-title")
        yield DataTable(id="bundle-table", cursor_type="row")
        yield Footer()

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
                row_key = table.add_row(
                    str(prx_path.relative_to(cwd)),
                    m.id,
                    m.query[:40] + ("..." if len(m.query) > 40 else ""),
                    ", ".join(m.providers_used),
                    str(m.created_at)[:10] if m.created_at else "",
                )
                self._row_paths[str(row_key)] = prx_path
            except Exception:
                table.add_row(str(prx_path.relative_to(cwd)), "error", "", "", "")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self._open_bundle(event.row_key)

    def action_select_bundle(self) -> None:
        table = self.query_one(DataTable)
        if table.row_count > 0:
            self._open_bundle(table.cursor_row)

    def _open_bundle(self, row_key) -> None:
        path = self._row_paths.get(str(row_key))
        if not path:
            return
        self.app._load_bundle(str(path))
