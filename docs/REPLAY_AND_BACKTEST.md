# Replay and backtest

## Single-series bar backtest

```bash
polybot backtest --strategy mean_reversion_micro --from 2025-01-01 --to 2025-03-01 --out outputs/metrics.csv
```

Uses synthetic bars when no file is provided (see `cli.py`).

## Multi-market engine

Programmatic API: `from app.backtest import MultiMarketBacktest` — multiple `pandas` DataFrames, optional per-market expiry bar. See `app/backtest/v4_multi_engine.py`.

## Session replay (roadmap)

Recorded sessions (CSV/JSONL/SQLite) will feed a **replay engine** so decisions and fair value can be reproduced offline. Stubs: `polybot replay`, `polybot backfill-history`.

When `app/data/recorder.py` and `replay_engine.py` land, this document will list exact schemas and CLI examples.
