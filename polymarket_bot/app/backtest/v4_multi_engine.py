"""
Multi-market backtest: several price series, capital allocation, optional per-market expiry bar.

Uses the legacy `strategies.get_strategy` signal generator + `conservative_fill` for fills.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from app.backtest.simulator import SimParams, conservative_fill
from app.config import Settings
from app.strategies import get_strategy


@dataclass
class MultiMarketResult:
    equity_curve: list[float]
    pnl_by_market: dict[str, float]
    trades: int
    bars: int
    meta: dict[str, Any] = field(default_factory=dict)


class MultiMarketBacktest:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def run(
        self,
        series: dict[str, pd.DataFrame],
        *,
        strategy_name: str,
        bankroll_usd: float,
        max_active_markets: int = 3,
        price_col: str = "close",
        spread_col: str = "spread_bps",
        expiry_bars: dict[str, int] | None = None,
    ) -> MultiMarketResult:
        """
        series: market_name -> OHLC-like DataFrame (rows = time bars).
        expiry_bars: market_name -> bar index at which that market is removed (resolved).
        """
        strat = get_strategy(strategy_name, settings=self._settings)
        params = SimParams(fee_bps=self._settings.paper_fee_bps, slippage_bps=self._settings.paper_slippage_bps)
        expiry_bars = expiry_bars or {}

        lengths = [len(df) for df in series.values()]
        max_bar = min(lengths) if lengths else 0
        equity: list[float] = [0.0]
        pnl_by_market: dict[str, float] = {k: 0.0 for k in series}
        trades = 0
        capital_per_slot = bankroll_usd / max(1, max_active_markets)

        active: set[str] = set(series.keys())

        for bar in range(max_bar):
            # drop expired
            for name, ex in expiry_bars.items():
                if bar >= ex and name in active:
                    active.discard(name)

            if not active:
                break

            # rank markets by absolute momentum proxy at this bar
            scores: list[tuple[str, float]] = []
            for name in active:
                df = series[name]
                row = df.iloc[bar]
                mom = float(row.get("mom", row.get(price_col, 0.0)))
                scores.append((name, abs(mom)))
            scores.sort(key=lambda x: -x[1])
            chosen = [n for n, _ in scores[:max_active_markets]]

            for name in chosen:
                df = series[name]
                row = df.iloc[bar]
                mid = float(row[price_col] if price_col in row else row.get("close", 0.5))
                spread_bps = float(row.get(spread_col, 10.0))
                state: dict[str, Any] = {
                    "market_id": name,
                    "token_id": name,
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
                side = "BUY" if sig.action.value in ("buy", "quote_bid") else "SELL"
                size = max(1.0, capital_per_slot / max(mid, 1e-6))
                fp, fee = conservative_fill(side, float(sig.price or mid), size, mid, spread_bps, params)
                pnl = (mid - fp) * size if side == "BUY" else (fp - mid) * size
                pnl -= fee
                pnl_by_market[name] += pnl
                equity.append(equity[-1] + pnl)
                trades += 1

        return MultiMarketResult(
            equity_curve=equity,
            pnl_by_market=pnl_by_market,
            trades=trades,
            bars=max_bar,
            meta={"max_active_markets": max_active_markets, "strategy": strategy_name},
        )
