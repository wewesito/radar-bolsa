"""Construcción y carga del universo de referencia (foto de fundamentales y precios).

La foto se guarda en la caché con su fecha. No caduca sola: se muestra su antigüedad y el
usuario decide cuándo reconstruirla (los fundamentales cambian trimestralmente).

- Todos los valores: fundamentales + estadísticas de precio (momentum y riesgo).
- Valores españoles y ETFs: además, todo el histórico diario para rentabilidades a 3 y
  5 años y el historial de dividendos.
- Valores españoles: además, las cuentas anuales para el ROIC.
"""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime

import pandas as pd

from radar.data.cache import Cache
from radar.data.service import MarketDataService
from radar.errors import RadarError
from radar.etfs import BY_TICKER as ETF_INFO
from radar.fundamentals.sector import add_derived, region_for
from radar.indicators.performance import (
    dividend_sustainability,
    dividend_years,
    period_returns,
    roic,
)
from radar.indicators.quality import price_warning
from radar.indicators.risk import price_stats
from radar.models import Fundamentals
from radar.universe_list import UNIVERSE, spain_index

# v2: + precio; v3: + moneda; v4: + España, ETFs, plazos y ROIC
SNAPSHOT_KEY = "universe:snapshot:v6"  # v6: + aviso de datos de precio sospechosos
STALE_AFTER_DAYS = 7
TEXT_COLUMNS = [
    "ticker",
    "name",
    "quote_type",
    "sector",
    "industry",
    "country",
    "currency",
    "price_currency",
    "region",
    "spain_index",
    "div_sustainability",
    "history_as_of",
    "last_close",
    "fundamentals_as_of",
    "last_report",
    "data_warning",
]
# Sin fundamentales de negocio en bancos y aseguradoras (su deuda es su materia prima).
NO_ROIC_SECTORS = {"Financial Services"}


@dataclass(frozen=True)
class UniverseSnapshot:
    df: pd.DataFrame
    built_at: datetime
    failed: list[str]

    @property
    def age_days(self) -> float:
        return (datetime.now(UTC) - self.built_at).total_seconds() / 86400


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def fundamentals_row(f: Fundamentals) -> dict:
    """Fila plana (ticker, sector, región y métricas) para un DataFrame de comparables."""
    return {
        "ticker": f.ticker,
        "name": f.name,
        "quote_type": f.quote_type,
        "sector": f.sector,
        "industry": f.industry,
        "country": f.country,
        "currency": f.currency,
        "price_currency": f.price_currency or f.currency,
        "region": region_for(f.ticker),
        "spain_index": spain_index(f.ticker),
        "fundamentals_as_of": _iso(f.as_of),
        "last_report": _iso(f.last_report),
        **add_derived(f.metrics),
    }


def needs_long_history(ticker: str) -> bool:
    return spain_index(ticker) is not None or ticker in ETF_INFO


def company_row(svc: MarketDataService, ticker: str) -> dict:
    """Fila completa de un valor. Sin histórico, momentum y riesgo quedan sin dato."""
    f = svc.get_fundamentals(ticker)
    row = fundamentals_row(f)
    long = needs_long_history(ticker)
    with suppress(RadarError):
        hist = svc.get_history(ticker, "MAXd" if long else "2A")
        data = hist.data
        row["history_as_of"] = _iso(hist.as_of)
        row["last_close"] = data.index[-1].isoformat()
        price_col = data["PriceClose"] if "PriceClose" in data else data["Close"]
        row["price"] = float(price_col.iloc[-1])
        row.update(price_stats(data["Close"]))
        row["data_warning"] = price_warning(price_col)
        if long:
            row.update(period_returns(price_col, data["Close"]))
            if "Dividends" in data:
                row["div_years"] = float(dividend_years(data["Dividends"], data.index[-1]))
    if row["spain_index"] and f.quote_type == "EQUITY" and f.sector not in NO_ROIC_SECTORS:
        with suppress(RadarError):
            row["roic"] = roic(svc.get_financials(ticker).items)
    if row["spain_index"]:
        row["div_sustainability"] = dividend_sustainability(
            row.get("payout_ratio"), row.get("dividend_yield"), int(row.get("div_years") or 0)
        )
    return row


def build_universe(
    svc: MarketDataService,
    tickers: list[str] = UNIVERSE,
    on_progress: Callable[[int, int], None] | None = None,
) -> UniverseSnapshot:
    rows, failed = [], []

    def one(t: str) -> dict:
        return company_row(svc, t)

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(one, t): t for t in tickers}
        for i, fut in enumerate(as_completed(futures), start=1):
            try:
                rows.append(fut.result())
            except RadarError:
                failed.append(futures[fut])
            if on_progress:
                on_progress(i, len(tickers))

    snap = UniverseSnapshot(pd.DataFrame(rows), datetime.now(UTC), sorted(failed))
    svc.cache.set(
        SNAPSHOT_KEY,
        {
            # astype(object) + where: los NaN pasan a None para que el JSON sea estándar
            "rows": snap.df.astype(object).where(snap.df.notna(), None).to_dict("records"),
            "built_at": snap.built_at.isoformat(),
            "failed": snap.failed,
        },
    )
    return snap


def load_universe(cache: Cache) -> UniverseSnapshot | None:
    entry = cache.get_any(SNAPSHOT_KEY)
    if entry is None:
        return None
    v = entry.value
    df = pd.DataFrame(v["rows"])
    for col in df.columns.difference(TEXT_COLUMNS):
        df[col] = pd.to_numeric(df[col], errors="coerce")  # None → NaN, todo float
    # En las de texto, un hueco es None (no NaN, que es "verdadero" y no es un texto)
    text = df.columns.intersection(TEXT_COLUMNS)
    df[text] = df[text].astype(object).where(df[text].notna(), None)
    return UniverseSnapshot(df, datetime.fromisoformat(v["built_at"]), v["failed"])
