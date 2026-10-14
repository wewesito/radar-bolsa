"""Sección del score transparente: total, componentes, fórmula y argumentos."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.charts import SERIES
from components.common import show_error
from components.universe_panel import universe_panel
from radar.data.service import MarketDataService
from radar.errors import RadarError
from radar.formatting import fmt_metric_value, fmt_number
from radar.fundamentals.metrics import ALL_METRICS
from radar.models import Quote
from radar.scoring.score import COMPONENTS, DEFAULT_WEIGHTS, ScoreResult, score_band, score_company
from radar.universe import company_row


def weights_editor() -> dict[str, float]:
    """Pesos ajustables (en %) guardados en la sesión. Se normalizan al calcular."""
    with st.expander("⚖️ Ajustar pesos de los componentes"):
        st.caption(
            "Por defecto todos pesan lo mismo (20 %). Cámbialos según lo que te importe más: "
            "un inversor por dividendos quizá prime salud y riesgo; uno de crecimiento, "
            "crecimiento y momentum. Los pesos se normalizan para que sumen 100 %."
        )
        cols = st.columns(len(COMPONENTS))
        weights = {}
        for col, c in zip(cols, COMPONENTS, strict=True):
            weights[c.key] = (
                col.slider(
                    c.label.split(" (")[0],
                    0,
                    100,
                    int(DEFAULT_WEIGHTS[c.key] * 100),
                    5,
                    key=f"w_{c.key}",
                )
                / 100
            )
    return weights


def components_chart(res: ScoreResult) -> go.Figure:
    labels = [c.label for c in res.components][::-1]
    scores = [c.score for c in res.components][::-1]
    fig = go.Figure(
        go.Bar(
            x=[s if s is not None else 0 for s in scores],
            y=labels,
            orientation="h",
            marker_color=SERIES[0],
            marker_line_width=0,
            text=[f"{s:.0f}" if s is not None else "sin datos" for s in scores],
            textposition="outside",
            hovertemplate="%{y}: %{x:.0f}<extra></extra>",
        )
    )
    fig.add_vline(x=50, line=dict(color="rgba(128,128,128,0.6)", width=1, dash="dot"))
    fig.update_layout(
        height=260,
        margin=dict(l=10, r=30, t=10, b=10),
        xaxis=dict(range=[0, 105], title="Puntuación (50 = mediana de los comparables)"),
        separators=",.",
    )
    return fig


def render_score(svc: MarketDataService, ticker: str, q: Quote) -> None:
    if q.quote_type != "EQUITY":
        st.info(
            "El score compara empresas con sus competidores; no se calcula para ETFs ni "
            "índices (para un ETF importan sobre todo su coste, su índice y su tamaño)."
        )
        return
    snap = universe_panel("score")
    if snap is None:
        return
    try:
        row = company_row(svc, ticker)
    except RadarError as e:
        show_error(e)
        return

    weights = weights_editor()
    res = score_company(row, snap.df, weights, currency=q.currency)

    col1, col2 = st.columns([1, 2])
    with col1:
        if res.total is None:
            st.metric("Score", "n/d")
        else:
            st.metric("Score", f"{res.total:.0f} / 100")
            st.caption(score_band(res.total).capitalize() + ".")
        for n in res.notes:
            st.caption(f"ℹ️ {n}")
    col2.plotly_chart(components_chart(res), width="stretch")

    if res.total is not None:
        parts = " + ".join(
            f"{c.effective_weight:.2f} × {c.score:.0f}".replace(".", ",")
            for c in res.components
            if c.score is not None and c.effective_weight > 0
        )
        st.markdown(f"**Fórmula:** Score = Σ peso × puntuación = {parts} = **{res.total:.0f}**")

    st.markdown("#### Cómo se calcula cada componente")
    for c in res.components:
        title = f"{c.label}: {'sin datos' if c.score is None else f'{c.score:.0f}'} "
        title += f"· datos {c.coverage} · comparado con {c.basis_label}"
        with st.expander(title):
            st.caption(c.description)
            records = []
            for i in c.inputs:
                meta = ALL_METRICS[i.key]
                pct = None if i.percentile is None else round(i.percentile * 100)
                records.append(
                    {
                        "Métrica": i.label,
                        "Valor": fmt_metric_value(meta.kind, i.value, q.currency),
                        "Mediana comparables": fmt_metric_value(
                            meta.kind, i.peer_median, q.currency
                        ),
                        "Nº comparables": i.n_peers,
                        "Mejor es": "más bajo" if meta.better == "lower" else "más alto",
                        "Percentil (0–100)": pct,
                    }
                )
            st.dataframe(
                pd.DataFrame(records),
                hide_index=True,
                width="stretch",
                column_config={
                    "Percentil (0–100)": st.column_config.ProgressColumn(
                        min_value=0, max_value=100, format="%d"
                    )
                },
            )
            valid = [i.percentile * 100 for i in c.inputs if i.percentile is not None]
            if valid:
                terms = " + ".join(fmt_number(v, 0) for v in valid)
                st.markdown(
                    f"Puntuación = media de percentiles = ({terms}) / {len(valid)} = "
                    f"**{c.score:.0f}**"
                )
            else:
                st.caption("Sin datos suficientes: este componente no entra en el total.")

    st.markdown("#### Argumentos que salen de los datos")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**A favor** (métricas en el mejor 25 % de sus comparables)")
        for t in res.pros or ["Ninguna métrica destaca por arriba."]:
            st.markdown(f"- {t}")
    with col2:
        st.markdown("**En contra** (métricas en el peor 25 % de sus comparables)")
        for t in res.cons or ["Ninguna métrica destaca por abajo."]:
            st.markdown(f"- {t}")

    with st.expander("Limitaciones del score"):
        st.markdown(
            "- Es **relativo**: compara con un universo de ~140 grandes empresas. Un 70 en un "
            "sector caro sigue pudiendo ser caro en términos absolutos.\n"
            "- Usa datos de una sola fuente (Yahoo), con sus errores (p. ej. ajustes de splits).\n"
            "- El crecimiento es del último trimestre interanual: muy ruidoso.\n"
            "- El momentum describe el pasado; no predice el futuro.\n"
            "- Los pesos son una decisión subjetiva: cambiarlos cambia el resultado.\n"
            "- **Un score alto no es una recomendación de compra** ni uno bajo de venta: es un "
            "resumen para orientar tu propio análisis."
        )
