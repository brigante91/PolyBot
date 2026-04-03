# Architecture

```
Data (Gamma, CLOB REST, optional WS) 
  → Discovery (universe, filter)
  → Analysis (live, historical, fair value, score)
  → Decision (strategy selector, portfolio, risk)
  → Execution (router, execution service, quote engine, reconciliation)
  → Observability (logs, metrics, TUI, runtime_state)
```

## Package layout

- `polymarket_bot/app/` — import name **`app`** after editable install.
- `app/orchestrator.py` — multi-market loop (`MultiMarketOrchestrator`).
- `app/runtime.py` — signal-safe runner for `run-multi`.
- `app/strategy/` — intent-based strategies (`can_trade`, `score`, `build_order_intent`, `explain`).
- `app/strategies/` — legacy bar backtest signal API (`get_strategy`).
- `app/realtime/state_engine.py` — thread-safe book/order snapshot hub (integrate with WS).
- `app/clients/` — lazy package exports; `ClobWrapper` loads `py_clob_client` only when used.

## Lazy imports

`app.analysis` and `app.clients` use **PEP 562** lazy exports so importing the package does not eagerly import heavy modules.
