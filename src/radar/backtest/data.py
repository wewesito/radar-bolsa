"""Datos del backtest: precios semanales en euros (con dividendos) e índices de referencia.

Es la única parte del backtest con E/S; todo pasa por el servicio de datos (caché con TTL).
"""

from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from radar.data.service import MarketDataService
from radar.errors import RadarError

RANGE = "10Aw"
WEEK = "W-FRI"

# IBEX 35 con dividendos: Yahoo no tiene el índice, se aproxima con el ETF que lo replica
# (Amundi IBEX 35, LYXIB.MC) usando su precio ajustado por dividendos (lleva su comisión).
IBEX_TR = ("LYXIB.MC", "IBEX 35 con dividendos (ETF LYXIB.MC)")
SP500_TR = ("^SP500TR", "S&P 500 con dividendos (en euros)")

# moneda → (par de Yahoo, cómo pasarlo a "euros por unidad")
FX: dict[str, tuple[str, str]] = {
    "USD": ("EURUSD=X", "inverse"),
    "GBP": ("GBPEUR=X", "direct"),
    "GBp": ("GBPEUR=X", "pence"),
    "CHF": ("CHFEUR=X", "direct"),
}


def weekly(series: pd.Series) -> pd.Series:
    s = series.copy()
    s.index = pd.DatetimeIndex(s.index).tz_convert("UTC").tz_localize(None)
    return s.resample(WEEK).last()


def eur_rates(svc: MarketDataService, currency: str) -> pd.Series | None:
    """Euros por unidad de `currency`, semanal. None si la moneda no está soportada."""
    if currency == "EUR":
        return None
    pair, mode = FX[currency]
    rate = weekly(svc.get_history(pair, RANGE).data["Close"])
    if mode == "inverse":
        return 1 / rate
    return rate / 100 if mode == "pence" else rate


def load_prices(
    svc: MarketDataService, currencies: dict[str, str]
) -> tuple[pd.DataFrame, list[str]]:
    """Cierres semanales ajustados por dividendos y pasados a euros. (precios, fallidos)."""
    fx: dict[str, pd.Series | None] = {}
    for cur in set(currencies.values()):
        if cur == "EUR" or cur in FX:
            fx[cur] = eur_rates(svc, cur)

    def one(item: tuple[str, str]) -> tuple[str, pd.Series | None]:
        ticker, cur = item
        if cur not in fx:
            return ticker, None
        try:
            s = weekly(svc.get_history(ticker, RANGE).data["Close"])
        except RadarError:
            return ticker, None
        rate = fx[cur]
        return ticker, s if rate is None else s * rate.reindex(s.index, method="ffill")

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(one, currencies.items()))
    cols = {t: s for t, s in results if s is not None and s.notna().sum() > 60}
    failed = sorted(t for t, _ in results if t not in cols)
    prices = pd.DataFrame(cols).sort_index()
    return prices.iloc[:-1] if len(prices) > 1 else prices, failed  # última semana incompleta


def load_benchmarks(svc: MarketDataService) -> dict[str, pd.Series]:
    out = {}
    ibex = weekly(svc.get_history(IBEX_TR[0], RANGE).data["Close"])
    out[IBEX_TR[1]] = ibex
    sp = weekly(svc.get_history(SP500_TR[0], RANGE).data["Close"])
    usd = eur_rates(svc, "USD")
    out[SP500_TR[1]] = sp * usd.reindex(sp.index, method="ffill")
    return out
