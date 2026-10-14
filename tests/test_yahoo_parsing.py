"""Tests del parseo de Yahoo con `info` simulados (sin red)."""

from datetime import UTC, datetime

import pytest

from radar.data.yahoo import parse_metrics, parse_quote
from radar.errors import TickerNotFoundError

NOW = datetime(2026, 10, 14, 10, 0, tzinfo=UTC)

# Extracto real de SAN.MC (14/10/2026)
SAN_INFO = {
    "quoteType": "EQUITY",
    "shortName": "BANCO SANTANDER S.A.",
    "currency": "EUR",
    "fullExchangeName": "MCE",
    "regularMarketPrice": 12.246,
    "regularMarketPreviousClose": 12.19,
    "regularMarketVolume": 2586433,
    "regularMarketTime": 1791973213,
    "marketState": "REGULAR",
    "exchangeDataDelayedBy": 15,
    "trailingPE": 13.91591,
    "profitMargins": 0.33464,
    "grossMargins": 0.0,
    "debtToEquity": None,
    "dividendYield": 2.09,
}


def test_parse_quote():
    q = parse_quote("SAN.MC", SAN_INFO, NOW)
    assert q.price == 12.246
    assert q.delay_minutes == 15
    assert q.is_market_open
    assert q.as_of == datetime.fromtimestamp(1791973213, UTC)
    assert q.change_pct == pytest.approx(12.246 / 12.19 - 1)


def test_parse_quote_without_price_is_not_found():
    with pytest.raises(TickerNotFoundError) as exc:
        parse_quote("SAN", {"quoteType": "EQUITY"}, NOW)
    assert "SAN.MC" in str(exc.value)  # sugiere el sufijo español


def test_parse_quote_falls_back_to_now_without_timestamp():
    info = {**SAN_INFO}
    del info["regularMarketTime"]
    assert parse_quote("SAN.MC", info, NOW).as_of == NOW


def test_metrics_units_are_normalized():
    m = parse_metrics(SAN_INFO)
    assert m["dividend_yield"] == pytest.approx(0.0209)  # 2.09 % → 0.0209
    assert m["profit_margin"] == pytest.approx(0.33464)  # ya venía en fracción
    assert m["pe_trailing"] == pytest.approx(13.91591)


def test_metrics_missing_are_none_not_zero():
    m = parse_metrics(SAN_INFO)
    assert m["debt_to_equity"] is None
    assert m["gross_margin"] is None  # 0 exacto = no aplica
    assert m["free_cash_flow"] is None  # ni siquiera venía


def test_debt_to_equity_percent_to_ratio():
    assert parse_metrics({"debtToEquity": 150.0})["debt_to_equity"] == pytest.approx(1.5)


@pytest.mark.parametrize("bad", ["Infinity", float("nan"), "n/a"])
def test_metrics_reject_non_finite(bad):
    assert parse_metrics({"trailingPE": bad})["pe_trailing"] is None


def test_etf_metrics_units():
    m = parse_metrics({"netExpenseRatio": 0.2, "ytdReturn": 12.5, "threeYearAverageReturn": 0.23})
    assert m["expense_ratio"] == pytest.approx(0.002)
    assert m["ytd_return"] == pytest.approx(0.125)
    assert m["return_3y"] == pytest.approx(0.23)
