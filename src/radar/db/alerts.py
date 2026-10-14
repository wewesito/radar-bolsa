"""Repositorio de alertas y de los avisos que han disparado."""

from dataclasses import dataclass
from datetime import UTC, datetime

from radar.alerts.rules import Alert
from radar.db.database import Database


@dataclass(frozen=True)
class AlertEvent:
    id: int
    alert_id: int
    triggered_at: datetime
    value: float
    message: str
    seen: bool


def _row_to_alert(r) -> Alert:
    state = r["last_state"]
    return Alert(
        r["ticker"],
        r["metric"],
        r["op"],
        r["threshold"],
        r["id"],
        bool(r["active"]),
        None if state is None else bool(state),
    )


class AlertsRepo:
    def __init__(self, db: Database):
        self.db = db

    def list(self, only_active: bool = False) -> list[Alert]:
        sql = "SELECT * FROM alerts" + (" WHERE active = 1" if only_active else "") + " ORDER BY id"
        with self.db.connect() as con:
            return [_row_to_alert(r) for r in con.execute(sql)]

    def last_values(self) -> dict[int, tuple[float | None, str | None]]:
        with self.db.connect() as con:
            rows = con.execute("SELECT id, last_value, last_checked_at FROM alerts")
            return {r["id"]: (r["last_value"], r["last_checked_at"]) for r in rows}

    def add(self, a: Alert) -> int:
        with self.db.connect() as con:
            cur = con.execute(
                "INSERT INTO alerts (ticker, metric, op, threshold) VALUES (?, ?, ?, ?)",
                (a.ticker, a.metric, a.op, a.threshold),
            )
            return int(cur.lastrowid)

    def delete(self, alert_id: int) -> None:
        with self.db.connect() as con:
            con.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))

    def set_active(self, alert_id: int, active: bool) -> None:
        with self.db.connect() as con:
            con.execute(
                "UPDATE alerts SET active = ?, last_state = NULL WHERE id = ?",
                (int(active), alert_id),
            )

    def save_check(self, alert_id: int, state: bool, value: float) -> None:
        with self.db.connect() as con:
            con.execute(
                "UPDATE alerts SET last_state = ?, last_value = ?, last_checked_at = ?"
                " WHERE id = ?",
                (int(state), value, datetime.now(UTC).isoformat(), alert_id),
            )

    def add_event(self, alert_id: int, value: float, message: str) -> None:
        with self.db.connect() as con:
            con.execute(
                "INSERT INTO alert_events (alert_id, triggered_at, value, message)"
                " VALUES (?, ?, ?, ?)",
                (alert_id, datetime.now(UTC).isoformat(), value, message),
            )

    def events(self, limit: int = 50) -> list[AlertEvent]:
        with self.db.connect() as con:
            rows = con.execute(
                "SELECT * FROM alert_events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            AlertEvent(
                r["id"],
                r["alert_id"],
                datetime.fromisoformat(r["triggered_at"]),
                r["value"],
                r["message"],
                bool(r["seen"]),
            )
            for r in rows
        ]

    def mark_all_seen(self) -> None:
        with self.db.connect() as con:
            con.execute("UPDATE alert_events SET seen = 1 WHERE seen = 0")
