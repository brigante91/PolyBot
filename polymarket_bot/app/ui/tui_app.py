"""Terminal UI — PolyBot production control room (Textual + Rich)."""

from __future__ import annotations

import threading

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Static

from app.config import RunMode, load_settings
from app.runtime import run_multi_market
from app.runtime_control import clear_orchestrator_stop, request_orchestrator_stop
from app.state.runtime_state import runtime_state
from app.ui.views import (
    DebugPanel,
    DecisionTracePanel,
    MarketPanel,
    MetricsPanel,
    OrderBlotterPanel,
    PortfolioPanel,
    RiskPanel,
    SystemPanel,
    TradePanel,
)


class PolyBotTui(App[None]):
    CSS = """
    Screen { layout: vertical; }
    #grid { height: 1fr; }
    #launcher_bar { height: auto; min-height: 3; padding: 0 1; background: $surface; }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("p", "pause", "Pause"),
        ("r", "risk", "Risk"),
        ("k", "soft_kill", "SoftKill"),
        ("f", "flatten_hint", "Flatten"),
        ("h", "help_keys", "Help"),
    ]

    def __init__(self, *, with_launcher: bool = False) -> None:
        super().__init__()
        self._with_launcher = with_launcher

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        if self._with_launcher:
            with Horizontal(id="launcher_bar"):
                yield Static(" Runtime ")
                yield Button("Test", id="btn-test", variant="primary")
                yield Button("Dry-run", id="btn-dry")
                yield Button("Paper", id="btn-paper")
                yield Button("Live", id="btn-live")
        with Horizontal(id="grid"):
            with Vertical():
                yield MarketPanel(id="radar")
                yield DecisionTracePanel()
                yield OrderBlotterPanel()
            with Vertical():
                yield TradePanel()
                yield PortfolioPanel()
                yield RiskPanel()
                yield MetricsPanel()
                yield SystemPanel()
                yield DebugPanel()
        yield Footer()

    def on_mount(self) -> None:
        if self._with_launcher:
            g = self.query_one("#grid")
            g.display = False
        self.set_interval(1.0, self.refresh_panels)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if not self._with_launcher:
            return
        mode_map = {
            "btn-test": RunMode.TEST,
            "btn-dry": RunMode.DRY_RUN,
            "btn-paper": RunMode.PAPER,
            "btn-live": RunMode.LIVE,
        }
        mode = mode_map.get(event.button.id or "")
        if not mode:
            return
        clear_orchestrator_stop()
        settings = load_settings()
        max_c = 1 if mode == RunMode.TEST else None

        def _run() -> None:
            run_multi_market(settings, mode=mode, max_cycles=max_c)

        threading.Thread(target=_run, name="polybot-orchestrator", daemon=True).start()
        self.query_one("#launcher_bar").display = False
        self.query_one("#grid").display = True
        runtime_state.push_debug(f"orchestrator started mode={mode.value}")

    def refresh_panels(self) -> None:
        for cls in (
            MarketPanel,
            DecisionTracePanel,
            OrderBlotterPanel,
            TradePanel,
            MetricsPanel,
            PortfolioPanel,
            RiskPanel,
            SystemPanel,
            DebugPanel,
        ):
            for w in self.query(cls):
                w.refresh()

    def action_quit(self) -> None:
        request_orchestrator_stop()
        self.exit()

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
        runtime_state.push_debug("flatten: polybot flatten-all (live) or cancel-all")

    def action_help_keys(self) -> None:
        runtime_state.push_debug(
            "keys: q quit | p pause | r risk | k soft_kill | f flatten hint | h help"
        )


def run_tui() -> None:
    """Control room only (no launcher) — for `polybot tui` CLI."""
    PolyBotTui(with_launcher=False).run()
