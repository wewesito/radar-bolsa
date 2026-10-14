from datetime import UTC, datetime

import pytest

from radar.formatting import NA, fmt_age, fmt_big, fmt_dt, fmt_number, fmt_pct, fmt_price


def test_fmt_number_spanish_separators():
    assert fmt_number(1234567.891) == "1.234.567,89"
    assert fmt_number(None) == NA


@pytest.mark.parametrize(
    ("x", "kwargs", "expected"),
    [
        (0.123, {}, "12,3 %"),
        (-0.0053, {"decimals": 2}, "−0,53 %"),
        (0.0053, {"decimals": 2, "signed": True}, "+0,53 %"),
        (None, {}, NA),
    ],
)
def test_fmt_pct(x, kwargs, expected):
    assert fmt_pct(x, **kwargs) == expected


def test_fmt_big():
    assert fmt_big(170_079_502_336, "EUR") == "170,1 mil M€"
    assert fmt_big(6_487_897_600, "USD") == "6,5 mil M$"
    assert fmt_big(-2_500_000, "EUR") == "−2,5 M€"
    assert fmt_big(3_000_000_000, "CHF") == "3,0 mil M CHF"
    assert fmt_big(None) == NA


def test_fmt_price():
    assert fmt_price(12.246, "EUR") == "12,25 €"
    assert fmt_price(0.5123, "USD") == "0,5123 $"


def test_fmt_dt_converts_to_madrid():
    # 10:24 UTC en octubre = 12:24 en Madrid (horario de verano)
    assert fmt_dt(datetime(2026, 10, 14, 10, 24, tzinfo=UTC)) == "14/10/2026 12:24"


@pytest.mark.parametrize(
    ("secs", "expected"),
    [(30, "hace <1 min"), (900, "hace 15 min"), (7200, "hace 2 h"), (200000, "hace 2 d")],
)
def test_fmt_age(secs, expected):
    assert fmt_age(secs) == expected
