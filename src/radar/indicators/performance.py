"""Rentabilidad a varios plazos, historial de dividendos y ROIC (funciones puras).

Dos series de precio distintas:
- `price_close`: el precio tal como cotizó → rentabilidad BURSÁTIL (sin dividendos).
- `total_close`: el precio ajustado por dividendos → rentabilidad TOTAL (dividendos
  reinvertidos el día en que se cobran).
"""

import pandas as pd

from radar.indicators.risk import return_over

# Si la fecha de inicio de un plazo cae antes del primer dato con más margen que este,
# no se calcula la rentabilidad (sería de un plazo más corto del que dice).
MAX_START_GAP_DAYS = 10

DEFAULT_TAX_RATE = 0.25  # si el tipo efectivo no se puede calcular o es absurdo
MAX_TAX_RATE = 0.5


def _return_over_checked(close: pd.Series, months: int) -> float | None:
    if close.empty:
        return None
    start = close.index[-1] - pd.DateOffset(months=months)
    if close.index[0] > start + pd.Timedelta(days=MAX_START_GAP_DAYS):
        return None  # no hay histórico suficiente
    return return_over(close, months)


def ytd_return(close: pd.Series) -> float | None:
    """Rentabilidad desde el último cierre del año anterior."""
    if close.empty:
        return None
    year = close.index[-1].year
    prev = close[close.index.year < year]
    if prev.empty:
        return None
    return float(close.iloc[-1] / prev.iloc[-1] - 1)


def period_returns(price_close: pd.Series, total_close: pd.Series) -> dict[str, float | None]:
    """Rentabilidades bursátiles (en el año, 1, 3 y 5 años) y totales (1 y 5 años)."""
    return {
        "ret_ytd": ytd_return(price_close),
        "ret_1y": _return_over_checked(price_close, 12),
        "ret_3y": _return_over_checked(price_close, 36),
        "ret_5y": _return_over_checked(price_close, 60),
        "tr_1y": _return_over_checked(total_close, 12),
        "tr_5y": _return_over_checked(total_close, 60),
    }


def dividend_years(dividends: pd.Series, as_of: pd.Timestamp) -> int:
    """Años naturales seguidos con algún dividendo, contando hacia atrás desde el último
    año completo (el año en curso no cuenta: puede que aún no haya pagado)."""
    paid_years = set(dividends[dividends > 0].index.year)
    year = as_of.year - 1
    count = 0
    while year in paid_years:
        count += 1
        year -= 1
    return count


def dividend_sustainability(payout: float | None, dividend_yield: float | None, years: int) -> str:
    """Lectura sencilla de si el dividendo parece sostenible.

    - Sin dividendo: "Sin dividendo".
    - Alta: payout ≤ 70 % y al menos 5 años seguidos pagando.
    - Baja: payout > 100 % (paga más de lo que gana) o sin beneficio.
    - Media: el resto (o sin dato de payout).
    """
    if not dividend_yield:
        return "Sin dividendo"
    if payout is None:
        return "Media"
    if payout <= 0 or payout > 1.0:
        return "Baja"
    if payout <= 0.7 and years >= 5:
        return "Alta"
    return "Media"


def roic(items: dict[str, float | None]) -> float | None:
    """ROIC = EBIT × (1 − tipo efectivo) / (deuda + patrimonio − caja).

    El tipo efectivo es impuesto / beneficio antes de impuestos, acotado a [0, 50 %];
    si no se puede calcular se usa el 25 %. Sin capital invertido positivo no hay ROIC.
    """
    ebit, equity = items.get("ebit"), items.get("equity")
    if ebit is None or equity is None:
        return None
    pretax, tax = items.get("pretax_income"), items.get("tax_provision")
    rate = DEFAULT_TAX_RATE
    if pretax and tax is not None and pretax > 0:
        rate = min(max(tax / pretax, 0.0), MAX_TAX_RATE)
    invested = equity + (items.get("total_debt") or 0.0) - (items.get("cash") or 0.0)
    if invested <= 0:
        return None
    return ebit * (1 - rate) / invested
