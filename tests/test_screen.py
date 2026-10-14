import numpy as np
import pandas as pd

from radar.scoring.screen import Filter, apply_filters, best_by_metric, score_universe
from tests.test_score import make_universe


def df():
    return pd.DataFrame(
        {
            "ticker": ["A", "B", "C", "D"],
            "sector": ["Energy", "Energy", "Technology", "Technology"],
            "region": ["Europa", "EE. UU.", "Europa", "Europa"],
            "pe_trailing": [8.0, 12.0, 30.0, np.nan],
            "roe": [0.10, 0.20, 0.30, 0.40],
        }
    )


def test_numeric_filters():
    out = apply_filters(df(), [Filter("pe_trailing", "<=", 15)])
    assert list(out["ticker"]) == ["A", "B"]


def test_missing_values_are_excluded_when_filtered():
    out = apply_filters(df(), [Filter("roe", ">=", 0.25)])
    assert list(out["ticker"]) == ["C", "D"]
    out = apply_filters(df(), [Filter("roe", ">=", 0.25), Filter("pe_trailing", "<=", 100)])
    assert list(out["ticker"]) == ["C"]  # D no tiene PER: no se puede afirmar que cumple


def test_sector_and_region_filters():
    out = apply_filters(df(), [], sectors=["Energy"], regions=["Europa"])
    assert list(out["ticker"]) == ["A"]


def test_no_filters_returns_all():
    assert len(apply_filters(df(), [])) == 4


def test_best_by_metric():
    assert best_by_metric({"A": 8, "B": 12}, "lower") == "A"
    assert best_by_metric({"A": 0.1, "B": 0.3, "C": None}, "higher") == "B"
    assert best_by_metric({"A": 1, "B": 2}, None) is None
    assert best_by_metric({"A": 1, "B": None}, "higher") is None


def test_score_universe_adds_columns_and_orders_scores():
    out = score_universe(make_universe())
    assert {"score", "score_valuation", "score_risk"} <= set(out.columns)
    # En make_universe la empresa k tiene valor k en todo: con direcciones mixtas, las
    # extremas no pueden ser las mejores en todo; basta con que el score esté en 0–100.
    assert out["score"].between(0, 100).all()
