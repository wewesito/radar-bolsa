from datetime import UTC, datetime

import pytest

from radar.data.markets import (
    CHART_RANGES,
    EXCHANGES,
    US,
    exchange_for,
    is_session_open,
    is_valid_format,
    normalize_ticker,
    suffix_hint,
)


def test_normalize_ticker():
    assert normalize_ticker("  san.mc ") == "SAN.MC"


@pytest.mark.parametrize("t", ["SAN.MC", "AAPL", "^IBEX", "BRK-B", "EURUSD=X", "IWDA.AS"])
def test_valid_formats(t):
    assert is_valid_format(t)


@pytest.mark.parametrize("t", ["", "SAN MC", "$AAPL", ".MC", "A" * 25])
def test_invalid_formats(t):
    assert not is_valid_format(t)


def test_exchange_for():
    assert exchange_for("SAN.MC").country == "España"
    assert exchange_for("AAPL") is US
    assert exchange_for("^IBEX") is None
    assert exchange_for("XXX.ZZ") is None
    assert exchange_for("NOKIA.HE").country == "Finlandia"


def test_suffix_hint_only_for_bare_tickers():
    assert "SAN.MC" in suffix_hint("SAN")
    assert suffix_hint("SAN.MC") is None
    assert suffix_hint("^IBEX") is None


def test_session_open_madrid():
    bme = EXCHANGES["MC"]
    # Miércoles 14/10/2026 10:00 en Madrid (CEST, UTC+2) → abierto
    assert is_session_open(bme, datetime(2026, 10, 14, 8, 0, tzinfo=UTC))
    # Mismo día 18:00 en Madrid → cerrado
    assert not is_session_open(bme, datetime(2026, 10, 14, 16, 0, tzinfo=UTC))
    # Sábado → cerrado
    assert not is_session_open(bme, datetime(2026, 10, 17, 10, 0, tzinfo=UTC))


def test_chart_ranges_intraday_flag():
    assert CHART_RANGES["1D"].intraday
    assert not CHART_RANGES["Máx"].intraday  # "1mo" no es intradía aunque acabe en "o"
    assert set(CHART_RANGES) == {"1D", "1S", "1M", "6M", "1A", "5A", "Máx"}
