import pytest

from radar.education.finance_math import (
    compound_growth,
    real_return,
    rule_of_72,
    savings_tax,
    years_to_double,
)
from radar.education.glossary import ENTRIES, by_key
from radar.fundamentals.metrics import ALL_METRICS
from radar.scoring.score import COMPONENTS


def test_every_metric_in_the_app_has_a_glossary_entry():
    missing = set(ALL_METRICS) - set(by_key())
    assert not missing, f"Métricas sin explicar en el glosario: {missing}"


def test_every_score_input_has_a_glossary_entry():
    keys = {i.key for c in COMPONENTS for i in c.inputs}
    assert keys <= set(by_key())


def test_glossary_entries_are_complete_and_unique():
    assert len({e.key for e in ENTRIES}) == len(ENTRIES)
    for e in ENTRIES:
        assert all([e.term, e.what, e.formula, e.reading, e.limits]), e.key


def test_compound_growth_without_contributions():
    df = compound_growth(1000, 0, 0.07, 10)
    assert df.loc[10, "value"] == pytest.approx(1000 * 1.07**10)
    assert df.loc[10, "contributed"] == 1000


def test_compound_growth_with_contributions_and_zero_return():
    df = compound_growth(0, 100, 0.0, 2)
    assert df.loc[2, "value"] == pytest.approx(2400)
    assert df.loc[2, "contributed"] == 2400


def test_fees_reduce_final_value():
    cheap = compound_growth(10_000, 0, 0.07, 30, annual_fee=0.002).loc[30, "value"]
    expensive = compound_growth(10_000, 0, 0.07, 30, annual_fee=0.015).loc[30, "value"]
    assert expensive < cheap * 0.75  # un 1,3 % más al año se lleva >25 % en 30 años


def test_rule_of_72_close_to_exact():
    assert rule_of_72(0.08) == pytest.approx(9)
    assert years_to_double(0.08) == pytest.approx(9.006, abs=0.01)
    assert rule_of_72(0) is None


def test_real_return():
    assert real_return(0.07, 0.03) == pytest.approx(1.07 / 1.03 - 1)


@pytest.mark.parametrize(
    ("base", "expected"),
    [
        (0, 0),
        (6_000, 1_140),  # 6.000 × 19 %
        (10_000, 1_140 + 4_000 * 0.21),
        (60_000, 1_140 + 44_000 * 0.21 + 10_000 * 0.23),
    ],
)
def test_savings_tax_is_progressive_by_brackets(base, expected):
    assert savings_tax(base) == pytest.approx(expected)


def test_risk_profile_bands():
    from radar.education.concepts import RISK_QUESTIONS, risk_profile

    assert len(RISK_QUESTIONS) == 5
    assert risk_profile([1] * 5)[0] == "Conservador"
    assert risk_profile([2] * 5)[0] == "Moderado"
    assert risk_profile([3] * 5)[0] == "Dinámico"


def test_tax_example_in_text_matches_calculation():
    from radar.education.concepts import TAX_ES

    gain = (1500 - 5) - (1000 + 5)
    assert gain == 490
    assert savings_tax(gain) == pytest.approx(93.10)
    assert "93,10 €" in TAX_ES
