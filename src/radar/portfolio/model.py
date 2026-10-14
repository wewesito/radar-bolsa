"""Cartera de ejemplo según el perfil (función pura, sin E/S).

Reglas (se muestran en la app):
1. El reparto de partida (ETFs / acciones / renta fija y liquidez) viene del perfil.
2. ETFs: un único indexado global como base (el primero de CORE_PREFERENCE que no esté en
   «Evitar»). Si el objetivo son los dividendos, un 30 % de la parte de ETFs va al mejor
   ETF de dividendos.
3. Parte segura: si es del 20 % o más, 70 % renta fija global (cubierta a euros) y 30 %
   liquidez (monetario); si es menor, toda en renta fija.
4. Acciones: tantas como indique el perfil, SOLO entre las que tienen señal «Comprar»,
   de mayor a menor puntuación, a partes iguales, con como mucho 2 por sector y al menos la
   mitad europeas (incluida España). Si no hay suficientes, el peso que falta va al ETF base.
"""

import math
from collections import defaultdict
from dataclasses import asdict, dataclass, field

from radar.etfs import BY_TICKER as ETF_INFO
from radar.fundamentals.sector import sector_es
from radar.profile.investor import InvestorProfile
from radar.recommend.engine import LABEL_ES, Recommendation

CORE_PREFERENCE = ["VWCE.DE", "IUSQ.DE", "EUNL.DE", "XDWD.DE", "SXR8.DE"]
BONDS_ETF = "EUNA.DE"
CASH_ETF = "XEON.DE"
DIVIDEND_SHARE_OF_ETF = 0.3
SAFE_SPLIT_THRESHOLD = 20  # % del total a partir del cual se separa liquidez
BONDS_SHARE_OF_SAFE = 0.7
MAX_PER_SECTOR = 2
MIN_EUROPE_SHARE = 0.5

BUCKET_ETF = "ETF indexado"
BUCKET_STOCK = "Acciones"
BUCKET_BONDS = "Renta fija"
BUCKET_CASH = "Liquidez"


@dataclass
class ModelPosition:
    ticker: str
    name: str
    bucket: str
    weight: float  # fracción del total
    amount_eur: float
    reason: str
    label: str | None = None
    score: float | None = None
    risk_level: int | None = None
    sector: str | None = None
    region: str | None = None


@dataclass
class ModelPortfolio:
    profile_label: str
    amount_eur: float
    positions: list[ModelPosition]
    by_bucket: dict[str, float]
    by_sector: dict[str, float]
    by_region: dict[str, float]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def region_of(rec: Recommendation) -> str:
    if rec.spain_index or rec.country == "Spain":
        return "España"
    if rec.country == "United States":
        return "EE. UU."
    return "Europa"


def _pick_etf(recs: dict[str, Recommendation], candidates: list[str]) -> str:
    for t in candidates:
        r = recs.get(t)
        if r is not None and r.label != "avoid":
            return t
    return candidates[0]


def pick_stocks(stocks: list[Recommendation], n: int) -> list[Recommendation]:
    """Selección de acciones con las restricciones de sector y región (regla 4)."""
    max_non_europe = n - math.ceil(n * MIN_EUROPE_SHARE)
    chosen: list[Recommendation] = []
    per_sector: dict[str, int] = defaultdict(int)
    non_europe = 0
    for r in sorted(stocks, key=lambda x: -(x.score or 0)):
        if len(chosen) == n:
            break
        if r.label != "buy":
            continue
        sector = r.sector or "Sin sector"
        if per_sector[sector] >= MAX_PER_SECTOR:
            continue
        europe = region_of(r) != "EE. UU."
        if not europe and non_europe >= max_non_europe:
            continue
        chosen.append(r)
        per_sector[sector] += 1
        non_europe += 0 if europe else 1
    return chosen


def build_model_portfolio(recs: list[Recommendation], profile: InvestorProfile) -> ModelPortfolio:
    by_ticker = {r.ticker: r for r in recs}
    alloc = profile.allocation
    amount = profile.amount_eur
    notes: list[str] = []
    weights: dict[str, tuple[float, str, str]] = {}  # ticker → (peso, cesta, motivo)

    def add(ticker: str, weight: float, bucket: str, reason: str) -> None:
        if weight <= 0:
            return
        old = weights.get(ticker, (0.0, bucket, reason))
        weights[ticker] = (old[0] + weight, bucket, old[2])

    # 4. Acciones (primero, para saber cuánto peso sobra para el ETF base)
    stock_share = alloc.stocks / 100
    stocks = [r for r in recs if r.kind == "stock"]
    chosen = pick_stocks(stocks, profile.positions) if stock_share and profile.positions else []
    if profile.positions and len(chosen) < profile.positions:
        notes.append(
            f"Hoy solo {len(chosen)} acciones cumplen todas las condiciones con las reglas de "
            f"diversificación (de {profile.positions} buscadas): el peso restante va al ETF base."
        )
    per_stock = stock_share / profile.positions if profile.positions else 0
    for r in chosen:
        add(r.ticker, per_stock, BUCKET_STOCK, r.summary)
    leftover = stock_share - per_stock * len(chosen)

    # 2. ETFs
    etf_share = alloc.etf / 100 + leftover
    core = _pick_etf(by_ticker, CORE_PREFERENCE)
    if profile.answers.objective == "dividends":
        dividend_etfs = sorted(
            (r for r in recs if r.etf_role == "dividend" and r.label != "avoid"),
            key=lambda r: -(r.score or 0),
        )
        if dividend_etfs:
            div = dividend_etfs[0].ticker
            add(
                div,
                etf_share * DIVIDEND_SHARE_OF_ETF,
                BUCKET_ETF,
                "Empresas de todo el mundo con dividendos altos, acorde con tu objetivo.",
            )
            etf_share *= 1 - DIVIDEND_SHARE_OF_ETF
    add(
        core,
        etf_share,
        BUCKET_ETF,
        "Base de la cartera: miles de empresas de todo el mundo con una comisión baja.",
    )

    # 3. Parte segura
    safe = alloc.safe / 100
    if alloc.safe >= SAFE_SPLIT_THRESHOLD:
        add(
            BONDS_ETF,
            safe * BONDS_SHARE_OF_SAFE,
            BUCKET_BONDS,
            "Renta fija global cubierta a euros: amortigua las caídas de la bolsa.",
        )
        add(
            CASH_ETF,
            safe * (1 - BONDS_SHARE_OF_SAFE),
            BUCKET_CASH,
            "Liquidez remunerada para imprevistos o para aprovechar caídas.",
        )
    else:
        add(
            BONDS_ETF,
            safe,
            BUCKET_BONDS,
            "Renta fija global cubierta a euros: amortigua las caídas de la bolsa.",
        )

    positions: list[ModelPosition] = []
    by_bucket: dict[str, float] = defaultdict(float)
    by_sector: dict[str, float] = defaultdict(float)
    by_region: dict[str, float] = defaultdict(float)
    for ticker, (w, bucket, reason) in weights.items():
        rec = by_ticker.get(ticker)
        etf = ETF_INFO.get(ticker)
        if etf:
            name = etf.short_name
            sector = {BUCKET_BONDS: "Renta fija", BUCKET_CASH: "Liquidez"}.get(
                bucket, "Diversificado (ETF)"
            )
            for region, pct in etf.regions.items():
                by_region[region] += w * pct / 100
            region = etf.zone
        else:
            name = rec.name if rec else ticker
            sector = sector_es(rec.sector) if rec and rec.sector else "Sin sector"
            region = region_of(rec) if rec else "Otros"
            by_region["España" if region == "España" else region] += w
        by_bucket[bucket] += w
        by_sector[sector] += w
        positions.append(
            ModelPosition(
                ticker=ticker,
                name=name,
                bucket=bucket,
                weight=w,
                amount_eur=amount * w,
                reason=reason,
                label=LABEL_ES[rec.label] if rec else None,
                score=rec.score if rec else None,
                risk_level=rec.risk_level if rec else None,
                sector=sector,
                region=region,
            )
        )
    positions.sort(key=lambda p: -p.weight)
    notes.append(
        "El reparto por país de los ETFs es aproximado (composición de su índice redondeada); "
        "consulta la ficha de cada ETF para el dato exacto."
    )
    srt = lambda d: dict(sorted(d.items(), key=lambda kv: -kv[1]))  # noqa: E731
    return ModelPortfolio(
        profile_label=profile.label,
        amount_eur=amount,
        positions=positions,
        by_bucket=srt(by_bucket),
        by_sector=srt(by_sector),
        by_region=srt(by_region),
        notes=notes + profile.notes,
    )
