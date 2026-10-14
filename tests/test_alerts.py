from dataclasses import replace

import pytest

from radar.alerts.rules import Alert, Observation, describe, evaluate


def run(alert: Alert, values: list[float], reference: float | None = None) -> list[bool]:
    """Evalúa una secuencia de observaciones arrastrando el estado como lo haría la BD."""
    fired = []
    for v in values:
        ev = evaluate(alert, Observation(v, reference))
        fired.append(ev.fired)
        alert = replace(alert, last_state=ev.state)
    return fired


def test_fires_only_on_crossing():
    a = Alert("SAN.MC", "price", "above", 12.0)
    #           fija estado  cruza  sigue   baja   vuelve a cruzar
    assert run(a, [11.0, 12.5, 13.0, 11.5, 12.1]) == [False, True, False, False, True]


def test_first_evaluation_never_fires_even_if_true():
    a = Alert("SAN.MC", "price", "above", 12.0)
    assert run(a, [13.0, 13.5]) == [False, False]


def test_below_and_change_pct():
    a = Alert("ITX.MC", "change_pct", "below", -3.0)
    assert run(a, [-1.0, -3.5]) == [False, True]


def test_sma_cross_uses_reference():
    a = Alert("SAN.MC", "sma200", "below", None)
    assert run(a, [10.5, 9.5], reference=10.0) == [False, True]


def test_inactive_alert_never_fires():
    a = Alert("SAN.MC", "price", "above", 12.0, active=False)
    assert run(a, [11.0, 13.0]) == [False, False]


def test_missing_reference_raises():
    with pytest.raises(ValueError):
        evaluate(Alert("X", "sma50", "above", None), Observation(10.0))


def test_describe():
    assert describe(Alert("SAN.MC", "price", "above", 12.5)) == "SAN.MC: Precio por encima de 12,5"
    assert "media de 200" in describe(Alert("SAN.MC", "sma200", "below", None))


class FakeQuote:
    def __init__(self, price, prev):
        self.price, self.previous_close = price, prev
        self.change_pct = price / prev - 1


class FakeService:
    def __init__(self):
        self.price = 11.0

    def get_quote(self, ticker):
        return FakeQuote(self.price, 10.0)


def test_checker_persists_state_and_fires_once(tmp_path):
    from radar.alerts.checker import check_all
    from radar.db.alerts import AlertsRepo
    from radar.db.database import Database

    repo = AlertsRepo(Database(tmp_path / "r.db"))
    repo.add(Alert("SAN.MC", "price", "above", 12.0))
    svc = FakeService()

    assert check_all(svc, repo) == []  # 11 < 12: fija estado
    svc.price = 12.5
    msgs = check_all(svc, repo)
    assert len(msgs) == 1 and "12,50" in msgs[0]
    assert check_all(svc, repo) == []  # sigue por encima: no repite
    assert len(repo.events()) == 1
    repo.mark_all_seen()
    assert repo.events()[0].seen
