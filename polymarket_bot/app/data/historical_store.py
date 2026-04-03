"""SQLite-backed summaries for historical analyzer (minimal v1)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.models.context import HistoricalProfile


class HistoricalStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or Path("./data/historical_summaries.db")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _init(self) -> None:
        with sqlite3.connect(self._path) as c:
            c.execute(
                """CREATE TABLE IF NOT EXISTS market_hist (
                market_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            )"""
            )

    def get_summary(self, market_id: str) -> HistoricalProfile | None:
        with sqlite3.connect(self._path) as c:
            row = c.execute("SELECT payload FROM market_hist WHERE market_id=?", (market_id,)).fetchone()
            if not row:
                return None
            d: dict[str, Any] = json.loads(row[0])
            return HistoricalProfile.model_validate(d)

    def upsert_summary(self, market_id: str, profile: HistoricalProfile) -> None:
        with sqlite3.connect(self._path) as c:
            c.execute(
                "INSERT OR REPLACE INTO market_hist (market_id, payload) VALUES (?, ?)",
                (market_id, profile.model_dump_json()),
            )
