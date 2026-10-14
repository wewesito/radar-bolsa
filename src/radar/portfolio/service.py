"""Cartera simulada: valoración y alta de operaciones con datos de mercado (con E/S).

Los cálculos viven en `calc.py` (puros); aquí solo se piden precios, divisas e históricos.
"""

from collections.abc import Callable
from datetime import UTC, date, datetime

import pandas as pd

from radar.data.service import MarketDataService
from radar.db.trades import TradesRepo
from radar.errors import RadarError
from radar.portfolio.calc import (
    Trade,
    allocation,
    effective_positions,
    shadow_benchmark,
    summarize,
    value_series,
)
from radar.portfolio.market import (
    BENCHMARKS,
    fx_series_to_eur,
    fx_to_eur_on,
    price_on,
    range_for,
)

MAX_POINTS = 260  # puntos del gráfico (se reduce el muestreo en históricos largos)


def add_trade(
    svc: MarketDataService,
    repo: TradesRepo,
    ticker: str,
    side: str,
    quantity: float,
    price: float | None,
    fee: float,
    when: date,
    note: str | None,
) -> int:
    """Registra una operación ficticia. Sin precio, usa el cierre de esa fecha."""
    currency = svc.get_quote(ticker).currency or "EUR"
    if price is None:
        price = price_on(svc, ticker, when)
        if price is None:
            raise RadarError(f"No hay precio de {ticker} en esa fecha.")
    fx = fx_to_eur_on(svc, currency, when)
    return repo.add(Trade(ticker, side, quantity, price, fee, currency, when, fx, note=note))  # type: ignore[arg-type]


def _thin(s: pd.Series) -> pd.Series:
    step = max(1, len(s) // MAX_POINTS)
    out = s.iloc[::step]
    return out if out.index[-1] == s.index[-1] else pd.concat([out, s.iloc[[-1]]])


def portfolio_view(
    svc: MarketDataService,
    trades: list[Trade],
    bench: str,
    info: Callable[[str], dict],
) -> dict:
    """Resumen, posiciones y evolución frente a un índice.

    `info(ticker)` devuelve nombre, sector y país del valor.
    """
    now = datetime.now(UTC)
    tickers = sorted({t.ticker for t in trades})
    quotes = svc.get_quotes(tickers)
    prices = {t: q.price for t, q in quotes.items() if not isinstance(q, RadarError)}
    failed = [t for t, q in quotes.items() if isinstance(q, RadarError)]
    fx_now = {c: fx_to_eur_on(svc, c, now.date()) for c in {t.currency for t in trades}}
    summary, df = summarize(trades, prices, fx_now)
    rows = []
    for r in df.to_dict("records"):
        meta = info(r["ticker"])
        q = quotes.get(r["ticker"])
        rows.append(
            {
                **r,
                "name": meta.get("name") or r["ticker"],
                "sector": meta.get("sector"),
                "country": meta.get("country"),
                "price_as_of": None if isinstance(q, RadarError) or q is None else q.as_of,
                "delay_minutes": None
                if isinstance(q, RadarError) or q is None
                else q.delay_minutes,
            }
        )
    out: dict = {
        "summary": {
            "market_value_eur": summary.market_value_eur,
            "unrealized_eur": summary.unrealized_eur,
            "realized_eur": summary.realized_eur,
            "total_return": summary.total_return,
            "total_invested_eur": summary.total_invested_eur,
            "net_contributed_eur": summary.net_contributed_eur,
        },
        "positions": rows,
        "failed": failed,
        "as_of": now,
        "source": "Yahoo Finance",
        "effective_positions": None,
        "by_sector": {},
        "by_country": {},
        "chart": None,
    }
    if df.empty or not rows:
        return out
    wdf = pd.DataFrame(rows).dropna(subset=["value_eur"])
    wdf["sector"] = wdf["sector"].fillna("Sin sector")
    wdf["country"] = wdf["country"].fillna("Sin país")
    out["effective_positions"] = effective_positions(wdf.set_index("ticker")["weight"])
    out["by_sector"] = allocation(wdf, "sector").to_dict()
    out["by_country"] = allocation(wdf, "country").to_dict()
    out["chart"] = _chart(svc, trades, bench)
    return out


def _chart(svc: MarketDataService, trades: list[Trade], bench: str) -> dict | None:
    start = min(t.trade_date for t in trades)
    rkey = range_for(start)
    try:
        closes = {t: svc.get_history(t, rkey).data["Close"] for t in {x.ticker for x in trades}}
        fx = {c: fx_series_to_eur(svc, c, rkey) for c in {t.currency for t in trades} if c != "EUR"}
        vs = value_series(trades, closes, fx)
        shadow = shadow_benchmark(trades, svc.get_history(bench, rkey).data["Close"])
    except RadarError:
        return None
    vs = vs.dropna()
    if len(vs) < 2:
        return None
    shadow = shadow.reindex(vs.index).ffill()
    vs = _thin(vs["value"]).to_frame("value").join(vs["contributed"])
    shadow = shadow.reindex(vs.index)
    return {
        "dates": [d.date().isoformat() for d in vs.index],
        "value": [float(v) for v in vs["value"]],
        "contributed": [float(v) for v in vs["contributed"]],
        "benchmark": [None if pd.isna(v) else float(v) for v in shadow],
        "benchmark_name": next(n for n, t in BENCHMARKS.items() if t == bench),
    }
