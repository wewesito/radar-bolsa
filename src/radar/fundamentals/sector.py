"""Comparación de métricas con los comparables del sector (funciones puras).

Decisiones de método:
- Usamos la MEDIANA, no la media: un PER de 400 (beneficio casi nulo) no la descuadra.
- Comparables = mismo sector y misma región si hay al menos MIN_PEERS; si no, el sector
  a nivel mundial. Europa y EE. UU. cotizan a múltiplos distintos (PER medio de EE. UU.
  más alto), así que mezclarlas haría parecer "baratas" a todas las europeas.
- El percentil se calcula con rango medio: los empates cuentan la mitad.
"""

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from radar.data.markets import US, exchange_for
from radar.fundamentals.metrics import Better

MIN_PEERS = 5

SECTOR_ES = {
    "Financial Services": "Servicios financieros",
    "Industrials": "Industria",
    "Consumer Cyclical": "Consumo cíclico",
    "Consumer Defensive": "Consumo defensivo",
    "Technology": "Tecnología",
    "Utilities": "Utilities (eléctricas, gas, agua)",
    "Healthcare": "Salud",
    "Communication Services": "Telecomunicaciones y medios",
    "Basic Materials": "Materiales básicos",
    "Real Estate": "Inmobiliario",
    "Energy": "Energía",
}


COUNTRY_ES = {
    "Spain": "España",
    "United States": "EE. UU.",
    "Germany": "Alemania",
    "France": "Francia",
    "Netherlands": "Países Bajos",
    "Italy": "Italia",
    "Belgium": "Bélgica",
    "Finland": "Finlandia",
    "United Kingdom": "Reino Unido",
    "Switzerland": "Suiza",
    "Portugal": "Portugal",
    "Ireland": "Irlanda",
    "Luxembourg": "Luxemburgo",
}


def country_es(country: str | None) -> str:
    return COUNTRY_ES.get(country or "", country or "n/d")


def sector_es(sector: str | None) -> str:
    return SECTOR_ES.get(sector or "", sector or "Sin sector")


def region_for(ticker: str) -> str:
    ex = exchange_for(ticker)
    if ex is US:
        return "EE. UU."
    if ex is not None:
        return "Europa"
    return "Otros"


def add_derived(metrics: dict[str, float | None]) -> dict[str, float | None]:
    """Métricas derivadas comparables entre empresas de distinto tamaño."""
    out = dict(metrics)
    fcf, cap, rev = metrics.get("free_cash_flow"), metrics.get("market_cap"), metrics.get("revenue")
    # FCF yield: flujo de caja libre / capitalización. Como un "PER al revés" con caja.
    out["fcf_yield"] = fcf / cap if fcf is not None and cap else None
    # Margen FCF: qué parte de las ventas acaba siendo caja libre.
    out["fcf_margin"] = fcf / rev if fcf is not None and rev else None
    return out


def percentile_rank(
    value: float, peers: Sequence[float], better: Better = "higher"
) -> float | None:
    """Fracción (0–1) de comparables a los que `value` supera según `better`.

    Con better="lower" (p. ej. PER) un valor bajo da percentil alto. Sin dirección
    (better=None) se mide simplemente qué fracción de comparables tiene un valor menor.
    """
    arr = np.asarray([p for p in peers if p is not None and np.isfinite(p)], dtype=float)
    if arr.size == 0:
        return None
    below = float(np.sum(arr < value))
    equal = float(np.sum(arr == value))
    pct = (below + 0.5 * equal) / arr.size
    return 1 - pct if better == "lower" else pct


@dataclass(frozen=True)
class PeerStats:
    n: int
    median: float
    p25: float
    p75: float


def peer_stats(values: Sequence[float | None]) -> PeerStats | None:
    arr = np.asarray([v for v in values if v is not None and np.isfinite(v)], dtype=float)
    if arr.size < MIN_PEERS:
        return None
    return PeerStats(
        int(arr.size),
        float(np.median(arr)),
        float(np.percentile(arr, 25)),
        float(np.percentile(arr, 75)),
    )


def select_peers(
    universe: pd.DataFrame, sector: str | None, region: str, exclude: str | None = None
) -> tuple[pd.DataFrame, str]:
    """Devuelve (comparables, descripción del grupo usado)."""
    if not sector:
        return universe.iloc[0:0], "sin sector"
    same_sector = universe[(universe["sector"] == sector) & (universe["ticker"] != exclude)]
    same_region = same_sector[same_sector["region"] == region]
    if len(same_region) >= MIN_PEERS:
        return same_region, f"{sector_es(sector)} · {region}"
    return same_sector, f"{sector_es(sector)} · mundial (pocas empresas en {region})"


@dataclass(frozen=True)
class MetricComparison:
    key: str
    value: float | None
    stats: PeerStats | None
    percentile: float | None  # ya orientado: alto = favorable si la métrica tiene dirección
    reading: str


def compare_metric(
    key: str, value: float | None, peers: pd.DataFrame, better: Better
) -> MetricComparison:
    stats = peer_stats(peers[key].tolist()) if key in peers else None
    if value is None:
        return MetricComparison(key, None, stats, None, "sin dato")
    if stats is None:
        return MetricComparison(key, value, None, None, "pocos comparables")
    pct = percentile_rank(value, peers[key].dropna().tolist(), better)
    if better is None:
        reading = "dato descriptivo (ni mejor ni peor)"
    elif pct >= 0.75:
        reading = "favorable frente al sector"
    elif pct <= 0.25:
        reading = "desfavorable frente al sector"
    else:
        reading = "en línea con el sector"
    return MetricComparison(key, value, stats, pct, reading)
