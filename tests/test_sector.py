import pandas as pd
import pytest

from radar.fundamentals.sector import (
    add_derived,
    compare_metric,
    peer_stats,
    percentile_rank,
    region_for,
    select_peers,
)


def test_percentile_rank_higher_is_better():
    peers = [1, 2, 3, 4]
    assert percentile_rank(5, peers) == 1.0
    assert percentile_rank(0, peers) == 0.0
    assert percentile_rank(2.5, peers) == 0.5


def test_percentile_rank_ties_count_half():
    assert percentile_rank(2, [1, 2, 3]) == pytest.approx(0.5)


def test_percentile_rank_lower_is_better_inverts():
    # PER 10 frente a [10, 20, 30, 40]: más barato que casi todos → percentil alto
    assert percentile_rank(10, [10, 20, 30, 40], "lower") == pytest.approx(0.875)


def test_percentile_rank_ignores_missing():
    assert percentile_rank(3, [None, float("nan"), 1, 5]) == 0.5
    assert percentile_rank(3, [None]) is None


def test_peer_stats_needs_min_peers():
    assert peer_stats([1, 2, 3, 4]) is None
    s = peer_stats([1, 2, 3, 4, 100])
    assert s.median == 3  # la mediana ignora el 100 atípico
    assert s.n == 5


def test_add_derived():
    m = add_derived({"free_cash_flow": 10.0, "market_cap": 200.0, "revenue": 50.0})
    assert m["fcf_yield"] == pytest.approx(0.05)
    assert m["fcf_margin"] == pytest.approx(0.2)
    assert add_derived({"free_cash_flow": None, "market_cap": 1})["fcf_yield"] is None


def test_region_for():
    assert region_for("SAN.MC") == "Europa"
    assert region_for("AAPL") == "EE. UU."
    assert region_for("^IBEX") == "Otros"


def _universe():
    rows = [(f"E{i}.MC", "Energy", "Europa", 10 + i) for i in range(3)]
    rows += [(f"U{i}", "Energy", "EE. UU.", 20 + i) for i in range(4)]
    rows += [(f"T{i}.DE", "Technology", "Europa", 30 + i) for i in range(6)]
    return pd.DataFrame(rows, columns=["ticker", "sector", "region", "pe_trailing"])


def test_select_peers_same_region_when_enough():
    peers, label = select_peers(_universe(), "Technology", "Europa", exclude="T0.DE")
    assert len(peers) == 5 and "Europa" in label


def test_select_peers_falls_back_to_world():
    peers, label = select_peers(_universe(), "Energy", "Europa")
    assert len(peers) == 7 and "mundial" in label


def test_compare_metric_reading():
    peers, _ = select_peers(_universe(), "Energy", "Europa")
    cheap = compare_metric("pe_trailing", 5.0, peers, "lower")
    assert cheap.percentile == 1.0
    assert cheap.reading == "favorable frente al sector"
    assert compare_metric("pe_trailing", None, peers, "lower").reading == "sin dato"
