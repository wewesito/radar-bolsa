"""Formato de números y fechas en español (1.234,56 · 12,3 % · 170,1 mil M€)."""

from datetime import datetime
from zoneinfo import ZoneInfo

from radar.config import DISPLAY_TZ

NA = "n/d"

CURRENCY_SYMBOLS = {"EUR": "€", "USD": "$", "GBP": "£", "CHF": "CHF", "GBp": "p"}


def fmt_number(x: float | None, decimals: int = 2) -> str:
    if x is None:
        return NA
    s = f"{x:,.{decimals}f}"  # formato inglés: 1,234.56
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def fmt_pct(x: float | None, decimals: int = 1, signed: bool = False) -> str:
    """`x` es una fracción: 0.123 → '12,3 %'."""
    if x is None:
        return NA
    s = fmt_number(abs(x) * 100, decimals)
    sign = "−" if x < 0 else ("+" if signed and x > 0 else "")
    return f"{sign}{s} %"


def fmt_big(x: float | None, currency: str | None = None) -> str:
    """Cantidades grandes abreviadas: 170.079.502.336 → '170,1 mil M€'."""
    if x is None:
        return NA
    sym = CURRENCY_SYMBOLS.get(currency or "", currency or "")
    sign, a = ("−" if x < 0 else ""), abs(x)
    if a >= 1e9:
        body = f"{fmt_number(a / 1e9, 1)} mil M"
    elif a >= 1e6:
        body = f"{fmt_number(a / 1e6, 1)} M"
    elif a >= 1e3:
        body = f"{fmt_number(a / 1e3, 1)} mil"
    else:
        body = fmt_number(a, 0)
    # Símbolos de un carácter van pegados (M€); códigos largos, separados (M CHF).
    return f"{sign}{body}{sym}" if len(sym) == 1 else f"{sign}{body} {sym}".rstrip()


def fmt_price(x: float | None, currency: str | None = None) -> str:
    if x is None:
        return NA
    sym = CURRENCY_SYMBOLS.get(currency or "", currency or "")
    decimals = 2 if x >= 1 else 4
    return f"{fmt_number(x, decimals)} {sym}".rstrip()


def fmt_dt(dt: datetime | None, with_date: bool = True) -> str:
    """Fecha/hora en la zona de visualización (Madrid)."""
    if dt is None:
        return NA
    local = dt.astimezone(ZoneInfo(DISPLAY_TZ))
    return local.strftime("%d/%m/%Y %H:%M" if with_date else "%H:%M:%S")
