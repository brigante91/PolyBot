"""Terminal UI — PolyBot V3 (textual + rich)."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from app.state.runtime_state import runtime_state


class MarketPanel(Static):
    """Markets table summary."""

    def render(self) -> str:
        snap = runtime_state.snapshot()
        lines = ["[bold]MARKETS[/bold]"]
        for m in snap.get("markets", [])[:20]:
            lines.append(
                f"{m.get('id','')[:12]:<12} score {m.get('score',0):.2f} "
                f"{m.get('strategy','')[:16]:<16} {m.get('edge',''):>6}"
            )
        if len(lines) == 1:
            lines.append("(no data — run orchestrator with TUI)")
        return "\n".join(lines)


class TradePanel(Static):
    def render(self) -> str:
        snap = runtime_state.snapshot()
        lines = ["[bold]ACTIVE / TRADES[/bold]"]
        for t in snap.get("trades", [])[:15]:
            lines.append(str(t))
        if len(lines) == 1:
            lines.append("(none)")
        return "\n".join(lines)


class PortfolioPanel(Static):
    def render(self) -> str:
        p = runtime_state.snapshot().get("portfolio", {})
        exp = p.get("exposure_pct", "—")
        dpnl = p.get("daily_pnl_pct", "—")
        op = p.get("open_positions", "—")
        return (
            f"[bold]PORTFOLIO[/bold]\n"
            f"Exposure: {exp}\n"
            f"Daily PnL: {dpnl}\n"
            f"Open positions: {op}\n"
        )


class SystemPanel(Static):
    def render(self) -> str:
        s = runtime_state.snapshot().get("system", {})
        ws = s.get("ws", "N/A")
        lat = s.get("latency_ms", "—")
        health = s.get("health", "UNKNOWN")
        return (
            f"[bold]SYSTEM[/bold]\n"
            f"WS: {ws} | Latency: {lat}ms | Health: {health}\n"
            f"Paused: {runtime_state.snapshot().get('paused', False)}\n"
        )


class DebugPanel(Static):
    def render(self) -> str:
        lines = list(runtime_state.snapshot().get("debug", [])[-12:])
        return "[bold]DEBUG[/bold]\n" + "\n".join(lines) if lines else "[bold]DEBUG[/bold]\n—"


class PolyBotTui(App[None]):
    CSS = """
    Screen { layout: vertical; }
    #grid { height: 1fr; }
    """

    BINDINGS = [("q", "quit", "Quit"), ("p", "pause", "Pause")]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="grid"):
            with Vertical():
                yield MarketPanel()
                yield TradePanel()
            with Vertical():
                yield PortfolioPanel()
                yield SystemPanel()
                yield DebugPanel()
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(1.0, self.refresh_panels)

    def refresh_panels(self) -> None:
        for cls in (MarketPanel, TradePanel, PortfolioPanel, SystemPanel, DebugPanel):
            for w in self.query(cls):
                w.refresh()

    def action_pause(self) -> None:
        runtime_state.paused = not runtime_state.paused
        runtime_state.push_debug(f"pause toggled -> {runtime_state.paused}")


def run_tui() -> None:
    PolyBotTui().run()
