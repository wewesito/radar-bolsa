"""ETFs de referencia para las recomendaciones y la cartera de ejemplo.

Solo ETFs UCITS (los que un inversor particular de la UE puede comprar: tienen KID en
español) y cotizados en euros. Comprobados contra Yahoo el 14/10/2026. Yahoo no da la
comisión (TER) de todos: si falta, la app lo indica en vez de inventarla.

Papel (`role`) de cada ETF en una cartera:
- core: renta variable amplia y barata, la base de una cartera indexada.
- complement: añade una zona o un estilo concreto; más concentrado o más volátil.
- dividend: renta variable orientada a dividendos.
- bonds: renta fija; amortigua las caídas.
- cash: monetario; casi sin oscilación, para liquidez.
"""

from dataclasses import dataclass
from typing import Literal

Role = Literal["core", "complement", "dividend", "bonds", "cash"]


@dataclass(frozen=True)
class EtfInfo:
    ticker: str
    short_name: str
    index: str
    role: Role
    zone: str  # exposición geográfica principal, para la diversificación
    accumulating: bool  # True: reinvierte dividendos (sin retención en España hasta vender)


ETFS: list[EtfInfo] = [
    EtfInfo("VWCE.DE", "Vanguard FTSE All-World", "FTSE All-World", "core", "Global", True),
    EtfInfo("IUSQ.DE", "iShares MSCI ACWI", "MSCI ACWI", "core", "Global", True),
    EtfInfo("EUNL.DE", "iShares Core MSCI World", "MSCI World", "core", "Desarrollados", True),
    EtfInfo("XDWD.DE", "Xtrackers MSCI World", "MSCI World", "core", "Desarrollados", True),
    EtfInfo("SXR8.DE", "iShares Core S&P 500", "S&P 500", "core", "EE. UU.", True),
    EtfInfo("MEUD.PA", "Amundi Core Stoxx Europe 600", "STOXX Europe 600", "core", "Europa", True),
    EtfInfo("IS3N.DE", "iShares Core MSCI EM IMI", "MSCI EM IMI", "complement", "Emergentes", True),
    EtfInfo("IUSN.DE", "iShares MSCI World Small Cap", "MSCI World Small Cap", "complement",
            "Desarrollados", True),
    EtfInfo("SXRV.DE", "iShares NASDAQ 100", "NASDAQ-100", "complement", "EE. UU.", True),
    EtfInfo("VHYL.AS", "Vanguard FTSE All-World High Dividend", "FTSE AW High Div. Yield",
            "dividend", "Global", False),
    EtfInfo("TDIV.AS", "VanEck Developed Markets Dividend Leaders", "Morningstar DM Div. Leaders",
            "dividend", "Desarrollados", False),
    EtfInfo("EUNA.DE", "iShares Core Global Aggregate Bond (EUR cubierto)",
            "Bloomberg Global Aggregate", "bonds", "Global", False),
    EtfInfo("XGLE.DE", "Xtrackers Eurozone Government Bond", "iBoxx € Sovereigns", "bonds",
            "Eurozona", True),
    EtfInfo("XEON.DE", "Xtrackers EUR Overnight Rate Swap", "€STR", "cash", "Eurozona", True),
]  # fmt: skip

BY_TICKER: dict[str, EtfInfo] = {e.ticker: e for e in ETFS}
ETF_TICKERS: list[str] = [e.ticker for e in ETFS]

ROLE_ES: dict[str, str] = {
    "core": "Base de cartera",
    "complement": "Complemento",
    "dividend": "Dividendos",
    "bonds": "Renta fija",
    "cash": "Liquidez",
}
