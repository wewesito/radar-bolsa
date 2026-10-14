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
