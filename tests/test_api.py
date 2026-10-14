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
from radar.models import PriceHistory, Quote, SearchResult
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


def test_backtest_endpoint_serves_cached_result(tmp_path):
    from radar.backtest.engine import run_backtest
    from radar.backtest.service import CACHE_KEY, _plain, result_to_dict

    svc = MarketDataService(FakeProvider(), Cache(tmp_path / "c.db"))
    engine = Engine(svc, Database(tmp_path / "r.db"))
    c = TestClient(create_app(engine, TOKEN))
    c.headers["X-Radar-Token"] = TOKEN
    assert c.get("/api/backtest").json() == {"result": None, "running": False, "error": None}

    idx = pd.date_range("2020-01-03", periods=130, freq="W-FRI")
    growth = {f"A{k}": 100 * (1 + 0.002 * k) ** pd.RangeIndex(130) for k in range(1, 9)}
    prices = pd.DataFrame(growth, index=idx)
    bench = {"Ref": pd.Series(range(100, 230), index=idx, dtype=float)}
    res = result_to_dict(run_backtest(prices, bench), ["X"], T0.isoformat())
    svc.cache.set(CACHE_KEY, _plain(res))

    body = c.get("/api/backtest").json()["result"]
    assert body["failed"] == ["X"] and body["last_selection"]["picks"]
    assert body["metrics"]["Ref"]["cagr"] > 0 and len(body["dates"]) == len(body["series"]["Ref"])


def test_guides_and_calculators(client):
    g = client.get("/api/guides").json()
    assert {x["key"] for x in g["guides"]} >= {"broker", "ordenes", "fiscalidad"}
    assert g["concepts"]
    c = client.get(
        "/api/calc/compound", params={"initial": 1000, "monthly": 100, "years": 10}
    ).json()
    assert c["rows"][0]["year"] == 0 and c["rows"][-1]["contributed"] == 1000 + 100 * 120
    assert c["gain"] > 0 and c["real_value"] < c["rows"][-1]["value"]
    assert client.get("/api/calc/compound", params={"years": 99}).status_code == 422
    t = client.get("/api/calc/tax", params={"base": 10000}).json()
    assert round(t["tax"], 2) == 6000 * 0.19 + 4000 * 0.21
    assert client.get("/api/calc/tax", params={"base": -1}).status_code == 422


class QuoteProvider(FakeProvider):
    def get_quote(self, ticker):
        if ticker == "NOPE":
            raise TickerNotFoundError(ticker)
        return Quote(ticker, "Eléctrica", 12.0, 11.0, 1000, "EUR", "MCE", "EQUITY", "REGULAR",
                     15, T0, "Fake")  # fmt: skip


@pytest.fixture
def qclient(tmp_path):
    svc = MarketDataService(QuoteProvider(), Cache(tmp_path / "c.db"))
    engine = Engine(svc, Database(tmp_path / "r.db"))
    engine.snapshot = snapshot()
    c = TestClient(create_app(engine, TOKEN))
    c.headers["X-Radar-Token"] = TOKEN
    return c


def test_portfolio_flow(qclient):
    c = qclient
    assert c.get("/api/portfolio").json()["trade_count"] == 0
    t = {
        "ticker": "e1.mc",
        "side": "BUY",
        "quantity": 10,
        "price": 10.0,
        "fee": 1,
        "date": "2026-09-05",
    }
    assert c.post("/api/portfolio/trades", json=t).status_code == 200
    body = c.get("/api/portfolio").json()
    pos = body["positions"][0]
    assert pos["ticker"] == "E1.MC" and pos["name"] == "Eléctrica 1"
    assert (
        body["summary"]["market_value_eur"] == 120.0
        and body["summary"]["unrealized_eur"] == 120 - 101
    )
    assert body["by_sector"] and body["effective_positions"] == 1.0
    assert body["chart"] is None or len(body["chart"]["dates"]) == len(body["chart"]["value"])
    # no se puede vender lo que no se tiene
    sell = {**t, "side": "SELL", "quantity": 50}
    r = c.post("/api/portfolio/trades", json=sell)
    assert r.status_code == 422 and r.json()["code"] == "invalid"
    assert c.post("/api/portfolio/trades", json={**t, "date": "2999-01-01"}).status_code == 422
    assert c.get("/api/portfolio", params={"bench": "XXX"}).status_code == 422
    tid = c.get("/api/portfolio/trades").json()[0]["id"]
    assert c.delete(f"/api/portfolio/trades/{tid}").status_code == 200
    assert c.get("/api/portfolio").json()["trade_count"] == 0


def test_alerts_flow(qclient):
    c = qclient
    a = {"ticker": "e1.mc", "metric": "price", "op": "above", "threshold": 15}
    assert c.post("/api/alerts", json=a).status_code == 200
    assert c.post("/api/alerts", json={**a, "threshold": None}).status_code == 422
    assert c.post("/api/alerts", json={**a, "ticker": "NOPE"}).status_code == 404
    assert c.post("/api/alerts/check").json() == {
        "fired": []
    }  # primera evaluación: solo fija estado
    body = c.get("/api/alerts").json()
    assert body["alerts"][0]["text"].startswith("E1.MC")
    assert body["alerts"][0]["last_value"] == 12.0
    aid = body["alerts"][0]["id"]
    assert c.put(f"/api/alerts/{aid}/active", params={"active": False}).status_code == 200
    assert c.delete(f"/api/alerts/{aid}").status_code == 200
    assert c.get("/api/alerts").json()["alerts"] == []
