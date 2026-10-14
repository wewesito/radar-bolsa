"""Watchlist: añadir/quitar tickers y ver sus cotizaciones con refresco automático."""

from datetime import UTC, datetime

import pandas as pd
import streamlit as st
from components.common import (
    delay_label,
    disclaimer,
    market_data,
    market_state_label,
    show_error,
    watchlist_repo,
)

from radar import config
from radar.data.markets import is_valid_format, normalize_ticker
from radar.errors import RadarError
from radar.formatting import fmt_age, fmt_dt

st.title("👀 Watchlist")
disclaimer()

repo = watchlist_repo()
svc = market_data()

# --- Añadir ---------------------------------------------------------------
with st.form("add", clear_on_submit=True, border=False):
    col1, col2 = st.columns([4, 1], vertical_alignment="bottom")
    raw = col1.text_input(
        "Añadir ticker",
        placeholder="SAN.MC, ITX.MC, ^IBEX, IWDA.AS, AAPL…",
        help="Las acciones españolas llevan el sufijo .MC (Bolsa de Madrid). "
        "Otras bolsas: .DE, .PA, .AS, .MI, .L. Sin sufijo = EE. UU.",
    )
    submitted = col2.form_submit_button("Añadir", width="stretch")

if submitted and raw:
    ticker = normalize_ticker(raw)
    if not is_valid_format(ticker):
        st.error(f"'{raw}' no tiene formato de ticker.", icon="✏️")
    else:
        try:
            q = svc.get_quote(ticker)  # valida que existe antes de guardarlo
        except RadarError as e:
            show_error(e)
        else:
            if repo.add(ticker, q.name):
                st.success(f"Añadido {ticker} · {q.name} ({q.exchange}, {q.currency})")
                if "." not in ticker and not ticker.startswith("^") and q.currency == "USD":
                    st.info(
                        f"{ticker} cotiza en EE. UU. Si buscabas una empresa europea, "
                        "puede que esto sea su ADR (un certificado en dólares). "
                        f"Para la cotización en Madrid usa {ticker}.MC.",
                        icon="💡",
                    )
            else:
                st.info(f"{ticker} ya estaba en la watchlist.")

tickers = repo.tickers()
if not tickers:
    st.info("La watchlist está vacía. Prueba a añadir SAN.MC, ITX.MC o ^IBEX.")
    st.stop()


# --- Tabla con refresco automático --------------------------------------------
# Un fragmento se re-ejecuta solo, sin recargar el resto de la página. La caché del
# servicio (TTL 60 s) garantiza que refrescar más a menudo no multiplica las llamadas.
@st.fragment(run_every=config.REFRESH_SECONDS)
def quotes_table(tickers: list[str]) -> None:
    results = svc.get_quotes(tickers)
    now = datetime.now(UTC)
    rows, errors = [], []
    for t, q in results.items():
        if isinstance(q, RadarError):
            errors.append((t, q))
            continue
        rows.append(
            {
                "Ticker": t,
                "Nombre": q.name,
                "Precio": q.price,
                "Moneda": "pts" if q.quote_type == "INDEX" else q.currency,
                "Var. %": q.change_pct * 100 if q.change_pct is not None else None,
                "Volumen": q.volume,
                "Mercado": market_state_label(q),
                "Retraso": delay_label(q),
                "Antigüedad": fmt_age((now - q.as_of).total_seconds()),
                "Hora dato": fmt_dt(q.as_of) + (" ⚠️ antiguo" if q.stale else ""),
                "Fuente": q.source,
            }
        )

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(
            df,
            hide_index=True,
            width="stretch",
            column_config={
                "Precio": st.column_config.NumberColumn(format="%.2f"),
                "Var. %": st.column_config.NumberColumn(format="%+.2f %%"),
                "Volumen": st.column_config.NumberColumn(format="localized"),
                "Mercado": st.column_config.TextColumn(
                    help="Estado según la fuente. Con * = estimado por horario (sin festivos)."
                ),
                "Retraso": st.column_config.TextColumn(
                    help="Retraso que DECLARA la fuente. Las bolsas europeas en fuentes "
                    "gratuitas suelen ir con 15 min."
                ),
                "Antigüedad": st.column_config.TextColumn(
                    help="Tiempo desde la última cotización recibida. Con el mercado abierto "
                    "es el retraso REAL observado (puede no coincidir con el declarado); "
                    "con el mercado cerrado, simplemente el tiempo desde el cierre."
                ),
            },
        )
    for t, e in errors:
        st.warning(f"{t}: {e}")
    st.caption(
        f"Actualizado {fmt_dt(datetime.now(UTC), with_date=False)} (hora de Madrid) · "
        f"refresco automático cada {config.REFRESH_SECONDS} s · Hora dato = última "
        "cotización recibida de la fuente."
    )


quotes_table(tickers)

# --- Acciones -------------------------------------------------------------
col1, col2 = st.columns(2)
with col1:
    sel = st.selectbox("Ver detalle de", tickers, key="detail_pick")
    if st.button("Abrir ficha 🏢"):
        st.session_state["ticker"] = sel
        st.switch_page("views/empresa.py")
with col2:
    rem = st.selectbox("Quitar de la watchlist", tickers, key="remove_pick")
    if st.button("Quitar 🗑️"):
        repo.remove(rem)
        st.rerun()
