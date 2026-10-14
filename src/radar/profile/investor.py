"""Perfil inversor: del test de 5 preguntas a un nivel de riesgo, un reparto y unos pesos.

Todo son reglas fijas y visibles (se muestran en la app):

1. Puntos de riesgo = horizonte (0–3) + reacción ante una caída del 20 % (0–3).
   - Objetivo "conservar capital": −2 puntos.
   - Sin experiencia: como mucho 4 puntos (moderado).
   - Horizonte de menos de 2 años: conservador siempre (no da tiempo a recuperarse).
2. Nivel: ≤ 2 puntos conservador, ≤ 4 moderado, más de 4 dinámico.
3. Riesgo que se tolera: conservador → bajo; moderado → hasta medio; dinámico → hasta alto.
4. Reparto de partida por nivel; con menos de 1.000 € todo en ETFs (las comisiones mínimas
   pesarían demasiado en acciones sueltas) y sin experiencia, como mucho un 15 % en acciones.
5. Pesos del score por nivel; el objetivo "dividendos" activa el componente de dividendo.
"""

from dataclasses import asdict, dataclass, field
from typing import Literal

Objective = Literal["growth", "dividends", "preserve"]
Level = Literal["conservador", "moderado", "dinamico"]

RISK_ES = ["bajo", "medio", "alto"]
LEVEL_ES: dict[str, str] = {
    "conservador": "Conservador",
    "moderado": "Moderado",
    "dinamico": "Dinámico",
}
OBJECTIVE_ES: dict[str, str] = {
    "growth": "crecimiento",
    "dividends": "dividendos",
    "preserve": "conservar capital",
}

# Textos de las opciones del test (la app los muestra tal cual)
QUESTIONS: list[dict] = [
    {
        "key": "horizon",
        "topic": "Horizonte",
        "question": "¿Cuánto tiempo puedes dejar este dinero invertido sin necesitarlo?",
        "hint": "Cuanto más largo, más tiempo hay para recuperarse de las caídas.",
        "options": [
            ["Menos de 2 años", "Lo necesitaré pronto"],
            ["De 2 a 5 años", "Medio plazo"],
            ["De 5 a 10 años", "Largo plazo"],
            ["Más de 10 años", "Por ejemplo, para la jubilación"],
        ],
    },
    {
        "key": "reaction",
        "topic": "Tolerancia al riesgo",
        "question": "Si tu inversión cae un 20 % en un mes, ¿qué harías?",
        "hint": "No hay respuesta correcta: describe cómo te sentirías de verdad.",
        "options": [
            ["Vendería todo", "No soporto ver pérdidas"],
            ["Vendería una parte", "Para dormir tranquilo"],
            ["Esperaría sin tocar nada", "Las caídas son normales"],
            ["Invertiría más", "Lo vería como una oportunidad"],
        ],
    },
    {
        "key": "amount",
        "topic": "Cantidad",
        "question": "¿Cuánto tienes disponible para invertir ahora?",
        "hint": "Solo dinero que no necesites para vivir ni para imprevistos.",
        "options": [
            ["Menos de 1.000 €", "Empezar poco a poco"],
            ["De 1.000 a 10.000 €", ""],
            ["De 10.000 a 50.000 €", ""],
            ["Más de 50.000 €", ""],
        ],
    },
    {
        "key": "objective",
        "topic": "Objetivo",
        "question": "¿Qué buscas principalmente?",
        "hint": "Cambia el tipo de empresas y ETFs que se priorizan.",
        "options": [
            ["Crecimiento", "Que el capital crezca a largo plazo"],
            ["Dividendos", "Ingresos periódicos"],
            ["Conservar capital", "Proteger lo que tengo frente a la inflación"],
        ],
        "values": ["growth", "dividends", "preserve"],
    },
    {
        "key": "experience",
        "topic": "Experiencia",
        "question": "¿Qué experiencia tienes invirtiendo?",
        "hint": "Ajusta el nivel de las explicaciones y de los productos sugeridos.",
        "options": [
            ["Ninguna", "Es mi primera vez"],
            ["He invertido en fondos", "Fondos de inversión o planes de pensiones"],
            ["Invierto en acciones o ETFs", "Algo de experiencia directa"],
            ["Varios años", "Entiendo bien los riesgos"],
        ],
    },
]

# Importe representativo de cada tramo de la pregunta "cantidad" (para los ejemplos)
AMOUNT_EUR = [500.0, 5_000.0, 25_000.0, 75_000.0]
# Número orientativo de acciones distintas para repartir el riesgo de empresa
POSITIONS = [0, 5, 10, 15]

ALLOCATION_BY_LEVEL: dict[str, tuple[int, int, int]] = {
    # (ETFs indexados, acciones, renta fija/liquidez) en %
    "conservador": (55, 10, 35),
    "moderado": (70, 25, 5),
    "dinamico": (65, 35, 0),
}
MAX_STOCKS_WITHOUT_EXPERIENCE = 15

WEIGHTS_BY_LEVEL: dict[str, dict[str, float]] = {
    "conservador": {
        "valuation": 0.2, "health": 0.3, "growth": 0.1, "momentum": 0.1, "risk": 0.3,
    },
    "moderado": {
        "valuation": 0.2, "health": 0.2, "growth": 0.2, "momentum": 0.2, "risk": 0.2,
    },
    "dinamico": {
        "valuation": 0.2, "health": 0.15, "growth": 0.3, "momentum": 0.25, "risk": 0.1,
    },
}  # fmt: skip
DIVIDEND_WEIGHT = 0.25
PRESERVE_EXTRA_RISK_WEIGHT = 0.1


@dataclass(frozen=True)
class Answers:
    horizon: int  # 0..3
    reaction: int  # 0..3
    amount: int  # 0..3
    objective: Objective
    experience: int  # 0..3

    def __post_init__(self) -> None:
        for name in ("horizon", "reaction", "amount", "experience"):
            if getattr(self, name) not in range(4):
                raise ValueError(f"Respuesta fuera de rango: {name}")
        if self.objective not in OBJECTIVE_ES:
            raise ValueError("Objetivo desconocido")


@dataclass(frozen=True)
class Allocation:
    etf: int  # % en ETFs indexados de renta variable
    stocks: int  # % en acciones individuales
    safe: int  # % en renta fija o liquidez


@dataclass(frozen=True)
class InvestorProfile:
    answers: Answers
    level: Level
    points: int
    max_risk: int  # 0 bajo, 1 medio, 2 alto
    allocation: Allocation
    weights: dict[str, float]
    amount_eur: float
    positions: int
    notes: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return LEVEL_ES[self.level]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["label"] = self.label
        d["max_risk_label"] = RISK_ES[self.max_risk]
        d["objective_label"] = OBJECTIVE_ES[self.answers.objective]
        return d


def compute_profile(a: Answers) -> InvestorProfile:
    """Aplica las reglas del docstring del módulo."""
    notes: list[str] = []
    points = a.horizon + a.reaction
    if a.objective == "preserve":
        points -= 2
    if a.experience == 0 and points > 4:
        points = 4
        notes.append("Sin experiencia previa, el perfil se limita a moderado.")
    if a.horizon == 0:
        level: Level = "conservador"
        notes.append(
            "Con menos de 2 años de horizonte no da tiempo a recuperarse de una caída: "
            "perfil conservador."
        )
    elif points <= 2:
        level = "conservador"
    elif points <= 4:
        level = "moderado"
    else:
        level = "dinamico"

    etf, stocks, safe = ALLOCATION_BY_LEVEL[level]
    if a.amount == 0 and stocks:
        etf, stocks = etf + stocks, 0
        notes.append(
            "Con menos de 1.000 € las comisiones mínimas pesan mucho en acciones sueltas: "
            "el reparto va entero a ETFs."
        )
    elif a.experience == 0 and stocks > MAX_STOCKS_WITHOUT_EXPERIENCE:
        etf, stocks = etf + stocks - MAX_STOCKS_WITHOUT_EXPERIENCE, MAX_STOCKS_WITHOUT_EXPERIENCE
        notes.append("Sin experiencia, como mucho un 15 % en acciones individuales.")

    weights = dict(WEIGHTS_BY_LEVEL[level])
    weights["dividend"] = DIVIDEND_WEIGHT if a.objective == "dividends" else 0.0
    if a.objective == "preserve":
        weights["risk"] += PRESERVE_EXTRA_RISK_WEIGHT

    return InvestorProfile(
        answers=a,
        level=level,
        points=points,
        max_risk={"conservador": 0, "moderado": 1, "dinamico": 2}[level],
        allocation=Allocation(etf, stocks, safe),
        weights=weights,
        amount_eur=AMOUNT_EUR[a.amount],
        positions=POSITIONS[a.amount] if stocks else 0,
        notes=notes,
    )


def answers_from_dict(d: dict) -> Answers:
    """Construye y valida las respuestas recibidas de la interfaz."""
    return Answers(
        horizon=int(d["horizon"]),
        reaction=int(d["reaction"]),
        amount=int(d["amount"]),
        objective=d["objective"],
        experience=int(d["experience"]),
    )


PROFILE_DESCRIPTIONS: dict[str, str] = {
    "conservador": "Priorizas no perder dinero. Verás sobre todo ETFs amplios, renta fija y "
    "empresas de riesgo bajo; las de riesgo alto aparecerán como «Evitar».",
    "moderado": "Aceptas caídas temporales a cambio de más rentabilidad a largo plazo. La base "
    "son ETFs indexados globales, con una parte en empresas sólidas.",
    "dinamico": "Toleras bien las caídas y tienes horizonte largo. Más peso en acciones, "
    "incluidas algunas de riesgo alto si sus números lo justifican.",
}
