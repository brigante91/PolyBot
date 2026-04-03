"""Market list panel (Textual + Rich markup)."""

from __future__ import annotations

from textual.widgets import Static

from app.state.runtime_state import runtime_state


class MarketPanel(Static):
    """Markets table: id, score, strategy, edge, fair/mkt, stale/blocked."""

    def render(self) -> str:
        snap = runtime_state.snapshot()
        lines = ["[bold]MARKET RADAR[/bold]"]
        for m in snap.get("markets", [])[:18]:
            trad = "Y" if m.get("tradable") else "N"
            st = "STALE" if m.get("stale") else "live"
            blk = "BLOCK" if m.get("blocked") else "ok"
            ta = "OK" if m.get("trade_allowed") else "NO"
            tier = str(m.get("row_tier", ""))[:4]
            eg = m.get("edge_gross")
            en = m.get("edge_net") if m.get("edge_net") is not None else m.get("edge")
            eg_s = f"{eg:>8.6f}" if isinstance(eg, (int, float)) else f"{eg!s:>8}" if eg is not None else f"{'—':>8}"
            en_s = f"{en:>8.6f}" if isinstance(en, (int, float)) else f"{en!s:>8}" if en is not None else f"{'—':>8}"
            thr = m.get("threshold_net", "—")
            lines.append(
                f"{str(m.get('id',''))[:10]:<10} {trad} {st} {blk} {tier} sc{m.get('score',0):.2f} "
                f"{str(m.get('strategy',''))[:12]:<12} conf {m.get('confidence',''):>4} "
                f"eg {eg_s} en {en_s} thr {thr} "
                f"gate[{ta}] act {str(m.get('action',''))[:16]}"
            )
            lines.append(
                f"  fv {m.get('fair','—')} mkt {m.get('mkt','—')} "
                f"[bold]{str(m.get('reason',''))[:40]}[/bold]"
            )
            ex = str(m.get("explain", ""))[:50]
            if ex:
                lines.append(f"  [dim]{ex}[/dim]")
        if len(lines) == 1:
            lines.append("(no data — start orchestrator from launcher)")
        return "\n".join(lines)
