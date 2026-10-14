"""Screener y comparador: score de todo el universo, filtros y 'mejor por métrica'."""

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from radar.fundamentals.metrics import Better
from radar.scoring.score import COMPONENTS, score_company


def score_universe(universe: pd.DataFrame, weights: dict[str, float] | None = None) -> pd.DataFrame:
    """Añade al universo la columna `score` y una por componente (`score_<clave>`)."""
    rows = []
    for _, r in universe.iterrows():
        res = score_company(r.to_dict(), universe, weights)
        rows.append({"score": res.total, **{f"score_{c.key}": c.score for c in res.components}})
    return pd.concat([universe.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


@dataclass(frozen=True)
class Filter:
    key: str
    op: Literal[">=", "<="]
    value: float


def apply_filters(
    df: pd.DataFrame,
    filters: list[Filter],
    sectors: list[str] | None = None,
    regions: list[str] | None = None,
) -> pd.DataFrame:
    """Filtra el DataFrame. Una fila sin dato en una métrica filtrada queda FUERA:
    no podemos afirmar que cumple un criterio que no sabemos medir."""
    mask = pd.Series(True, index=df.index)
    if sectors:
        mask &= df["sector"].isin(sectors)
    if regions:
        mask &= df["region"].isin(regions)
    for f in filters:
        col = df[f.key]
        mask &= (col >= f.value) if f.op == ">=" else (col <= f.value)
        mask &= col.notna()
    return df[mask]


def best_by_metric(values: dict[str, float | None], better: Better) -> str | None:
    """Ticker con el valor más favorable (None si la métrica es descriptiva o no hay datos)."""
    valid = {t: v for t, v in values.items() if v is not None and not pd.isna(v)}
    if better is None or len(valid) < 2:
        return None
    pick = max if better == "higher" else min
    return pick(valid, key=valid.get)


SCORE_COLUMNS = ["score"] + [f"score_{c.key}" for c in COMPONENTS]
