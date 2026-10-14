"""Backtest con precios sintéticos de resultado conocido."""

import numpy as np
import pandas as pd
import pytest

from radar.backtest.engine import (
    MODEL,
    UNIVERSE,
    BacktestConfig,
    metrics,
    price_scores,
    run_backtest,
    simulate,
    yearly_returns,
)

IDX = pd.date_range("2020-01-03", periods=160, freq="W-FRI")


def panel(**cols) -> pd.DataFrame:
    return pd.DataFrame({k: v for k, v in cols.items()}, index=IDX)


def growth(rate: float, n: int = len(IDX)) -> np.ndarray:
    return 100 * (1 + rate) ** np.arange(n)


def noisy(rate: float, noise: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    r = rate + rng.normal(0, noise, len(IDX))
    return 100 * np.cumprod(1 + r)


def test_steady_winner_scores_above_volatile_loser():
    window = panel(A=growth(0.01), B=noisy(-0.005, 0.05, 1), C=noisy(0.0, 0.02, 2)).iloc[:53]
    s = price_scores(window)
    assert s["A"] == s.max()
    assert s["A"] > s["B"]
    assert ((s >= 0) & (s <= 100)).all()


def test_selects_the_winner_and_matches_its_return_without_costs():
    prices = panel(A=growth(0.01), B=growth(0.0), C=growth(-0.002))
    cfg = BacktestConfig(top_n=1, rebalance_weeks=13, cost=0.0)
    eq, sel = simulate(prices, cfg)
    assert all(picks[0][0] == "A" for _, picks in sel)
    weeks = len(eq) - 1
    assert eq.iloc[-1] == pytest.approx(100 * 1.01**weeks)


def test_costs_only_on_turnover():
    prices = panel(A=growth(0.01), B=growth(0.0))
    eq, _ = simulate(prices, BacktestConfig(top_n=1, cost=0.01))
    weeks = len(eq) - 1
    # Siempre elige A: solo paga la compra inicial (100 % de rotación)
    assert eq.iloc[-1] == pytest.approx(99 * 1.01**weeks)


def test_no_lookahead_future_prices_do_not_change_past_selection():
    base = panel(A=noisy(0.004, 0.02, 3), B=noisy(0.002, 0.01, 4), C=noisy(0.003, 0.03, 5))
    cfg = BacktestConfig(top_n=1, rebalance_weeks=13, cost=0.0)
    _, sel1 = simulate(base, cfg)
    changed = base.copy()
    changed.iloc[100:] = changed.iloc[100:] * np.linspace(0.2, 5, len(changed) - 100)[:, None]
    _, sel2 = simulate(changed, cfg)
    for (d1, p1), (d2, p2) in zip(sel1, sel2, strict=True):
        if d1 < IDX[100]:
            assert p1 == p2 and d1 == d2


def test_assets_without_full_year_are_not_eligible():
    young = growth(0.05).astype(float)
    young[:80] = np.nan  # empieza a cotizar más tarde
    prices = panel(A=growth(0.01), Y=young)
    _, sel = simulate(prices, BacktestConfig(top_n=1, cost=0.0))
    first_date, first = sel[0]
    assert first[0][0] == "A"
    assert any(p[0][0] == "Y" for d, p in sel if d > IDX[80 + 52])


def test_metrics_known_values():
    s = pd.Series([100.0, 50.0, 100.0, 200.0], index=pd.to_datetime(
        ["2020-01-01", "2020-07-01", "2020-12-31", "2021-12-31"]))  # fmt: skip
    m = metrics(s)
    assert m.total_return == pytest.approx(1.0)
    assert m.max_drawdown == pytest.approx(-0.5)
    assert m.cagr == pytest.approx(2 ** (1 / ((s.index[-1] - s.index[0]).days / 365.25)) - 1)
    y = yearly_returns(s)
    assert y[2020] == pytest.approx(0.0) and y[2021] == pytest.approx(1.0)


def test_run_backtest_aligns_benchmarks_to_base_100():
    prices = panel(A=growth(0.01), B=growth(0.002), C=growth(0.0))
    bench = pd.Series(growth(0.003), index=IDX)
    res = run_backtest(prices, {"Índice": bench}, BacktestConfig(top_n=1, cost=0.0))
    assert set(res.series) == {MODEL, UNIVERSE, "Índice"}
    assert res.series["Índice"][0] == pytest.approx(100)
    assert res.metrics[MODEL].cagr > res.metrics[UNIVERSE].cagr > res.metrics["Índice"].cagr
    assert len(res.dates) == len(res.series[MODEL])


def test_too_short_history_raises():
    with pytest.raises(ValueError):
        simulate(panel(A=growth(0.01)).iloc[:40], BacktestConfig())
