"""Registro diario de señales: una foto de «Comprar / Vigilar / Evitar» por fecha."""

from dataclasses import dataclass
from datetime import date

from radar.db.database import Database


@dataclass(frozen=True)
class LoggedSignal:
    logged_on: date
    ticker: str
    label: str
    score: float | None
    price: float
    profile: str


class SignalsRepo:
    def __init__(self, db: Database):
        self.db = db

    def has_day(self, day: date) -> bool:
        with self.db.connect() as con:
            row = con.execute(
                "SELECT 1 FROM signal_log WHERE logged_on = ? LIMIT 1", (day.isoformat(),)
            ).fetchone()
        return row is not None

    def add_day(self, day: date, signals: list[LoggedSignal]) -> int:
        """Guarda las señales del día (si ya había, se respetan las primeras). Devuelve cuántas."""
        with self.db.connect() as con:
            cur = con.executemany(
                "INSERT OR IGNORE INTO signal_log (logged_on, ticker, label, score, price,"
                " profile) VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (day.isoformat(), s.ticker, s.label, s.score, s.price, s.profile)
                    for s in signals
                ],
            )
            return cur.rowcount

    def all(self) -> list[LoggedSignal]:
        with self.db.connect() as con:
            rows = con.execute("SELECT * FROM signal_log ORDER BY logged_on, ticker").fetchall()
        return [
            LoggedSignal(
                date.fromisoformat(r["logged_on"]),
                r["ticker"],
                r["label"],
                r["score"],
                r["price"],
                r["profile"],
            )
            for r in rows
        ]
