"""Repositorio de ajustes: valores JSON por clave (perfil inversor, preferencias)."""

import json
from typing import Any

from radar.db.database import Database


class SettingsRepo:
    def __init__(self, db: Database):
        self.db = db

    def get(self, key: str) -> Any | None:
        with self.db.connect() as con:
            row = con.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return json.loads(row["value"]) if row else None

    def set(self, key: str, value: Any) -> None:
        with self.db.connect() as con:
            con.execute(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT (key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
                """,
                (key, json.dumps(value, ensure_ascii=False)),
            )

    def delete(self, key: str) -> None:
        with self.db.connect() as con:
            con.execute("DELETE FROM settings WHERE key = ?", (key,))
