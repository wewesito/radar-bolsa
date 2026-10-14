"""Sección de noticias con sentimiento por titular."""

import re

import streamlit as st

from components.common import market_data, show_error
from radar.errors import RadarError
from radar.formatting import fmt_dt, fmt_number
from radar.models import Quote
from radar.news.sentiment import analyze
from radar.news.sources import get_news, search_name

ICON = {"positivo": "▲", "negativo": "▼", "neutral": "●"}
_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|<>~$])")


def md_escape(text: str) -> str:
    """Escapa los caracteres con significado en Markdown de un texto externo."""
    return _MD_SPECIAL.sub(r"\\\1", text)


def render_news(ticker: str, q: Quote) -> None:
    try:
        items = get_news(market_data().cache, ticker, q.name)
    except RadarError as e:
        show_error(e)
        return
    if not items:
        st.info("No se han encontrado noticias recientes.")
        return

    scored = [(i, analyze(i.title)) for i in items]
    counts = {lab: sum(s.label == lab for _, s in scored) for lab in ICON}
    avg = sum(s.score for _, s in scored) / len(scored)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("▲ Positivas", counts["positivo"])
    c2.metric("● Neutras", counts["neutral"])
    c3.metric("▼ Negativas", counts["negativo"])
    c4.metric("Tono medio (−1 a +1)", fmt_number(avg, 2))
    providers = sorted({i.provider for i in items})
    st.caption(
        f"Búsqueda: «{search_name(ticker, q.name)}» con términos financieros, últimos 30 días · "
        f"fuente: {', '.join(providers)} · se actualiza cada 30 min · horas de Madrid."
    )

    for item, s in scored:
        when = fmt_dt(item.published) if item.published else "sin fecha"
        # Titulares de terceros: sin HTML y con Markdown escapado (un '[' rompería el enlace)
        st.markdown(f"{ICON[s.label]} [{md_escape(item.title)}]({item.url})")
        words = [f"+{w}" for w in s.positives] + [f"−{w}" for w in s.negatives]
        detail = f" · sentimiento {s.label} ({s.score:+.2f}): {', '.join(words)}" if words else ""
        st.caption(f"{md_escape(item.publisher)} · {when}{detail}")

    with st.expander("Cómo se calcula el sentimiento y sus limitaciones"):
        st.markdown(
            "- Se cuentan palabras de dos listas (positivas y negativas) de vocabulario "
            "financiero en el **titular**; 'no' o 'sin' justo antes invierten el signo.\n"
            "- Tono = (positivas − negativas) / (positivas + negativas). Entre −0,2 y +0,2 se "
            "considera neutral.\n"
            "- **No entiende contexto ni ironía**: 'recorta distancias con el líder' cuenta "
            "como negativo; 'la competencia se hunde' también, aunque pueda ser bueno para "
            "la empresa.\n"
            "- Muchos titulares no tienen palabras de las listas y salen neutros.\n"
            "- Las noticias que llegan a la prensa suelen estar ya reflejadas en el precio. "
            "Úsalo para enterarte de qué pasa, no como señal para operar."
        )
