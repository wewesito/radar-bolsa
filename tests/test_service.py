"""Tests del servicio con un proveedor falso: comprobamos la política de caché sin red."""

from datetime import UTC, datetime

import pandas as pd
import pytest

from radar.data.cache import Cache
from radar.data.service import MarketDataService
from radar.errors import ProviderUnavailableError, TickerNotFoundError
from radar.models import PriceHistory, Quote

T0 = datetime(2026, 10, 14, 8, 0, tzinfo=UTC)


class FakeClock:
    def __init__(self):
        self.t = T0.timestamp()

    def __call__(self):
        return self.t


class FakeProvider:
    name = "Fake"

    def __init__(self):
        self.calls = 0
        self.fail: Exception | None = None

    def get_quote(self, ticker):
        self.calls += 1
        if self.fail:
            raise self.fail
        if ticker == "NOPE":
            raise TickerNotFoundError(ticker)
        return Quote(ticker, "Test SA", 10.0 + self.calls, 10.0, 100, "EUR", "MCE",
                     "EQUITY", "REGULAR", 15, T0, "Fake")

    def get_history(self, ticker, range_key):
        self.calls += 1
        idx = pd.date_range("2026-10-01", periods=3, freq="D", tz="UTC")
        df = pd.DataFrame({"Open": 1.0, "High": 2.0, "Low": 0.5, "Close": 1.5, "Volume": 10},
                          index=idx)
        return PriceHistory(ticker, range_key, "1d", df, T0, "Fake")

    def get_fundamentals(self, ticker):
        raise NotImplementedError


@pytest.fixture
def setup(tmp_path):
    clock, provider = FakeClock(), FakeProvider()
    return MarketDataService(provider, Cache(tmp_path / "c.db", clock=clock)), provider, clock


def test_quote_is_cached_within_ttl(setup):
    svc, provider, clock = setup
    first = svc.get_quote("SAN.MC")
    clock.t += 30
    second = svc.get_quote("SAN.MC")
    assert provider.calls == 1
    assert second == first


def test_quote_refetched_after_ttl(setup):
    svc, provider, clock = setup
    svc.get_quote("SAN.MC")
    clock.t += 61
    assert svc.get_quote("SAN.MC").price == 12.0
    assert provider.calls == 2


def test_stale_fallback_when_provider_down(setup):
    svc, provider, clock = setup
    svc.get_quote("SAN.MC")
    clock.t += 3600
    provider.fail = ProviderUnavailableError("caída")
    q = svc.get_quote("SAN.MC")
    assert q.stale
    assert q.price == 11.0


def test_provider_down_without_cache_raises(setup):
    svc, provider, _ = setup
    provider.fail = ProviderUnavailableError("caída")
    with pytest.raises(ProviderUnavailableError):
        svc.get_quote("SAN.MC")


def test_get_quotes_isolates_errors(setup):
    svc, _, _ = setup
    res = svc.get_quotes(["SAN.MC", "NOPE"])
    assert isinstance(res["SAN.MC"], Quote)
    assert isinstance(res["NOPE"], TickerNotFoundError)


def test_history_roundtrip_through_cache(setup):
    svc, provider, _ = setup
    first = svc.get_history("SAN.MC", "1M")
    second = svc.get_history("SAN.MC", "1M")
    assert provider.calls == 1
    pd.testing.assert_frame_equal(first.data, second.data, check_freq=False, check_dtype=False)
