"""Construcción y carga del universo de referencia (foto de fundamentales de ~120 empresas).

La foto se guarda en la caché con su fecha. No caduca sola: se muestra su antigüedad y el
usuario decide cuándo reconstruirla (los fundamentales cambian trimestralmente).
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
from radar.fundamentals.sector import add_derived, region_for
from radar.indicators.risk import price_stats
from radar.models import Fundamentals
from radar.universe_list import UNIVERSE

SNAPSHOT_KEY = "universe:snapshot:v3"  # v2: + estadísticas de precio; v3: + moneda
STALE_AFTER_DAYS = 7
TEXT_COLUMNS = ["ticker", "name", "sector", "industry", "country", "currency", "region"]


@dataclass(frozen=True)
class UniverseSnapshot:
    df: pd.DataFrame
    built_at: datetime
    failed: list[str]

    @property
    def age_days(self) -> float:
        return (datetime.now(UTC) - self.built_at).total_seconds() / 86400


def fundamentals_row(f: Fundamentals) -> dict:
    """Fila plana (ticker, sector, región y métricas) para un DataFrame de comparables."""
    return {
        "ticker": f.ticker,
        "name": f.name,
        "sector": f.sector,
        "industry": f.industry,
        "country": f.country,
        "currency": f.currency,
        "region": region_for(f.ticker),
        **add_derived(f.metrics),
    }


def company_row(svc: MarketDataService, ticker: str) -> dict:
    """Fundamentales + estadísticas de precio (2 años diarios) de una empresa."""
    row = fundamentals_row(svc.get_fundamentals(ticker))
    # Sin histórico, momentum y riesgo quedan sin dato (el score lo indica).
    with suppress(RadarError):
        row.update(price_stats(svc.get_history(ticker, "2A").data["Close"]))
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
    return UniverseSnapshot(df, datetime.fromisoformat(v["built_at"]), v["failed"])
