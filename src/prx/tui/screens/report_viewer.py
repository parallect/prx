"""Report viewer screen: side-by-side provider reports."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Header, Label, ListItem, ListView
from textual.widgets import Markdown as MarkdownWidget


class ReportViewerScreen(Screen):
    """Side-by-side view: provider list on left, report on right."""

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield ListView(id="provider-list")
            yield MarkdownWidget(id="report-content")

    def on_mount(self) -> None:
        bundle = self.app._bundle
        if not bundle:
            return

        provider_list = self.query_one("#provider-list", ListView)
        for provider in bundle.providers:
            provider_list.append(ListItem(Label(provider.name)))

        if bundle.synthesis_md:
            provider_list.append(ListItem(Label("Synthesis")))

        # Show first provider by default
        if bundle.providers:
            self._show_report(bundle.providers[0].name)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        label = event.item.query_one(Label)
        name = str(label.renderable)

        bundle = self.app._bundle
        if name == "Synthesis" and bundle.synthesis_md:
            md = self.query_one("#report-content", MarkdownWidget)
            md.update(bundle.synthesis_md)
        else:
            self._show_report(name)

    def _show_report(self, provider_name: str) -> None:
        bundle = self.app._bundle
        prov_map = {p.name: p for p in bundle.providers}
        if provider_name in prov_map:
            md = self.query_one("#report-content", MarkdownWidget)
            md.update(prov_map[provider_name].report_md)
