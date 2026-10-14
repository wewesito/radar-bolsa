"""Punto de entrada: configura la app y define la navegación entre páginas."""

import streamlit as st

from components.common import alerts_repo
from radar import DISCLAIMER

st.set_page_config(page_title="Radar Bolsa", page_icon="📈", layout="wide")

with st.sidebar:
    st.warning(DISCLAIMER, icon="⚠️")
    unseen = sum(not e.seen for e in alerts_repo().events())
    if unseen:
        st.info(f"🔔 {unseen} aviso(s) de alertas sin ver", icon="🔔")

pages = [
    st.Page("views/watchlist.py", title="Watchlist", icon="👀", default=True),
    st.Page("views/empresa.py", title="Empresa", icon="🏢"),
    st.Page("views/screener.py", title="Screener", icon="🔎"),
    st.Page("views/comparador.py", title="Comparador", icon="⚖️"),
    st.Page("views/cartera.py", title="Cartera simulada", icon="💼"),
    st.Page("views/alertas.py", title="Alertas", icon="🔔"),
]
st.navigation(pages).run()
