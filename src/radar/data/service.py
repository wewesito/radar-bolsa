"""Servicio de datos de mercado: proveedor + caché. Es la única puerta que usa la UI.

Política por petición:
1. Si hay dato fresco en caché (dentro de su TTL) → se devuelve sin llamar a la API.
2. Si no, se pide al proveedor y se guarda.
3. Si el proveedor falla por red/límite y hay una copia antigua → se devuelve marcada `stale`.
   Un TickerNotFoundError no usa la copia antigua: el error es del ticker, no de la fuente.
"""

import dataclasses
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, TypeVar

from radar import config
from radar.data.base import DataProvider
from radar.data.cache import Cache, df_from_json, df_to_json
from radar.data.markets import ALL_RANGES
from radar.errors import ProviderUnavailableError, RadarError
from radar.models import Financials, Fundamentals, PriceHistory, Quote, SearchResult

T = TypeVar("T")

# Se antepone a todas las claves. Súbelo cuando cambie la estructura de los modelos o el
# parseo: las entradas antiguas dejan de leerse en vez de servir datos con formato viejo.
CACHE_VERSION = "v4"  # v4: histórico con PriceClose y Dividends; payout

# Pocas peticiones en paralelo: más rápido que en serie sin parecer un ataque a Yahoo.
MAX_WORKERS = 4


def _encode(obj: Any) -> dict[str, Any]:
    out = {}
    for f in dataclasses.fields(obj):
        v = getattr(obj, f.name)
        if isinstance(v, datetime):
            v = v.isoformat()
        elif f.name == "data":  # DataFrame de PriceHistory
            v = df_to_json(v)
        out[f.name] = v
    return out


def _decode(cls: type[T], d: dict[str, Any]) -> T:
    d = dict(d)
    for key in ("as_of", "last_report", "period_end"):
        if d.get(key):
            d[key] = datetime.fromisoformat(d[key])
    if "data" in d:
        d["data"] = df_from_json(d["data"])
    return cls(**d)


class MarketDataService:
    def __init__(self, provider: DataProvider, cache: Cache):
        self.provider = provider
        self.cache = cache

    def _cached(self, key: str, ttl: float, cls: type[T], fetch: Callable[[], T]) -> T:
        key = f"{CACHE_VERSION}:{key}"
        if entry := self.cache.get(key, ttl):
            return _decode(cls, entry.value)
        try:
            fresh = fetch()
        except ProviderUnavailableError:
            if old := self.cache.get_any(key):
                return dataclasses.replace(_decode(cls, old.value), stale=True)
            raise
        self.cache.set(key, _encode(fresh))
        return fresh

    def get_quote(self, ticker: str) -> Quote:
        return self._cached(
            f"quote:{ticker}", config.TTL_QUOTE, Quote, lambda: self.provider.get_quote(ticker)
        )

    def get_quotes(self, tickers: list[str]) -> dict[str, Quote | RadarError]:
        """Cotizaciones de varios tickers. Un fallo en uno no tumba al resto."""

        def one(t: str) -> Quote | RadarError:
            try:
                return self.get_quote(t)
            except RadarError as e:
                return e

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            return dict(zip(tickers, pool.map(one, tickers), strict=True))

    def get_history(self, ticker: str, range_key: str) -> PriceHistory:
        ttl = (
            config.TTL_HISTORY_INTRADAY
            if ALL_RANGES[range_key].intraday
            else config.TTL_HISTORY_DAILY
        )
        return self._cached(
            f"history:{ticker}:{range_key}",
            ttl,
            PriceHistory,
            lambda: self.provider.get_history(ticker, range_key),
        )

    def get_fundamentals(self, ticker: str) -> Fundamentals:
        return self._cached(
            f"fundamentals:{ticker}",
            config.TTL_FUNDAMENTALS,
            Fundamentals,
            lambda: self.provider.get_fundamentals(ticker),
        )

    def get_financials(self, ticker: str) -> Financials:
        return self._cached(
            f"financials:{ticker}",
            config.TTL_FUNDAMENTALS,
            Financials,
            lambda: self.provider.get_financials(ticker),
        )

    def search(self, query: str) -> list[SearchResult]:
        """Búsqueda en la fuente (caché de un día). Sin copia antigua: si falla, lista vacía."""
        key = f"{CACHE_VERSION}:search:{query.strip().lower()}"
        if entry := self.cache.get(key, config.TTL_FUNDAMENTALS):
            return [SearchResult(**r) for r in entry.value]
        try:
            results = self.provider.search(query)
        except ProviderUnavailableError:
            return []
        self.cache.set(key, [dataclasses.asdict(r) for r in results])
        return results


def default_service() -> MarketDataService:
    from radar.data.yahoo import YahooProvider

    return MarketDataService(YahooProvider(), Cache(config.CACHE_PATH))
