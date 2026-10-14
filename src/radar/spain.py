"""Sección España: tabla de rankings del IBEX 35 y el Mercado Continuo (función pura).

Cada fila trae las métricas de los cuatro rankings (bolsa, negocio, dividendo, valoración),
las medianas de su sector para comparar y la señal del modelo con el perfil del usuario.
Las medianas del sector se calculan con los mismos comparables que el score
(mismo sector y región; si hay pocos, el sector mundial).
"""

from collections.abc import Mapping

import numpy as np
import pandas as pd

from radar.fundamentals.sector import MIN_PEERS, sector_es, select_peers
from radar.recommend.engine import LABEL_ES, Recommendation

CHEAP_RATIO = 0.85  # PER más de un 15 % por debajo de la mediana del sector
EXPENSIVE_RATIO = 1.15

COLUMNS = [
    "market_cap",
    "price",
    "ret_ytd",
    "ret_1y",
    "ret_3y",
    "ret_5y",
    "tr_1y",
    "tr_5y",
    "roe",
    "roic",
    "operating_margin",
    "profit_margin",
    "earnings_growth",
    "revenue_growth",
    "dividend_yield",
    "div_years",
    "payout_ratio",
    "pe_trailing",
    "price_to_book",
]


def valuation_reading(pe: float | None, pe_sector: float | None) -> str | None:
    """'Barata vs. sector', 'En línea' o 'Cara vs. sector' según el PER (None sin datos)."""
    if pe is None or pe_sector is None or pe <= 0 or pe_sector <= 0:
        return None
    ratio = pe / pe_sector
    if ratio < CHEAP_RATIO:
        return "Barata vs. sector"
    if ratio > EXPENSIVE_RATIO:
        return "Cara vs. sector"
    return "En línea"


def _median(peers: pd.DataFrame, key: str) -> float | None:
    if key not in peers:
        return None
    col = peers[key].dropna()
    col = col[col > 0]
    return float(np.median(col)) if len(col) >= MIN_PEERS else None


def _val(v) -> float | None:
    return None if v is None or pd.isna(v) else float(v)


def spain_table(df: pd.DataFrame, recs: Mapping[str, Recommendation]) -> list[dict]:
    """Filas de los valores españoles con medianas del sector y señal del modelo."""
    stocks = df[df["quote_type"] == "EQUITY"]
    spain = stocks[stocks["spain_index"].notna()]
    rows = []
    for row in spain.to_dict("records"):
        others = stocks[stocks["ticker"] != row["ticker"]]
        peers, group = select_peers(others, row.get("sector"), row.get("region", ""))
        pe_sector = _median(peers, "pe_trailing")
        rec = recs.get(row["ticker"])
        out = {
            "ticker": row["ticker"],
            "name": row.get("name"),
            "spain_index": row["spain_index"],
            "sector": row.get("sector"),
            "sector_es": sector_es(row.get("sector")),
            "currency": row.get("price_currency") or row.get("currency"),
            "peer_group": group,
            "pe_sector": pe_sector,
            "pb_sector": _median(peers, "price_to_book"),
            "valuation_reading": valuation_reading(_val(row.get("pe_trailing")), pe_sector),
            "div_sustainability": row.get("div_sustainability"),
            "score": rec.score if rec else None,
            "label": rec.label if rec else None,
            "label_es": LABEL_ES[rec.label] if rec else None,
            "risk_level": rec.risk_level if rec else None,
            "fundamentals_as_of": row.get("fundamentals_as_of"),
            "history_as_of": row.get("history_as_of"),
        }
        out.update({k: _val(row.get(k)) for k in COLUMNS})
        rows.append(out)
    return sorted(rows, key=lambda r: -(r["score"] if r["score"] is not None else -1))
