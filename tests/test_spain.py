"""Tabla de la sección España con un universo sintético."""

import pandas as pd
import pytest

from radar.profile.investor import Answers, compute_profile
from radar.recommend.engine import recommend_all
from radar.spain import spain_table, valuation_reading
from radar.universe_list import spain_index


@pytest.mark.parametrize(
    ("pe", "sector", "expected"),
    [
        (8.0, 10.0, "Barata vs. sector"),
        (10.0, 10.0, "En línea"),
        (12.0, 10.0, "Cara vs. sector"),
        (-5.0, 10.0, None),
        (None, 10.0, None),
    ],
)
def test_valuation_reading(pe, sector, expected):
    assert valuation_reading(pe, sector) == expected


def make_df() -> pd.DataFrame:
    rows = []
    tickers = ["IBE.MC", "ELE.MC", "NTGY.MC", "RED.MC", "ENG.MC", "SLR.MC", "ENER.MC"]
    for k, t in enumerate(tickers, start=1):
        rows.append(
            {
                "ticker": t,
                "name": t,
                "quote_type": "EQUITY",
                "sector": "Utilities",
                "region": "Europa",
                "spain_index": spain_index(t),
                "price": 10.0,
                "pe_trailing": float(10 + k),
                "price_to_book": 1.0 + k / 10,
                "roe": 0.05 * k,
                "vol_1y": 0.15,
                "mdd_1y": -0.1,
            }
        )
    rows.append({**rows[0], "ticker": "EOAN.DE", "spain_index": None})  # no es española
    return pd.DataFrame(rows)


def test_spain_table_has_only_spanish_stocks_with_sector_medians():
    df = make_df()
    profile = compute_profile(Answers(2, 2, 2, "growth", 2))
    recs = {r.ticker: r for r in recommend_all(df, profile)}
    table = spain_table(df, recs)
    tickers = {r["ticker"] for r in table}
    assert "EOAN.DE" not in tickers and len(table) == 7
    ibe = next(r for r in table if r["ticker"] == "IBE.MC")
    assert ibe["spain_index"] == "IBEX 35"
    assert ibe["pe_sector"] is not None
    assert ibe["valuation_reading"] == "Barata vs. sector"  # PER 11, el más bajo
    assert ibe["label_es"] in ("Comprar", "Vigilar", "Evitar")
    ener = next(r for r in table if r["ticker"] == "ENER.MC")
    assert ener["spain_index"] == "Mercado Continuo"
    scores = [r["score"] for r in table if r["score"] is not None]
    assert scores == sorted(scores, reverse=True)
