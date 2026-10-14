"""Catálogo de métricas fundamentales: etiqueta, formato, grupo y explicación breve.

Es la semilla del glosario (Fase 9): la UI muestra `help` como tooltip.
"""

from dataclasses import dataclass
from typing import Literal

Kind = Literal["ratio", "pct", "money", "per_share"]


@dataclass(frozen=True)
class MetricDef:
    key: str
    label: str
    kind: Kind
    group: str
    help: str


EQUITY_METRICS: list[MetricDef] = [
    MetricDef(
        "market_cap",
        "Capitalización",
        "money",
        "Tamaño",
        "Precio × número de acciones. Lo que 'vale' la empresa en bolsa.",
    ),
    MetricDef(
        "pe_trailing",
        "PER",
        "ratio",
        "Valoración",
        "Precio / beneficio por acción de los últimos 12 meses. Cuántos años de "
        "beneficio actual pagas. Solo tiene sentido comparado con su sector.",
    ),
    MetricDef(
        "pe_forward",
        "PER estimado",
        "ratio",
        "Valoración",
        "Como el PER pero con el beneficio que los analistas esperan para los "
        "próximos 12 meses. Depende de estimaciones que pueden fallar.",
    ),
    MetricDef(
        "peg",
        "PEG",
        "ratio",
        "Valoración",
        "PER / crecimiento esperado del beneficio (%). Cerca de 1 se suele leer "
        "como 'precio acorde al crecimiento'. Muy sensible a la estimación.",
    ),
    MetricDef(
        "price_to_book",
        "Precio / valor contable",
        "ratio",
        "Valoración",
        "Capitalización / patrimonio neto contable. Útil sobre todo en bancos y aseguradoras.",
    ),
    MetricDef(
        "eps_trailing",
        "BPA (EPS)",
        "per_share",
        "Valoración",
        "Beneficio por acción de los últimos 12 meses.",
    ),
    MetricDef(
        "gross_margin",
        "Margen bruto",
        "pct",
        "Rentabilidad",
        "(Ventas − coste de lo vendido) / ventas. No aplica a bancos.",
    ),
    MetricDef(
        "operating_margin",
        "Margen operativo",
        "pct",
        "Rentabilidad",
        "Beneficio de explotación / ventas: lo que gana el negocio antes de intereses e impuestos.",
    ),
    MetricDef(
        "profit_margin",
        "Margen neto",
        "pct",
        "Rentabilidad",
        "Beneficio neto / ventas: lo que queda de cada euro vendido.",
    ),
    MetricDef(
        "roe",
        "ROE",
        "pct",
        "Rentabilidad",
        "Beneficio neto / patrimonio neto. Cuánto rinde el dinero de los "
        "accionistas. Un ROE alto con mucha deuda es menos meritorio.",
    ),
    MetricDef(
        "revenue_growth",
        "Crecimiento ventas",
        "pct",
        "Crecimiento",
        "Variación de las ventas del último trimestre frente al mismo trimestre del año anterior.",
    ),
    MetricDef(
        "earnings_growth",
        "Crecimiento beneficio",
        "pct",
        "Crecimiento",
        "Variación del beneficio del último trimestre frente al mismo trimestre "
        "del año anterior. Muy volátil.",
    ),
    MetricDef(
        "debt_to_equity",
        "Deuda / patrimonio",
        "ratio",
        "Salud financiera",
        "Deuda total / patrimonio neto. Por encima de 2 suele considerarse alto "
        "fuera de sectores regulados. No aplica bien a bancos.",
    ),
    MetricDef(
        "free_cash_flow",
        "Flujo de caja libre",
        "money",
        "Salud financiera",
        "Caja que genera el negocio después de inversiones. Es lo que puede "
        "repartir, recomprar acciones o usar para reducir deuda.",
    ),
    MetricDef(
        "dividend_yield",
        "Rentabilidad por dividendo",
        "pct",
        "Dividendo",
        "Dividendo anual / precio. Un valor muy alto puede indicar que el precio "
        "ha caído por problemas (y el dividendo podría recortarse).",
    ),
    MetricDef(
        "beta",
        "Beta",
        "ratio",
        "Riesgo",
        "Sensibilidad frente al mercado: 1 = se mueve como el índice, >1 amplifica "
        "los movimientos, <1 los suaviza.",
    ),
]

ETF_METRICS: list[MetricDef] = [
    MetricDef(
        "expense_ratio",
        "Comisión (TER)",
        "pct",
        "Costes",
        "Gasto anual que el fondo descuenta de tu inversión. En ETFs indexados "
        "suele estar entre 0,05 % y 0,30 %; pequeñas diferencias se notan a 20 años.",
    ),
    MetricDef(
        "total_assets",
        "Patrimonio",
        "money",
        "Tamaño",
        "Dinero total gestionado. Fondos muy pequeños tienen más riesgo de cierre.",
    ),
    MetricDef(
        "ytd_return", "Rentabilidad en el año", "pct", "Rentabilidad", "Desde el 1 de enero."
    ),
    MetricDef(
        "return_3y",
        "Rentabilidad media 3 años",
        "pct",
        "Rentabilidad",
        "Anualizada. Rentabilidades pasadas no garantizan las futuras.",
    ),
    MetricDef(
        "return_5y",
        "Rentabilidad media 5 años",
        "pct",
        "Rentabilidad",
        "Anualizada. Rentabilidades pasadas no garantizan las futuras.",
    ),
    MetricDef(
        "dividend_yield",
        "Rentabilidad por dividendo",
        "pct",
        "Dividendo",
        "Solo en ETFs de distribución; los de acumulación reinvierten y muestran 0.",
    ),
]


def metrics_for(quote_type: str | None) -> list[MetricDef]:
    return ETF_METRICS if quote_type in ("ETF", "MUTUALFUND") else EQUITY_METRICS
