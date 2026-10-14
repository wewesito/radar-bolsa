"""Conocimiento del dominio: bolsas, sufijos de ticker, horarios y rangos de gráfico.

Funciones puras (sin red) para poder testearlas.
"""

import re
from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Exchange:
    name: str
    country: str
    tz: str
    open: time
    close: time
    typical_delay_min: int  # retraso habitual en fuentes gratuitas


US = Exchange("NYSE / Nasdaq", "EE. UU.", "America/New_York", time(9, 30), time(16, 0), 0)

# Sufijo de Yahoo → bolsa. Horarios de la sesión continua (sin subastas ni festivos).
EXCHANGES: dict[str, Exchange] = {
    "MC": Exchange("Bolsa de Madrid (BME)", "España", "Europe/Madrid", time(9), time(17, 30), 15),
    "DE": Exchange("Xetra", "Alemania", "Europe/Berlin", time(9), time(17, 30), 15),
    "F": Exchange("Fráncfort", "Alemania", "Europe/Berlin", time(8), time(22), 15),
    "PA": Exchange("Euronext París", "Francia", "Europe/Paris", time(9), time(17, 30), 15),
    "AS": Exchange(
        "Euronext Ámsterdam", "Países Bajos", "Europe/Amsterdam", time(9), time(17, 30), 15
    ),
    "BR": Exchange("Euronext Bruselas", "Bélgica", "Europe/Brussels", time(9), time(17, 30), 15),
    "LS": Exchange("Euronext Lisboa", "Portugal", "Europe/Lisbon", time(8), time(16, 30), 15),
    "MI": Exchange("Borsa Italiana", "Italia", "Europe/Rome", time(9), time(17, 30), 15),
    "L": Exchange("Bolsa de Londres", "Reino Unido", "Europe/London", time(8), time(16, 30), 15),
    "SW": Exchange("SIX Swiss", "Suiza", "Europe/Zurich", time(9), time(17, 30), 15),
    "HE": Exchange("Nasdaq Helsinki", "Finlandia", "Europe/Helsinki", time(10), time(18, 30), 15),
}

# Tickers válidos de Yahoo: letras, dígitos, punto, guion, ^ (índices) y = (divisas/futuros).
_TICKER_RE = re.compile(r"^\^?[A-Z0-9][A-Z0-9.\-=]{0,19}$")


def normalize_ticker(raw: str) -> str:
    """Limpia lo que escribe el usuario: espacios fuera y mayúsculas."""
    return raw.strip().upper()


def is_valid_format(ticker: str) -> bool:
    """Comprueba solo el formato; que exista lo decide la fuente de datos."""
    return bool(_TICKER_RE.match(ticker))


def exchange_for(ticker: str) -> Exchange | None:
    """Bolsa según el sufijo. Sin sufijo se asume EE. UU.; los índices (^) no tienen bolsa."""
    if ticker.startswith("^"):
        return None
    if "." in ticker:
        return EXCHANGES.get(ticker.rsplit(".", 1)[1])
    return US


def suffix_hint(ticker: str) -> str | None:
    """Sugerencia cuando un ticker sin sufijo falla: quizá era una acción europea."""
    if "." in ticker or ticker.startswith("^"):
        return None
    return (
        f"Si es una acción española prueba con '{ticker}.MC'; "
        f"para otras bolsas europeas usa .DE, .PA, .AS, .MI o .L."
    )


def is_session_open(exchange: Exchange, now: datetime) -> bool:
    """Estimación por horario (lunes-viernes, sin festivos). Respaldo si la fuente no lo indica."""
    local = now.astimezone(ZoneInfo(exchange.tz))
    if local.weekday() >= 5:
        return False
    return exchange.open <= local.time() < exchange.close


@dataclass(frozen=True)
class ChartRange:
    label: str
    period: str  # parámetro `period` de yfinance
    interval: str  # granularidad de las velas

    @property
    def intraday(self) -> bool:
        return self.interval.endswith("m") and not self.interval.endswith("mo")


# Elegimos la granularidad para que cada gráfico tenga entre ~50 y ~400 velas:
# muchas más saturan el gráfico y muchas menos no muestran nada.
CHART_RANGES: dict[str, ChartRange] = {
    "1D": ChartRange("1 día", "1d", "5m"),
    "1S": ChartRange("1 semana", "5d", "30m"),
    "1M": ChartRange("1 mes", "1mo", "1d"),
    "6M": ChartRange("6 meses", "6mo", "1d"),
    "1A": ChartRange("1 año", "1y", "1d"),
    "5A": ChartRange("5 años", "5y", "1wk"),
    "Máx": ChartRange("Máximo", "max", "1mo"),
}

# Rangos que no aparecen en el selector del gráfico pero usan los análisis:
# 2 años diarios para que la media de 200 sesiones tenga un año entero de valores, y
# 5 años diarios para valorar carteras con operaciones antiguas.
ALL_RANGES: dict[str, ChartRange] = {
    **CHART_RANGES,
    "2A": ChartRange("2 años", "2y", "1d"),
    "5Ad": ChartRange("5 años (diario)", "5y", "1d"),
    # Todo el histórico diario: rentabilidades a 3–5 años e historial de dividendos.
    "MAXd": ChartRange("Máximo (diario)", "max", "1d"),
}
