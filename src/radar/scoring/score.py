"""Score transparente (0–100) por empresa.

Cómo se calcula (todo visible en la UI):
1. Cada métrica de entrada se convierte en un PERCENTIL (0–1) frente a sus comparables,
   orientado para que 1 = mejor (PER más bajo, ROE más alto, menos volatilidad...).
   - Valoración, salud y crecimiento: frente al SECTOR (un PER de 15 es caro para un
     banco y barato para una tecnológica).
   - Momentum y riesgo: frente a TODO el universo (son comparables entre sectores).
2. Puntuación de un componente = media de los percentiles disponibles × 100.
3. Score total = media ponderada de los componentes disponibles. Si falta alguno, su
   peso se reparte entre los demás (se indica en la UI). Con menos de 3 componentes no
   se da score total: no habría base suficiente.

Un score alto significa "sus métricas son mejores que las de sus comparables", no que el
precio vaya a subir.
"""

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd

from radar.formatting import fmt_metric_value
from radar.fundamentals.metrics import ALL_METRICS, Better
from radar.fundamentals.sector import MIN_PEERS, percentile_rank, select_peers

Basis = Literal["sector", "universe"]
MIN_COMPONENTS = 3
PRO_THRESHOLD = 0.75
CON_THRESHOLD = 0.25


@dataclass(frozen=True)
class InputDef:
    key: str
    better: Better


@dataclass(frozen=True)
class ComponentDef:
    key: str
    label: str
    basis: Basis
    inputs: list[InputDef]
    description: str


COMPONENTS: list[ComponentDef] = [
    ComponentDef(
        "valuation",
        "Valoración",
        "sector",
        [
            InputDef("pe_trailing", "lower"),
            InputDef("pe_forward", "lower"),
            InputDef("peg", "lower"),
            InputDef("price_to_book", "lower"),
            InputDef("fcf_yield", "higher"),
        ],
        "¿Cuánto pagas por lo que la empresa gana y genera, comparado con su sector?",
    ),
    ComponentDef(
        "health",
        "Salud financiera",
        "sector",
        [
            InputDef("debt_to_equity", "lower"),
            InputDef("fcf_margin", "higher"),
            InputDef("roe", "higher"),
            InputDef("operating_margin", "higher"),
        ],
        "¿Es rentable, genera caja y su deuda es razonable para su sector?",
    ),
    ComponentDef(
        "growth",
        "Crecimiento",
        "sector",
        [InputDef("revenue_growth", "higher"), InputDef("earnings_growth", "higher")],
        "¿Crecen sus ventas y beneficios más que los de su sector? (último trimestre interanual)",
    ),
    ComponentDef(
        "momentum",
        "Momentum",
        "universe",
        [
            InputDef("ret_12m", "higher"),
            InputDef("ret_6m", "higher"),
            InputDef("dist_sma200", "higher"),
        ],
        "¿Cómo se ha comportado el precio en los últimos 6–12 meses frente al resto?",
    ),
    ComponentDef(
        "risk",
        "Riesgo (más alto = menos riesgo)",
        "universe",
        [InputDef("vol_1y", "lower"), InputDef("mdd_1y", "higher"), InputDef("beta", "lower")],
        "¿Cuánto oscila y cuánto ha llegado a caer el precio frente al resto?",
    ),
    ComponentDef(
        "dividend",
        "Dividendo",
        "sector",
        [InputDef("dividend_yield", "higher"), InputDef("payout_ratio", "lower")],
        "¿Paga más dividendo que su sector, y de forma sostenible? (solo cuenta si tu "
        "objetivo es cobrar dividendos)",
    ),
]

# El dividendo pesa 0 salvo que el perfil tenga como objetivo cobrar dividendos.
DEFAULT_WEIGHTS: dict[str, float] = {
    "valuation": 0.2,
    "health": 0.2,
    "growth": 0.2,
    "momentum": 0.2,
    "risk": 0.2,
    "dividend": 0.0,
}


@dataclass(frozen=True)
class InputScore:
    key: str
    label: str
    value: float | None
    peer_median: float | None
    n_peers: int
    percentile: float | None  # orientado: 1 = mejor


@dataclass
class ComponentScore:
    key: str
    label: str
    description: str
    basis_label: str
    weight: float
    inputs: list[InputScore]
    score: float | None = None  # 0–100
    effective_weight: float = 0.0  # tras repartir los pesos de componentes sin dato

    @property
    def coverage(self) -> str:
        used = sum(i.percentile is not None for i in self.inputs)
        return f"{used}/{len(self.inputs)}"


@dataclass
class ScoreResult:
    total: float | None
    components: list[ComponentScore]
    pros: list[str] = field(default_factory=list)
    cons: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _input_score(inp: InputDef, row: dict, peers: pd.DataFrame) -> InputScore:
    meta = ALL_METRICS[inp.key]
    value = row.get(inp.key)
    value = None if value is None or pd.isna(value) else float(value)
    col = peers[inp.key].dropna() if inp.key in peers else pd.Series(dtype=float)
    if value is None or len(col) < MIN_PEERS:
        return InputScore(inp.key, meta.label, value, None, len(col), None)
    return InputScore(
        inp.key,
        meta.label,
        value,
        float(np.median(col)),
        len(col),
        percentile_rank(value, col.tolist(), inp.better),
    )


def _explain(inp: InputScore, basis_label: str, currency: str | None) -> str:
    meta = ALL_METRICS[inp.key]
    v = fmt_metric_value(meta.kind, inp.value, currency)
    med = fmt_metric_value(meta.kind, inp.peer_median, currency)
    pct = round(inp.percentile * 100)
    return f"{meta.label} {v} frente a una mediana de {med} ({basis_label}): mejor que el {pct} %."


def score_company(
    row: dict,
    universe: pd.DataFrame,
    weights: dict[str, float] | None = None,
    currency: str | None = None,
) -> ScoreResult:
    """Calcula el score de `row` (dict con ticker, sector, region y métricas)."""
    weights = weights or DEFAULT_WEIGHTS
    ticker = row.get("ticker")
    others = universe[universe["ticker"] != ticker]
    sector_peers, sector_label = select_peers(others, row.get("sector"), row.get("region", ""))
    comps: list[ComponentScore] = []
    pros: list[tuple[float, str]] = []
    cons: list[tuple[float, str]] = []

    for cdef in COMPONENTS:
        if cdef.basis == "sector":
            peers, basis_label = sector_peers, sector_label
        else:
            peers, basis_label = others, "todo el universo"
        inputs = [_input_score(i, row, peers) for i in cdef.inputs]
        valid = [i.percentile for i in inputs if i.percentile is not None]
        comp = ComponentScore(
            cdef.key, cdef.label, cdef.description, basis_label, weights.get(cdef.key, 0), inputs
        )
        if valid:
            comp.score = float(np.mean(valid) * 100)
        comps.append(comp)
        for i in inputs:
            if i.percentile is None:
                continue
            if i.percentile >= PRO_THRESHOLD:
                pros.append((i.percentile, _explain(i, basis_label, currency)))
            elif i.percentile <= CON_THRESHOLD:
                cons.append((1 - i.percentile, _explain(i, basis_label, currency)))

    available = [c for c in comps if c.score is not None and c.weight > 0]
    notes: list[str] = []
    total = None
    weight_sum = sum(c.weight for c in available)
    if len(available) >= MIN_COMPONENTS and weight_sum > 0:
        for c in available:
            c.effective_weight = c.weight / weight_sum
        total = float(sum(c.score * c.effective_weight for c in available))
        missing = [c.label for c in comps if c.score is None and c.weight > 0]
        if missing:
            notes.append(
                f"Sin datos para: {', '.join(missing)}. Su peso se ha repartido "
                "proporcionalmente entre los demás componentes."
            )
    else:
        notes.append(
            f"Solo hay datos para {len(available)} componente(s); hacen falta al menos "
            f"{MIN_COMPONENTS} para dar un score total con sentido."
        )

    return ScoreResult(
        total=total,
        components=comps,
        pros=[t for _, t in sorted(pros, reverse=True)],
        cons=[t for _, t in sorted(cons, reverse=True)],
        notes=notes,
    )


def score_band(total: float) -> str:
    """Descripción neutra de la puntuación (no es una recomendación)."""
    if total >= 70:
        return "métricas claramente mejores que las de sus comparables"
    if total >= 55:
        return "métricas algo mejores que las de sus comparables"
    if total > 45:
        return "métricas en línea con sus comparables"
    if total > 30:
        return "métricas algo peores que las de sus comparables"
    return "métricas claramente peores que las de sus comparables"
