"""Repositorio de la watchlist."""

from dataclasses import dataclass

from radar.db.database import Database


@dataclass(frozen=True)
class WatchItem:
    ticker: str
    name: str
    added_at: str


class WatchlistRepo:
    def __init__(self, db: Database):
        self.db = db

    def list(self) -> list[WatchItem]:
        with self.db.connect() as con:
            rows = con.execute("SELECT ticker, name, added_at FROM watchlist ORDER BY added_at, rowid")
            return [WatchItem(**dict(r)) for r in rows]

    def tickers(self) -> list[str]:
        return [item.ticker for item in self.list()]

    def add(self, ticker: str, name: str) -> bool:
        """Añade el ticker. Devuelve False si ya estaba."""
        with self.db.connect() as con:
            cur = con.execute(
                "INSERT OR IGNORE INTO watchlist (ticker, name) VALUES (?, ?)", (ticker, name)
            )
            return cur.rowcount == 1

    def remove(self, ticker: str) -> bool:
        with self.db.connect() as con:
            return con.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker,)).rowcount == 1
