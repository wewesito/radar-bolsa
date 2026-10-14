"""Indicadores técnicos como funciones puras sobre series de pandas.

Convenciones: entrada = Series de cierres (o DataFrame OHLC) con índice temporal ordenado;
salida = Series/DataFrame alineados con la entrada (NaN mientras no hay datos suficientes).
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd


def sma(close: pd.Series, n: int) -> pd.Series:
    """Media móvil simple de `n` periodos."""
    return close.rolling(n, min_periods=n).mean()


def ema(close: pd.Series, n: int) -> pd.Series:
    """Media móvil exponencial: da más peso a los datos recientes."""
    return close.ewm(span=n, adjust=False, min_periods=n).mean()


def _wilder_smooth(x: np.ndarray, n: int) -> np.ndarray:
    """Media de Wilder: arranca con la media simple de los n primeros valores y luego
    avg_t = (avg_{t-1}·(n−1) + x_t) / n. Es una EMA con alpha = 1/n pero con otra semilla."""
    out = np.full(len(x), np.nan)
    if len(x) < n:
        return out
    out[n - 1] = x[:n].mean()
    for i in range(n, len(x)):
        out[i] = (out[i - 1] * (n - 1) + x[i]) / n
    return out


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    """RSI de Wilder (0–100): fuerza media de las subidas frente a la de las bajadas.

    Ojo: si se suaviza con una EMA que arranca en el primer dato (p. ej. pandas `ewm`) en vez
    de con la media simple inicial, los primeros valores cambian mucho. Por eso distintas webs
    muestran RSI algo distintos para el mismo valor.
    """
    delta = close.diff().to_numpy()[1:]  # la primera diferencia no existe
    avg_gain = _wilder_smooth(np.clip(delta, 0, None), n)
    avg_loss = _wilder_smooth(np.clip(-delta, 0, None), n)
    with np.errstate(divide="ignore", invalid="ignore"):
        values = 100 - 100 / (1 + avg_gain / avg_loss)
    values = np.where(avg_loss == 0, 100.0, values)  # sin bajadas → 100
    values = np.where((avg_gain == 0) & (avg_loss == 0), 50.0, values)  # plano → 50
    values = np.where(np.isnan(avg_gain), np.nan, values)
    return pd.Series(np.concatenate([[np.nan], values]), index=close.index)


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """MACD = EMA rápida − EMA lenta; señal = EMA de la MACD; histograma = diferencia."""
    line = ema(close, fast) - ema(close, slow)
    sig = line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return pd.DataFrame({"macd": line, "signal": sig, "hist": line - sig})


def bollinger(close: pd.Series, n: int = 20, k: float = 2.0) -> pd.DataFrame:
    """Bandas de Bollinger: media de `n` ± `k` desviaciones típicas (poblacionales, ddof=0)."""
    mid = sma(close, n)
    std = close.rolling(n, min_periods=n).std(ddof=0)
    return pd.DataFrame({"mid": mid, "upper": mid + k * std, "lower": mid - k * std})


@dataclass(frozen=True)
class Level:
    price: float
    touches: int
    kind: Literal["soporte", "resistencia"]


def _pivots(series: pd.Series, window: int, mode: Literal["high", "low"]) -> pd.Series:
    """Máximos (o mínimos) locales: el valor extremo en una ventana centrada de 2·window+1."""
    roll = series.rolling(2 * window + 1, center=True)
    extreme = roll.max() if mode == "high" else roll.min()
    return series[series == extreme]


def _cluster(levels: list[float], tolerance: float) -> list[tuple[float, int]]:
    """Agrupa niveles cercanos (a menos de `tolerance` relativo) → (precio medio, toques)."""
    clusters: list[list[float]] = []
    for p in sorted(levels):
        if clusters and abs(p / np.mean(clusters[-1]) - 1) <= tolerance:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    return [(float(np.mean(c)), len(c)) for c in clusters]


def support_resistance(
    ohlc: pd.DataFrame, window: int = 5, tolerance: float = 0.02, max_levels: int = 3
) -> list[Level]:
    """Soportes y resistencias básicos a partir de máximos y mínimos locales.

    1. Busca pivotes: mínimos locales (posibles soportes) y máximos locales (resistencias).
    2. Agrupa los que están a menos de un 2 % entre sí: un nivel "tocado" varias veces pesa más.
    3. Clasifica según el último precio: por debajo = soporte, por encima = resistencia.
    Devuelve los `max_levels` más cercanos al precio de cada tipo.
    """
    last = float(ohlc["Close"].iloc[-1])
    pivots = list(_pivots(ohlc["Low"], window, "low")) + list(_pivots(ohlc["High"], window, "high"))
    levels = _cluster(pivots, tolerance)
    supports = sorted((lv for lv in levels if lv[0] < last), key=lambda lv: last - lv[0])
    resist = sorted((lv for lv in levels if lv[0] > last), key=lambda lv: lv[0] - last)
    return [Level(p, t, "soporte") for p, t in supports[:max_levels]] + [
        Level(p, t, "resistencia") for p, t in resist[:max_levels]
    ]


@dataclass(frozen=True)
class Cross:
    date: pd.Timestamp
    kind: Literal["cruce dorado", "cruce de la muerte"]


def last_ma_cross(close: pd.Series, fast: int = 50, slow: int = 200) -> Cross | None:
    """Último cruce entre la media rápida y la lenta.

    Cruce dorado: la rápida pasa por encima de la lenta; de la muerte: por debajo.
    """
    diff = (sma(close, fast) - sma(close, slow)).dropna()
    sign = np.sign(diff)
    changes = sign[sign != sign.shift()].iloc[1:]  # el primer valor no es un cruce
    changes = changes[changes != 0]
    if changes.empty:
        return None
    when = changes.index[-1]
    return Cross(when, "cruce dorado" if changes.iloc[-1] > 0 else "cruce de la muerte")


def suspicious_jumps(close: pd.Series, threshold: float = 0.4) -> pd.Series:
    """Variaciones entre velas consecutivas mayores que `threshold` (40 %).

    En grandes empresas suelen ser errores de datos (splits mal ajustados), no movimientos
    reales. Devuelve las variaciones sospechosas indexadas por fecha.
    """
    ret = close.pct_change()
    return ret[ret.abs() > threshold]
