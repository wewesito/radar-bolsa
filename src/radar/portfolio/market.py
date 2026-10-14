"""Datos de mercado para la cartera: precios y tipos de cambio en fechas concretas."""

from datetime import UTC, date, datetime

import pandas as pd

from radar.data.service import MarketDataService
from radar.portfolio.calc import fx_pair, to_eur_rate

# Índices de referencia. ETFs cotizados en EUR: así la comparación no depende del tipo de
# cambio y (al ser de acumulación) incluyen los dividendos reinvertidos.
BENCHMARKS = {
    "MSCI World (ETF EUNL.DE, en €, con dividendos)": "EUNL.DE",
    "S&P 500 (ETF SXR8.DE, en €, con dividendos)": "SXR8.DE",
    "IBEX 35 (^IBEX, sin dividendos)": "^IBEX",
}


def range_for(start: date) -> str:
    """El rango diario más corto que cubre desde `start` hasta hoy."""
    days = (datetime.now(UTC).date() - start).days
    if days <= 360:
        return "1A"
    if days <= 720:
        return "2A"
    if days <= 1800:
        return "5Ad"
    return "Máx"  # mensual: menos preciso, pero es lo que hay más allá de 5 años


def close_on(series: pd.Series, d: date) -> float | None:
    """Último cierre en o antes de `d` (si `d` es festivo, el del día hábil anterior)."""
    idx = pd.DatetimeIndex(series.index)
    if idx.tz is not None:
        idx = idx.tz_convert("Europe/Madrid").tz_localize(None)
    s = pd.Series(series.to_numpy(), index=idx.normalize())
    past = s.loc[: pd.Timestamp(d)]
    return float(past.iloc[-1]) if not past.empty else None


def price_on(svc: MarketDataService, ticker: str, d: date) -> float | None:
    if d >= datetime.now(UTC).date():
        return svc.get_quote(ticker).price
    return close_on(svc.get_history(ticker, range_for(d)).data["Close"], d)


def fx_to_eur_on(svc: MarketDataService, currency: str, d: date) -> float:
    """Euros por 1 unidad de `currency` en la fecha `d`."""
    pair, _ = fx_pair(currency)
    if pair is None:
        return 1.0
    if d >= datetime.now(UTC).date():
        return to_eur_rate(currency, svc.get_quote(pair).price)
    return to_eur_rate(currency, close_on(svc.get_history(pair, range_for(d)).data["Close"], d))


def fx_series_to_eur(svc: MarketDataService, currency: str, range_key: str) -> pd.Series:
    """Serie diaria de euros por unidad de `currency`."""
    pair, divisor = fx_pair(currency)
    close = svc.get_history(pair, range_key).data["Close"]
    return 1.0 / close / divisor
