"""Performance metrics and CSV export."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class BacktestMetrics:
    net_pnl: float = 0.0
    sharpe: float | None = None
    sortino: float | None = None
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    expectancy: float = 0.0
    profit_factor: float = 0.0
    avg_hold_bars: float = 0.0
    fill_ratio: float = 0.0
    adverse_excursion_avg: float = 0.0
    trades: list[dict[str, Any]] = field(default_factory=list)

    def to_row(self) -> dict[str, Any]:
        return {
            "net_pnl": self.net_pnl,
            "sharpe": self.sharpe,
            "sortino": self.sortino,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "expectancy": self.expectancy,
            "profit_factor": self.profit_factor,
            "avg_hold_bars": self.avg_hold_bars,
            "fill_ratio": self.fill_ratio,
            "adverse_excursion_avg": self.adverse_excursion_avg,
        }


def compute_metrics(
    equity_curve: list[float],
    trade_pnls: list[float],
    hold_bars: list[float],
    fills: int,
    signals: int,
) -> BacktestMetrics:
    m = BacktestMetrics()
    if trade_pnls:
        m.net_pnl = float(sum(trade_pnls))
        wins = [p for p in trade_pnls if p > 0]
        losses = [p for p in trade_pnls if p < 0]
        m.win_rate = len(wins) / len(trade_pnls)
        m.expectancy = float(np.mean(trade_pnls))
        gp, gl = sum(wins), abs(sum(losses)) if losses else 0.0
        m.profit_factor = (gp / gl) if gl > 0 else (999.0 if gp > 0 else 0.0)
    if equity_curve:
        arr = np.array(equity_curve, dtype=float)
        peak = np.maximum.accumulate(arr)
        dd = peak - arr
        m.max_drawdown = float(np.max(dd)) if len(dd) else 0.0
        rets = np.diff(arr)
        if len(rets) > 1 and np.std(rets) > 0:
            m.sharpe = float(np.mean(rets) / np.std(rets) * np.sqrt(252))
            downside = rets[rets < 0]
            if len(downside) > 1 and np.std(downside) > 0:
                m.sortino = float(np.mean(rets) / np.std(downside) * np.sqrt(252))
    if hold_bars:
        m.avg_hold_bars = float(np.mean(hold_bars))
    if signals > 0:
        m.fill_ratio = fills / signals
    return m


def write_csv(path: Path, metrics: BacktestMetrics) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(metrics.to_row().keys()))
        w.writeheader()
        w.writerow(metrics.to_row())
