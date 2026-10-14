"""Construcción y recarga del universo con un servicio falso (sin red)."""

from datetime import UTC, datetime

from radar.data.cache import Cache
from radar.data.service import MarketDataService
from radar.errors import TickerNotFoundError
from radar.models import Fundamentals
from radar.universe import build_universe, load_universe


class FakeProvider:
    name = "Fake"

    def get_fundamentals(self, ticker):
        if ticker == "BAD.MC":
            raise TickerNotFoundError(ticker)
        return Fundamentals(
            ticker,
            ticker,
            "EQUITY",
            "Energy",
            None,
            "Spain",
            "EUR",
            metrics={
                "pe_trailing": 10.0,
                "free_cash_flow": 5.0,
                "market_cap": 100.0,
                "revenue": None,
                "expense_ratio": None,
            },
            as_of=datetime.now(UTC),
            source="Fake",
        )


def test_build_and_reload(tmp_path):
    svc = MarketDataService(FakeProvider(), Cache(tmp_path / "c.db"))
    calls = []
    snap = build_universe(svc, ["A.MC", "B.MC", "BAD.MC"], on_progress=lambda i, n: calls.append(i))

    assert snap.failed == ["BAD.MC"]
    assert len(snap.df) == 2
    assert calls == [1, 2, 3]

    back = load_universe(svc.cache)
    assert set(back.df["ticker"]) == {"A.MC", "B.MC"}
    assert back.df["fcf_yield"].iloc[0] == 0.05  # derivada calculada al construir
    assert back.df["expense_ratio"].dtype == float  # columnas vacías siguen siendo numéricas
    assert (back.df["region"] == "Europa").all()


def test_load_without_snapshot(tmp_path):
    assert load_universe(Cache(tmp_path / "c.db")) is None
