"""SQLite persistence: markets, orders, signals, fills, PnL, risk events, heartbeat."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

from app.config import Settings


class PersistenceService:
    SCHEMA_VERSION = 1

    def __init__(self, settings: Settings) -> None:
        self._path = Path(settings.sqlite_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as c:
            c.execute(
                """CREATE TABLE IF NOT EXISTS schema_version (
                id INTEGER PRIMARY KEY,
                version INTEGER NOT NULL
            )"""
            )
            row = c.execute("SELECT version FROM schema_version WHERE id=1").fetchone()
            if row is None:
                c.execute("INSERT INTO schema_version (id, version) VALUES (1, ?)", (self.SCHEMA_VERSION,))

            ddl = [
                """CREATE TABLE IF NOT EXISTS market_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT,
                payload TEXT,
                created_at TEXT
            )""",
                """CREATE TABLE IF NOT EXISTS orderbook_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_id TEXT,
                best_bid REAL,
                best_ask REAL,
                payload TEXT,
                created_at TEXT
            )""",
                """CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy TEXT,
                market_id TEXT,
                token_id TEXT,
                action TEXT,
                payload TEXT,
                created_at TEXT
            )""",
                """CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                market_id TEXT,
                token_id TEXT,
                side TEXT,
                price REAL,
                size REAL,
                status TEXT,
                mode TEXT,
                payload TEXT,
                created_at TEXT
            )""",
                """CREATE TABLE IF NOT EXISTS fills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT,
                price REAL,
                size REAL,
                fee REAL,
                payload TEXT,
                created_at TEXT
            )""",
                """CREATE TABLE IF NOT EXISTS positions (
                market_id TEXT,
                token_id TEXT,
                size REAL,
                avg_price REAL,
                payload TEXT,
                updated_at TEXT,
                PRIMARY KEY (market_id, token_id)
            )""",
                """CREATE TABLE IF NOT EXISTS pnl_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                realized REAL,
                unrealized REAL,
                payload TEXT,
                created_at TEXT
            )""",
                """CREATE TABLE IF NOT EXISTS risk_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reason TEXT,
                message TEXT,
                payload TEXT,
                created_at TEXT
            )""",
                """CREATE TABLE IF NOT EXISTS heartbeat (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                last_beat TEXT,
                payload TEXT
            )""",
            ]
            for s in ddl:
                c.execute(s)

    def insert_signal(self, payload: dict[str, Any]) -> None:
        with self._conn() as c:
            c.execute(
                """INSERT INTO signals (strategy, market_id, token_id, action, payload, created_at)
                VALUES (?,?,?,?,?,?)""",
                (
                    payload.get("strategy"),
                    payload.get("market_id"),
                    payload.get("token_id"),
                    payload.get("action"),
                    json.dumps(payload),
                    datetime.utcnow().isoformat(),
                ),
            )

    def insert_order(self, oid: str, payload: dict[str, Any]) -> None:
        with self._conn() as c:
            c.execute(
                """INSERT OR REPLACE INTO orders (id, market_id, token_id, side, price, size, status, mode, payload, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    oid,
                    payload.get("market_id"),
                    payload.get("token_id"),
                    payload.get("side"),
                    payload.get("price"),
                    payload.get("size"),
                    payload.get("status"),
                    payload.get("mode"),
                    json.dumps(payload),
                    datetime.utcnow().isoformat(),
                ),
            )

    def insert_risk_event(self, reason: str, message: str, payload: dict[str, Any] | None = None) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO risk_events (reason, message, payload, created_at) VALUES (?,?,?,?)",
                (reason, message, json.dumps(payload or {}), datetime.utcnow().isoformat()),
            )

    def heartbeat(self, extra: dict[str, Any] | None = None) -> None:
        with self._conn() as c:
            c.execute(
                """INSERT INTO heartbeat (id, last_beat, payload) VALUES (1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET last_beat=excluded.last_beat, payload=excluded.payload""",
                (datetime.utcnow().isoformat(), json.dumps(extra or {})),
            )

    def get_last_heartbeat(self) -> dict[str, Any] | None:
        with self._conn() as c:
            row = c.execute("SELECT last_beat, payload FROM heartbeat WHERE id=1").fetchone()
            if not row:
                return None
            return {"last_beat": row["last_beat"], "payload": json.loads(row["payload"] or "{}")}

    def recent_risk_events(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT reason, message, created_at FROM risk_events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [{"reason": r["reason"], "message": r["message"], "created_at": r["created_at"]} for r in rows]
