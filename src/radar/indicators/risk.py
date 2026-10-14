"""Métricas de rentabilidad y riesgo sobre series de precios (funciones puras)."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from radar.indicators.technical import sma

TRADING_DAYS = 252  # sesiones bursátiles aproximadas en un año


def returns(close: pd.Series) -> pd.Series:
    return close.pct_change().dropna()


def annualized_volatility(close: pd.Series, periods_per_year: int = TRADING_DAYS) -> float | None:
    """Desviación típica de los rendimientos, escalada a un año con √periodos.

    La raíz cuadrada viene de que la varianza de rendimientos independientes se suma:
    la de un año es ~252 veces la diaria, así que la desviación típica es ~√252 veces.
    """
    r = returns(close)
    if len(r) < 20:
        return None
    return float(r.std(ddof=1) * np.sqrt(periods_per_year))


def drawdown(close: pd.Series) -> pd.Series:
    """Caída desde el máximo previo en cada momento (0 = en máximos, −0,3 = 30 % por debajo)."""
    return close / close.cummax() - 1


@dataclass(frozen=True)
class MaxDrawdown:
    value: float  # negativo: −0,35 = caída del 35 %
    peak: pd.Timestamp
    trough: pd.Timestamp


def max_drawdown(close: pd.Series) -> MaxDrawdown | None:
    """La peor caída de máximo a mínimo del periodo."""
    if len(close) < 2:
        return None
    dd = drawdown(close)
    trough = dd.idxmin()
    peak = close.loc[:trough].idxmax()
    return MaxDrawdown(float(dd.min()), peak, trough)


def beta(asset: pd.Series, benchmark: pd.Series) -> float | None:
    """Beta = cov(rend. activo, rend. índice) / var(rend. índice), con fechas alineadas."""
    df = pd.concat([asset, benchmark], axis=1, join="inner").pct_change().dropna()
    if len(df) < 20:
        return None
    cov = np.cov(df.iloc[:, 0], df.iloc[:, 1], ddof=1)
    return float(cov[0, 1] / cov[1, 1]) if cov[1, 1] else None


def return_over(close: pd.Series, months: int) -> float | None:
    """Rentabilidad de los últimos `months` meses (precio al cierre más cercano anterior)."""
    end = close.index[-1]
    start_date = end - pd.DateOffset(months=months)
    past = close.loc[:start_date]
    if past.empty:
        return None
    return float(close.iloc[-1] / past.iloc[-1] - 1)


def price_stats(close: pd.Series) -> dict[str, float | None]:
    """Resumen de momentum y riesgo del último año a partir de cierres diarios."""
    last_year = close.loc[close.index[-1] - pd.DateOffset(years=1) :]
    mdd = max_drawdown(last_year)
    sma200 = sma(close, 200).iloc[-1]
    return {
        "ret_6m": return_over(close, 6),
        "ret_12m": return_over(close, 12),
        "vol_1y": annualized_volatility(last_year),
        "mdd_1y": mdd.value if mdd else None,
        "dist_sma200": float(close.iloc[-1] / sma200 - 1) if pd.notna(sma200) else None,
    }
