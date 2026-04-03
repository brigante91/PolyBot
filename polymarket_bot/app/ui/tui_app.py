"""Terminal UI — PolyBot production control room (Textual + Rich)."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header

from app.state.runtime_state import runtime_state
from app.ui.views import (
    DebugPanel,
    DecisionTracePanel,
    MarketPanel,
    MetricsPanel,
    OrderBlotterPanel,
    PortfolioPanel,
    SystemPanel,
    TradePanel,
)


class PolyBotTui(App[None]):
    CSS = """
    Screen { layout: vertical; }
    #grid { height: 1fr; }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("p", "pause", "Pause"),
        ("r", "risk", "Risk"),
        ("k", "soft_kill", "SoftKill"),
        ("f", "flatten_hint", "Flatten"),
        ("h", "help_keys", "Help"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="grid"):
            with Vertical():
                yield MarketPanel(id="radar")
                yield DecisionTracePanel()
                yield OrderBlotterPanel()
            with Vertical():
                yield TradePanel()
                yield PortfolioPanel()
                yield MetricsPanel()
                yield SystemPanel()
                yield DebugPanel()
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(1.0, self.refresh_panels)

    def refresh_panels(self) -> None:
        for cls in (
            MarketPanel,
            DecisionTracePanel,
            OrderBlotterPanel,
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
        runtime_state.push_debug(f"pause -> {runtime_state.paused}")

    def action_risk(self) -> None:
        cycle = [0.5, 1.0, 1.5]
        try:
            i = cycle.index(runtime_state.risk_level)
            j = (i + 1) % len(cycle)
        except ValueError:
            j = 1
        runtime_state.risk_level = cycle[j]
        runtime_state.push_debug(f"risk_level -> {runtime_state.risk_level}")

    def action_soft_kill(self) -> None:
        runtime_state.soft_kill = not runtime_state.soft_kill
        runtime_state.push_debug(f"soft_kill -> {runtime_state.soft_kill}")

    def action_flatten_hint(self) -> None:
        runtime_state.push_debug("flatten: use polybot cancel-all when live; positions close manually")

    def action_help_keys(self) -> None:
        runtime_state.push_debug(
            "keys: q quit | p pause | r risk | k soft_kill | f flatten hint | h help"
        )


def run_tui() -> None:
    PolyBotTui().run()
