"""Modelos de datos. Todo dato lleva su fuente (`source`) y su fecha (`as_of`, en UTC)."""

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd


@dataclass(frozen=True)
class Quote:
    """Cotización puntual de un valor."""

    ticker: str
    name: str
    price: float
    previous_close: float | None
    volume: int | None
    currency: str | None
    exchange: str | None
    quote_type: str | None  # EQUITY, ETF, INDEX...
    market_state: str | None  # REGULAR, CLOSED, PRE, POST...
    delay_minutes: int | None
    as_of: datetime  # hora de la última cotización según la fuente
    source: str
    stale: bool = False  # True si viene de caché caducada porque la fuente falló

    @property
    def change(self) -> float | None:
        if self.previous_close is None:
            return None
        return self.price - self.previous_close

    @property
    def change_pct(self) -> float | None:
        if not self.previous_close:
            return None
        return self.price / self.previous_close - 1

    @property
    def is_market_open(self) -> bool:
        return self.market_state == "REGULAR"


@dataclass(frozen=True)
class PriceHistory:
    """Serie OHLCV. `data` tiene índice datetime y columnas Open, High, Low, Close, Volume."""

    ticker: str
    range_key: str
    interval: str
    data: pd.DataFrame
    as_of: datetime  # cuándo se descargó
    source: str
    stale: bool = False


@dataclass(frozen=True)
class Fundamentals:
    """Métricas fundamentales. Ratios como fracción (0.12 = 12 %). None = no disponible."""

    ticker: str
    name: str
    quote_type: str | None
    sector: str | None
    industry: str | None
    country: str | None
    currency: str | None
    metrics: dict[str, float | None] = field(default_factory=dict)
    fund_family: str | None = None  # gestora, solo ETFs
    price_currency: str | None = None  # moneda en la que cotiza (puede diferir de la contable)
    last_report: datetime | None = None  # último trimestre reportado
    as_of: datetime | None = None  # cuándo se descargó
    source: str = ""
    stale: bool = False


@dataclass(frozen=True)
class Financials:
    """Partidas del último ejercicio anual (en la moneda de las cuentas). None = sin dato."""

    ticker: str
    items: dict[str, float | None]
    period_end: datetime | None  # cierre del ejercicio
    as_of: datetime  # cuándo se descargó
    source: str
    stale: bool = False


@dataclass(frozen=True)
class SearchResult:
    """Un resultado del buscador de valores."""

    ticker: str
    name: str
    quote_type: str | None
    exchange: str | None
