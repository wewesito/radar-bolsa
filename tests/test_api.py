"""API local con un proveedor falso y un universo sintético (sin red)."""

from datetime import UTC, datetime

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from radar.api.app import create_app
from radar.api.state import Engine
from radar.data.cache import Cache
from radar.data.service import MarketDataService
from radar.db.database import Database
from radar.errors import TickerNotFoundError
from radar.models import PriceHistory, SearchResult
from radar.scoring.score import COMPONENTS
from radar.universe import UniverseSnapshot

TOKEN = "secreto"
T0 = datetime(2026, 10, 14, 8, 0, tzinfo=UTC)
INPUTS = {i.key for c in COMPONENTS for i in c.inputs}


class FakeProvider:
    name = "Fake"

    def get_history(self, ticker, range_key):
        if ticker == "NOPE":
            raise TickerNotFoundError(ticker)
        idx = pd.date_range("2026-09-01", periods=30, freq="D", tz="UTC")
        df = pd.DataFrame(
            {"Open": 1.0, "High": 2.0, "Low": 0.5, "Close": 1.5, "Volume": 10,
             "PriceClose": 1.4, "Dividends": 0.0},
            index=idx,
        )  # fmt: skip
        return PriceHistory(ticker, range_key, "1d", df, T0, "Fake")

    def get_quote(self, ticker):
        raise TickerNotFoundError(ticker)

    def get_fundamentals(self, ticker):
        raise TickerNotFoundError(ticker)

    def search(self, query):
        return [SearchResult("TEF", "Telefonica SA ADR", "EQUITY", "NYSE")]


def snapshot() -> UniverseSnapshot:
    rows = []
    for k in range(1, 9):
        row = {
            "ticker": f"E{k}.MC",
            "name": f"Eléctrica {k}",
            "quote_type": "EQUITY",
            "sector": "Utilities",
            "region": "Europa",
            "spain_index": "IBEX 35" if k < 5 else "Mercado Continuo",
            "price": 10.0,
            "price_currency": "EUR",
            "profit_margin": 0.1,
            "market_cap": 5e9,
            "vol_1y": 0.15,
            "mdd_1y": -0.1,
        }
        row.update({key: float(k) for key in INPUTS if key not in ("vol_1y", "mdd_1y")})
        rows.append(row)
    rows.append({**rows[0], "ticker": "Telefónica.MC", "name": "Telefónica, S.A."})
    rows.append({"ticker": "VWCE.DE", "name": "Vanguard", "quote_type": "ETF", "price": 100.0,
                 "vol_1y": 0.12, "mdd_1y": -0.08, "expense_ratio": 0.0019})  # fmt: skip
    return UniverseSnapshot(pd.DataFrame(rows), T0, [])


@pytest.fixture
def client(tmp_path):
    svc = MarketDataService(FakeProvider(), Cache(tmp_path / "c.db"))
    engine = Engine(svc, Database(tmp_path / "r.db"))
    engine.snapshot = snapshot()
    c = TestClient(create_app(engine, TOKEN))
    c.headers["X-Radar-Token"] = TOKEN
    return c


ANSWERS = {"horizon": 2, "reaction": 2, "amount": 2, "objective": "growth", "experience": 2}


def test_requires_token(client):
    assert client.get("/health").status_code == 200  # sin token
    r = client.get("/api/profile", headers={"X-Radar-Token": "otro"})
    assert r.status_code == 401


def test_profile_flow(client):
    assert client.get("/api/profile").json() == {"answers": None, "profile": None}
    r = client.get("/api/recommendations")
    assert r.status_code == 409 and r.json()["code"] == "no_profile"
    r = client.put("/api/profile", json=ANSWERS)
    assert r.status_code == 200
    assert r.json()["profile"]["label"] == "Moderado"
    assert client.put("/api/profile", json={**ANSWERS, "horizon": 9}).status_code == 422


def test_recommendations_and_detail(client):
    client.put("/api/profile", json=ANSWERS)
    body = client.get("/api/recommendations").json()
    assert sum(body["counts"].values()) == len(body["items"]) == 10
    item = body["items"][0]
    assert {"label_es", "score", "risk_label", "summary", "market"} <= set(item)
    assert "components" not in item
    detail = client.get("/api/recommendations/E8.MC").json()
    assert detail["ticker"] == "E8.MC" and len(detail["components"]) >= 5
    assert detail["market"]["exchange"].startswith("Bolsa de Madrid")
    assert detail["profile_is_default"] is False
    etf = client.get("/api/recommendations/VWCE.DE").json()
    assert etf["kind"] == "etf" and etf["etf"]["role"] == "core"


def test_unknown_ticker_is_friendly_404(client):
    client.put("/api/profile", json=ANSWERS)
    r = client.get("/api/recommendations/NOPE")
    assert r.status_code == 404 and "NOPE" in r.json()["detail"]


def test_spain_uses_default_profile_without_test(client):
    body = client.get("/api/spain").json()
    assert body["profile_is_default"] is True
    assert {r["spain_index"] for r in body["items"]} == {"IBEX 35", "Mercado Continuo"}
    assert all(r["pe_sector"] is not None for r in body["items"])


def test_no_universe_is_409(client, tmp_path):
    svc = MarketDataService(FakeProvider(), Cache(tmp_path / "c2.db"))
    c = TestClient(create_app(Engine(svc, Database(tmp_path / "r2.db")), TOKEN))
    r = c.get("/api/spain", headers={"X-Radar-Token": TOKEN})
    assert r.status_code == 409 and r.json()["code"] == "no_universe"


def test_search_folds_accents_and_falls_back_to_source(client):
    res = client.get("/api/search", params={"q": "telefonica"}).json()
    assert res[0]["ticker"] == "Telefónica.MC" and res[0]["in_universe"] is True
    assert any(r["ticker"] == "TEF" and r["in_universe"] is False for r in res)
    assert client.get("/api/search", params={"q": "e"}).json() == []


def test_history_returns_real_price_points(client):
    body = client.get("/api/history/E1.MC", params={"range": "1M"}).json()
    assert body["points"][0][1] == pytest.approx(1.4)  # PriceClose, no el ajustado
    assert body["source"] == "Fake"
    assert client.get("/api/history/E1.MC", params={"range": "3D"}).status_code == 422


def test_glossary_and_methodology(client):
    g = client.get("/api/glossary").json()
    assert any(e["key"] == "model_label" for e in g["entries"])
    m = client.get("/api/methodology").json()
    assert "Comprar" in m["signal"] and "Puntos de riesgo" in m["profile"]
