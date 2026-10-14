"""Ficha de una empresa/ETF: cotización, gráfico histórico y fundamentales."""

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

from radar.data.markets import CHART_RANGES, exchange_for, is_valid_format, normalize_ticker
from radar.errors import RadarError
from radar.formatting import NA, fmt_big, fmt_dt, fmt_number, fmt_pct, fmt_price
from radar.fundamentals.metrics import MetricDef, metrics_for

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

# --- Gráfico ----------------------------------------------------------------
st.subheader("Histórico")
col1, col2, col3 = st.columns([3, 1.2, 1])
range_key = col1.segmented_control("Rango", list(CHART_RANGES), default="6M", key="range") or "6M"
kind = col2.segmented_control("Tipo", ["Velas", "Línea"], default="Velas", key="kind") or "Velas"
log_scale = col3.toggle(
    "Escala log",
    value=range_key in ("5A", "Máx"),
    key=f"log_{range_key}",
    help="En escala logarítmica, subir de 1 a 2 € (+100 %) ocupa lo mismo que subir de 50 a "
    "100 € (+100 %). Imprescindible para comparar periodos largos.",
)

try:
    hist = svc.get_history(ticker, range_key)
except RadarError as e:
    show_error(e)
else:
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

# --- Fundamentales ------------------------------------------------------------
st.subheader("Fundamentales")
if q.quote_type == "INDEX":
    st.info("Los índices no tienen métricas fundamentales propias.")
    st.stop()

try:
    f = svc.get_fundamentals(ticker)
except RadarError as e:
    show_error(e)
    st.stop()


def fmt_metric(m: MetricDef, value: float | None, currency: str | None) -> str:
    if m.kind == "pct":
        return fmt_pct(value)
    if m.kind == "money":
        return fmt_big(value, currency)
    if m.kind == "per_share":
        return fmt_price(value, currency)
    return fmt_number(value)


info_bits = [b for b in (f.sector, f.industry, f.country, f.fund_family) if b]
if info_bits:
    st.caption(" · ".join(info_bits))

defs = metrics_for(f.quote_type)
groups: dict[str, list[MetricDef]] = {}
for m in defs:
    groups.setdefault(m.group, []).append(m)

for group, items in groups.items():
    st.markdown(f"**{group}**")
    cols = st.columns(3)
    for i, m in enumerate(items):
        cols[i % 3].metric(m.label, fmt_metric(m, f.metrics.get(m.key), f.currency), help=m.help)

missing = sum(f.metrics.get(m.key) is None for m in defs)
notes = [
    source_line(f.source, f.as_of, stale=f.stale).replace("dato de", "descargado"),
]
if f.last_report:
    notes.append(f"último trimestre reportado: {fmt_dt(f.last_report).split()[0]}")
if missing:
    notes.append(
        f"{missing} métrica(s) n/d: la fuente no la publica o no aplica a este tipo de empresa "
        "(p. ej. deuda/patrimonio o margen bruto en bancos)"
    )
st.caption(" · ".join(notes))
st.caption("La comparación con la media del sector llega en la Fase 2.")
