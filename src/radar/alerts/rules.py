"""Reglas de alerta (funciones puras).

Las alertas saltan al CRUZAR el umbral ("edge-triggered"), no mientras se cumple la
condición: si el precio ya está por encima y sigue por encima, no se repite el aviso cada
minuto. Para volver a avisar, la condición tiene que dejar de cumplirse y cumplirse otra vez.
"""

from dataclasses import dataclass
from typing import Literal

Metric = Literal["price", "change_pct", "rsi", "sma50", "sma200"]
Op = Literal["above", "below"]

METRIC_LABELS: dict[str, str] = {
    "price": "Precio",
    "change_pct": "Variación diaria (%)",
    "rsi": "RSI (14)",
    "sma50": "Precio frente a su SMA 50",
    "sma200": "Precio frente a su SMA 200",
}
OP_LABELS = {"above": "por encima de", "below": "por debajo de"}
NEEDS_HISTORY = {"rsi", "sma50", "sma200"}


@dataclass(frozen=True)
class Alert:
    ticker: str
    metric: Metric
    op: Op
    threshold: float | None  # None en las alertas de cruce con medias
    id: int | None = None
    active: bool = True
    last_state: bool | None = None  # None = aún no evaluada


@dataclass(frozen=True)
class Observation:
    value: float  # precio, variación en %, RSI...
    reference: float | None = None  # valor de la media en alertas sma50/sma200


def describe(a: Alert) -> str:
    if a.metric in ("sma50", "sma200"):
        n = a.metric[3:]
        return f"{a.ticker}: precio {OP_LABELS[a.op]} su media de {n} sesiones"
    unit = " %" if a.metric == "change_pct" else ""
    thr = f"{a.threshold:g}".replace(".", ",")
    return f"{a.ticker}: {METRIC_LABELS[a.metric].split(' (')[0]} {OP_LABELS[a.op]} {thr}{unit}"


def condition(a: Alert, obs: Observation) -> bool:
    target = obs.reference if a.metric in ("sma50", "sma200") else a.threshold
    if target is None:
        raise ValueError(f"Falta el valor de referencia para {a.metric}")
    return obs.value > target if a.op == "above" else obs.value < target


@dataclass(frozen=True)
class Evaluation:
    state: bool  # ¿se cumple ahora?
    fired: bool  # ¿hay que avisar? (pasó de no cumplirse a cumplirse)


def evaluate(a: Alert, obs: Observation) -> Evaluation:
    """Primera evaluación: solo fija el estado (no avisa). Después avisa en cada cruce."""
    state = condition(a, obs)
    fired = a.active and a.last_state is False and state
    return Evaluation(state, fired)
