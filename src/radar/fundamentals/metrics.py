"""Catálogo de métricas fundamentales: etiqueta, formato, grupo, dirección y explicación breve.

`help` es el texto corto del tooltip; la explicación larga vive en `radar.education`.
`better` indica qué dirección se considera favorable al comparar con el sector
("lower" para múltiplos de valoración, "higher" para márgenes...). None = descriptiva.
"""

from dataclasses import dataclass
from typing import Literal

Kind = Literal["ratio", "pct", "money", "per_share"]
Better = Literal["higher", "lower"] | None


@dataclass(frozen=True)
class MetricDef:
    key: str
    label: str
    kind: Kind
    group: str
    better: Better
    help: str


EQUITY_METRICS: list[MetricDef] = [
    MetricDef(
        "market_cap",
        "Capitalización",
        "money",
        "Tamaño",
        None,
        "Precio × número de acciones. Lo que 'vale' la empresa en bolsa.",
    ),
    MetricDef(
        "pe_trailing",
        "PER",
        "ratio",
        "Valoración",
        "lower",
        "Precio / beneficio por acción de los últimos 12 meses. Cuántos años de "
        "beneficio actual pagas. Solo tiene sentido comparado con su sector.",
    ),
    MetricDef(
        "pe_forward",
        "PER estimado",
        "ratio",
        "Valoración",
        "lower",
        "Como el PER pero con el beneficio que los analistas esperan para los "
        "próximos 12 meses. Depende de estimaciones que pueden fallar.",
    ),
    MetricDef(
        "peg",
        "PEG",
        "ratio",
        "Valoración",
        "lower",
        "PER / crecimiento esperado del beneficio (%). Cerca de 1 se suele leer "
        "como 'precio acorde al crecimiento'. Muy sensible a la estimación.",
    ),
    MetricDef(
        "price_to_book",
        "Precio / valor contable",
        "ratio",
        "Valoración",
        "lower",
        "Capitalización / patrimonio neto contable. Útil sobre todo en bancos y aseguradoras.",
    ),
    MetricDef(
        "fcf_yield",
        "Rentabilidad FCF",
        "pct",
        "Valoración",
        "higher",
        "Flujo de caja libre / capitalización. Como un 'PER al revés' pero con caja: "
        "cuánto efectivo genera la empresa por cada euro que cuesta.",
    ),
    MetricDef(
        "eps_trailing",
        "BPA (EPS)",
        "per_share",
        "Valoración",
        None,
        "Beneficio por acción de los últimos 12 meses. No se compara entre empresas: "
        "depende de cuántas acciones haya.",
    ),
    MetricDef(
        "gross_margin",
        "Margen bruto",
        "pct",
        "Rentabilidad",
        "higher",
        "(Ventas − coste de lo vendido) / ventas. No aplica a bancos.",
    ),
    MetricDef(
        "operating_margin",
        "Margen operativo",
        "pct",
        "Rentabilidad",
        "higher",
        "Beneficio de explotación / ventas: lo que gana el negocio antes de intereses e impuestos.",
    ),
    MetricDef(
        "profit_margin",
        "Margen neto",
        "pct",
        "Rentabilidad",
        "higher",
        "Beneficio neto / ventas: lo que queda de cada euro vendido.",
    ),
    MetricDef(
        "roe",
        "ROE",
        "pct",
        "Rentabilidad",
        "higher",
        "Beneficio neto / patrimonio neto. Cuánto rinde el dinero de los accionistas. "
        "Un ROE alto con mucha deuda es menos meritorio.",
    ),
    MetricDef(
        "revenue_growth",
        "Crecimiento ventas",
        "pct",
        "Crecimiento",
        "higher",
        "Variación de las ventas del último trimestre frente al mismo trimestre del año anterior.",
    ),
    MetricDef(
        "earnings_growth",
        "Crecimiento beneficio",
        "pct",
        "Crecimiento",
        "higher",
        "Variación del beneficio del último trimestre frente al mismo trimestre del "
        "año anterior. Muy volátil.",
    ),
    MetricDef(
        "debt_to_equity",
        "Deuda / patrimonio",
        "ratio",
        "Salud financiera",
        "lower",
        "Deuda total / patrimonio neto. Por encima de 2 suele considerarse alto fuera "
        "de sectores regulados. No aplica bien a bancos.",
    ),
    MetricDef(
        "fcf_margin",
        "Margen FCF",
        "pct",
        "Salud financiera",
        "higher",
        "Flujo de caja libre / ventas: qué parte de lo que vende acaba siendo caja disponible.",
    ),
    MetricDef(
        "free_cash_flow",
        "Flujo de caja libre",
        "money",
        "Salud financiera",
        None,
        "Caja que genera el negocio después de inversiones. Es lo que puede repartir, "
        "recomprar acciones o usar para reducir deuda.",
    ),
    MetricDef(
        "dividend_yield",
        "Rentabilidad por dividendo",
        "pct",
        "Dividendo",
        None,
        "Dividendo anual / precio. Un valor muy alto puede indicar que el precio ha "
        "caído por problemas (y el dividendo podría recortarse).",
    ),
    MetricDef(
        "beta",
        "Beta",
        "ratio",
        "Riesgo",
        None,
        "Sensibilidad frente al mercado: 1 = se mueve como el índice, >1 amplifica los "
        "movimientos, <1 los suaviza.",
    ),
]

ETF_METRICS: list[MetricDef] = [
    MetricDef(
        "expense_ratio",
        "Comisión (TER)",
        "pct",
        "Costes",
        "lower",
        "Gasto anual que el fondo descuenta de tu inversión. En ETFs indexados suele "
        "estar entre 0,05 % y 0,30 %; pequeñas diferencias se notan a 20 años.",
    ),
    MetricDef(
        "total_assets",
        "Patrimonio",
        "money",
        "Tamaño",
        None,
        "Dinero total gestionado. Fondos muy pequeños tienen más riesgo de cierre.",
    ),
    MetricDef(
        "ytd_return", "Rentabilidad en el año", "pct", "Rentabilidad", None, "Desde el 1 de enero."
    ),
    MetricDef(
        "return_3y",
        "Rentabilidad media 3 años",
        "pct",
        "Rentabilidad",
        None,
        "Anualizada. Rentabilidades pasadas no garantizan las futuras.",
    ),
    MetricDef(
        "return_5y",
        "Rentabilidad media 5 años",
        "pct",
        "Rentabilidad",
        None,
        "Anualizada. Rentabilidades pasadas no garantizan las futuras.",
    ),
    MetricDef(
        "dividend_yield",
        "Rentabilidad por dividendo",
        "pct",
        "Dividendo",
        None,
        "Solo en ETFs de distribución; los de acumulación reinvierten y muestran 0.",
    ),
]

# Calculadas a partir del histórico de precios (indicators.risk.price_stats)
PRICE_METRICS: list[MetricDef] = [
    MetricDef(
        "ret_12m",
        "Rentabilidad 12 meses",
        "pct",
        "Momentum",
        "higher",
        "Variación del precio en el último año.",
    ),
    MetricDef(
        "ret_6m",
        "Rentabilidad 6 meses",
        "pct",
        "Momentum",
        "higher",
        "Variación del precio en los últimos 6 meses.",
    ),
    MetricDef(
        "dist_sma200",
        "Distancia a la SMA 200",
        "pct",
        "Momentum",
        "higher",
        "Cuánto está el precio por encima (+) o por debajo (−) de su media de 200 sesiones.",
    ),
    MetricDef(
        "vol_1y",
        "Volatilidad anual",
        "pct",
        "Riesgo",
        "lower",
        "Desviación típica de los rendimientos diarios del último año, anualizada. "
        "Mide cuánto 'se mueve' el precio.",
    ),
    MetricDef(
        "mdd_1y",
        "Caída máxima 1 año",
        "pct",
        "Riesgo",
        "higher",
        "Peor caída de máximo a mínimo en el último año (drawdown). Más cerca de 0 = menos caída.",
    ),
]

ALL_METRICS: dict[str, MetricDef] = {m.key: m for m in EQUITY_METRICS + ETF_METRICS + PRICE_METRICS}


def metrics_for(quote_type: str | None) -> list[MetricDef]:
    return ETF_METRICS if quote_type in ("ETF", "MUTUALFUND") else EQUITY_METRICS
