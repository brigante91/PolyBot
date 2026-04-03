"""
PolyBot TUI — launcher + control room.

This version adds:
- explicit startup launcher
- test / dry-run / paper / live selection
- doctor and replay shortcuts
- live confirmation gate
"""

from __future__ import annotations

import threading
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, Static

from app.cli_health import run_doctor
from app.cli_live import validate_live_config
from app.config import RunMode, load_settings
from app.data.replay_engine import replay_file
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
    TimelinePanel,
    TradePanel,
)


class LiveConfirmScreen(ModalScreen[bool]):
    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("⚠️ LIVE MODE ENABLED"),
            Label('Type: I UNDERSTAND'),
            Input(placeholder="I UNDERSTAND", id="confirm_input"),
            Horizontal(
                Button("Cancel", id="cancel"),
                Button("Start Live", id="confirm", variant="error"),
            ),
            id="live_confirm",
        )

    @on(Button.Pressed, "#cancel")
    def cancel(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, "#confirm")
    def confirm(self) -> None:
        value = self.query_one("#confirm_input", Input).value.strip()
        self.dismiss(value == "I UNDERSTAND")


class PolyBotTui(App[None]):
    CSS = """
    Screen { layout: vertical; }
    #grid { height: 1fr; }
    #launcher_bar { height: auto; min-height: 3; padding: 0 1; background: $surface; }
    #status_bar { height: auto; padding: 0 1; background: $boost; }
    #live_confirm { width: 60; height: auto; padding: 1 2; background: $surface; border: round $error; }
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
        self._running_mode: str | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        if self._with_launcher:
            with Horizontal(id="launcher_bar"):
                yield Static(" Runtime ")
                yield Button("Test", id="btn-test", variant="primary")
                yield Button("Dry-run", id="btn-dry")
                yield Button("Paper", id="btn-paper")
                yield Button("Live", id="btn-live", variant="error")
                yield Button("Doctor", id="btn-doctor")
                yield Button("Replay", id="btn-replay")
        yield Static("Idle", id="status_bar")
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
                yield TimelinePanel()
                yield SystemPanel()
                yield DebugPanel()
        yield Footer()

    def on_mount(self) -> None:
        if self._with_launcher:
            self.query_one("#grid").display = False
        self.set_interval(1.0, self.refresh_panels)
        self._set_status("Idle")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if not self._with_launcher:
            return

        if event.button.id == "btn-doctor":
            self._run_doctor()
            return

        if event.button.id == "btn-replay":
            self._run_replay()
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

        if mode == RunMode.LIVE:
            ok = await self.push_screen_wait(LiveConfirmScreen())
            if not ok:
                runtime_state.push_debug("live launch cancelled")
                self._set_status("Live launch cancelled")
                return
            st = load_settings()
            live_ok, live_msg = validate_live_config(st)
            if not live_ok:
                runtime_state.push_debug(f"live blocked: {live_msg}")
                self._set_status(f"Live blocked: {live_msg}")
                return

        self._start_mode(mode)

    def _start_mode(self, mode: RunMode) -> None:
        clear_orchestrator_stop()
        settings = load_settings()
        max_c = 1 if mode == RunMode.TEST else None

        def _run() -> None:
            run_multi_market(settings, mode=mode, max_cycles=max_c)

        threading.Thread(target=_run, name="polybot-orchestrator", daemon=True).start()
        if self._with_launcher:
            self.query_one("#launcher_bar").display = False
            self.query_one("#grid").display = True
        self._running_mode = mode.value
        self._set_status(f"Running mode={mode.value}")
        runtime_state.push_debug(f"orchestrator started mode={mode.value}")

    def _run_doctor(self) -> None:
        def _task() -> None:
            code = run_doctor()
            msg = "Doctor OK" if code == 0 else "Doctor FAILED"
            runtime_state.push_debug(msg)
            runtime_state.update(doctor_last={"status": "pass" if code == 0 else "fail", "exit_code": code})
            self.call_from_thread(self._set_status, msg)

        threading.Thread(target=_task, name="polybot-doctor", daemon=True).start()
        self._set_status("Running doctor...")

    def _run_replay(self) -> None:
        candidates = sorted(Path("data/sessions").glob("session_*.jsonl"))
        if not candidates:
            runtime_state.push_debug("replay: no session files found in data/sessions")
            self._set_status("Replay: no session file")
            return
        path = candidates[-1]

        def _task() -> None:
            n = replay_file(path, speed=5.0, only="all")
            runtime_state.push_debug(f"replay: {n} records from {path.name}")
            self.call_from_thread(self._set_status, f"Replay done: {path.name}")

        threading.Thread(target=_task, name="polybot-replay", daemon=True).start()
        self._set_status(f"Replaying {path.name}")

    def refresh_panels(self) -> None:
        for cls in (
            MarketPanel,
            DecisionTracePanel,
            OrderBlotterPanel,
            TradePanel,
            MetricsPanel,
            PortfolioPanel,
            RiskPanel,
            TimelinePanel,
            SystemPanel,
            DebugPanel,
        ):
            for widget in self.query(cls):
                widget.refresh()

    def _set_status(self, text: str) -> None:
        self.query_one("#status_bar", Static).update(text)

    def action_quit(self) -> None:
        request_orchestrator_stop()
        self.exit()

    def action_pause(self) -> None:
        runtime_state.paused = not runtime_state.paused
        runtime_state.push_debug(f"pause -> {runtime_state.paused}")
        self._set_status(f"Paused={runtime_state.paused}")

    def action_risk(self) -> None:
        cycle = [0.5, 1.0, 1.5]
        try:
            i = cycle.index(runtime_state.risk_level)
            j = (i + 1) % len(cycle)
        except ValueError:
            j = 1
        runtime_state.risk_level = cycle[j]
        runtime_state.push_debug(f"risk_level -> {runtime_state.risk_level}")
        self._set_status(f"Risk level={runtime_state.risk_level}")

    def action_soft_kill(self) -> None:
        runtime_state.soft_kill = not runtime_state.soft_kill
        runtime_state.push_debug(f"soft_kill -> {runtime_state.soft_kill}")
        self._set_status(f"Soft kill={runtime_state.soft_kill}")

    def action_flatten_hint(self) -> None:
        runtime_state.push_debug("flatten: use polybot flatten-all for live order cancel / flatten flow")
        self._set_status("Flatten hint logged")

    def action_help_keys(self) -> None:
        runtime_state.push_debug(
            "keys: q quit | p pause | r risk | k soft_kill | f flatten hint | h help"
        )
        self._set_status("Help pushed to debug panel")


def run_tui() -> None:
    """Control room only (no launcher) — for scripts and `polybot tui` if wired."""
    PolyBotTui(with_launcher=False).run()
