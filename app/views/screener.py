"""Screener: filtrar el universo de referencia por métricas y score."""

import pandas as pd
import streamlit as st

from components.common import disclaimer, watchlist_repo
from components.universe_panel import universe_panel
from radar.fundamentals.sector import SECTOR_ES, sector_es
from radar.scoring.score import DEFAULT_WEIGHTS
from radar.scoring.screen import Filter, apply_filters, score_universe

st.title("🔎 Screener")
disclaimer()
st.caption(
    "Filtra las empresas del universo de referencia. Un filtro no es una recomendación: "
    "sirve para acotar dónde mirar con más detalle."
)

snap = universe_panel("screener")
if snap is None:
    st.stop()


@st.cache_data(show_spinner="Calculando el score de todo el universo…")
def scored(built_at: str, weights: tuple[tuple[str, float], ...]) -> pd.DataFrame:
    # built_at y weights son la clave de la caché: si cambian, se recalcula.
    return score_universe(snap.df, dict(weights))


weights = {k: st.session_state.get(f"w_{k}", v * 100) / 100 for k, v in DEFAULT_WEIGHTS.items()}
df = scored(snap.built_at.isoformat(), tuple(sorted(weights.items())))

# --- Filtros ------------------------------------------------------------------
with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    regions = c1.multiselect("Región", sorted(df["region"].dropna().unique()))
    sector_labels = c2.multiselect(
        "Sector", sorted(sector_es(s) for s in df["sector"].dropna().unique())
    )
    min_score = c3.slider("Score mínimo", 0, 100, 0, 5)

    st.caption("Deja un campo vacío para no filtrar por esa métrica.")
    c1, c2, c3, c4 = st.columns(4)
    max_pe = c1.number_input("PER máximo", min_value=0.0, value=None, step=1.0)
    min_roe = c2.number_input("ROE mínimo (%)", value=None, step=1.0)
    min_div = c3.number_input("Dividendo mínimo (%)", min_value=0.0, value=None, step=0.5)
    max_de = c4.number_input("Deuda/patrimonio máx.", min_value=0.0, value=None, step=0.1)
    c1, c2, c3, c4 = st.columns(4)
    min_growth = c1.number_input("Crec. ventas mínimo (%)", value=None, step=1.0)
    min_ret = c2.number_input("Rentab. 12 m mínima (%)", value=None, step=5.0)
    max_vol = c3.number_input("Volatilidad máx. (%)", min_value=0.0, value=None, step=5.0)
    max_mdd = c4.number_input(
        "Caída máx. 1 año (%) ≤",
        min_value=0.0,
        value=None,
        step=5.0,
        help="Por ejemplo 20 = solo empresas que no han caído más de un "
        "20 % desde un máximo en el último año.",
    )

filters: list[Filter] = []
if min_score:
    filters.append(Filter("score", ">=", min_score))
for value, key, op, scale in [
    (max_pe, "pe_trailing", "<=", 1),
    (min_roe, "roe", ">=", 100),
    (min_div, "dividend_yield", ">=", 100),
    (max_de, "debt_to_equity", "<=", 1),
    (min_growth, "revenue_growth", ">=", 100),
    (min_ret, "ret_12m", ">=", 100),
    (max_vol, "vol_1y", "<=", 100),
]:
    if value is not None:
        filters.append(Filter(key, op, value / scale))
if max_mdd is not None:
    filters.append(Filter("mdd_1y", ">=", -max_mdd / 100))  # caída guardada en negativo

es_to_en = {v: k for k, v in SECTOR_ES.items()}
sectors = [es_to_en.get(s, s) for s in sector_labels]
result = apply_filters(df, filters, sectors, regions).sort_values("score", ascending=False)

# --- Resultados ----------------------------------------------------------------
st.markdown(f"**{len(result)}** de {len(df)} empresas cumplen los filtros.")
view = result.assign(sector=result["sector"].map(sector_es))[
    [
        "ticker",
        "name",
        "sector",
        "region",
        "score",
        "score_valuation",
        "score_health",
        "score_growth",
        "score_momentum",
        "score_risk",
        "pe_trailing",
        "roe",
        "dividend_yield",
        "debt_to_equity",
        "revenue_growth",
        "ret_12m",
        "vol_1y",
    ]
]
pct_cols = ["roe", "dividend_yield", "revenue_growth", "ret_12m", "vol_1y"]
view[pct_cols] = view[pct_cols] * 100
score_cfg = {"min_value": 0, "max_value": 100, "format": "%.0f"}
event = st.dataframe(
    view,
    hide_index=True,
    width="stretch",
    on_select="rerun",
    selection_mode="multi-row",
    key="screener_table",
    column_config={
        "ticker": "Ticker",
        "name": st.column_config.TextColumn("Nombre", width="medium"),
        "sector": "Sector",
        "region": "Región",
        "score": st.column_config.ProgressColumn("Score", **score_cfg),
        "score_valuation": st.column_config.NumberColumn("Valor.", format="%.0f"),
        "score_health": st.column_config.NumberColumn("Salud", format="%.0f"),
        "score_growth": st.column_config.NumberColumn("Crec.", format="%.0f"),
        "score_momentum": st.column_config.NumberColumn("Mom.", format="%.0f"),
        "score_risk": st.column_config.NumberColumn(
            "Riesgo", format="%.0f", help="Más alto = menos riesgo"
        ),
        "pe_trailing": st.column_config.NumberColumn("PER", format="%.1f"),
        "roe": st.column_config.NumberColumn("ROE %", format="%.1f"),
        "dividend_yield": st.column_config.NumberColumn("Div. %", format="%.2f"),
        "debt_to_equity": st.column_config.NumberColumn("D/E", format="%.2f"),
        "revenue_growth": st.column_config.NumberColumn("Crec. ventas %", format="%.1f"),
        "ret_12m": st.column_config.NumberColumn("Rent. 12 m %", format="%.1f"),
        "vol_1y": st.column_config.NumberColumn("Volat. %", format="%.1f"),
    },
)
st.caption(
    "Score y componentes 0–100 (50 = mediana de los comparables). Selecciona filas para "
    "añadirlas a la watchlist o compararlas. Datos: foto del universo (Yahoo Finance)."
)

picked = view.iloc[event.selection.rows]["ticker"].tolist() if event.selection.rows else []
c1, c2 = st.columns(2)
if c1.button(f"➕ Añadir a la watchlist ({len(picked)})", disabled=not picked):
    repo = watchlist_repo()
    names = dict(zip(result["ticker"], result["name"], strict=True))
    added = [t for t in picked if repo.add(t, names.get(t, t))]
    st.success(f"Añadidas: {', '.join(added) or 'ninguna (ya estaban)'}")
if c2.button(
    "⚖️ Comparar seleccionadas",
    disabled=not 2 <= len(picked) <= 4,
    help="Selecciona entre 2 y 4 empresas.",
):
    st.session_state["compare"] = picked
    st.switch_page("views/comparador.py")
