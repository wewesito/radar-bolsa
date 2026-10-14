"""Tests del score con un universo sintético de resultado conocido."""

import pandas as pd
import pytest

from radar.scoring.score import COMPONENTS, DEFAULT_WEIGHTS, score_band, score_company

# Métricas usadas por el score y su dirección (para fabricar "la mejor" y "la peor")
INPUTS = {i.key: i.better for c in COMPONENTS for i in c.inputs}


def make_universe(n: int = 10) -> pd.DataFrame:
    """n empresas del mismo sector y región con valores 1..n en cada métrica."""
    rows = []
    for k in range(1, n + 1):
        row = {"ticker": f"P{k}.MC", "sector": "Industrials", "region": "Europa"}
        row.update({key: float(k) for key in INPUTS})
        rows.append(row)
    return pd.DataFrame(rows)


def company(best: bool) -> dict:
    """Empresa mejor (o peor) que todas en cada métrica según su dirección."""
    row = {"ticker": "X.MC", "sector": "Industrials", "region": "Europa"}
    for key, better in INPUTS.items():
        high = 100.0 if best else -100.0
        row[key] = high if better == "higher" else -high
    return row


def test_best_company_scores_100():
    res = score_company(company(best=True), make_universe())
    assert res.total == pytest.approx(100)
    assert all(c.score == pytest.approx(100) for c in res.components)
    assert len(res.pros) == len(INPUTS) and not res.cons


def test_worst_company_scores_0():
    res = score_company(company(best=False), make_universe())
    assert res.total == pytest.approx(0)
    assert len(res.cons) == len(INPUTS) and not res.pros


def test_median_company_scores_50():
    row = {"ticker": "X.MC", "sector": "Industrials", "region": "Europa"}
    row.update({key: 5.5 for key in INPUTS})  # justo en medio de 1..10
    assert score_company(row, make_universe()).total == pytest.approx(50)


def test_company_in_universe_is_not_its_own_peer():
    uni = make_universe()
    row = uni.iloc[-1].to_dict()  # P10: el mayor valor en todo
    res = score_company(row, uni)
    growth = next(c for c in res.components if c.key == "growth")
    assert growth.inputs[0].n_peers == 9
    assert growth.score == pytest.approx(100)


def test_missing_component_redistributes_weight():
    row = company(best=True)
    row["revenue_growth"] = row["earnings_growth"] = None  # sin crecimiento
    res = score_company(row, make_universe())
    growth = next(c for c in res.components if c.key == "growth")
    assert growth.score is None
    assert sum(c.effective_weight for c in res.components) == pytest.approx(1)
    assert any("Crecimiento" in n for n in res.notes)


def test_too_few_components_gives_no_total():
    row = {"ticker": "X.MC", "sector": "Industrials", "region": "Europa", "pe_trailing": 1.0}
    res = score_company(row, make_universe())
    assert res.total is None
    assert res.notes


def test_weights_change_total():
    row = company(best=True)
    for key in ("ret_12m", "ret_6m", "dist_sma200"):
        row[key] = -100.0  # momentum pésimo
    equal = score_company(row, make_universe()).total
    heavy = score_company(row, make_universe(), {**DEFAULT_WEIGHTS, "momentum": 0.8}).total
    assert heavy < equal


def test_pros_and_cons_are_neutral_language():
    res = score_company(company(best=True), make_universe())
    text = " ".join(res.pros + res.cons).lower()
    for word in ("compra", "vende", "deberías", "recomend"):
        assert word not in text
    assert "mediana" in res.pros[0]


def test_score_band():
    assert "en línea" in score_band(50)
    assert "claramente mejores" in score_band(80)
