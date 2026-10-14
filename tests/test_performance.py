"""Rentabilidades por plazos, dividendos y ROIC con datos sintéticos de resultado conocido."""

import pandas as pd
import pytest

from radar.indicators.performance import (
    dividend_sustainability,
    dividend_years,
    period_returns,
    roic,
    ytd_return,
)


def daily(start: str, end: str, f) -> pd.Series:
    idx = pd.date_range(start, end, freq="D", tz="UTC")
    return pd.Series([f(i) for i in range(len(idx))], index=idx, dtype=float)


def test_ytd_uses_last_close_of_previous_year():
    s = pd.Series(
        [100.0, 110.0, 99.0, 121.0],
        index=pd.to_datetime(["2025-12-30", "2025-12-31", "2026-01-02", "2026-10-14"], utc=True),
    )
    assert ytd_return(s) == pytest.approx(121 / 110 - 1)


def test_ytd_without_previous_year_is_none():
    s = daily("2026-03-01", "2026-10-14", lambda i: 10.0)
    assert ytd_return(s) is None


def test_period_returns_with_known_doubling():
    # Precio constante 50 hasta hace 5 años, después 100: +100 % a 5 años, 0 % a 1 y 3 años
    price = daily("2021-09-01", "2026-10-14", lambda i: 50.0 if i < 60 else 100.0)
    total = price * 1.5  # factor constante: misma rentabilidad relativa
    r = period_returns(price, total)
    assert r["ret_5y"] == pytest.approx(1.0)
    assert r["ret_1y"] == pytest.approx(0.0)
    assert r["ret_3y"] == pytest.approx(0.0)
    assert r["tr_5y"] == pytest.approx(1.0)


def test_period_returns_without_enough_history_are_none():
    price = daily("2024-06-01", "2026-10-14", lambda i: 10.0 + i * 0.01)
    r = period_returns(price, price)
    assert r["ret_1y"] is not None
    assert r["ret_3y"] is None and r["ret_5y"] is None and r["tr_5y"] is None


def test_total_return_includes_dividends():
    # Precio plano en 10; el ajustado sube un 5 % cada año por el dividendo reinvertido
    price = daily("2021-01-01", "2026-10-14", lambda i: 10.0)
    total = daily("2021-01-01", "2026-10-14", lambda i: 10.0 * 1.05 ** (i / 365.25))
    r = period_returns(price, total)
    assert r["ret_5y"] == pytest.approx(0.0)
    assert r["tr_5y"] == pytest.approx(1.05**5 - 1, rel=1e-2)


def test_dividend_years_counts_consecutive_full_years():
    dates = ["2019-06-01", "2021-06-01", "2022-06-01", "2023-06-01", "2024-06-01", "2025-06-01"]
    divs = pd.Series(0.5, index=pd.to_datetime(dates, utc=True))
    # 2025, 2024, 2023, 2022, 2021 → 5 (2020 sin pago corta la racha; 2026 no cuenta)
    assert dividend_years(divs, pd.Timestamp("2026-10-14", tz="UTC")) == 5


def test_dividend_years_zero_when_last_year_missing():
    divs = pd.Series(0.5, index=pd.to_datetime(["2023-06-01", "2024-06-01"], utc=True))
    assert dividend_years(divs, pd.Timestamp("2026-10-14", tz="UTC")) == 0


@pytest.mark.parametrize(
    ("payout", "dy", "years", "expected"),
    [
        (0.5, 0.03, 10, "Alta"),
        (0.5, 0.03, 2, "Media"),
        (0.85, 0.05, 20, "Media"),
        (1.5, 0.07, 20, "Baja"),
        (None, 0.03, 10, "Media"),
        (0.0, None, 0, "Sin dividendo"),
    ],
)
def test_dividend_sustainability(payout, dy, years, expected):
    assert dividend_sustainability(payout, dy, years) == expected


def test_roic_known_value():
    items = {
        "ebit": 100.0,
        "pretax_income": 80.0,
        "tax_provision": 20.0,  # tipo efectivo 25 %
        "total_debt": 300.0,
        "equity": 500.0,
        "cash": 50.0,
    }
    assert roic(items) == pytest.approx(100 * 0.75 / 750)


def test_roic_clamps_absurd_tax_and_needs_positive_capital():
    base = {"ebit": 100.0, "pretax_income": 10.0, "tax_provision": 9.0, "equity": 100.0}
    assert roic(base) == pytest.approx(100 * 0.5 / 100)  # tipo acotado al 50 %
    assert roic({**base, "cash": 500.0}) is None
    assert roic({"ebit": None, "equity": 1.0}) is None
