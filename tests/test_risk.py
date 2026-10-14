import numpy as np
import pandas as pd
import pytest

from radar.indicators.risk import (
    annualized_volatility,
    beta,
    max_drawdown,
    price_stats,
    return_over,
)


def prices_from_returns(rets, start=100.0, start_date="2025-01-01"):
    values = start * np.cumprod(np.concatenate([[1.0], 1 + np.asarray(rets)]))
    return pd.Series(values, index=pd.bdate_range(start_date, periods=len(values)))


def test_annualized_volatility():
    s = prices_from_returns([0.01, -0.01] * 100)
    # std diaria ≈ 1 % → anual ≈ 1 % · √252 ≈ 15,9 %
    assert annualized_volatility(s) == pytest.approx(0.01 * np.sqrt(252), rel=0.02)


def test_volatility_needs_data():
    assert annualized_volatility(prices_from_returns([0.01] * 5)) is None


def test_max_drawdown():
    s = pd.Series([100, 120, 60, 130], index=pd.date_range("2026-01-01", periods=4))
    mdd = max_drawdown(s)
    assert mdd.value == pytest.approx(-0.5)
    assert mdd.peak == s.index[1]
    assert mdd.trough == s.index[2]


def test_beta_of_leveraged_series_is_two():
    rng = np.random.default_rng(42)
    bench_r = rng.normal(0, 0.01, 250)
    bench = prices_from_returns(bench_r)
    asset = prices_from_returns(2 * bench_r)
    assert beta(asset, bench) == pytest.approx(2.0, rel=1e-6)


def test_return_over():
    idx = pd.bdate_range("2025-01-01", "2026-01-01")
    s = pd.Series(np.linspace(100, 200, len(idx)), index=idx)
    assert return_over(s, 12) == pytest.approx(1.0, abs=0.01)
    assert return_over(s, 36) is None  # no hay tanta historia


def test_price_stats_keys():
    s = prices_from_returns([0.001] * 500)
    stats = price_stats(s)
    assert set(stats) == {"ret_6m", "ret_12m", "vol_1y", "mdd_1y", "dist_sma200"}
    assert stats["mdd_1y"] == 0  # siempre sube: sin caídas
    assert stats["dist_sma200"] > 0  # por encima de su media de 200
