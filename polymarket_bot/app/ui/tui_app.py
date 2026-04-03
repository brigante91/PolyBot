"""Terminal UI — PolyBot V4 (textual + rich)."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header

from app.state.runtime_state import runtime_state
from app.ui.views import DebugPanel, MarketPanel, MetricsPanel, PortfolioPanel, SystemPanel, TradePanel


class PolyBotTui(App[None]):
    CSS = """
    Screen { layout: vertical; }
    #grid { height: 1fr; }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("p", "pause", "Pause"),
        ("r", "risk", "Risk"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="grid"):
            with Vertical():
                yield MarketPanel()
                yield TradePanel()
                yield MetricsPanel()
            with Vertical():
                yield PortfolioPanel()
                yield SystemPanel()
                yield DebugPanel()
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(1.0, self.refresh_panels)

    def refresh_panels(self) -> None:
        for cls in (
            MarketPanel,
            TradePanel,
            MetricsPanel,
            PortfolioPanel,
            SystemPanel,
            DebugPanel,
        ):
            for w in self.query(cls):
                w.refresh()

    def action_pause(self) -> None:
        runtime_state.paused = not runtime_state.paused
        runtime_state.push_debug(f"pause toggled -> {runtime_state.paused}")

    def action_risk(self) -> None:
        cycle = [0.5, 1.0, 1.5]
        try:
            i = cycle.index(runtime_state.risk_level)
            j = (i + 1) % len(cycle)
        except ValueError:
            j = 1
        runtime_state.risk_level = cycle[j]
        runtime_state.push_debug(f"risk_level -> {runtime_state.risk_level}")


def run_tui() -> None:
    PolyBotTui().run()
