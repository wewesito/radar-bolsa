"""Estado del universo de referencia y botón para (re)construirlo."""

import streamlit as st

from components.common import market_data
from radar.formatting import fmt_dt
from radar.universe import STALE_AFTER_DAYS, UniverseSnapshot, build_universe, load_universe
from radar.universe_list import UNIVERSE


def get_universe() -> UniverseSnapshot | None:
    return load_universe(market_data().cache)


def universe_panel(key: str) -> UniverseSnapshot | None:
    """Muestra la fecha de la foto del universo y permite reconstruirla."""
    snap = get_universe()
    col1, col2 = st.columns([4, 1], vertical_alignment="center")
    if snap is None:
        col1.info(
            f"Para comparar con el sector hace falta el universo de referencia "
            f"({len(UNIVERSE)} grandes empresas de España, Europa y EE. UU.). "
            "Se descarga una vez y se reutiliza.",
            icon="🌍",
        )
        label = "Construir universo"
    else:
        old = snap.age_days > STALE_AFTER_DAYS
        col1.caption(
            f"{'⚠️ ' if old else ''}Universo de referencia: {len(snap.df)} empresas · "
            f"foto del {fmt_dt(snap.built_at)} · fuente: Yahoo Finance"
            + (f" · descartados: {', '.join(snap.failed)}" if snap.failed else "")
            + (" · tiene más de una semana, conviene actualizarlo" if old else "")
        )
        label = "Actualizar universo"
    if col2.button(label, key=f"build_universe_{key}", width="stretch"):
        bar = st.progress(0.0, text="Descargando fundamentales…")
        snap = build_universe(
            market_data(), on_progress=lambda i, n: bar.progress(i / n, text=f"{i}/{n} empresas")
        )
        bar.empty()
        st.rerun()
    return snap
