"""Main Textual application for prx."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from prx.tui.screens.bundle_browser import BundleBrowserScreen
from prx.tui.screens.claims_viewer import ClaimsViewerScreen
from prx.tui.screens.diff_viewer import DiffViewerScreen
from prx.tui.screens.report_viewer import ReportViewerScreen
from prx.tui.screens.sources_viewer import SourcesViewerScreen


class PrxApp(App):
    """Terminal UI for browsing .prx bundles."""

    TITLE = "prx"
    CSS_PATH = "app.tcss"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("b", "browser", "Browser"),
        Binding("r", "report", "Reports"),
        Binding("c", "claims_view", "Claims"),
        Binding("s", "sources", "Sources"),
        Binding("d", "diff", "Diff"),
    ]

    SCREENS = {
        "browser": BundleBrowserScreen,
        "viewer": ReportViewerScreen,
        "claims": ClaimsViewerScreen,
        "sources": SourcesViewerScreen,
    }

    def __init__(self, bundle_path: str | None = None) -> None:
        super().__init__()
        self.bundle_path = bundle_path
        self._bundle = None
        self._bundle_b = None  # Second bundle for diff

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        if self.bundle_path:
            self._load_bundle(self.bundle_path)
        else:
            self.push_screen("browser")

    def _load_bundle(self, path: str) -> None:
        from prx_spec import read_bundle

        try:
            self._bundle = read_bundle(Path(path))
            self.push_screen("viewer")
        except Exception as e:
            self.notify(f"Failed to load bundle: {e}", severity="error")
            self.push_screen("browser")

    def action_browser(self) -> None:
        self.push_screen("browser")

    def action_report(self) -> None:
        if self._bundle:
            self.push_screen("viewer")

    def action_claims_view(self) -> None:
        if self._bundle:
            self.push_screen("claims")

    def action_sources(self) -> None:
        if self._bundle:
            self.push_screen("sources")

    def action_diff(self) -> None:
        if self._bundle:
            screen = DiffViewerScreen(
                bundle_a=self._bundle,
                bundle_b=self._bundle_b,
            )
            self.push_screen(screen)
