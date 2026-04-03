"""
Replay feed for recorded PolyBot sessions.

Supports:
- JSONL session logs with event records
- CSV exports with a `type` column
- simple offline iteration for backtests / TUI replays
"""

from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


@dataclass(slots=True)
class ReplayTick:
    timestamp: float
    type: str
    payload: dict[str, Any]


class ReplayFeed:
    """
    Load recorded session data and yield normalized replay ticks.

    Supported JSONL schema:
    {"ts": 1730000000.0, "type": "cycle", ...}
    {"timestamp": "...", "type": "snapshot", ...}

    Supported CSV schema:
    timestamp,type,payload_json
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(self.path)

    def iter_ticks(
        self,
        *,
        allowed_types: set[str] | None = None,
        max_rows: int | None = None,
    ) -> Iterator[ReplayTick]:
        ext = self.path.suffix.lower()
        if ext == ".jsonl":
            yield from self._iter_jsonl(allowed_types=allowed_types, max_rows=max_rows)
            return
        if ext == ".csv":
            yield from self._iter_csv(allowed_types=allowed_types, max_rows=max_rows)
            return
        raise ValueError(f"unsupported replay format: {self.path.suffix}")

    def replay(
        self,
        callback,
        *,
        speed: float = 1.0,
        allowed_types: set[str] | None = None,
        max_rows: int | None = None,
    ) -> int:
        """
        Invoke callback(tick) for each replay row.
        If speed > 0, preserves relative time gaps approximately.
        """
        count = 0
        previous_ts: float | None = None
        for tick in self.iter_ticks(allowed_types=allowed_types, max_rows=max_rows):
            if previous_ts is not None and speed > 0:
                delta = max(0.0, tick.timestamp - previous_ts)
                time.sleep(min(delta / speed, 1.0))
            callback(tick)
            previous_ts = tick.timestamp
            count += 1
        return count

    def summary(self, *, max_rows: int | None = None) -> dict[str, Any]:
        counts: dict[str, int] = {}
        first_ts: float | None = None
        last_ts: float | None = None
        for tick in self.iter_ticks(max_rows=max_rows):
            counts[tick.type] = counts.get(tick.type, 0) + 1
            first_ts = tick.timestamp if first_ts is None else min(first_ts, tick.timestamp)
            last_ts = tick.timestamp if last_ts is None else max(last_ts, tick.timestamp)
        return {
            "path": str(self.path),
            "counts": counts,
            "first_ts": first_ts,
            "last_ts": last_ts,
            "duration_seconds": (last_ts - first_ts) if first_ts is not None and last_ts is not None else 0.0,
        }

    def _iter_jsonl(
        self,
        *,
        allowed_types: set[str] | None,
        max_rows: int | None,
    ) -> Iterator[ReplayTick]:
        with self.path.open("r", encoding="utf-8") as handle:
            count = 0
            for line in handle:
                if max_rows is not None and count >= max_rows:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                tick = _normalize_tick(payload)
                if tick is None:
                    continue
                if allowed_types and tick.type not in allowed_types:
                    continue
                yield tick
                count += 1

    def _iter_csv(
        self,
        *,
        allowed_types: set[str] | None,
        max_rows: int | None,
    ) -> Iterator[ReplayTick]:
        with self.path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            count = 0
            for row in reader:
                if max_rows is not None and count >= max_rows:
                    break
                try:
                    payload = json.loads(row.get("payload_json") or "{}")
                except json.JSONDecodeError:
                    payload = {}
                payload.setdefault("timestamp", row.get("timestamp"))
                payload.setdefault("type", row.get("type"))
                tick = _normalize_tick(payload)
                if tick is None:
                    continue
                if allowed_types and tick.type not in allowed_types:
                    continue
                yield tick
                count += 1


def _normalize_tick(payload: dict[str, Any]) -> ReplayTick | None:
    if not isinstance(payload, dict):
        return None
    raw_ts = payload.get("ts") or payload.get("timestamp") or payload.get("created_at") or time.time()
    ts = _parse_timestamp(raw_ts)
    tick_type = str(payload.get("type") or payload.get("event_type") or "unknown")
    return ReplayTick(timestamp=ts, type=tick_type, payload=payload)


def _parse_timestamp(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            pass
        try:
            from datetime import datetime
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return time.time()
    return time.time()
