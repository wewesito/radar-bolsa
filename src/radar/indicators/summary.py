"""Lecturas de los indicadores técnicos en lenguaje neutro.

Describen lo que dicen los indicadores según su interpretación clásica y su límite.
Nunca recomiendan comprar ni vender.
"""

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from radar.indicators.technical import bollinger, last_ma_cross, macd, rsi, sma

Tone = Literal["alcista", "bajista", "neutral"]


@dataclass(frozen=True)
class Observation:
    indicator: str
    text: str
    tone: Tone


def _pct(x: float) -> str:
    return f"{x * 100:+.1f} %".replace(".", ",")


def technical_observations(close: pd.Series) -> list[Observation]:
    obs: list[Observation] = []
    last = close.iloc[-1]

    for n in (50, 200):
        m = sma(close, n).iloc[-1]
        if pd.notna(m):
            dist = last / m - 1
            horizon = "corto/medio" if n == 50 else "largo"
            obs.append(
                Observation(
                    f"SMA {n}",
                    f"Precio {_pct(dist)} respecto a su media de {n} sesiones. La lectura "
                    f"clásica considera la tendencia de {horizon} plazo "
                    f"{'alcista' if dist > 0 else 'bajista'} mientras el precio esté "
                    f"{'por encima' if dist > 0 else 'por debajo'}.",
                    "alcista" if dist > 0 else "bajista",
                )
            )

    cross = last_ma_cross(close)
    if cross is not None:
        days = (close.index[-1] - cross.date).days
        obs.append(
            Observation(
                "Cruce de medias",
                f"Último {cross.kind} (SMA 50 vs SMA 200) hace {days} días, el "
                f"{cross.date:%d/%m/%Y}. Es una señal lenta: llega cuando buena parte del "
                "movimiento ya ha ocurrido.",
                "alcista" if cross.kind == "cruce dorado" else "bajista",
            )
        )

    r = rsi(close).iloc[-1]
    if pd.notna(r):
        if r >= 70:
            text, tone = (
                "zona que tradicionalmente se interpreta como 'sobrecompra'. En tendencias "
                "fuertes puede mantenerse ahí mucho tiempo sin que el precio caiga.",
                "neutral",
            )
        elif r <= 30:
            text, tone = (
                "zona que tradicionalmente se interpreta como 'sobreventa'. En caídas "
                "fuertes puede mantenerse ahí mucho tiempo sin que el precio rebote.",
                "neutral",
            )
        else:
            text, tone = "zona intermedia (30–70), sin lectura extrema.", "neutral"
        obs.append(Observation("RSI 14", f"RSI {r:.0f}: {text}", tone))

    md = macd(close).iloc[-1]
    if pd.notna(md["signal"]):
        above = md["macd"] > md["signal"]
        obs.append(
            Observation(
                "MACD",
                f"La línea MACD está {'por encima' if above else 'por debajo'} de su señal: "
                f"el impulso reciente es {'positivo' if above else 'negativo'} según la "
                "lectura clásica. Da muchas señales falsas en mercados laterales.",
                "alcista" if above else "bajista",
            )
        )

    bb = bollinger(close).iloc[-1]
    if pd.notna(bb["upper"]):
        width = (bb["upper"] - bb["lower"]) / bb["mid"]
        if last > bb["upper"]:
            pos = "por encima de la banda superior (movimiento inusualmente fuerte al alza)"
        elif last < bb["lower"]:
            pos = "por debajo de la banda inferior (movimiento inusualmente fuerte a la baja)"
        else:
            pos = "dentro de las bandas"
        obs.append(
            Observation(
                "Bollinger",
                f"Precio {pos}. Anchura de las bandas: {_pct(width).lstrip('+')} del precio "
                "(bandas estrechas = volatilidad baja, que a menudo precede a movimientos "
                "amplios, sin indicar la dirección).",
                "neutral",
            )
        )
    return obs
