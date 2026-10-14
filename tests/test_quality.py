"""Control de calidad de precios y su efecto en la señal."""

import numpy as np
import pandas as pd

from radar.indicators.quality import price_warning
from radar.recommend.engine import recommend
from tests.test_recommend import MODERATE, company, universe


def series(values):
    return pd.Series(values, index=pd.date_range("2026-01-01", periods=len(values)))


def test_clean_series_has_no_warning():
    assert price_warning(series(100 + np.arange(50) * 0.5)) is None


def test_huge_jump_is_flagged_with_date_and_size():
    msg = price_warning(series([10, 10, 10_000, 10, 10]))
    assert msg and "01/03/2026" not in msg and "03/01/2026" in msg and "+99.900" in msg


def test_zero_price_and_empty_series():
    assert "cero" in price_warning(series([10, 0, 10]))
    assert price_warning(series([])) is None


def test_old_jump_outside_the_checked_year_is_ignored():
    values = [10, 1000] + [1000.0] * 300
    assert price_warning(series(values)) is None


def test_suspect_data_never_gets_buy():
    peers = universe()
    base = recommend(company(True), peers, MODERATE)
    assert base.label == "buy"  # sin aviso, la empresa perfecta sale «Comprar»
    flagged = recommend(company(True, data_warning="Salto sospechoso"), peers, MODERATE)
    assert flagged.label == "watch"
    assert any(c.rule == "Datos de precio fiables" and not c.passed for c in flagged.checks)
