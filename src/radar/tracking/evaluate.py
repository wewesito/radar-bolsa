"""Evaluación de las señales registradas (funciones puras, sin E/S).

Pregunta que responde: «las valores que el modelo marcó como Comprar, ¿rindieron más que el
resto desde entonces?». Para cada plazo (30, 90, 180 y 365 días) se toma la foto más reciente
con al menos ese tiempo de antigüedad y se compara el precio de entonces con el de hoy.

Límites (se muestran en la app): rentabilidad de precio sin dividendos y en la moneda de cada
valor; pocas fechas y pocos valores dan resultados poco concluyentes; se mide el perfil que
tenías cuando se registró la señal.
"""

from dataclasses import dataclass
from datetime import date

import numpy as np

from radar.db.signals import LoggedSignal

HORIZONS = (30, 90, 180, 365)
LABELS = ("buy", "watch", "avoid")
MIN_SAMPLE = 10  # por debajo, el promedio de un grupo no se considera concluyente


@dataclass(frozen=True)
class GroupResult:
    label: str
    count: int
    mean_return: float | None
    hit_rate: float | None  # fracción que superó al promedio de todos
    reliable: bool


@dataclass(frozen=True)
class HorizonResult:
    days: int
    from_date: date
    universe_mean: float | None
    groups: list[GroupResult]


def evaluate(
    log: list[LoggedSignal], prices_now: dict[str, float], today: date
) -> list[HorizonResult]:
    """Resultados por plazo. Solo aparecen los plazos ya cumplidos por alguna foto."""
    days = sorted({s.logged_on for s in log})
    results = []
    for h in HORIZONS:
        eligible = [d for d in days if (today - d).days >= h]
        if not eligible:
            continue
        start = eligible[-1]
        rows = [s for s in log if s.logged_on == start and prices_now.get(s.ticker, 0) > 0]
        rets = {s.ticker: prices_now[s.ticker] / s.price - 1 for s in rows}
        if not rets:
            continue
        mean_all = float(np.mean(list(rets.values())))
        groups = []
        for label in LABELS:
            vals = [rets[s.ticker] for s in rows if s.label == label]
            groups.append(
                GroupResult(
                    label,
                    len(vals),
                    float(np.mean(vals)) if vals else None,
                    float(np.mean([v > mean_all for v in vals])) if vals else None,
                    len(vals) >= MIN_SAMPLE,
                )
            )
        results.append(HorizonResult(h, start, mean_all, groups))
    return results
