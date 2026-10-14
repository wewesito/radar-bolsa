import pytest

from radar.news.sentiment import analyze, normalize


def test_normalize_removes_accents():
    assert normalize("Caída RÉCORD") == "caida record"


@pytest.mark.parametrize(
    "text",
    [
        "Inditex dispara su beneficio y bate récord de ventas",
        "Iberdrola gana un 15 % más y eleva el dividendo",
        "Apple beats estimates as iPhone sales surge",
    ],
)
def test_positive_headlines(text):
    res = analyze(text)
    assert res.label == "positivo"
    assert res.positives


@pytest.mark.parametrize(
    "text",
    [
        "Telefónica se desploma tras registrar pérdidas",
        "Grifols cae en bolsa por la investigación de la CNMV",
        "Nvidia shares fall after weak guidance and tariff concerns",
    ],
)
def test_negative_headlines(text):
    assert analyze(text).label == "negativo"


def test_negation_flips_polarity():
    res = analyze("El banco no mejora sus previsiones")
    assert res.label == "negativo"
    assert res.negatives == ["no mejora"]


def test_neutral_without_terms():
    res = analyze("Repsol celebra su junta de accionistas en Madrid")
    assert res.label == "neutral"
    assert res.score == 0


def test_mixed_headline_is_neutral():
    assert analyze("Santander gana más pero cae en bolsa").label == "neutral"


def test_roots_do_not_catch_unrelated_words():
    assert analyze("New window design for the mission and advertising").label == "neutral"
    assert analyze("Surgen dudas sobre el plan").positives == []  # falso amigo inglés/español
    res = analyze("Escalada de tensiones comerciales")
    assert res.positives == []  # 'escalada' no es positivo...
    assert res.label == "negativo"  # ...y 'tensiones' sí es negativo
