"""Punto de entrada de la app Streamlit."""

import streamlit as st

from radar import DISCLAIMER

st.set_page_config(page_title="Radar Bolsa", page_icon="📈", layout="wide")
st.warning(DISCLAIMER, icon="⚠️")
st.title("Radar Bolsa")
st.write("Esqueleto en construcción.")
