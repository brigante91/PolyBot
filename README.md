# PolyBot-V2 — Polymarket research bot

Production-like Python 3.11+ toolkit for **disciplined research and automation** on Polymarket: public market data, optional CLOB trading (explicitly gated), **paper** and **dry-run** modes by default, SQLite persistence, backtesting primitives, and a standalone **risk engine**.

This software does **not** guarantee profits. It is designed to favour **operational safety**, **observability**, and **repeatable experiments**—not maximum trade frequency.

## Architecture

### Core (legacy + shared)

- **`app/config.py`** — `pydantic-settings` validation; live trading requires explicit flags and risk limits.
- **`app/clients/`** — Gamma, CLOB (`py-clob-client`), Data API; **`polymarket_rest.py`** facade; WS stubs (`polymarket_ws_*`) with TODOs until official WS docs are wired.
- **`app/services/`** — Execution (pre-trade, dedup, reason codes), persistence, legacy single-market `TradingService`.
- **`app/risk/`** — Kill switch, exposure limits, position sizing, `RiskEngine`; **`market_risk_rules.py`** / **`portfolio_risk_rules.py`** for per-market vs portfolio gates.
- **`app/strategies/`** — Original signal-style strategies (still importable).
- **`app/paper/`** — Conservative simulated fills (fees, slippage, queue assumption).
- **`app/backtest/`** — Bar engine, simulator, metrics + CSV export.
- **`app/cli.py`** — Typer CLI (orchestration only).

### Multi-market adaptive engine (V2)

Operational pipeline (see **`app/orchestrator.py`**):

`universe scan → filter → live analysis → historical profile → scoring → strategy selection → portfolio/risk → order routing → reconciliation`

| Package | Role |
|--------|------|
| **`app/discovery/`** | `market_universe.py` (full universe), `market_filter.py` (hard exclusions) |
| **`app/analysis/`** | `live_market_analyzer.py`, `historical_analyzer.py`, `market_scorer.py`, `feature_builder.py` |
| **`app/strategy/`** | `strategy_selector.py`, per-strategy modules with **`can_trade` / `score` / `build_order_intent`** only (no direct order send) |
| **`app/portfolio/`** | `portfolio_manager.py`, `exposure_allocator.py`, `position_registry.py`, `pnl_tracker.py` |
| **`app/execution/`** | `order_router.py`, `reconciliation.py`, `quote_manager.py` (maker-first hooks) |
| **`app/data/`** | `market_store.py`, `historical_store.py`, `cache.py`, `replay.py` (replay stub) |
| **`app/monitor/`** | `metrics.py`, `health.py` |
| **`app/runtime.py`** | Signal-safe loop calling **`MultiMarketOrchestrator`** |

Structured JSON logs include **decision records** per `market_id` (strategy, action, size, reason).

## APIs: Gamma vs Data vs CLOB

| API | Role | Auth |
|-----|------|------|
| **Gamma** | Markets, events, metadata, `clobTokenIds` | Public |
| **Data** | Positions, trades, activity for a wallet address | Public reads (see docs) |
| **CLOB** | Order book, midpoint, spreads, prices, **orders** | Public reads; trading needs key + API creds (see Polymarket docs) |

## Setup

The package **`app`** lives under `polymarket_bot/app/`. You must install the project in **editable** mode (or set `PYTHONPATH=polymarket_bot`). Installing only `requirements.txt` dependencies is **not** enough: you will get `ModuleNotFoundError: No module named 'app'`.

### Using uv (recommended)

```bash
cd PolyBot-V2
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
cp .env.example .env
```

Use **`uv pip`** so packages go into the venv. If you run plain `pip install -e .` and see “Defaulting to user installation”, the editable install is **not** in your venv—fix permissions or use `uv pip install -e ".[dev]"`.

### Alternative: requirements + editable line

`requirements.txt` includes `-e .` so this also registers `app`:

```bash
uv pip install -r requirements.txt
```

### pip / venv

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run the CLI:

```bash
python -m app.cli --help
# or, after install:
polybot --help
```

Without installing, one-off:

```bash
PYTHONPATH=polymarket_bot python -m app.cli --help
```

## Environment

Copy `.env.example` to `.env`. **Never commit secrets.** Required behaviour:

- **`MODE`**: `paper` (default), `dry_run`, or `live`.
- **`ENABLE_LIVE_TRADING`**: must be `true` for real orders; must be paired with risk limits.
- **`KILL_SWITCH`**: global halt; optional file flag `KILL_SWITCH_FILE` (default `./data/kill_switch`).
- Risk caps: `MAX_ORDER_SIZE_USD`, `MAX_MARKET_EXPOSURE_USD`, `MAX_TOTAL_EXPOSURE_USD`, `DAILY_LOSS_LIMIT_USD`, `MAX_OPEN_ORDERS`, etc.

## Public market data

Discovery example (Gamma):

```http
GET https://gamma-api.polymarket.com/markets?active=true&closed=false&limit=10
```

From code:

```bash
python -m app.cli discover-markets --limit 10
```

Order book via the CLOB wrapper uses `py-clob-client` (`get_order_book(token_id)`).

## PolyBot V3 (production-grade path)

- **WebSockets**: `app/clients/polymarket_ws_market.py` / `polymarket_ws_user.py` — CLOB market & user channels ([docs](https://docs.polymarket.com/developers/CLOB/websocket/wss-overview)). Set **`ENABLE_WS=true`** and wire **`V3Coordinator`** (`app/v3_coordinator.py`) with a `WsMarketHub` for event-driven books; reconciliation hooks user events in `ReconciliationService`.
- **Fair value**: `app/analysis/fair_value_engine.py` — `fair_prob`, `edge`, `edge_net`, `confidence` (replaces naive RSI/MACD-only signals for V3 paths).
- **Quote engine**: `app/execution/quote_engine.py` — post-only / maker-first via `ClobWrapper.create_limit_order_post(..., post_only=True)`.
- **WS handler**: `app/execution/ws_handler.py` — normalizes `book` / `best_bid_ask` events into `OrderBookSnapshot`.
- **TUI**: `python -m app.cli tui` or `polybot-tui` — Textual dashboard (markets, trades, portfolio, system, debug). Run **`run-multi`** in another terminal to feed `runtime_state`.
- **State**: `app/state/runtime_state.py` — thread-safe snapshot consumed by the TUI.
- **Metrics**: `app/monitor/advanced_metrics.py` — counters for fill/cancel/maker ratio (extend in orchestrator).

## Multi-market mode (recommended)

```bash
python -m app.cli run-multi --mode paper
# one cycle then exit (testing):
python -m app.cli run-multi --mode paper --max-cycles 1
```

Set **`MULTI_MARKET_MODE=true`** and tune **`UNIVERSE_*`**, **`LIVE_ANALYSIS_TOP_N`**, **`SCORE_MIN_TRADABLE`**, **`MAX_CONCURRENT_POSITIONS`**, **`ORCHESTRATOR_INTERVAL_SECONDS`** in `.env`.

The orchestrator **scores and ranks** markets; only the best candidates proceed to strategy selection and execution. **Limit orders** are the default; **`ALLOW_MARKET_ORDERS`** defaults to false.

## Paper trading (single-market legacy loop)

```bash
python -m app.cli run --mode paper --strategy market_making_passive
```

Paper mode simulates fills with configurable **fee**, **slippage**, and **queue** assumptions (`PAPER_*` in `.env`).

## Dry-run

```bash
python -m app.cli run --mode dry_run --strategy mean_reversion_micro
```

Signals are logged and persisted; **no orders** are submitted.

## Live trading (danger)

1. Configure wallet/API credentials per Polymarket documentation (Level 1/2 auth).
2. Set **`ENABLE_LIVE_TRADING=true`** and **`MODE=live`**.
3. Ensure all risk limits are set to sane values; verify **`KILL_SWITCH`** is off.
4. Use `python -m app.cli cancel-all` only when live is intentionally enabled.

If `ENABLE_LIVE_TRADING` is false, `cancel-all` refuses to run.

## Backtest

```bash
python -m app.cli backtest --strategy mean_reversion_micro --from 2025-01-01 --to 2025-03-01 --out outputs/metrics.csv
```

The bundled driver uses **synthetic** daily bars when no file is supplied—replace with your historical series for research.

## Status & risk report

```bash
python -m app.cli status
python -m app.cli risk-report
```

## Tests

```bash
python -m pytest tests/ -q
```

## Docker (optional)

```bash
docker compose build
docker compose run --rm app python -m app.cli discover-markets --limit 3
```

Mount a local `.env` and `data/` volume as needed (see `docker-compose.yml`).

## Adding a strategy (V2)

1. Add a module under **`app/strategy/`** implementing **`StrategyBase`**: `can_trade`, `score`, `build_order_intent`.
2. Register it in **`StrategySelector.__init__`** (list order matters for tie-breaks; `no_trade` is implicit).
3. Add unit tests under **`tests/`**.

## Risk disclaimer

Trading prediction markets involves **substantial risk of loss**. This project is for **education and research**. Past backtests or paper results do not predict future performance. Review Polymarket terms and applicable regulations before using real funds.

## License

MIT (verify `py-clob-client` and dependencies’ licenses for your use case).
