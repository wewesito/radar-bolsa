"""Proveedor basado en yfinance (Yahoo Finance, API no oficial).

Aquí se concentran las rarezas de Yahoo para que el resto de la app no las vea:
- Unidades mezcladas: márgenes en fracción, pero dividendYield y debtToEquity en %.
- Un ticker inexistente no lanza error: devuelve un `info` casi vacío.
- Campos ausentes (p. ej. deuda/patrimonio en bancos) llegan como None o no llegan.
"""

import logging
import math
from datetime import UTC, datetime
from typing import Any

import pandas as pd
import requests
import yfinance as yf
from yfinance.exceptions import YFException, YFRateLimitError

from radar.data.markets import ALL_RANGES, suffix_hint
from radar.errors import ProviderUnavailableError, RateLimitError, TickerNotFoundError
from radar.models import Financials, Fundamentals, PriceHistory, Quote, SearchResult

log = logging.getLogger(__name__)

SOURCE = "Yahoo Finance"

# Campo de Yahoo → (nuestro nombre, divisor para pasar a fracción)
_METRIC_MAP: dict[str, tuple[str, float]] = {
    "marketCap": ("market_cap", 1),
    "trailingPE": ("pe_trailing", 1),
    "forwardPE": ("pe_forward", 1),
    "trailingPegRatio": ("peg", 1),
    "trailingEps": ("eps_trailing", 1),
    "forwardEps": ("eps_forward", 1),
    "grossMargins": ("gross_margin", 1),
    "operatingMargins": ("operating_margin", 1),
    "profitMargins": ("profit_margin", 1),
    "revenueGrowth": ("revenue_growth", 1),
    "earningsGrowth": ("earnings_growth", 1),
    "debtToEquity": ("debt_to_equity", 100),  # Yahoo: 150 significa 1,5x
    "returnOnEquity": ("roe", 1),
    "freeCashflow": ("free_cash_flow", 1),
    "dividendYield": ("dividend_yield", 100),  # Yahoo: 2.09 significa 2,09 %
    "payoutRatio": ("payout_ratio", 1),  # fracción: 0.58 = reparte el 58 % del beneficio
    "beta": ("beta", 1),
    "priceToBook": ("price_to_book", 1),
    "totalRevenue": ("revenue", 1),
    "netIncomeToCommon": ("net_income", 1),
    # Solo ETFs/fondos (Yahoo los cubre mucho peor en Europa que en EE. UU.)
    "netExpenseRatio": ("expense_ratio", 100),  # Yahoo: 0.2 significa 0,20 %
    "totalAssets": ("total_assets", 1),
    "ytdReturn": ("ytd_return", 100),  # Yahoo: 12.7 significa 12,7 %
    "threeYearAverageReturn": ("return_3y", 1),
    "fiveYearAverageReturn": ("return_5y", 1),
}


def _num(value: Any) -> float | None:
    """Convierte a float descartando None, NaN, infinitos y textos ('Infinity')."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _epoch_to_utc(value: Any) -> datetime | None:
    f = _num(value)
    return datetime.fromtimestamp(f, UTC) if f else None


def parse_metrics(info: dict[str, Any]) -> dict[str, float | None]:
    """Extrae y normaliza las métricas de un `info` de Yahoo (función pura, testeable)."""
    metrics: dict[str, float | None] = {}
    for yahoo_key, (key, divisor) in _METRIC_MAP.items():
        v = _num(info.get(yahoo_key))
        metrics[key] = v / divisor if v is not None else None
    # Un margen bruto de 0 exacto suele ser "no aplica" (p. ej. bancos), no un margen real.
    if metrics["gross_margin"] == 0:
        metrics["gross_margin"] = None
    return metrics


def parse_quote(ticker: str, info: dict[str, Any], now: datetime) -> Quote:
    """Construye una Quote desde `info` (función pura, testeable)."""
    price = _num(info.get("regularMarketPrice")) or _num(info.get("currentPrice"))
    if price is None:
        raise TickerNotFoundError(ticker, suffix_hint(ticker))
    prev = _num(info.get("regularMarketPreviousClose")) or _num(info.get("previousClose"))
    volume = _num(info.get("regularMarketVolume"))
    delay = _num(info.get("exchangeDataDelayedBy"))
    return Quote(
        ticker=ticker,
        name=info.get("longName") or info.get("shortName") or ticker,  # short a veces truncado
        price=price,
        previous_close=prev,
        volume=int(volume) if volume is not None else None,
        currency=info.get("currency"),
        exchange=info.get("fullExchangeName") or info.get("exchange"),
        quote_type=info.get("quoteType"),
        market_state=info.get("marketState"),
        delay_minutes=int(delay) if delay is not None else None,
        as_of=_epoch_to_utc(info.get("regularMarketTime")) or now,
        source=SOURCE,
    )


def adjust_prices(raw: pd.DataFrame) -> pd.DataFrame:
    """Ajusta OHLC por dividendos (como `auto_adjust`) conservando el cierre real.

    - `Close` (y Open/High/Low) quedan ajustados: sirven para rentabilidad TOTAL, que
      incluye los dividendos reinvertidos, y para los indicadores.
    - `PriceClose` es el cierre tal como cotizó: sirve para la rentabilidad bursátil.
    - `Dividends` es el dividendo pagado en cada fecha (0 si no hubo).
    """
    df = raw.copy()
    df["PriceClose"] = df["Close"]
    if "Adj Close" in df:
        ratio = (df["Adj Close"] / df["Close"]).where(df["Close"] > 0)
        for col in ("Open", "High", "Low", "Close"):
            df[col] = df[col] * ratio
    df["Dividends"] = df["Dividends"].fillna(0.0) if "Dividends" in df else 0.0
    return df


EXTRA_COLUMNS = ("PriceClose", "Dividends")


def clean_ohlc(df: pd.DataFrame, extra: tuple[str, ...] = ()) -> pd.DataFrame:
    """Limpieza mínima del histórico: sin cierre o con precios <= 0 no son velas válidas.

    Yahoo devuelve a veces precios NEGATIVOS en datos antiguos (su ajuste por dividendos
    hacia atrás sobre precios muy pequeños pasa de cero). Un precio nunca puede ser <= 0.
    `extra` son columnas adicionales que se conservan si existen.
    """
    cols = ["Open", "High", "Low", "Close", "Volume"] + [c for c in extra if c in df]
    df = df[cols].dropna(subset=["Close"])
    prices = df[["Open", "High", "Low", "Close"]]
    valid = (prices > 0).all(axis=1)
    if not valid.all():
        log.info("Descartadas %d velas con precios <= 0", int((~valid).sum()))
    return df[valid]


class YahooProvider:
    name = SOURCE

    def _info(self, ticker: str) -> dict[str, Any]:
        try:
            info = yf.Ticker(ticker).info or {}
        except YFRateLimitError as e:
            raise RateLimitError("Yahoo está limitando las peticiones; espera un minuto.") from e
        except (requests.RequestException, OSError) as e:
            raise ProviderUnavailableError(f"No se pudo conectar con Yahoo: {e}") from e
        except YFException as e:
            raise TickerNotFoundError(ticker, suffix_hint(ticker)) from e
        if not info.get("quoteType"):
            raise TickerNotFoundError(ticker, suffix_hint(ticker))
        return info

    def get_quote(self, ticker: str) -> Quote:
        return parse_quote(ticker, self._info(ticker), datetime.now(UTC))

    def get_history(self, ticker: str, range_key: str) -> PriceHistory:
        rng = ALL_RANGES[range_key]
        try:
            df = yf.Ticker(ticker).history(
                period=rng.period, interval=rng.interval, auto_adjust=False
            )
        except YFRateLimitError as e:
            raise RateLimitError("Yahoo está limitando las peticiones; espera un minuto.") from e
        except (requests.RequestException, OSError) as e:
            raise ProviderUnavailableError(f"No se pudo conectar con Yahoo: {e}") from e
        if df is None or df.empty:
            raise TickerNotFoundError(ticker, suffix_hint(ticker))
        df = clean_ohlc(adjust_prices(df), extra=EXTRA_COLUMNS)
        df.index = pd.DatetimeIndex(df.index).tz_convert("UTC")
        return PriceHistory(
            ticker=ticker,
            range_key=range_key,
            interval=rng.interval,
            data=df,
            as_of=datetime.now(UTC),
            source=SOURCE,
        )

    def get_fundamentals(self, ticker: str) -> Fundamentals:
        info = self._info(ticker)
        return Fundamentals(
            ticker=ticker,
            name=info.get("longName") or info.get("shortName") or ticker,
            quote_type=info.get("quoteType"),
            sector=info.get("sector"),
            industry=info.get("industry"),
            country=info.get("country"),
            currency=info.get("financialCurrency") or info.get("currency"),
            metrics=parse_metrics(info),
            fund_family=info.get("fundFamily"),
            price_currency=info.get("currency"),
            last_report=_epoch_to_utc(info.get("mostRecentQuarter")),
            as_of=datetime.now(UTC),
            source=SOURCE,
        )

    def get_financials(self, ticker: str) -> Financials:
        try:
            t = yf.Ticker(ticker)
            income, balance = t.income_stmt, t.balance_sheet
        except YFRateLimitError as e:
            raise RateLimitError("Yahoo está limitando las peticiones; espera un minuto.") from e
        except (requests.RequestException, OSError) as e:
            raise ProviderUnavailableError(f"No se pudo conectar con Yahoo: {e}") from e
        items, period_end = parse_financials(income, balance)
        return Financials(ticker, items, period_end, datetime.now(UTC), SOURCE)

    def search(self, query: str) -> list[SearchResult]:
        try:
            quotes = yf.Search(query, max_results=10, news_count=0).quotes
        except YFRateLimitError as e:
            raise RateLimitError("Yahoo está limitando las peticiones; espera un minuto.") from e
        except (requests.RequestException, OSError) as e:
            raise ProviderUnavailableError(f"No se pudo conectar con Yahoo: {e}") from e
        return parse_search(quotes)


# Partida de Yahoo → nuestro nombre (último ejercicio anual)
_INCOME_ITEMS = {"EBIT": "ebit", "Pretax Income": "pretax_income", "Tax Provision": "tax_provision"}
_BALANCE_ITEMS = {
    "Total Debt": "total_debt",
    "Stockholders Equity": "equity",
    "Cash And Cash Equivalents": "cash",
}


def parse_financials(
    income: pd.DataFrame | None, balance: pd.DataFrame | None
) -> tuple[dict[str, float | None], datetime | None]:
    """Extrae del último ejercicio las partidas necesarias para el ROIC (función pura)."""
    items: dict[str, float | None] = {}
    period_end = None
    for df, mapping in ((income, _INCOME_ITEMS), (balance, _BALANCE_ITEMS)):
        has_data = df is not None and not df.empty
        for yahoo_key, key in mapping.items():
            v = df.loc[yahoo_key].iloc[0] if has_data and yahoo_key in df.index else None
            items[key] = _num(v)
        if has_data and period_end is None:
            period_end = pd.Timestamp(df.columns[0]).to_pydatetime().replace(tzinfo=UTC)
    return items, period_end


def parse_search(quotes: list[dict[str, Any]]) -> list[SearchResult]:
    """Resultados de búsqueda de Yahoo: solo acciones, ETFs e índices (función pura)."""
    out = []
    for q in quotes:
        kind = q.get("quoteType")
        if kind not in ("EQUITY", "ETF", "INDEX") or not q.get("symbol"):
            continue
        out.append(
            SearchResult(
                ticker=q["symbol"],
                name=q.get("longname") or q.get("shortname") or q["symbol"],
                quote_type=kind,
                exchange=q.get("exchDisp") or q.get("exchange"),
            )
        )
    return out
