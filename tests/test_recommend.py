"""Reglas de la señal (Comprar / Vigilar / Evitar) con universos sintéticos."""

import pandas as pd
import pytest

from radar.profile.investor import Answers, compute_profile
from radar.recommend.engine import (
    AVOID_SCORE,
    BUY_SCORE,
    entry_range,
    recommend,
    recommend_all,
    risk_level,
)
from radar.scoring.score import COMPONENTS

INPUTS = {i.key: i.better for c in COMPONENTS for i in c.inputs}

MODERATE = compute_profile(Answers(2, 2, 2, "growth", 2))
CONSERVATIVE = compute_profile(Answers(1, 1, 2, "growth", 2))
DYNAMIC = compute_profile(Answers(3, 3, 2, "growth", 2))


def stock_row(k: float, ticker: str, **over) -> dict:
    row = {
        "ticker": ticker,
        "name": ticker,
        "quote_type": "EQUITY",
        "sector": "Industrials",
        "region": "Europa",
        "price": 10.0,
        "price_currency": "EUR",
    }
    row.update({key: float(k) for key in INPUTS})
    row.update({"vol_1y": 0.15, "mdd_1y": -0.10, "profit_margin": 0.1})  # riesgo bajo
    row.update(over)
    return row


def universe(*extra: dict) -> pd.DataFrame:
    return pd.DataFrame([stock_row(k, f"P{k}.MC") for k in range(1, 11)] + list(extra))


def company(best: bool, **over) -> dict:
    """Mejor (o peor) que todas en cada métrica según su dirección."""
    row = stock_row(0, "X.MC")
    for key, better in INPUTS.items():
        high = 100.0 if best else -100.0
        row[key] = high if better == "higher" else -high
    row.update({"vol_1y": 0.15, "mdd_1y": -0.10, "profit_margin": 0.1})
    row.update(over)
    return row


@pytest.mark.parametrize(
    ("vol", "mdd", "level"),
    [
        (0.15, -0.10, 0),
        (0.15, -0.25, 1),  # poca volatilidad pero caída fuerte
        (0.25, -0.10, 1),
        (0.40, -0.10, 2),
        (0.25, -0.40, 2),
        (None, None, None),
    ],
)
def test_risk_level(vol, mdd, level):
    assert risk_level(vol, mdd) == level


@pytest.mark.parametrize(("cap", "level"), [(5e10, 0), (5e8, 1), (1e8, 2), (None, 0)])
def test_small_companies_have_more_risk(cap, level):
    assert risk_level(0.10, -0.05, cap) == level


def test_micro_cap_is_never_buy_even_for_dynamic_profile():
    rec = recommend(company(best=True, market_cap=5e7), universe(), DYNAMIC)
    assert rec.risk_level == 2 and rec.label == "watch"
    assert "pequeña" in rec.summary


def test_loss_making_company_is_never_buy():
    rec = recommend(company(best=True, profit_margin=-0.05), universe(), MODERATE)
    assert rec.label == "watch"
    assert not next(c for c in rec.checks if "beneficio" in c.rule).passed
    assert "pérdidas" in rec.cons[0].text


def peers_df(n: int = 6) -> pd.DataFrame:
    return pd.DataFrame(
        {"pe_trailing": [10.0] * n, "price_to_book": [1.0] * n, "fcf_yield": [0.05] * n}
    )


def test_entry_range_inside_when_priced_like_peers():
    row = {"price": 100.0, "pe_trailing": 10.0, "price_to_book": 1.0, "fcf_yield": 0.05}
    r = entry_range(row, peers_df(), "grupo")
    assert r.low == pytest.approx(100) and r.high == pytest.approx(100)
    assert r.position == "inside"


def test_entry_range_above_when_twice_as_expensive():
    row = {"price": 100.0, "pe_trailing": 20.0, "price_to_book": 2.0, "fcf_yield": 0.025}
    r = entry_range(row, peers_df(), "grupo")
    assert r.high == pytest.approx(50)
    assert r.position == "above"


def test_entry_range_below_when_cheap():
    row = {"price": 100.0, "pe_trailing": 8.0, "price_to_book": 0.8, "fcf_yield": 0.06}
    r = entry_range(row, peers_df(), "grupo")
    assert r.low == pytest.approx(120) and r.position == "below"


def test_entry_range_unreliable_when_estimates_disagree():
    row = {"price": 100.0, "pe_trailing": 5.0, "price_to_book": 4.0, "fcf_yield": 0.05}
    r = entry_range(row, peers_df(), "grupo")  # 200 frente a 25: más de 2,5 veces
    assert not r.reliable and "difieren" in r.note


def test_entry_range_needs_two_methods_and_skips_fcf_for_banks():
    row = {
        "price": 100.0,
        "pe_trailing": 10.0,
        "price_to_book": None,
        "fcf_yield": 0.05,
        "sector": "Financial Services",
    }
    r = entry_range(row, peers_df(), "grupo")
    assert not r.reliable and [e.metric for e in r.estimates] == ["pe_trailing"]


def test_entry_range_needs_enough_peers():
    row = {"price": 100.0, "pe_trailing": 10.0, "price_to_book": 1.0, "fcf_yield": 0.05}
    assert not entry_range(row, peers_df(3), "grupo").reliable


def test_best_low_risk_company_is_buy():
    rec = recommend(company(best=True), universe(), MODERATE)
    assert rec.score >= BUY_SCORE
    assert rec.label == "buy"
    assert all(c.passed for c in rec.checks)
    assert len(rec.pros) == 3


def test_worst_company_is_avoid_with_three_risks():
    rec = recommend(company(best=False), universe(), MODERATE)
    assert rec.score < AVOID_SCORE
    assert rec.label == "avoid"
    assert len(rec.cons) == 3


def test_high_risk_depends_on_profile():
    risky = company(best=True, vol_1y=0.45, mdd_1y=-0.40)
    assert recommend(risky, universe(), DYNAMIC).label == "buy"
    assert recommend(risky, universe(), MODERATE).label == "watch"  # un nivel por encima
    assert recommend(risky, universe(), CONSERVATIVE).label == "avoid"  # dos niveles


def test_expensive_vs_range_is_watch():
    # Mejor en todo menos en precio: PER, P/VC y FCF del doble de caro que sus comparables
    row = company(best=True, pe_trailing=20.0, price_to_book=20.0, fcf_yield=0.5)
    uni = universe()
    uni["fcf_yield"] = 1.0  # FCF de los comparables: el doble que el suyo
    rec = recommend(row, uni, MODERATE)
    assert rec.entry.reliable and rec.entry.position == "above"
    assert rec.label == "watch"
    assert "rango" in rec.summary


def test_foreign_currency_adds_currency_risk():
    rec = recommend(company(best=True, price_currency="USD"), universe(), MODERATE)
    assert any("USD" in c.text for c in rec.cons)


def test_no_imperative_language_in_explanations():
    for best in (True, False):
        rec = recommend(company(best=best), universe(), MODERATE)
        texts = [rec.summary, rec.fit] + [r.text for r in rec.pros + rec.cons]
        for t in texts:
            low = t.lower()
            assert "compra" not in low and "vende" not in low and "recomend" not in low


# --- ETFs -------------------------------------------------------------------------------


def etf_row(ticker: str, vol: float, ter: float | None = 0.002, **over) -> dict:
    row = {
        "ticker": ticker,
        "name": ticker,
        "quote_type": "ETF",
        "price": 100.0,
        "price_currency": "EUR",
        "expense_ratio": ter,
        "total_assets": 1e10,
        "vol_1y": vol,
        "mdd_1y": -vol / 2,
        "ret_12m": 0.1,
    }
    row.update(over)
    return row


def etf_universe() -> pd.DataFrame:
    return pd.DataFrame(
        [
            etf_row("VWCE.DE", 0.12),
            etf_row("EUNL.DE", 0.13),
            etf_row("SXRV.DE", 0.45),  # complemento muy volátil
            etf_row("EUNA.DE", 0.05),  # renta fija
            etf_row("XEON.DE", 0.01, ter=None),  # liquidez, sin TER en la fuente
            etf_row("IS3N.DE", 0.18),
        ]
    )


def test_core_etf_is_buy_for_moderate():
    df = etf_universe()
    rec = recommend(df.iloc[0].to_dict(), df, MODERATE)
    assert rec.kind == "etf" and rec.label == "buy" and rec.entry is None


def test_volatile_complement_is_avoid_for_conservative():
    df = etf_universe()
    assert recommend(df.iloc[2].to_dict(), df, CONSERVATIVE).label == "avoid"


def test_bonds_fit_conservative_but_not_dynamic():
    df = etf_universe()
    bonds = df.iloc[3].to_dict()
    assert recommend(bonds, df, CONSERVATIVE).label == "buy"
    assert recommend(bonds, df, DYNAMIC).label == "watch"


def test_missing_ter_is_flagged_not_invented():
    df = etf_universe()
    rec = recommend(df.iloc[4].to_dict(), df, MODERATE)
    assert "KID" in rec.cons[0].text


def test_recommend_all_orders_buy_first_then_by_score():
    df = pd.concat([universe(company(best=True), company(best=False, ticker="Y.MC")),
                    etf_universe()])  # fmt: skip
    recs = recommend_all(df, MODERATE)
    order = {"buy": 0, "watch": 1, "avoid": 2}
    keys = [(order[r.label], -(r.score or 0)) for r in recs]
    assert keys == sorted(keys)
    assert {r.kind for r in recs} == {"stock", "etf"}
    d = recs[0].to_dict()
    assert d["label_es"] in ("Comprar", "Vigilar", "Evitar") and "risk_label" in d
