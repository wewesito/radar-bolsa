import pandas as pd

from radar.data.cache import Cache, df_from_json, df_to_json


class FakeClock:
    def __init__(self, t: float = 1_000_000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t


def test_fresh_and_expired(tmp_path):
    clock = FakeClock()
    cache = Cache(tmp_path / "c.db", clock=clock)
    cache.set("k", {"price": 12.3})

    assert cache.get("k", ttl=60).value == {"price": 12.3}

    clock.t += 61
    assert cache.get("k", ttl=60) is None  # caducada para uso normal...
    assert cache.get_any("k").value == {"price": 12.3}  # ...pero disponible como respaldo


def test_missing_key(tmp_path):
    cache = Cache(tmp_path / "c.db")
    assert cache.get("nada", ttl=60) is None
    assert cache.get_any("nada") is None


def test_overwrite_resets_age(tmp_path):
    clock = FakeClock()
    cache = Cache(tmp_path / "c.db", clock=clock)
    cache.set("k", 1)
    clock.t += 100
    cache.set("k", 2)
    assert cache.get("k", ttl=60).value == 2


def test_dataframe_roundtrip_keeps_utc_index():
    idx = pd.date_range("2026-10-01 07:00", periods=3, freq="h", tz="UTC")
    df = pd.DataFrame({"Close": [1.0, 2.0, 3.5], "Volume": [10, 20, 30]}, index=idx)

    back = df_from_json(df_to_json(df))

    assert list(back["Close"]) == [1.0, 2.0, 3.5]
    assert back.index.tz is not None
    assert (back.index == idx).all()
