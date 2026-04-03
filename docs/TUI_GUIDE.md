# TUI guide

The control room is implemented with **Textual** + **Rich** (`polybot-tui` or `polybot tui`).

## Panels

| Area | Content |
|------|---------|
| **Markets (radar)** | Ranked candidates: score, strategy, confidence, fair/mkt prob, edge, explain, tradable |
| **Decision trace** | Per monitored market: strategy, second-best, edge_net, action, explain, scorer_ok |
| **Order blotter** | Last routed orders: lifecycle (`filled` / `sent` / `dry_run` / `rejected`), side, price, size, post-only, strategy |
| **Trades** | Open positions when wired to `runtime_state.trades` |
| **Metrics** | Advanced metrics: fill rate, cancel ratio, edge at entry, etc. |
| **Portfolio** | Exposure, capital used, daily PnL placeholder, open positions |
| **System** | WS, latency, health, **execution gate** (OK / PAUSED / SOFT_KILL / KILL_SWITCH), kill switch, soft kill, pause, risk multiplier |
| **Debug** | Recent cycle lines + no-trade hints |

## Keys

| Key | Action |
|-----|--------|
| `q` | Quit |
| `p` | Pause / resume — orchestrator skips execution when paused |
| `r` | Cycle risk level (0.5 → 1.0 → 1.5) — sizing multiplier |
| `k` | Toggle **soft kill** — blocks new orders until toggled off |
| `f` | Hint for flatten (real flatten: `polybot cancel-all` when live) |
| `h` | Help (pushes a debug line) |

## Requirements

The TUI only displays data the **orchestrator** pushes to `runtime_state`. Run `run-multi` concurrently for a live dashboard.

Further views (order blotter, full decision trace) are being extended per product roadmap.
