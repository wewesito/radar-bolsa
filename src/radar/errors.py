"""Excepciones propias. La UI las traduce a mensajes amables."""


class RadarError(Exception):
    """Base de todos los errores de la app."""


class TickerNotFoundError(RadarError):
    """El ticker no existe o la fuente no tiene datos de él."""

    def __init__(self, ticker: str, hint: str | None = None):
        self.ticker = ticker
        self.hint = hint
        msg = f"No se encontraron datos para '{ticker}'."
        super().__init__(f"{msg} {hint}" if hint else msg)


class ProviderUnavailableError(RadarError):
    """La fuente de datos no responde (caída, sin red...)."""


class RateLimitError(ProviderUnavailableError):
    """La fuente nos limita por exceso de peticiones."""
