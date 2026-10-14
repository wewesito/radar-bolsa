"""Conexión a SQLite y migraciones mínimas versionadas con PRAGMA user_version."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

# Cada entrada sube la versión del esquema en 1. Nunca se editan las ya publicadas:
# para cambiar algo se añade una nueva al final.
MIGRATIONS: list[str] = [
    # v1: watchlist
    """
    CREATE TABLE watchlist (
        ticker   TEXT PRIMARY KEY,
        name     TEXT NOT NULL,
        added_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
    );
    """,
    # v2: operaciones de la cartera simulada
    """
    CREATE TABLE trades (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker     TEXT NOT NULL,
        side       TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
        quantity   REAL NOT NULL CHECK (quantity > 0),
        price      REAL NOT NULL CHECK (price > 0),
        fee        REAL NOT NULL DEFAULT 0 CHECK (fee >= 0),
        currency   TEXT NOT NULL,
        trade_date TEXT NOT NULL,          -- AAAA-MM-DD
        fx_to_eur  REAL NOT NULL CHECK (fx_to_eur > 0),
        note       TEXT,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
    );
    CREATE INDEX idx_trades_ticker ON trades (ticker);
    """,
    # v3: alertas y avisos disparados
    """
    CREATE TABLE alerts (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker          TEXT NOT NULL,
        metric          TEXT NOT NULL
                        CHECK (metric IN ('price', 'change_pct', 'rsi', 'sma50', 'sma200')),
        op              TEXT NOT NULL CHECK (op IN ('above', 'below')),
        threshold       REAL,
        active          INTEGER NOT NULL DEFAULT 1,
        last_state      INTEGER,           -- NULL = aún no evaluada
        last_value      REAL,
        last_checked_at TEXT,
        created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
    );
    CREATE TABLE alert_events (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        alert_id     INTEGER NOT NULL REFERENCES alerts (id) ON DELETE CASCADE,
        triggered_at TEXT NOT NULL,
        value        REAL NOT NULL,
        message      TEXT NOT NULL,
        seen         INTEGER NOT NULL DEFAULT 0
    );
    """,
]


class Database:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.path, timeout=10)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        try:
            with con:
                yield con
        finally:
            con.close()

    def _migrate(self) -> None:
        with self.connect() as con:
            version = con.execute("PRAGMA user_version").fetchone()[0]
            for i, sql in enumerate(MIGRATIONS[version:], start=version + 1):
                con.executescript(sql)
                con.execute(f"PRAGMA user_version = {i}")
