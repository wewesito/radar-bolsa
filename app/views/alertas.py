"""Alertas: avisos cuando un precio o indicador cruza un umbral."""

import pandas as pd
import streamlit as st

from components.common import alerts_repo, disclaimer, market_data, show_error, watchlist_repo
from radar.alerts.checker import check_all, observe
from radar.alerts.rules import METRIC_LABELS, OP_LABELS, Alert, condition, describe
from radar.data.markets import is_valid_format, normalize_ticker
from radar.errors import RadarError
from radar.formatting import fmt_dt, fmt_number

st.title("🔔 Alertas")
disclaimer()
st.caption(
    "Una alerta avisa cuando la condición **pasa a cumplirse** (cruce del umbral), no mientras "
    "se cumple: así no recibes el mismo aviso cada minuto. Se comprueban en cada refresco de la "
    "watchlist mientras la app está abierta, o desde la terminal (ver abajo)."
)

svc = market_data()
repo = alerts_repo()

# --- Nueva alerta -----------------------------------------------------------------
with st.container(border=True):
    st.markdown("**Nueva alerta**")
    c1, c2, c3, c4 = st.columns([2, 2, 1.5, 1.5])
    options = watchlist_repo().tickers()
    pick = c1.selectbox("Ticker", options or ["—"])
    typed = c1.text_input("…u otro", placeholder="p. ej. REP.MC", key="alert_typed")
    ticker = normalize_ticker(typed) if typed else (pick if options else "")
    metric = c2.selectbox("Qué vigilar", list(METRIC_LABELS), format_func=METRIC_LABELS.get)
    op = c3.selectbox("Condición", list(OP_LABELS), format_func=OP_LABELS.get)
    is_cross = metric in ("sma50", "sma200")
    threshold = None
    if not is_cross:
        default = 70.0 if metric == "rsi" else (-3.0 if metric == "change_pct" else 0.0)
        threshold = c4.number_input("Umbral", value=default, step=0.5, key=f"thr_{metric}")

    if ticker and is_valid_format(ticker):
        draft = Alert(ticker, metric, op, threshold)
        try:
            obs = observe(svc, draft)
            ref = f" (media: {fmt_number(obs.reference)})" if obs.reference is not None else ""
            status = (
                "⚠️ La condición **ya se cumple**: avisará cuando deje de cumplirse y vuelva a "
                "cumplirse."
                if condition(draft, obs)
                else "Ahora no se cumple: avisará cuando se cumpla."
            )
            label = METRIC_LABELS[metric]
            st.caption(f"Valor actual ({label}): **{fmt_number(obs.value)}**{ref}. {status}")
        except RadarError as e:
            show_error(e)
        if st.button("Crear alerta", type="primary"):
            repo.add(draft)
            check_all(svc, repo)  # primera evaluación: fija el estado sin avisar
            st.success(f"Alerta creada: {describe(draft)}")
            st.rerun()

# --- Alertas existentes -------------------------------------------------------------
alerts = repo.list()
if not alerts:
    st.info("No tienes alertas. Crea una arriba.")
    st.stop()

c1, c2 = st.columns([1, 4])
if c1.button("🔄 Comprobar ahora"):
    for msg in check_all(svc, repo):
        st.toast(msg, icon="🔔")

last = repo.last_values()
table = pd.DataFrame(
    [
        {
            "id": a.id,
            "Alerta": describe(a),
            "Estado": "activa" if a.active else "pausada",
            "¿Se cumple ahora?": {None: "—", True: "sí", False: "no"}[a.last_state],
            "Último valor": last.get(a.id, (None, None))[0],
            "Última comprobación": fmt_dt(pd.Timestamp(last[a.id][1]).to_pydatetime())
            if last.get(a.id, (None, None))[1]
            else "—",
        }
        for a in alerts
    ]
)
event = st.dataframe(
    table,
    hide_index=True,
    width="stretch",
    on_select="rerun",
    selection_mode="single-row",
    column_config={"id": None, "Último valor": st.column_config.NumberColumn(format="%.2f")},
)
if event.selection.rows:
    sel = alerts[event.selection.rows[0]]
    c1, c2, _ = st.columns([1, 1, 4])
    if c1.button("⏸️ Pausar" if sel.active else "▶️ Reactivar"):
        repo.set_active(sel.id, not sel.active)
        st.rerun()
    if c2.button("🗑️ Borrar"):
        repo.delete(sel.id)
        st.rerun()

# --- Historial de avisos ------------------------------------------------------------
st.subheader("Avisos recibidos")
events = repo.events()
if not events:
    st.caption("Todavía no ha saltado ninguna alerta.")
else:
    for e in events:
        st.markdown(f"{'🆕 ' if not e.seen else ''}{fmt_dt(e.triggered_at)} · {e.message}")
    if any(not e.seen for e in events) and st.button("Marcar todos como vistos"):
        repo.mark_all_seen()
        st.rerun()

with st.expander("Comprobar alertas con la app cerrada (opcional)"):
    st.markdown(
        "Desde la terminal, en la carpeta del proyecto:\n\n"
        "```bash\n.venv/bin/python -m radar.alerts.checker --notify\n```\n\n"
        "`--notify` muestra una notificación de macOS por cada alerta disparada. Para hacerlo "
        "periódicamente puedes programarlo con `cron` (p. ej. cada 15 min en horario de "
        "mercado). Recuerda que los datos gratuitos llevan ~15 min de retraso."
    )
