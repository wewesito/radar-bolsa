"""Repositorio de operaciones de la cartera simulada."""

from datetime import date

from radar.db.database import Database
from radar.portfolio.calc import Trade, build_positions, validate_new_trade


class TradesRepo:
    def __init__(self, db: Database):
        self.db = db

    def list(self) -> list[Trade]:
        with self.db.connect() as con:
            rows = con.execute(
                "SELECT id, ticker, side, quantity, price, fee, currency, trade_date, fx_to_eur,"
                " note FROM trades ORDER BY trade_date, id"
            ).fetchall()
        return [
            Trade(
                r["ticker"],
                r["side"],
                r["quantity"],
                r["price"],
                r["fee"],
                r["currency"],
                date.fromisoformat(r["trade_date"]),
                r["fx_to_eur"],
                r["id"],
                r["note"],
            )
            for r in rows
        ]

    def add(self, t: Trade) -> int:
        """Valida (FIFO: no se puede vender lo que no se tiene) y guarda. Devuelve el id."""
        validate_new_trade(self.list(), t)
        with self.db.connect() as con:
            cur = con.execute(
                "INSERT INTO trades (ticker, side, quantity, price, fee, currency, trade_date,"
                " fx_to_eur, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    t.ticker,
                    t.side,
                    t.quantity,
                    t.price,
                    t.fee,
                    t.currency,
                    t.trade_date.isoformat(),
                    t.fx_to_eur,
                    t.note,
                ),
            )
            return int(cur.lastrowid)

    def delete(self, trade_id: int) -> None:
        """Borra una operación si la cartera resultante sigue siendo posible."""
        remaining = [t for t in self.list() if t.id != trade_id]
        build_positions(remaining)  # lanza PortfolioError si, p. ej., deja una venta sin compra
        with self.db.connect() as con:
            con.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
