"""Motor de recomendaciones: de la puntuación a una señal "Comprar / Vigilar / Evitar".

Reglas fijas y visibles en la app (pestaña Metodología y detalle de cada valor):

Acciones
- Comprar: puntuación ≥ 65, precio dentro o por debajo del rango de entrada (si no hay
  rango fiable, componente de valoración ≥ 50), riesgo dentro de tu tolerancia,
  beneficio positivo (una empresa en pérdidas nunca sale como "Comprar") y al menos 200
  millones de capitalización (por debajo, comprar y vender sin mover el precio es difícil).
- Evitar: puntuación < 40, riesgo dos niveles por encima de tu tolerancia, o sin cotizar
  desde hace más de 10 días (suele ser una exclusión de bolsa, p. ej. tras una OPA).
- Datos de precio sospechosos (saltos diarios imposibles, ver `indicators/quality.py`): nunca
  «Comprar»; sale «Vigilar» con el aviso.
- Vigilar: el resto.

ETFs (se comparan con los demás ETFs de referencia en coste, tamaño, riesgo y momentum)
- Evitar: riesgo dos niveles por encima de tu tolerancia.
- Vigilar: riesgo un nivel por encima.
- Comprar: ETF "base de cartera" (o de dividendos, si tu objetivo son dividendos); renta
  fija y liquidez si tu perfil es conservador o buscas conservar capital; complementos con
  puntuación ≥ 65.
- Vigilar: el resto.

Nivel de riesgo (último año): bajo si volatilidad < 20 % y caída máxima menor del 20 %;
medio si volatilidad < 32 % y caída menor del 35 %; alto en otro caso. En acciones, el
tamaño lo sube: capitalización < 1.000 millones → al menos medio; < 200 millones → alto
(valores pequeños y poco líquidos pueden moverse mucho de golpe).

Rango de entrada (acciones): precio que tendría con el PER, el precio/valor contable y la
rentabilidad FCF medianos de sus comparables. Va de la estimación más baja a la mediana.
Sin rango si hay menos de 2 estimaciones o si la mayor es más de 2,5 veces la menor.
"""

from dataclasses import asdict, dataclass, field
from typing import Literal

import numpy as np
import pandas as pd

from radar.etfs import BY_TICKER as ETF_INFO
from radar.etfs import ROLE_ES
from radar.formatting import fmt_metric_value, fmt_price
from radar.fundamentals.metrics import ALL_METRICS
from radar.fundamentals.sector import MIN_PEERS, percentile_rank, sector_es, select_peers
from radar.profile.investor import RISK_ES, InvestorProfile
from radar.recommend import texts
from radar.scoring.score import (
    CON_THRESHOLD,
    PRO_THRESHOLD,
    ComponentScore,
    InputScore,
    score_company,
)

Label = Literal["buy", "watch", "avoid"]
LABEL_ES: dict[str, str] = {"buy": "Comprar", "watch": "Vigilar", "avoid": "Evitar"}
LABEL_ORDER: dict[str, int] = {"buy": 0, "watch": 1, "avoid": 2}

BUY_SCORE = 65
AVOID_SCORE = 40
MIN_VALUATION_WITHOUT_RANGE = 50
LOW_VOL, MID_VOL = 0.20, 0.32
LOW_MDD, MID_MDD = -0.20, -0.35
SMALL_CAP = 1e9  # en la moneda de las cuentas (≈ euros o dólares)
MICRO_CAP = 2e8
RANGE_MAX_SPREAD = 2.5
STALE_PRICE_DAYS = 10
MAX_REASONS = 3

# Métricas que dicen casi lo mismo: si ya hay una, no se repite la otra como razón
_SIMILAR = [{"pe_trailing", "pe_forward"}, {"ret_12m", "ret_6m"}]

ETF_COMPONENTS: list[tuple[str, str, float, list[tuple[str, str]], str]] = [
    # (clave, etiqueta, peso, [(métrica, mejor)], descripción)
    ("cost", "Coste", 0.3, [("expense_ratio", "lower")], "¿Cobra menos comisión anual?"),
    ("size", "Tamaño", 0.2, [("total_assets", "higher")], "¿Gestiona mucho dinero?"),
    (
        "risk",
        "Riesgo (más alto = menos riesgo)",
        0.3,
        [("vol_1y", "lower"), ("mdd_1y", "higher")],
        "¿Cuánto oscila y cuánto ha llegado a caer?",
    ),
    ("momentum", "Momentum", 0.2, [("ret_12m", "higher")], "¿Cómo le ha ido en 12 meses?"),
]


@dataclass(frozen=True)
class Reason:
    text: str
    data: str = ""
    metric: str | None = None


@dataclass(frozen=True)
class RuleCheck:
    rule: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class FairValueEstimate:
    method: str
    metric: str
    value: float
    peer_median: float
    estimate: float


@dataclass(frozen=True)
class EntryRange:
    low: float | None
    high: float | None
    position: Literal["below", "inside", "above"] | None
    estimates: list[FairValueEstimate]
    peer_group: str
    note: str

    @property
    def reliable(self) -> bool:
        return self.low is not None


@dataclass
class Recommendation:
    ticker: str
    name: str
    kind: Literal["stock", "etf"]
    label: Label
    score: float | None
    risk_level: int | None
    price: float | None
    currency: str | None
    summary: str
    fit: str
    pros: list[Reason]
    cons: list[Reason]
    checks: list[RuleCheck]
    components: list[ComponentScore]
    entry: EntryRange | None
    entry_note: str
    risk_detail: str
    sector: str | None = None
    country: str | None = None
    spain_index: str | None = None
    etf_role: str | None = None
    etf_index: str | None = None
    notes: list[str] = field(default_factory=list)
    as_of: dict[str, str | None] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["label_es"] = LABEL_ES[self.label]
        d["risk_label"] = RISK_ES[self.risk_level] if self.risk_level is not None else "n/d"
        d["sector_es"] = sector_es(self.sector) if self.sector else None
        d["etf_role_es"] = ROLE_ES.get(self.etf_role or "")
        return d


# --- Piezas sueltas (puras) ---------------------------------------------------------


def _num(v) -> float | None:
    return None if v is None or pd.isna(v) else float(v)


def size_floor(market_cap: float | None) -> int:
    """Riesgo mínimo por tamaño: 2 si < 200 millones, 1 si < 1.000 millones, si no 0."""
    if market_cap is None:
        return 0
    if market_cap < MICRO_CAP:
        return 2
    if market_cap < SMALL_CAP:
        return 1
    return 0


def risk_level(vol: float | None, mdd: float | None, market_cap: float | None = None) -> int | None:
    """0 bajo, 1 medio, 2 alto (ver docstring del módulo). None si no hay volatilidad."""
    if vol is None:
        return None
    if vol < LOW_VOL and (mdd is None or mdd > LOW_MDD):
        level = 0
    elif vol < MID_VOL and (mdd is None or mdd > MID_MDD):
        level = 1
    else:
        level = 2
    return max(level, size_floor(market_cap))


def risk_detail(
    vol: float | None,
    mdd: float | None,
    beta: float | None = None,
    market_cap: float | None = None,
) -> str:
    if vol is None:
        return "Sin histórico suficiente para medir el riesgo: se trata como medio."
    parts = [f"volatilidad anual del {fmt_metric_value('pct', vol)}"]
    if mdd is not None:
        parts.append(f"peor caída en un año del {fmt_metric_value('pct', mdd)}")
    if beta is not None:
        parts.append(f"beta de {fmt_metric_value('ratio', beta)}")
    text = "En el último año: " + ", ".join(parts) + "."
    floor = size_floor(market_cap)
    if floor:
        size = "muy pequeña (menos de 200 millones)" if floor == 2 else "pequeña (menos de "
        size += "" if floor == 2 else "1.000 millones)"
        text += f" Además es una empresa {size}: puede moverse mucho de golpe y es menos líquida."
    return text


def last_close_gap_days(row: dict) -> float | None:
    """Días entre el último cierre y la descarga. None si falta alguna de las dos fechas."""
    last, fetched = row.get("last_close"), row.get("history_as_of")
    if not last or not fetched:
        return None
    return (pd.Timestamp(fetched) - pd.Timestamp(last)).total_seconds() / 86400


def is_trading(row: dict) -> bool:
    """False si el último cierre es de hace más de STALE_PRICE_DAYS días."""
    gap = last_close_gap_days(row)
    return gap is None or gap <= STALE_PRICE_DAYS


def is_profitable(row: dict) -> bool | None:
    """True si gana dinero (margen neto o PER positivos), False si pierde, None sin datos."""
    margin, pe = _num(row.get("profit_margin")), _num(row.get("pe_trailing"))
    if margin is not None:
        return margin > 0
    if pe is not None:
        return pe > 0
    return None


_FAIR_METHODS: list[tuple[str, str, str]] = [
    ("pe_trailing", "PER", "lower"),
    ("price_to_book", "Precio/valor contable", "lower"),
    ("fcf_yield", "Rentabilidad FCF", "higher"),
]


def entry_range(row: dict, peers: pd.DataFrame, peer_group: str) -> EntryRange | None:
    """Rango de entrada por múltiplos medianos del sector (ver docstring del módulo)."""
    price = _num(row.get("price"))
    if price is None or price <= 0:
        return None
    estimates: list[FairValueEstimate] = []
    for key, label, better in _FAIR_METHODS:
        if key == "fcf_yield" and row.get("sector") == "Financial Services":
            continue  # el flujo de caja de un banco no mide lo mismo
        v = _num(row.get(key))
        col = peers[key].dropna() if key in peers else pd.Series(dtype=float)
        col = col[col > 0]
        if v is None or v <= 0 or len(col) < MIN_PEERS:
            continue
        med = float(np.median(col))
        est = price * med / v if better == "lower" else price * v / med
        estimates.append(FairValueEstimate(label, key, v, med, est))
    if len(estimates) < 2:
        return EntryRange(
            None, None, None, estimates, peer_group,
            "Hay menos de dos métodos con datos suficientes: no se da un rango fiable.",
        )  # fmt: skip
    values = [e.estimate for e in estimates]
    if max(values) / min(values) > RANGE_MAX_SPREAD:
        return EntryRange(
            None, None, None, estimates, peer_group,
            "Las estimaciones difieren demasiado entre sí: no se da un rango fiable.",
        )  # fmt: skip
    low, high = min(values), float(np.median(values))
    position = "below" if price < low else "inside" if price <= high else "above"
    note = {
        "below": "El precio está por debajo del rango: más barata que sus comparables.",
        "inside": "El precio está dentro del rango según los múltiplos de su sector.",
        "above": "El precio está por encima del rango: hoy cotiza más cara que sus comparables.",
    }[position]
    return EntryRange(low, high, position, estimates, peer_group, note)


def _reason_data(inp: InputScore, basis: str, currency: str | None) -> str:
    kind = ALL_METRICS[inp.key].kind
    v = fmt_metric_value(kind, inp.value, currency)
    med = fmt_metric_value(kind, inp.peer_median, currency)
    return f"{inp.label} {v} frente a {med} ({basis})."


def pick_reasons(
    components: list[ComponentScore], currency: str | None
) -> tuple[list[Reason], list[Reason]]:
    """Las razones más claras a favor y en contra: percentiles más extremos primero."""
    pros: list[tuple[float, Reason]] = []
    cons: list[tuple[float, Reason]] = []
    for c in components:
        if c.weight <= 0:
            continue  # un componente que no cuenta para el perfil no da razones
        for i in c.inputs:
            if i.percentile is None or i.key not in texts.METRIC_TEXTS:
                continue
            good, bad = texts.METRIC_TEXTS[i.key]
            data = _reason_data(i, c.basis_label, currency)
            if i.percentile >= PRO_THRESHOLD:
                pros.append((i.percentile, Reason(good, data, i.key)))
            elif i.percentile <= CON_THRESHOLD:
                cons.append((1 - i.percentile, Reason(bad, data, i.key)))

    def top(items: list[tuple[float, Reason]]) -> list[Reason]:
        out: list[Reason] = []
        for _, r in sorted(items, key=lambda t: -t[0]):
            if any(r.metric in g and any(o.metric in g for o in out) for g in _SIMILAR):
                continue
            out.append(r)
            if len(out) == MAX_REASONS:
                break
        return out

    return top(pros), top(cons)


def _fill_cons(cons: list[Reason], extra: list[str]) -> list[Reason]:
    out = list(cons)
    for text in extra:
        if len(out) >= MAX_REASONS:
            break
        out.append(Reason(text))
    return out


def fit_text(risk: int | None, profile: InvestorProfile) -> str:
    r = 1 if risk is None else risk
    name = profile.label
    if r <= profile.max_risk:
        return f"Encaja con tu perfil {name}: riesgo {RISK_ES[r]}, dentro de lo que toleras."
    if r == profile.max_risk + 1:
        return f"Riesgo {RISK_ES[r]}: algo por encima de lo que toleras con tu perfil {name}."
    return f"Riesgo {RISK_ES[r]}: muy por encima de lo que toleras con tu perfil {name}."


def _as_of(row: dict) -> dict[str, str | None]:
    return {k: row.get(k) for k in ("fundamentals_as_of", "history_as_of", "last_report")}


# --- Acciones -----------------------------------------------------------------------


def recommend_stock(row: dict, stocks: pd.DataFrame, profile: InvestorProfile) -> Recommendation:
    currency = row.get("price_currency") or row.get("currency")
    res = score_company(row, stocks, weights=profile.weights, currency=currency)
    vol, mdd = _num(row.get("vol_1y")), _num(row.get("mdd_1y"))
    cap = _num(row.get("market_cap"))
    risk = risk_level(vol, mdd, cap)
    r = 1 if risk is None else risk
    others = stocks[stocks["ticker"] != row.get("ticker")]
    peers, group = select_peers(others, row.get("sector"), row.get("region", ""))
    entry = entry_range(row, peers, group)

    score = res.total
    valuation = next((c.score for c in res.components if c.key == "valuation"), None)
    checks = [
        RuleCheck(
            f"Puntuación de {BUY_SCORE} o más",
            score is not None and score >= BUY_SCORE,
            f"{score:.0f}/100" if score is not None else "Sin datos suficientes para puntuar",
        )
    ]
    if entry and entry.reliable:
        val_ok = entry.position in ("below", "inside")
        checks.append(
            RuleCheck(
                "Precio dentro o por debajo del rango de entrada",
                val_ok,
                f"Precio {fmt_price(row.get('price'), currency)}; rango "
                f"{fmt_price(entry.low, currency)} – {fmt_price(entry.high, currency)}",
            )
        )
    else:
        val_ok = valuation is not None and valuation >= MIN_VALUATION_WITHOUT_RANGE
        checks.append(
            RuleCheck(
                f"Sin rango fiable: valoración frente al sector de {MIN_VALUATION_WITHOUT_RANGE} "
                "o más",
                val_ok,
                f"Valoración {valuation:.0f}/100" if valuation is not None else "Sin dato",
            )
        )
    risk_ok = r <= profile.max_risk
    checks.append(
        RuleCheck(
            "Riesgo dentro de tu tolerancia",
            risk_ok,
            f"Riesgo {RISK_ES[r]}; tu perfil {profile.label} tolera hasta "
            f"{RISK_ES[profile.max_risk]}",
        )
    )
    profitable = is_profitable(row)
    checks.append(
        RuleCheck(
            "Gana dinero (beneficio neto positivo)",
            bool(profitable),
            {True: "Sí", False: "No: está en pérdidas", None: "Sin dato de beneficio"}[profitable],
        )
    )

    big_enough = cap is None or cap >= MICRO_CAP
    checks.append(
        RuleCheck(
            "Tamaño suficiente (200 millones o más de capitalización)",
            big_enough,
            f"Capitalización {fmt_metric_value('money', cap, row.get('currency'))}"
            if cap is not None
            else "Sin dato: no se aplica",
        )
    )

    trading = is_trading(row)
    if not trading:
        last = pd.Timestamp(row["last_close"]).strftime("%d/%m/%Y")
        checks.append(RuleCheck("Cotiza con normalidad", False, f"Último cierre: {last}"))

    warning = row.get("data_warning") or None
    if warning:
        checks.append(RuleCheck("Datos de precio fiables", False, warning))

    pros, cons = pick_reasons(res.components, currency)
    if profitable is False:
        cons.insert(0, Reason("Está en pérdidas: no gana dinero con su negocio actual."))
        cons = cons[:MAX_REASONS]
    extra_cons = []
    if currency and currency != "EUR":
        extra_cons.append(texts.currency_risk(currency))
    if row.get("sector") in texts.SECTOR_RISKS:
        extra_cons.append(texts.SECTOR_RISKS[row["sector"]])
    extra_cons.append(texts.SINGLE_STOCK_RISK)
    cons = _fill_cons(cons, extra_cons)

    label: Label
    if not trading:
        label = "avoid"
        summary = (
            f"No cotiza desde el {last}: puede haber sido excluida de bolsa (por ejemplo, "
            "tras una OPA). Sus datos ya no son fiables."
        )
    elif score is None:
        label = "watch"
        summary = "No hay datos suficientes para puntuarla: revisa sus números a mano."
    elif warning and score >= BUY_SCORE:
        label = "watch"
        summary = "Sus datos de precio parecen erróneos: no es fiable darle señal de compra."
    elif score < AVOID_SCORE:
        label = "avoid"
        summary = (
            cons[0].text if cons else "Sus métricas son claramente peores que las de su sector."
        )
    elif r >= profile.max_risk + 2:
        label = "avoid"
        summary = f"Riesgo {RISK_ES[r]}: demasiado para tu perfil {profile.label}."
    elif all(c.passed for c in checks):
        label = "buy"
        summary = pros[0].text if pros else "Cumple las tres condiciones del modelo."
    else:
        label = "watch"
        if score >= BUY_SCORE and not val_ok:
            summary = "Buenos números, pero hoy cotiza por encima de su rango razonable."
        elif score >= BUY_SCORE and not risk_ok:
            summary = "Buenos números, pero con más riesgo del que toleras."
        elif score >= BUY_SCORE and not profitable:
            summary = "Buenas métricas relativas, pero ahora mismo no gana dinero."
        elif score >= BUY_SCORE and not big_enough:
            summary = "Buenas métricas, pero es una empresa muy pequeña y poco líquida."
        else:
            summary = "Métricas en línea con sus comparables: ni destaca ni preocupa."

    fit = fit_text(risk, profile)
    dy = _num(row.get("dividend_yield"))
    if profile.answers.objective == "dividends" and dy:
        fit += f" Paga un dividendo del {fmt_metric_value('pct', dy)}."

    return Recommendation(
        ticker=row["ticker"],
        name=row.get("name") or row["ticker"],
        kind="stock",
        label=label,
        score=score,
        risk_level=risk,
        price=_num(row.get("price")),
        currency=currency,
        summary=summary,
        fit=fit,
        pros=pros,
        cons=cons,
        checks=checks,
        components=res.components,
        entry=entry,
        entry_note=entry.note if entry else "Sin precio disponible: no se calcula el rango.",
        risk_detail=risk_detail(vol, mdd, _num(row.get("beta")), cap),
        sector=row.get("sector"),
        country=row.get("country"),
        spain_index=row.get("spain_index"),
        notes=res.notes,
        as_of=_as_of(row),
    )


# --- ETFs ---------------------------------------------------------------------------


def score_etf(row: dict, etfs: pd.DataFrame) -> tuple[float | None, list[ComponentScore]]:
    """Puntuación frente a los demás ETFs de referencia (percentiles, como el score)."""
    others = etfs[etfs["ticker"] != row["ticker"]]
    comps: list[ComponentScore] = []
    for key, label, weight, inputs, desc in ETF_COMPONENTS:
        scored = []
        for metric, better in inputs:
            v = _num(row.get(metric))
            col = others[metric].dropna() if metric in others else pd.Series(dtype=float)
            pct = percentile_rank(v, col.tolist(), better) if v is not None and len(col) else None
            med = float(np.median(col)) if len(col) else None
            scored.append(InputScore(metric, ALL_METRICS[metric].label, v, med, len(col), pct))
        comp = ComponentScore(key, label, desc, "ETFs de referencia", weight, scored)
        valid = [i.percentile for i in scored if i.percentile is not None]
        if valid:
            comp.score = float(np.mean(valid) * 100)
        comps.append(comp)
    available = [c for c in comps if c.score is not None]
    if len(available) < 2:
        return None, comps
    total_w = sum(c.weight for c in available)
    for c in available:
        c.effective_weight = c.weight / total_w
    return float(sum(c.score * c.effective_weight for c in available)), comps


def recommend_etf(row: dict, etfs: pd.DataFrame, profile: InvestorProfile) -> Recommendation:
    info = ETF_INFO[row["ticker"]]
    score, comps = score_etf(row, etfs)
    vol, mdd = _num(row.get("vol_1y")), _num(row.get("mdd_1y"))
    risk = risk_level(vol, mdd)
    r = 1 if risk is None else risk
    objective = profile.answers.objective
    role = info.role
    acts_as_core = role == "core" or (role == "dividend" and objective == "dividends")
    wants_safety = profile.level == "conservador" or objective == "preserve"

    checks = [
        RuleCheck(
            "Riesgo dentro de tu tolerancia",
            r <= profile.max_risk,
            f"Riesgo {RISK_ES[r]}; tu perfil {profile.label} tolera hasta "
            f"{RISK_ES[profile.max_risk]}",
        ),
        RuleCheck(
            "Encaja como pieza de tu cartera",
            acts_as_core
            or (role in ("bonds", "cash") and wants_safety)
            or (role == "complement" and score is not None and score >= BUY_SCORE),
            f"Papel: {ROLE_ES[role]}",
        ),
    ]

    label: Label
    if r >= profile.max_risk + 2:
        label = "avoid"
    elif all(c.passed for c in checks):
        label = "buy"
    else:
        label = "watch"

    pros = [Reason(texts.ETF_ROLE_PROS[role], f"Replica el índice {info.index}.")]
    cons: list[Reason] = []
    ter = next(i for c in comps for i in c.inputs if i.key == "expense_ratio")
    for c in comps:
        for i in c.inputs:
            if i.key in texts.METRIC_TEXTS and i.percentile is not None:
                good, bad = texts.METRIC_TEXTS[i.key]
                data = _reason_data(i, "ETFs de referencia", None)
                if i.percentile >= PRO_THRESHOLD:
                    pros.append(Reason(good, data, i.key))
                elif i.percentile <= CON_THRESHOLD:
                    cons.append(Reason(bad, data, i.key))
    if info.accumulating:
        pros.append(Reason(texts.ETF_ACCUMULATING))
    elif objective == "dividends":
        pros.append(Reason("Reparte dividendos periódicos, acorde con tu objetivo."))
    else:
        cons.append(Reason(texts.ETF_DISTRIBUTING))
    if ter.value is None:
        cons.insert(0, Reason(texts.ETF_NO_TER))
    if role == "bonds":
        cons.append(Reason(texts.ETF_BONDS_RATE_RISK))
    elif role == "cash":
        cons.append(Reason(texts.ETF_CASH_RISK))
    elif info.zone in texts.ETF_ZONE_RISKS:
        cons.append(Reason(texts.ETF_ZONE_RISKS[info.zone]))
    elif info.zone in ("Global", "Desarrollados"):
        cons.append(Reason(texts.ETF_GLOBAL_FX_RISK))
    pros, cons = pros[:MAX_REASONS], cons[:MAX_REASONS]

    if label == "buy":
        summary = texts.ETF_ROLE_PROS[role]
    elif label == "avoid":
        summary = f"Riesgo {RISK_ES[r]}: demasiado para tu perfil {profile.label}."
    elif r > profile.max_risk:
        summary = "Oscila más de lo que toleras con tu perfil."
    elif role in ("bonds", "cash"):
        summary = "Útil para amortiguar caídas, aunque tu perfil busca más rentabilidad."
    else:
        summary = "Útil como complemento, pero no es la base de una cartera."

    return Recommendation(
        ticker=row["ticker"],
        name=info.short_name,
        kind="etf",
        label=label,
        score=score,
        risk_level=risk,
        price=_num(row.get("price")),
        currency=row.get("price_currency") or row.get("currency"),
        summary=summary,
        fit=fit_text(risk, profile),
        pros=pros,
        cons=cons,
        checks=checks,
        components=comps,
        entry=None,
        entry_note="En un ETF indexado el momento de entrada importa menos: encaja invertir "
        "una cantidad fija cada mes (aportaciones periódicas).",
        risk_detail=risk_detail(vol, mdd),
        etf_role=role,
        etf_index=info.index,
        as_of=_as_of(row),
    )


# --- Todo el universo -----------------------------------------------------------------


def split_universe(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(acciones, ETFs de referencia)."""
    stocks = df[df["quote_type"] == "EQUITY"]
    etfs = df[df["ticker"].isin(list(ETF_INFO))]
    return stocks, etfs


def recommend(row: dict, df: pd.DataFrame, profile: InvestorProfile) -> Recommendation:
    """Recomendación de un valor (que puede no estar en el universo)."""
    stocks, etfs = split_universe(df)
    if row.get("ticker") in ETF_INFO:
        return recommend_etf(row, etfs, profile)
    return recommend_stock(row, stocks, profile)


def recommend_all(df: pd.DataFrame, profile: InvestorProfile) -> list[Recommendation]:
    """Todas las recomendaciones, ordenadas: Comprar primero y, dentro, por puntuación."""
    stocks, etfs = split_universe(df)
    recs = [recommend_stock(r, stocks, profile) for r in stocks.to_dict("records")]
    recs += [recommend_etf(r, etfs, profile) for r in etfs.to_dict("records")]
    return sorted(recs, key=lambda x: (LABEL_ORDER[x.label], -(x.score or 0)))
