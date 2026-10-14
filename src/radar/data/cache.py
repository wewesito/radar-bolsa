"""Caché clave-valor en SQLite con TTL.

Guarda JSON (no pickle) para que el contenido sea legible y seguro de cargar.
Una conexión por operación: Streamlit ejecuta cada sesión en su propio hilo.
"""

import json
import sqlite3
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class CacheEntry:
    value: Any
    fetched_at: datetime

    def age_seconds(self, now: float) -> float:
        return now - self.fetched_at.timestamp()


class Cache:
    def __init__(self, path: Path, clock: Callable[[], float] = time.time):
        self.path = path
        self.clock = clock  # inyectable para testear la caducidad sin esperar
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as con:
            con.execute(
                "CREATE TABLE IF NOT EXISTS cache ("
                " key TEXT PRIMARY KEY, value TEXT NOT NULL, fetched_at REAL NOT NULL)"
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Abre, confirma y cierra. (`with sqlite3.connect()` confirma pero NO cierra.)"""
        con = sqlite3.connect(self.path, timeout=10)
        try:
            with con:
                yield con
        finally:
            con.close()

    def get(self, key: str, ttl: float) -> CacheEntry | None:
        """Devuelve la entrada solo si tiene menos de `ttl` segundos."""
        entry = self.get_any(key)
        if entry is None or entry.age_seconds(self.clock()) > ttl:
            return None
        return entry

    def get_any(self, key: str) -> CacheEntry | None:
        """Devuelve la entrada aunque esté caducada (respaldo si la fuente falla)."""
        with self._connect() as con:
            row = con.execute(
                "SELECT value, fetched_at FROM cache WHERE key = ?", (key,)
            ).fetchone()
        if row is None:
            return None
        return CacheEntry(json.loads(row[0]), datetime.fromtimestamp(row[1], UTC))

    def set(self, key: str, value: Any) -> None:
        with self._connect() as con:
            con.execute(
                "INSERT OR REPLACE INTO cache (key, value, fetched_at) VALUES (?, ?, ?)",
                (key, json.dumps(value), self.clock()),
            )

    def clear(self) -> None:
        with self._connect() as con:
            con.execute("DELETE FROM cache")


def df_to_json(df: pd.DataFrame) -> str:
    return df.to_json(orient="split", date_format="iso", date_unit="s")


def df_from_json(payload: str) -> pd.DataFrame:
    df = pd.read_json(StringIO(payload), orient="split", convert_dates=False)
    df.index = pd.to_datetime(df.index, utc=True)
    return df
