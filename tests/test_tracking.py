"""Registro y evaluación de señales con datos sintéticos de resultado conocido."""

from datetime import date

import pytest

from radar.db.database import Database
from radar.db.signals import LoggedSignal, SignalsRepo
from radar.tracking.evaluate import MIN_SAMPLE, evaluate

D0 = date(2026, 1, 1)


def sig(ticker, label, price=100.0, day=D0):
    return LoggedSignal(day, ticker, label, 70.0, price, "Moderado")


def test_repo_keeps_first_snapshot_of_the_day(tmp_path):
    repo = SignalsRepo(Database(tmp_path / "r.db"))
    assert not repo.has_day(D0)
    assert repo.add_day(D0, [sig("A", "buy"), sig("B", "avoid")]) == 2
    assert repo.add_day(D0, [sig("A", "avoid", 5.0)]) == 0  # ya existía: no se pisa
    assert repo.has_day(D0)
    assert {s.ticker: s.label for s in repo.all()} == {"A": "buy", "B": "avoid"}


def test_no_horizon_until_enough_days_pass():
    assert evaluate([sig("A", "buy")], {"A": 120.0}, date(2026, 1, 20)) == []


def test_buy_group_beats_the_rest():
    log = [sig(f"B{i}", "buy") for i in range(MIN_SAMPLE)]
    log += [sig(f"W{i}", "watch") for i in range(MIN_SAMPLE)]
    now = {f"B{i}": 120.0 for i in range(MIN_SAMPLE)} | {f"W{i}": 100.0 for i in range(MIN_SAMPLE)}
    (h,) = evaluate(log, now, date(2026, 2, 15))  # 45 días: solo el plazo de 30
    assert h.days == 30 and h.from_date == D0
    assert h.universe_mean == pytest.approx(0.10)
    buy, watch, avoid = h.groups
    assert buy.mean_return == pytest.approx(0.20) and buy.hit_rate == 1.0 and buy.reliable
    assert watch.mean_return == pytest.approx(0.0) and watch.hit_rate == 0.0
    assert avoid.count == 0 and avoid.mean_return is None


def test_small_groups_are_not_reliable_and_missing_prices_are_skipped():
    log = [sig("A", "buy"), sig("B", "buy"), sig("GONE", "buy")]
    (h,) = evaluate(log, {"A": 110.0, "B": 90.0}, date(2026, 2, 15))
    assert h.groups[0].count == 2 and not h.groups[0].reliable
    assert h.groups[0].mean_return == pytest.approx(0.0)


def test_each_horizon_uses_the_latest_old_enough_snapshot():
    old, recent = date(2025, 6, 1), date(2025, 12, 1)
    log = [sig("A", "buy", 100.0, old), sig("A", "buy", 200.0, recent)]
    res = {h.days: h for h in evaluate(log, {"A": 220.0}, date(2026, 1, 1))}
    assert res[30].from_date == recent and res[30].groups[0].mean_return == pytest.approx(0.10)
    assert res[180].from_date == old and res[180].groups[0].mean_return == pytest.approx(1.20)
    assert 365 not in res
