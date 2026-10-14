"""Piezas compartidas por todas las páginas: servicios, aviso legal, badges y errores."""

from datetime import UTC, datetime

import streamlit as st

from radar import DISCLAIMER, config
from radar.data.markets import exchange_for, is_session_open
from radar.data.service import MarketDataService, default_service
from radar.db.database import Database
from radar.db.watchlist import WatchlistRepo
from radar.errors import RadarError, RateLimitError, TickerNotFoundError
from radar.formatting import fmt_dt
from radar.models import Quote


@st.cache_resource
def market_data() -> MarketDataService:
    """Un único servicio para toda la app (se crea una vez y se reutiliza)."""
    return default_service()


@st.cache_resource
def watchlist_repo() -> WatchlistRepo:
    return WatchlistRepo(Database(config.DB_PATH))


def disclaimer() -> None:
    st.caption(f"⚠️ {DISCLAIMER}")


MARKET_STATES = {
    "REGULAR": "🟢 Abierto",
    "PRE": "🟡 Preapertura",
    "PREPRE": "⚪ Cerrado",
    "POST": "🟡 Post-cierre",
    "POSTPOST": "⚪ Cerrado",
    "CLOSED": "⚪ Cerrado",
}


def market_state_label(quote: Quote) -> str:
    if quote.market_state in MARKET_STATES:
        return MARKET_STATES[quote.market_state]
    # La fuente no lo indica: lo estimamos por horario (sin festivos).
    ex = exchange_for(quote.ticker)
    if ex is None:
        return "—"
    return "🟢 Abierto*" if is_session_open(ex, datetime.now(UTC)) else "⚪ Cerrado*"


def delay_label(quote: Quote) -> str:
    if quote.delay_minutes is None:
        return "desconocido"
    return "tiempo real" if quote.delay_minutes == 0 else f"{quote.delay_minutes} min"


def source_line(
    source: str, as_of: datetime | None, delay: str | None = None, stale: bool = False
) -> str:
    parts = [f"Fuente: {source}", f"dato de {fmt_dt(as_of)} (hora de Madrid)"]
    if delay:
        parts.append(f"retraso: {delay}")
    line = " · ".join(parts)
    return f"⚠️ **Datos antiguos** (la fuente no responde) · {line}" if stale else line


def show_error(err: RadarError) -> None:
    if isinstance(err, TickerNotFoundError):
        st.error(str(err), icon="🔎")
    elif isinstance(err, RateLimitError):
        st.warning(str(err), icon="⏳")
    else:
        st.error(f"Fuente de datos no disponible. {err}", icon="📡")
