"""Comparador: 2–4 empresas lado a lado (métricas, score y evolución del precio)."""

import pandas as pd
import streamlit as st

from components.charts import normalized_chart
from components.common import disclaimer, market_data, show_error, watchlist_repo
from components.universe_panel import universe_panel
from radar.data.markets import is_valid_format, normalize_ticker
from radar.errors import RadarError
from radar.formatting import fmt_metric_value
from radar.fundamentals.metrics import EQUITY_METRICS, PRICE_METRICS
from radar.fundamentals.sector import country_es, sector_es
from radar.scoring.score import COMPONENTS, DEFAULT_WEIGHTS, score_company
from radar.scoring.screen import best_by_metric
from radar.universe import company_row

st.title("⚖️ Comparador")
disclaimer()

svc = market_data()
snap = universe_panel("comparador")

options = list(dict.fromkeys(
    watchlist_repo().tickers() + (snap.df["ticker"].tolist() if snap is not None else [])
))  # fmt: skip
default = [t for t in st.session_state.get("compare", []) if t in options] or options[:2]
c1, c2 = st.columns([3, 1])
picked = c1.multiselect("Empresas (2–4)", options, default=default, max_selections=4)
extra = c2.text_input("Otro ticker", placeholder="p. ej. ENG.MC")
if extra:
    t = normalize_ticker(extra)
    if is_valid_format(t) and t not in picked and len(picked) < 4:
        picked.append(t)
st.session_state["compare"] = picked

if len(picked) < 2:
    st.info("Elige al menos dos empresas.")
    st.stop()

rows: dict[str, dict] = {}
for t in picked:
    try:
        rows[t] = company_row(svc, t)
    except RadarError as e:
        show_error(e)
if len(rows) < 2:
    st.stop()

# --- Evolución del precio -------------------------------------------------------
st.subheader("Evolución del precio (base 100)")
rng = st.segmented_control("Rango", ["6M", "1A", "2A", "5A"], default="1A", key="cmp_range")
series = {}
for t in rows:
    try:
        series[t] = svc.get_history(t, rng or "1A").data["Close"]
    except RadarError as e:
        show_error(e)
if len(series) >= 2:
    st.plotly_chart(normalized_chart(series, log_scale=rng == "5A"), width="stretch")
    st.caption(
        "Cada serie empieza en 100 en la primera fecha común: así se compara la evolución "
        "aunque los precios (y monedas) sean muy distintos. Precios ajustados por dividendos "
        "y splits, en la moneda de cada valor (no incluye el efecto divisa). Fuente: Yahoo Finance."
    )

# --- Tabla lado a lado ------------------------------------------------------------
st.subheader("Métricas lado a lado")
scores = {}
if snap is not None:
    weights = {k: st.session_state.get(f"w_{k}", v * 100) / 100 for k, v in DEFAULT_WEIGHTS.items()}
    scores = {t: score_company(r, snap.df, weights) for t, r in rows.items()}

table, best_col = [], []
if scores:
    vals = {t: s.total for t, s in scores.items()}
    table.append(
        {
            "Grupo": "Score",
            "Métrica": "Score total",
            **{t: "n/d" if v is None else f"{v:.0f}" for t, v in vals.items()},
        }
    )
    best_col.append(best_by_metric(vals, "higher"))
    for c in COMPONENTS:
        vals = {t: next(x.score for x in s.components if x.key == c.key) for t, s in scores.items()}
        table.append(
            {
                "Grupo": "Score",
                "Métrica": c.label,
                **{t: "n/d" if v is None else f"{v:.0f}" for t, v in vals.items()},
            }
        )
        best_col.append(best_by_metric(vals, "higher"))

table.append(
    {
        "Grupo": "Perfil",
        "Métrica": "Sector",
        **{t: sector_es(r.get("sector")) for t, r in rows.items()},
    }
)
best_col.append(None)
table.append(
    {
        "Grupo": "Perfil",
        "Métrica": "País",
        **{t: country_es(r.get("country")) for t, r in rows.items()},
    }
)
best_col.append(None)
for m in EQUITY_METRICS + PRICE_METRICS:
    vals = {t: r.get(m.key) for t, r in rows.items()}
    table.append(
        {
            "Grupo": m.group,
            "Métrica": m.label,
            **{t: fmt_metric_value(m.kind, v, rows[t].get("currency")) for t, v in vals.items()},
        }
    )
    # Importes absolutos y "por acción" no son comparables entre empresas
    best_col.append(best_by_metric(vals, m.better) if m.kind in ("pct", "ratio") else None)

df = pd.DataFrame(table)
df["Mejor dato"] = [b or "—" for b in best_col]
st.dataframe(df, hide_index=True, width="stretch", height=35 * (len(df) + 1) + 3)
st.caption(
    "'Mejor dato' indica qué empresa tiene el valor más favorable en cada métrica según su "
    "dirección (PER más bajo, ROE más alto...), sin tener en cuenta el sector: compara "
    "empresas de sectores distintos con cautela. Importes en la moneda de cada empresa."
)
