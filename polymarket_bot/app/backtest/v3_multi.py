"""
Multi-market backtest / replay (V3) — orchestrates scan → score → allocation over many series.

Extend `BacktestEngine` with per-market DataFrames and shared capital; full expiry/rollover
simulation is TODO (requires historical WS snapshots or stored books).
"""

from __future__ import annotations

# Placeholder for V3 backtest integration tests and CSV batch runs.
