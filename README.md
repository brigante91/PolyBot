# PolyBot-V2 — Multi-market adaptive Polymarket engine

Python **3.11+** toolkit for **research and automation** on [Polymarket](https://polymarket.com): Gamma/CLOB/Data API clients, **paper** and **dry-run** by default, optional **live** trading (explicitly gated), SQLite persistence, risk engine, backtesting, and a **multi-market orchestrator** with optional **WebSockets**, **fair value** modelling, **maker-first** execution, and a **terminal UI (TUI)**.

This software does **not** guarantee profits. It favours **operational safety**, **observability**, and **selective trading** (“tradare meglio, non di più”).

### Production-ready checklist (V4 FINAL target)

| Criterion | How |
|-----------|-----|
| Install | `uv pip install -e ".[dev]"` or `pip install -e ".[dev]"` from repo root |
| Tests | `pytest -q` — no live API keys required |
| Health | `polybot doctor` / `polybot check-env` |
| Run | `polybot run-multi --mode paper` |
| TUI | `polybot-tui` — markets, **decision trace**, **order blotter**, metrics, portfolio, system (kill/pause/soft-kill), debug |
| Live | Same code path — set `MODE=live`, `ENABLE_LIVE_TRADING=true`, credentials and risk in `.env` |
| Safety | Env/file **kill switch**, TUI **pause** (`p`) and **soft kill** (`k`) skip routing; limit orders + post-only defaults |

---

## What the bot does

Instead of a single fixed market and strategy, the recommended path is:

**universe scan → filter → live + historical analysis → scoring → strategy selection → portfolio/risk → order routing → reconciliation → (optional) TUI**

The orchestrator (**`app/orchestrator.py`**, driven by **`app/runtime.py`**) ranks candidates and only proceeds with the best opportunities under global and per-group limits.

---

## Architecture (logical layers)

| Layer | Role | Main locations |
|--------|------|----------------|
| **Data** | REST (Gamma, CLOB), optional **market/user WebSockets**, optional **spot REST** / **RTDS stub** | `app/clients/` |
| **Intelligence** | Live features, historical profile, **fair value** (`fair_prob`, `edge`, `edge_net`, `confidence`), scoring | `app/analysis/` |
| **Decision** | Strategy selection, portfolio, risk | `app/strategy/`, `app/portfolio/`, `app/risk/` |
| **Execution** | Order router, execution service, **quote engine** (post-only / tiered edge), reconciliation | `app/execution/`, `app/services/execution_service.py` |
| **Observability** | TUI, orchestrator metrics, advanced metrics, structured logs | `app/ui/`, `app/state/`, `app/monitor/` |

Legacy **signal-style** strategies for bar backtests remain under **`app/strategies/`**; the live pipeline uses **`app/strategy/`** (intent-based, no direct order sends).

---

## Repository layout

Application code lives under **`polymarket_bot/app/`** (import name **`app`** after editable install).

```
polymarket_bot/app/
├── cli.py, main.py, runtime.py, orchestrator.py, v3_coordinator.py
├── analysis/          # live, historical, scorer, fair_value_engine, feature_builder
├── backtest/          # bar engine, v4 multi-market driver
├── clients/           # gamma, clob, rest facade, ws market/user, spot_price, rtds stub
├── data/              # market_store, cache, replay, …
├── discovery/         # market_universe, market_filter, market_metadata
├── execution/         # order_router, quote_engine, ws_handler, reconciliation
├── monitor/           # metrics, health, advanced_metrics
├── portfolio/         # manager, exposure_allocator, correlation_manager, …
├── risk/              # risk_engine, rules, kill_switch
├── services/          # execution, persistence, legacy trading_service
├── state/             # runtime_state (TUI / cross-thread snapshot)
├── realtime/          # state_engine (thread-safe snapshots for WS-fed state)
├── strategy/          # selector + passive_mm, momentum, mean_reversion, fair_value_gap, inventory_reduction, no_trade
├── strategies/        # legacy backtest strategies (get_strategy)
├── ui/                # textual TUI + views (market, trades, portfolio, system, debug, metrics)
└── …
```

---

## Installation

The package must be installed so that **`import app`** resolves. Installing **only** transitive deps (e.g. `uv pip install -r requirements.txt` **without** the project) is **not** enough: you will get `ModuleNotFoundError: No module named 'app'`.

### Recommended: `uv` + editable install

```bash
cd PolyBot-V2
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
cp .env.example .env
```

Use **`uv pip install -e ".[dev]"`** so the editable install lands **inside** the venv. If plain `pip install -e .` prints **“Defaulting to user installation”**, the project is not in the active venv—use `uv pip` or fix venv permissions.

### Alternative

- **`requirements.txt`** may include `-e .`; run:  
  `uv pip install -r requirements.txt`  
  from the project root so the package is linked.

### Run without installing (one-off)

```bash
PYTHONPATH=polymarket_bot python -m app.cli --help
```

### Entry points (after install)

| Command | Purpose |
|---------|---------|
| `polybot` | Same as `python -m app.cli` |
| `polybot-tui` | Launches the Textual TUI |

---

## First run (operational checklist)

1. `uv pip install -e ".[dev]"` and `cp .env.example .env`
2. `polybot check-env` — local imports, data dir, optional deps (**no network**)
3. `polybot doctor` — same + public **Gamma/CLOB HTTP** reachability
4. `polybot run-multi --mode paper --max-cycles 1`
5. Optional: second terminal → `polybot-tui` while `run-multi` is running

Full walkthrough: **[docs/FIRST_RUN.md](docs/FIRST_RUN.md)** · TUI: **[docs/TUI_GUIDE.md](docs/TUI_GUIDE.md)** · Architecture: **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** · Risk: **[docs/RISK_MODEL.md](docs/RISK_MODEL.md)** · Replay/backtest: **[docs/REPLAY_AND_BACKTEST.md](docs/REPLAY_AND_BACKTEST.md)**

---

## Configuration

Copy **`.env.example`** → **`.env`**. Never commit secrets.

**Modes**

- **`MODE`**: `paper` (default), `dry_run`, `live`.
- **`ENABLE_LIVE_TRADING`**: must be `true` for real CLOB orders; combine with risk limits.
- **`KILL_SWITCH`** / **`KILL_SWITCH_FILE`**: global halt.

**Multi-market (orchestrator)**

- **`MULTI_MARKET_MODE`**, **`UNIVERSE_*`**, **`LIVE_ANALYSIS_TOP_N`**, **`SCORE_MIN_TRADABLE`**, **`MAX_CONCURRENT_POSITIONS`**, **`ORCHESTRATOR_INTERVAL_SECONDS`**, **`MAX_EXPOSURE_GROUP_USD`** (correlation groups), etc.

**Maker-first**

- **`MAKER_FIRST_POST_ONLY`**, **`ALLOW_MARKET_ORDERS`** (default off for safety).

**WebSockets (event-driven books / user events)**

- **`ENABLE_WS`**, **`WS_MARKET_URL`**, **`WS_USER_URL`**. When enabled, the orchestrator can start **`V3Coordinator`** (market hub + user channel into reconciliation).

**Underlying spot for fair value (optional)**

- **`ENABLE_SPOT_PRICE_REST`**, **`SPOT_PRICE_TTL_SECONDS`** — REST fallback for BTC/ETH/SOL-style keywords in market text.
- **`ENABLE_RTDS`**, **`RTDS_WS_URL`** — placeholder for a streaming feed (see `app/clients/rtds_client.py`).

**Paper / backtest**

- **`PAPER_FEE_BPS`**, **`PAPER_SLIPPAGE_BPS`**, etc.

---

## CLI reference

```bash
python -m app.cli --help
```

| Command | Description |
|---------|-------------|
| **`check-env`** | Validate install, paths, Textual/websockets (**no network**) |
| **`doctor`** | `check-env` + public Gamma/CLOB HTTP smoke tests |
| **`run-multi`** | Multi-market loop: `--mode paper\|dry_run\|live`, optional `--max-cycles N` |
| **`tui`** | Terminal UI (run **`run-multi`** in another terminal to feed live state) |
| **`replay`** | Stub — offline session replay (see docs) |
| **`backfill-history`** | Stub — historical backfill job |
| **`flatten-all`** | Stub — emergency flatten (requires live + future implementation) |
| **`discover-markets`** | Sample Gamma markets (`--limit`) |
| **`run`** | Legacy single-market loop via `TradingService` (`--strategy`, `--max-iter`) |
| **`backtest`** | Single-series bar backtest to CSV (`--strategy`, `--from`, `--to`, `--out`) |
| **`status`** | Last heartbeat / DB path |
| **`risk-report`** | Recent risk events |
| **`cancel-all`** | CLOB `cancel_all` — only if **`ENABLE_LIVE_TRADING=true`** |

Examples:

```bash
python -m app.cli run-multi --mode paper
python -m app.cli run-multi --mode paper --max-cycles 1
python -m app.cli discover-markets --limit 10
python -m app.cli tui
```

---

## Multi-market pipeline (detail)

1. **Scan** — `MarketUniverseScanner` (Gamma pages, cap by settings).  
2. **Filter** — `MarketFilter` (liquidity, time to resolution, volume, spread, tokens, …).  
3. **Live analysis** — `LiveMarketAnalyzer` (order book via CLOB; optional **`WsMarketHub`** when WS enabled).  
4. **Historical** — `HistoricalAnalyzer` → profile (expectancy, edge stability, …).  
5. **Score** — `MarketScorer` → `score_total`, `recommended`.  
6. **Fair value** — `FairValueEngine` on each candidate (`MarketContext.fair_value`).  
7. **Strategy** — `StrategySelector` → action (`NO_TRADE`, `PASSIVE_QUOTE`, limit buy/sell, …).  
8. **Portfolio / risk** — `ExposureAllocator`, `PortfolioManager`, `RiskEngine`, **`CorrelationManager`** (e.g. BTC/ETH/SOL groups).  
9. **Route** — `OrderRouter` → **`ExecutionService`** (dedup, slippage, paper/live; **`QuoteEngine`** for maker tiers / post-only live).  
10. **Reconcile** — `ReconciliationService` (intent → sent → WS events); **`AdvancedMetrics`** (edge at entry, fill/cancel ratios, …).  
11. **TUI** — `runtime_state` updated each cycle (markets, portfolio, system, metrics, debug, no-trade hints).

---

## WebSockets & fair value

- **Market WS** (`polymarket_ws_market.py`): subscribe by asset (token) ids; events applied via **`WsMarketHub`** (`ws_handler.py`).  
- **User WS** (`polymarket_ws_user.py`): authenticated user channel; order/trade events feed reconciliation.  
- **Fair value** (`fair_value_engine.py`): structural + microstructure blend; optional **underlying** / **strike** when data is available.  
- **Quote engine** (`quote_engine.py`): adjusts limits by `edge_net`; skips very low edge; live path uses **post-only** when configured.

---

## TUI (Textual + Rich)

```bash
polybot-tui
# or
python -m app.cli tui
```

Panels: markets, trades, **metrics**, portfolio, system, debug (and no-trade hints). Keys: **`q`** quit, **`p`** pause, **`r`** cycle risk multiplier (also used by orchestrator for sizing).

---

## Backtesting

**Single series** (legacy signal strategies):

```bash
python -m app.cli backtest --strategy mean_reversion_micro --from 2025-01-01 --to 2025-03-01 --out outputs/metrics.csv
```

**Multi-market driver** (programmatic): `app.backtest.MultiMarketBacktest` in `app/backtest/v4_multi_engine.py` — several DataFrames, optional per-market **expiry** bar, shared bankroll. The CLI **`backtest`** command still uses the single-DF engine unless you extend it.

---

## Tests

```bash
python -m pytest tests/ -q
```

`pyproject.toml` sets `pythonpath = ["polymarket_bot"]` for pytest.

---

## Docker (optional)

```bash
docker compose build
docker compose run --rm app python -m app.cli discover-markets --limit 3
```

Mount `.env` and `data/` as needed (see `docker-compose.yml`).

---

## Adding a strategy (orchestrator path)

1. Implement **`StrategyBase`** in **`app/strategy/`**: `can_trade`, `score`, `build_order_intent` (no direct sends).  
2. Register in **`StrategySelector`** (list order affects tie-breaks; **`no_trade`** is implicit).  
3. Use **`MarketContext`** including optional **`fair_value`** for FV-aware logic.  
4. Add tests under **`tests/`**.

For **backtest-only** signal plugins, use **`app/strategies/`** and `get_strategy`; consider aligning names with **`app/strategy/`** (e.g. `passive_market_making` alias in `strategies/__init__.py`).

---

## APIs (reminder)

| API | Role | Auth |
|-----|------|------|
| **Gamma** | Markets, metadata, `clobTokenIds` | Public |
| **Data API** | Activity / positions (wallet-scoped) | See Polymarket docs |
| **CLOB** | Books, midpoint, **orders** | Reads public; trading needs wallet + API credentials per docs |

---

## Risk disclaimer

Trading prediction markets involves **substantial risk of loss**. This project is for **education and research**. Not financial advice. Review Polymarket terms and applicable laws before using real funds.

---

## License

MIT (verify licenses of `py-clob-client` and other dependencies for your use case).
