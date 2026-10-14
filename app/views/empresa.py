"""Ficha de una empresa/ETF: cabecera con cotización y secciones de análisis."""

import streamlit as st

from components.charts import price_chart
from components.common import (
    delay_label,
    disclaimer,
    market_data,
    market_state_label,
    show_error,
    source_line,
    watchlist_repo,
)
from components.fundamentals_view import render_fundamentals
from components.universe_panel import universe_panel
from radar.data.markets import CHART_RANGES, exchange_for, is_valid_format, normalize_ticker
from radar.errors import RadarError
from radar.formatting import NA, fmt_number, fmt_pct, fmt_price

svc = market_data()
tickers = watchlist_repo().tickers()

# --- Selección del ticker -------------------------------------------------------
current = st.session_state.get("ticker") or (tickers[0] if tickers else "SAN.MC")
col1, col2 = st.columns([2, 2])
options = tickers if current in tickers else [current, *tickers]
picked = col1.selectbox("Watchlist", options, index=options.index(current))
typed = col2.text_input("…u otro ticker", placeholder="p. ej. TEF.MC")

ticker = normalize_ticker(typed) if typed else picked
if not is_valid_format(ticker):
    st.error(f"'{typed}' no tiene formato de ticker.")
    st.stop()
st.session_state["ticker"] = ticker

# --- Cabecera ---------------------------------------------------------------
try:
    q = svc.get_quote(ticker)
except RadarError as e:
    show_error(e)
    st.stop()

st.title(f"🏢 {q.name}")
disclaimer()
ex = exchange_for(ticker)
# Un índice se mide en puntos, no en la moneda de su bolsa.
unit = None if q.quote_type == "INDEX" else q.currency
st.caption(
    f"{ticker} · {q.exchange or (ex.name if ex else '')} · {unit or 'puntos'} · "
    f"{market_state_label(q)}"
)

delta = None
if q.change is not None:
    decimals = 2 if q.price >= 1 else 4  # la variación con los mismos decimales que el precio
    delta = f"{fmt_price(q.change, unit, decimals)} ({fmt_pct(q.change_pct, 2, signed=True)})"

c1, c2, c3 = st.columns(3)
c1.metric("Precio", fmt_price(q.price, unit), delta)
c2.metric("Volumen", fmt_number(q.volume, 0) if q.volume is not None else NA)
c3.metric("Cierre anterior", fmt_price(q.previous_close, unit))
st.caption(source_line(q.source, q.as_of, delay_label(q), q.stale))

# --- Secciones ---------------------------------------------------------------
# Un selector en vez de st.tabs: st.tabs ejecuta el código de TODAS las pestañas en cada
# interacción (más llamadas a la API); así solo se calcula la sección visible.
SECTIONS = ["📈 Gráfico", "📊 Fundamentales"]
section = st.segmented_control("Sección", SECTIONS, default=SECTIONS[0], key="section")
section = section or SECTIONS[0]


def section_chart() -> None:
    col1, col2, col3 = st.columns([3, 1.2, 1])
    range_key = (
        col1.segmented_control("Rango", list(CHART_RANGES), default="6M", key="range") or "6M"
    )
    kind = (
        col2.segmented_control("Tipo", ["Velas", "Línea"], default="Velas", key="kind") or "Velas"
    )
    log_scale = col3.toggle(
        "Escala log",
        value=range_key in ("5A", "Máx"),
        key=f"log_{range_key}",
        help="En escala logarítmica, subir de 1 a 2 € (+100 %) ocupa lo mismo que subir de "
        "50 a 100 € (+100 %). Imprescindible para comparar periodos largos.",
    )
    try:
        hist = svc.get_history(ticker, range_key)
    except RadarError as e:
        show_error(e)
        return
    rng = CHART_RANGES[range_key]
    st.plotly_chart(price_chart(hist, kind, rng.intraday, log_scale), width="stretch")
    first, last = hist.data["Close"].iloc[0], hist.data["Close"].iloc[-1]
    st.caption(
        f"Variación en el rango ({rng.label}): {fmt_pct(last / first - 1, 2, signed=True)} · "
        f"velas de {rng.interval} · precios ajustados por dividendos y splits · "
        + source_line(hist.source, hist.as_of, stale=hist.stale).replace("dato de", "descargado")
    )
    if rng.intraday:
        st.caption(
            "ℹ️ El volumen intradía de Yahoo es incompleto (no incluye subastas ni todas las "
            "operaciones y a veces acumula volumen en una sola vela). Para comparar volúmenes "
            "usa rangos de 1M o más."
        )


def section_fundamentals() -> None:
    if q.quote_type == "INDEX":
        st.info("Los índices no tienen métricas fundamentales propias.")
        return
    try:
        f = svc.get_fundamentals(ticker)
    except RadarError as e:
        show_error(e)
        return
    snap = None if f.quote_type in ("ETF", "MUTUALFUND") else universe_panel("empresa")
    render_fundamentals(f, snap)


{
    "📈 Gráfico": section_chart,
    "📊 Fundamentales": section_fundamentals,
}[section]()
