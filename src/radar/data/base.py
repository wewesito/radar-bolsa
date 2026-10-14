"""Contrato que debe cumplir cualquier proveedor de datos de mercado."""

from typing import Protocol

from radar.models import Financials, Fundamentals, PriceHistory, Quote, SearchResult


class DataProvider(Protocol):
    name: str

    def get_quote(self, ticker: str) -> Quote:
        """Cotización actual. Lanza TickerNotFoundError o ProviderUnavailableError."""
        ...

    def get_history(self, ticker: str, range_key: str) -> PriceHistory:
        """Histórico OHLCV para una clave de `markets.CHART_RANGES`."""
        ...

    def get_fundamentals(self, ticker: str) -> Fundamentals:
        """Métricas fundamentales, normalizadas a fracciones."""
        ...

    def get_financials(self, ticker: str) -> Financials:
        """Partidas del último ejercicio anual (EBIT, impuestos, deuda, patrimonio, caja)."""
        ...

    def search(self, query: str) -> list[SearchResult]:
        """Busca valores por nombre o ticker."""
        ...
