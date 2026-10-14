"""Cálculos de la sección educativa (funciones puras)."""

import math

import pandas as pd


def compound_growth(
    initial: float,
    monthly: float,
    annual_return: float,
    years: int,
    annual_fee: float = 0.0,
) -> pd.DataFrame:
    """Evolución mes a mes de una inversión con aportaciones periódicas.

    Rentabilidad neta = rentabilidad bruta − comisión anual, aplicada mensualmente:
    (1 + r_neta)^(1/12) − 1. Las aportaciones se hacen al final de cada mes.
    Devuelve por año: aportado acumulado y valor de la inversión.
    """
    r = (1 + annual_return - annual_fee) ** (1 / 12) - 1
    value, contributed = float(initial), float(initial)
    rows = [{"year": 0, "contributed": contributed, "value": value}]
    for month in range(1, years * 12 + 1):
        value = value * (1 + r) + monthly
        contributed += monthly
        if month % 12 == 0:
            rows.append({"year": month // 12, "contributed": contributed, "value": value})
    return pd.DataFrame(rows).set_index("year")


def rule_of_72(annual_return: float) -> float | None:
    """Años aproximados para duplicar el dinero: 72 / rentabilidad en %."""
    return 72 / (annual_return * 100) if annual_return > 0 else None


def years_to_double(annual_return: float) -> float | None:
    """Cálculo exacto para comparar con la regla del 72: ln 2 / ln(1 + r)."""
    return math.log(2) / math.log(1 + annual_return) if annual_return > 0 else None


def real_return(nominal: float, inflation: float) -> float:
    """Rentabilidad real (descontada la inflación): (1 + nominal) / (1 + inflación) − 1."""
    return (1 + nominal) / (1 + inflation) - 1


# Tramos de la base del ahorro del IRPF (estatal + autonómico) vigentes desde 2025.
# Información general: compruébalo en la AEAT, la normativa cambia.
SAVINGS_BRACKETS: list[tuple[float, float]] = [
    (6_000, 0.19),
    (50_000, 0.21),
    (200_000, 0.23),
    (300_000, 0.27),
    (math.inf, 0.30),
]


def savings_tax(base: float) -> float:
    """Cuota aproximada sobre la base del ahorro (ganancias + dividendos + intereses netos).

    Es progresivo POR TRAMOS: cada euro tributa al tipo de su tramo, no todo al tipo más alto.
    """
    tax, lower = 0.0, 0.0
    for upper, rate in SAVINGS_BRACKETS:
        if base <= lower:
            break
        tax += (min(base, upper) - lower) * rate
        lower = upper
    return tax
