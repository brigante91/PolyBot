# First run

## 1. Clone and install

```bash
cd PolyBot-V2
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
cp .env.example .env
```

Do **not** rely on `uv pip install -r requirements.txt` alone without the editable package: the `app` module must resolve (`ModuleNotFoundError` means you skipped `pip install -e .`).

## 2. Validate environment

```bash
polybot check-env    # local paths + imports (no network)
polybot doctor       # + public Gamma/CLOB HTTP checks
```

Set `POLYBOT_SKIP_NETWORK=1` is not required; doctor uses public endpoints only.

## 3. Paper trading loop

```bash
polybot run-multi --mode paper --max-cycles 1
```

## 4. Terminal UI

In a second terminal (same venv):

```bash
polybot-tui
```

Run `polybot run-multi --mode paper` in the first terminal to feed live state.

## 5. Live trading (danger)

1. Fill wallet/API fields per Polymarket docs.
2. Set `MODE=live`, `ENABLE_LIVE_TRADING=true`, risk limits, `KILL_SWITCH=false`.
3. `polybot doctor` should pass.
4. Start with minimal size and `run-multi` with monitoring.

See also [TUI_GUIDE.md](TUI_GUIDE.md) and [RISK_MODEL.md](RISK_MODEL.md).
