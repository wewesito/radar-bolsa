"""Reglas del perfil inversor con respuestas de resultado conocido."""

import pytest

from radar.db.database import Database
from radar.db.settings import SettingsRepo
from radar.profile.investor import Answers, answers_from_dict, compute_profile


def make(horizon=2, reaction=2, amount=2, objective="growth", experience=2) -> Answers:
    return Answers(horizon, reaction, amount, objective, experience)


@pytest.mark.parametrize(
    ("horizon", "reaction", "level", "max_risk"),
    [
        (1, 1, "conservador", 0),  # 2 puntos
        (2, 2, "moderado", 1),  # 4 puntos
        (3, 2, "dinamico", 2),  # 5 puntos
        (3, 3, "dinamico", 2),
    ],
)
def test_level_from_points(horizon, reaction, level, max_risk):
    p = compute_profile(make(horizon=horizon, reaction=reaction))
    assert p.level == level and p.max_risk == max_risk


def test_short_horizon_is_always_conservative():
    p = compute_profile(make(horizon=0, reaction=3))
    assert p.level == "conservador"
    assert any("2 años" in n for n in p.notes)


def test_preserve_objective_subtracts_points_and_weights_risk():
    p = compute_profile(make(horizon=3, reaction=2, objective="preserve"))  # 5 − 2 = 3
    assert p.level == "moderado"
    assert p.weights["risk"] == pytest.approx(0.3)


def test_no_experience_caps_at_moderate_and_limits_stocks():
    p = compute_profile(make(horizon=3, reaction=3, experience=0))
    assert p.level == "moderado"
    assert p.allocation.stocks <= 15
    assert p.allocation.etf + p.allocation.stocks + p.allocation.safe == 100


def test_small_amount_goes_all_to_etfs():
    p = compute_profile(make(amount=0))
    assert p.allocation.stocks == 0 and p.positions == 0
    assert p.allocation.etf + p.allocation.safe == 100


def test_dividend_objective_activates_dividend_component():
    assert compute_profile(make(objective="dividends")).weights["dividend"] > 0
    assert compute_profile(make(objective="growth")).weights["dividend"] == 0


def test_allocations_always_add_up_to_100():
    for h in range(4):
        for r in range(4):
            for amt in range(4):
                for exp in range(4):
                    for obj in ("growth", "dividends", "preserve"):
                        a = compute_profile(make(h, r, amt, obj, exp)).allocation
                        assert a.etf + a.stocks + a.safe == 100


def test_invalid_answers_are_rejected():
    with pytest.raises(ValueError):
        make(horizon=4)
    with pytest.raises(ValueError):
        make(objective="lottery")
    with pytest.raises(KeyError):
        answers_from_dict({"horizon": 1})


def test_profile_roundtrip_in_settings(tmp_path):
    repo = SettingsRepo(Database(tmp_path / "t.db"))
    assert repo.get("profile") is None
    answers = {"horizon": 2, "reaction": 1, "amount": 1, "objective": "dividends", "experience": 1}
    repo.set("profile", answers)
    repo.set("profile", {**answers, "reaction": 2})  # sobrescribe
    assert compute_profile(answers_from_dict(repo.get("profile"))).level == "moderado"
    repo.delete("profile")
    assert repo.get("profile") is None
