# Risk model

Risk is enforced in layers:

1. **Pre-trade** (`RiskEngine.check_pre_trade`) — exposure, daily loss, open orders, spread/slippage, kill switch, cooldowns.
2. **Portfolio** (`check_portfolio` + `PortfolioManager`) — max concurrent positions, strategy loss limits, **correlation groups** (BTC/ETH/SOL-style caps via `CorrelationManager`).
3. **Execution** — deduplication, dry-run short-circuit, live gated by `ENABLE_LIVE_TRADING`.

## Configuration

See `.env.example`: `MAX_TOTAL_EXPOSURE_USD`, `MAX_MARKET_EXPOSURE_USD`, `MAX_CONCURRENT_POSITIONS`, `MAX_EXPOSURE_GROUP_USD`, `DAILY_LOSS_LIMIT_USD`, `STRATEGY_LOSS_LIMIT_USD`, `KILL_SWITCH`, etc.

## Operational safety

- Default **paper** mode; **live** requires explicit flags.
- **Maker-first** defaults (`MAKER_FIRST_POST_ONLY`).
- Orchestrator records **no-trade reasons** and risk blocks in `runtime_state` for TUI/debug.

Tuning limits is mandatory before real capital.
