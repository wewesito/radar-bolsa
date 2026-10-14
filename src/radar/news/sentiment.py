"""Sentimiento de titulares por léxico (español e inglés), totalmente explicable.

Método:
1. Se normaliza el texto (minúsculas, sin tildes) y se parte en palabras.
2. Cada palabra se compara con listas de términos financieros positivos y negativos.
   Un término acabado en '*' es una raíz: 'desplom*' cubre desploma, desplome... Las raíces
   deben ser específicas: 'win*' cazaría 'window', 'miss*' cazaría 'mission' y 'surge*'
   (inglés: dispararse) cazaría el español 'surgen'.
3. Negación simple: si una de las 2 palabras anteriores es 'no', 'sin', 'not'...,
   el término cuenta con el signo contrario ('no mejora' → negativo).
4. Puntuación = (positivos − negativos) / (positivos + negativos), de −1 a +1.

Limitaciones (se muestran en la UI): no entiende ironía, contexto ni a quién afecta la
noticia ('la competencia de Inditex se hunde' cuenta como negativa), y las listas son
pequeñas. Inspirado en el enfoque del diccionario financiero de Loughran-McDonald, pero
con listas propias reducidas.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Literal

Label = Literal["positivo", "negativo", "neutral"]
NEUTRAL_BAND = 0.2

POSITIVE = {
    # español (sin tildes: el texto se normaliza)
    "benefici*",
    "ganancia*",
    "gana",
    "ganan",
    "record*",
    "maximo*",
    "dispar*",
    "sube",
    "suben",
    "subida*",
    "alza*",
    "repunt*",
    "rebot*",
    "mejor*",
    "supera*",
    "bate",
    "baten",
    "crec*",
    "impuls*",
    "aument*",
    "eleva*",
    "fortalec*",
    "solid*",
    "optimis*",
    "acuerdo*",
    "adjudic*",
    "contrato*",
    "expansion",
    "lider*",
    "exito*",
    "recompra*",
    "revaloriz*",
    "triplic*",
    "duplic*",
    "avanza*",
    "recupera*",
    # inglés
    "profit*",
    "gain*",
    "beat*",
    "surge",
    "surges",
    "surged",
    "surging",
    "soar*",
    "jump*",
    "rall*",
    "rise*",
    "rising",
    "grow*",
    "strong*",
    "upgrade*",
    "outperform*",
    "boost*",
    "expand*",
    "won",
    "wins",
    "winning",
    "buyback*",
    "raise*",
    "raised",
    "exceed*",
    "improv*",
    "recover*",
}

NEGATIVE = {
    # español
    "perdida*",
    "pierde",
    "pierden",
    "perder",
    "cae",
    "caen",
    "caida*",
    "desplom*",
    "hund*",
    "baja",
    "bajan",
    "bajada*",
    "recort*",
    "rebaj*",
    "multa*",
    "sancion*",
    "investiga*",
    "quiebra",
    "concurso",
    "crisis",
    "despido*",
    "ere",
    "huelga*",
    "retras*",
    "peor*",
    "minimo*",
    "debil*",
    "incertidumbre",
    "preocup*",
    "alerta*",
    "riesgo*",
    "advierte",
    "advertencia*",
    "rebaja",
    "deficit",
    "endeud*",
    "fraude",
    "escandalo*",
    "dimision*",
    "frena*",
    "lastr*",
    "castig*",
    "suspend*",
    "aranceles",
    "arancel",
    "deterior*",
    "sufre",
    "empeor*",
    "desconfianza",
    "pinchazo",
    "tension*",
    "volatil*",
    # inglés
    "loss*",
    "lose",
    "loses",
    "fall*",
    "fell",
    "drop*",
    "plunge*",
    "slump*",
    "tumble*",
    "decline*",
    "cut*",
    "downgrade*",
    "fine*",
    "lawsuit*",
    "probe*",
    "investigation*",
    "bankrupt*",
    "layoff*",
    "strike*",
    "delay*",
    "weak*",
    "miss",
    "misses",
    "missed",
    "warn*",
    "risk*",
    "fraud",
    "scandal*",
    "resign*",
    "tariff*",
    "slowdown",
    "underperform*",
    "concern*",
}

NEGATORS = {"no", "sin", "ni", "nunca", "not", "never", "without", "fails", "failed"}


def normalize(text: str) -> str:
    """Minúsculas y sin tildes ('Caída' → 'caida') para comparar con las listas."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _matches(token: str, terms: set[str]) -> bool:
    for term in terms:
        if term.endswith("*"):
            if token.startswith(term[:-1]):
                return True
        elif token == term:
            return True
    return False


@dataclass(frozen=True)
class Sentiment:
    score: float  # −1 … +1
    label: Label
    positives: list[str] = field(default_factory=list)
    negatives: list[str] = field(default_factory=list)


def analyze(text: str) -> Sentiment:
    tokens = re.findall(r"[a-z0-9ñ]+", normalize(text))
    pos: list[str] = []
    neg: list[str] = []
    for i, tok in enumerate(tokens):
        polarity = 0
        if _matches(tok, POSITIVE):
            polarity = 1
        elif _matches(tok, NEGATIVE):
            polarity = -1
        if polarity == 0:
            continue
        negated = any(t in NEGATORS for t in tokens[max(0, i - 2) : i])
        if negated:
            polarity = -polarity
            tok = f"no {tok}"
        (pos if polarity > 0 else neg).append(tok)
    total = len(pos) + len(neg)
    score = (len(pos) - len(neg)) / total if total else 0.0
    if score > NEUTRAL_BAND:
        label: Label = "positivo"
    elif score < -NEUTRAL_BAND:
        label = "negativo"
    else:
        label = "neutral"
    return Sentiment(score, label, pos, neg)
