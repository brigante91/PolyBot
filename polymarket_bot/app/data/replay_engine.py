"""Replay JSONL session files into runtime_state for TUI / offline review."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from app.state.runtime_state import runtime_state


def replay_file(
    path: Path | str,
    *,
    speed: float = 1.0,
    max_lines: int | None = None,
) -> int:
    """
    Read session JSONL and push markets/decisions/orders into runtime_state with delay.
    Returns number of records applied.
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(p)
    n = 0
    with p.open(encoding="utf-8") as f:
        for line in f:
            if max_lines is not None and n >= max_lines:
                break
            line = line.strip()
            if not line:
                continue
            try:
                obj: dict[str, Any] = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = obj.get("type", "")
            if t == "cycle":
                patch: dict[str, Any] = {
                    "markets": obj.get("markets", []),
                    "decisions": obj.get("decisions", []),
                    "orders": obj.get("orders", []),
                    "metrics": obj.get("metrics", {}),
                }
                if "risk" in obj:
                    patch["risk"] = obj.get("risk") or {}
                runtime_state.update(**patch)
            elif t == "snapshot":
                runtime_state.update(
                    markets=obj.get("markets", []),
                    decisions=obj.get("decisions", []),
                    orders=obj.get("orders", []),
                )
            n += 1
            if speed > 0:
                time.sleep(0.05 / speed)
    runtime_state.push_debug(f"replay done: {n} records from {p.name}")
    return n
