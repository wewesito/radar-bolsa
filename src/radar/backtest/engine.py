"""Backtest de la puntuación de precio (funciones puras, sin E/S).

Qué se prueba y qué no (se muestra tal cual en la app):
- SÍ: la parte de PRECIO de la puntuación (momentum y riesgo), recalculada en cada fecha solo
  con los precios conocidos hasta ese día: rentabilidad de 52 y 26 semanas, distancia a la
  media de 40 semanas (≈ 200 sesiones), volatilidad y peor caída de 52 semanas. Percentiles
  frente al resto de valores; puntuación = media de momentum y riesgo.
- NO: valoración, salud, crecimiento y dividendo. Las fuentes gratuitas solo dan la foto
  ACTUAL de los fundamentales; usarla en el pasado sería mirar al futuro.
- Cartera: las `top_n` mejores, a partes iguales, revisadas cada `rebalance_weeks` semanas,
  con un coste de `cost` por euro comprado o vendido. Todo en euros y con dividendos.
- Datos sospechosos: Yahoo trae a veces precios corruptos (saltos de miles de %). Se excluyen
  los valores con alguna semana por debajo de -60 % o por encima de +100 % (`drop_suspect`).
- Sesgo de supervivencia: el universo son las empresas que cotizan HOY (las que quebraron o
  dejaron de cotizar no están). Por eso se compara también con el universo entero a partes
  iguales: tiene el mismo sesgo, y la diferencia con él mide lo que aporta la selección.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

WEEKS_PER_YEAR = 52
MIN_WEEKLY_MOVE = -0.60  # caída semanal máxima creíble
MAX_WEEKLY_MOVE = 1.00  # subida semanal máxima creíble


@dataclass(frozen=True)
class BacktestConfig:
    top_n: int = 20
    rebalance_weeks: int = 13  # trimestral
    cost: float = 0.001  # 0,1 % por euro negociado (comisión + horquilla, aproximado)
    lookback_weeks: int = 52
    momentum_weight: float = 0.5  # el resto, riesgo


@dataclass(frozen=True)
class Metrics:
    total_return: float
    cagr: float
    volatility: float
    max_drawdown: float
    return_per_risk: float | None  # CAGR / volatilidad


@dataclass
class BacktestResult:
    dates: list[pd.Timestamp]
    series: dict[str, list[float]]  # nombre → valor (base 100)
    metrics: dict[str, Metrics]
    yearly: dict[int, dict[str, float]]  # año → nombre → rentabilidad
    selections: list[tuple[pd.Timestamp, list[tuple[str, float]]]]  # fecha → [(ticker, puntos)]
    config: BacktestConfig
    universe_size: int
    notes: list[str] = field(default_factory=list)


def price_scores(window: pd.DataFrame, momentum_weight: float = 0.5) -> pd.Series:
    """Puntuación de precio (0–100) en la última fecha de `window` (semanal, sin huecos).

    Solo usa las filas de `window`: es imposible que mire al futuro.
    """
    last = window.iloc[-1]
    rets = window.pct_change().iloc[1:]
    feats = pd.DataFrame(
        {
            "ret_52": last / window.iloc[0] - 1,
            "ret_26": last / window.iloc[-27] - 1,
            "dist_40": last / window.iloc[-40:].mean() - 1,
            "vol": rets.std(ddof=1) * np.sqrt(WEEKS_PER_YEAR),
            "mdd": (window / window.cummax() - 1).min(),
        }
    )
    pct = feats.rank(pct=True)
    momentum = pct[["ret_52", "ret_26", "dist_40"]].mean(axis=1)
    risk = ((1 - pct["vol"]) + pct["mdd"]) / 2  # menos volatilidad y caídas más suaves = mejor
    return 100 * (momentum_weight * momentum + (1 - momentum_weight) * risk)


def drop_suspect(prices: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Quita los valores con saltos semanales imposibles (datos corruptos). (precios, quitados)."""
    moves = prices.pct_change()
    bad = ((moves < MIN_WEEKLY_MOVE) | (moves > MAX_WEEKLY_MOVE)).any()
    dropped = sorted(bad[bad].index)
    return prices.drop(columns=dropped), dropped


def _eligible(window: pd.DataFrame) -> list[str]:
    """Valores con todo el año de precios en la ventana (sin huecos)."""
    return [c for c in window.columns if window[c].notna().all() and (window[c] > 0).all()]


def simulate(
    prices: pd.DataFrame, cfg: BacktestConfig, select_all: bool = False
) -> tuple[pd.Series, list[tuple[pd.Timestamp, list[tuple[str, float]]]]]:
    """Valor de la cartera (base 100) y las selecciones en cada revisión.

    Con `select_all` compra todo el universo elegible a partes iguales (referencia).
    """
    i0 = cfg.lookback_weeks
    if len(prices) <= i0 + 1:
        raise ValueError("Histórico insuficiente para el backtest")
    rebalance = set(range(i0, len(prices) - 1, cfg.rebalance_weeks))
    values: dict[str, float] = {}
    total = 100.0
    equity: list[float] = []
    selections = []
    for i in range(i0, len(prices)):
        if i > i0 and values:
            growth = prices.iloc[i] / prices.iloc[i - 1]
            for t in values:
                g = growth[t]
                values[t] *= 1.0 if pd.isna(g) else float(g)  # sin precio: se queda igual
            total = sum(values.values())
        equity.append(total)
        if i in rebalance:
            window = prices.iloc[i - cfg.lookback_weeks : i + 1]
            names = _eligible(window)
            if not names:
                continue
            if select_all:
                picks = [(t, float("nan")) for t in names]
            else:
                scores = price_scores(window[names], cfg.momentum_weight)
                top = scores.sort_values(ascending=False).head(cfg.top_n)
                picks = [(t, float(s)) for t, s in top.items()]
            selections.append((prices.index[i], picks))
            target = {t: total / len(picks) for t, _ in picks}
            turnover = sum(
                abs(target.get(t, 0) - values.get(t, 0)) for t in set(target) | set(values)
            )
            after = total - turnover * cfg.cost
            values = {t: v * after / total for t, v in target.items()}
            total = after
    return pd.Series(equity, index=prices.index[i0:]), selections


def metrics(series: pd.Series) -> Metrics:
    s = series.dropna()
    years = (s.index[-1] - s.index[0]).days / 365.25
    total = float(s.iloc[-1] / s.iloc[0] - 1)
    cagr = float((1 + total) ** (1 / years) - 1) if years > 0 else 0.0
    vol = float(s.pct_change().std(ddof=1) * np.sqrt(WEEKS_PER_YEAR))
    mdd = float((s / s.cummax() - 1).min())
    return Metrics(total, cagr, vol, mdd, cagr / vol if vol else None)


def yearly_returns(series: pd.Series) -> dict[int, float]:
    """Rentabilidad de cada año natural (el primero y el último pueden ser parciales)."""
    s = series.dropna()
    out = {}
    prev = s.iloc[0]
    for year, chunk in s.groupby(s.index.year):
        out[int(year)] = float(chunk.iloc[-1] / prev - 1)
        prev = chunk.iloc[-1]
    return out


MODEL = "Modelo (puntuación de precio)"
UNIVERSE = "Universo a partes iguales"


def run_backtest(
    prices: pd.DataFrame, benchmarks: dict[str, pd.Series], cfg: BacktestConfig | None = None
) -> BacktestResult:
    """Simula el modelo y el universo, y alinea los índices de referencia (base 100)."""
    cfg = cfg or BacktestConfig()
    model, selections = simulate(prices, cfg)
    universe, _ = simulate(prices, cfg, select_all=True)
    series = {MODEL: model, UNIVERSE: universe}
    for name, s in benchmarks.items():
        aligned = s.reindex(model.index, method="ffill")
        aligned = aligned / aligned.dropna().iloc[0] * 100
        series[name] = aligned
    years: dict[int, dict[str, float]] = {}
    for name, s in series.items():
        for y, r in yearly_returns(s).items():
            years.setdefault(y, {})[name] = r
    return BacktestResult(
        dates=list(model.index),
        series={k: [None if pd.isna(v) else float(v) for v in s] for k, s in series.items()},
        metrics={k: metrics(s) for k, s in series.items()},
        yearly=years,
        selections=selections,
        config=cfg,
        universe_size=prices.shape[1],
    )
