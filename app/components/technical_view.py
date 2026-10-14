"""Sección de análisis técnico de la ficha."""

import pandas as pd
import streamlit as st

from components.charts import technical_chart
from components.common import show_error, source_line
from radar.data.service import MarketDataService
from radar.errors import RadarError
from radar.formatting import fmt_dt, fmt_pct
from radar.indicators.summary import technical_observations
from radar.indicators.technical import support_resistance, suspicious_jumps

TONE_ICON = {"alcista": "▲", "bajista": "▼", "neutral": "●"}


def jumps_warning(close: pd.Series, label: str = "") -> None:
    jumps = suspicious_jumps(close)
    if not jumps.empty:
        items = ", ".join(
            f"{fmt_dt(d).split()[0]} ({fmt_pct(v, 0, signed=True)})" for d, v in jumps.items()
        )
        st.warning(
            f"Saltos sospechosos de más del 40 % entre velas consecutivas{label}: {items}. "
            "En grandes empresas suelen ser errores de la fuente (splits mal ajustados), no "
            "movimientos reales: tenlo en cuenta al leer el gráfico y los indicadores.",
            icon="🧐",
        )


def render_technical(svc: MarketDataService, ticker: str) -> None:
    try:
        hist = svc.get_history(ticker, "2A")
    except RadarError as e:
        show_error(e)
        return
    ohlc = hist.data
    close = ohlc["Close"]
    if len(close) < 60:
        st.info("No hay suficiente histórico para calcular los indicadores (mínimo ~60 sesiones).")
        return

    jumps_warning(close)
    last_year = ohlc.loc[ohlc.index[-1] - pd.Timedelta(days=365) :]
    levels = support_resistance(last_year)

    st.markdown("**Qué dicen los indicadores** (lectura clásica, no una predicción)")
    for o in technical_observations(close):
        st.markdown(f"{TONE_ICON[o.tone]} **{o.indicator}** · {o.text}")

    st.plotly_chart(technical_chart(close, levels), width="stretch")
    st.caption(
        "Indicadores calculados sobre 2 años de cierres diarios ajustados; se muestra el último "
        "año. Soportes (S) y resistencias (R): zonas donde el precio giró varias veces en el "
        "último año (máximos/mínimos locales agrupados a ±2 %). · "
        + source_line(hist.source, hist.as_of, stale=hist.stale).replace("dato de", "descargado")
    )
    with st.expander("Limitaciones del análisis técnico"):
        st.markdown(
            "- Los indicadores se calculan **solo con precios pasados**: describen lo ocurrido, "
            "no garantizan lo que vendrá.\n"
            "- Las reglas clásicas (RSI 70/30, cruces de medias) tienen muchas señales falsas, "
            "sobre todo en mercados laterales.\n"
            "- Con miles de inversores mirando los mismos niveles, a veces funcionan por "
            "profecía autocumplida y a veces se rompen precisamente por eso.\n"
            "- Combínalo con el análisis fundamental: el técnico habla del *cuándo* y del "
            "sentimiento, no de si el negocio es bueno."
        )
