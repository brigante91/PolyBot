"""Bar-level backtest driver using strategy signals and conservative simulator."""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.backtest.metrics import BacktestMetrics, compute_metrics, write_csv
from app.backtest.simulator import SimParams, conservative_fill
from app.config import Settings
from app.strategies import get_strategy


class BacktestEngine:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def run_from_df(
        self,
        df: pd.DataFrame,
        *,
        strategy_name: str,
        price_col: str = "close",
        mid_col: str | None = None,
        spread_col: str = "spread_bps",
    ) -> BacktestMetrics:
        strat = get_strategy(strategy_name, settings=self._settings)
        params = SimParams(fee_bps=self._settings.paper_fee_bps, slippage_bps=self._settings.paper_slippage_bps)
        equity = [0.0]
        trade_pnls: list[float] = []
        hold_bars: list[float] = []
        fills = 0
        signals = 0

        for i, row in df.iterrows():
            mid = float(row[mid_col] if mid_col and mid_col in row else row[price_col])
            spread_bps = float(row.get(spread_col, 10.0))
            state: dict[str, Any] = {
                "market_id": "bt",
                "token_id": "bt",
                "mid": mid,
                "spread_bps": spread_bps,
                "depth_usd": float(row.get("depth_usd", 5000.0)),
                "vol_score": float(row.get("vol_score", 0.1)),
                "momentum_score": float(row.get("mom", 0.0)),
                "volume_confirm": float(row.get("vol_conf", 0.8)),
                "bars_held": 0,
            }
            strat.prepare({"mid": mid})
            sig = strat.generate_signal(state)
            if sig is None:
                continue
            signals += 1
            side = "BUY" if sig.action.value in ("buy", "quote_bid") else "SELL"
            size = max(1.0, self._settings.max_order_size_usd / max(mid, 1e-6))
            fp, fee = conservative_fill(side, float(sig.price or mid), size, mid, spread_bps, params)
            pnl = (mid - fp) * size if side == "BUY" else (fp - mid) * size
            pnl -= fee
            trade_pnls.append(pnl)
            fills += 1
            equity.append(equity[-1] + pnl)
            hold_bars.append(1.0)

        m = compute_metrics(equity, trade_pnls, hold_bars, fills, max(signals, 1))
        m.trades = [{"i": i, "pnl": p} for i, p in enumerate(trade_pnls)]
        return m

    def export_csv(self, metrics: BacktestMetrics, path: str) -> None:
        from pathlib import Path

        p = Path(path)
        if not p.is_absolute():
            p = Path.cwd() / p
        write_csv(p, metrics)
