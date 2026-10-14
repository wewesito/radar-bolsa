"""Punto de entrada: configura la app y define la navegación entre páginas."""

import streamlit as st

from radar import DISCLAIMER

st.set_page_config(page_title="Radar Bolsa", page_icon="📈", layout="wide")

with st.sidebar:
    st.warning(DISCLAIMER, icon="⚠️")

pages = [
    st.Page("views/watchlist.py", title="Watchlist", icon="👀", default=True),
    st.Page("views/empresa.py", title="Empresa", icon="🏢"),
    st.Page("views/screener.py", title="Screener", icon="🔎"),
    st.Page("views/comparador.py", title="Comparador", icon="⚖️"),
]
st.navigation(pages).run()
