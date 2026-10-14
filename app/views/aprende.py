"""Sección educativa: glosario, conceptos, calculadoras, perfil de riesgo y fiscalidad."""

import streamlit as st

from components.charts import compound_chart
from components.common import disclaimer
from radar.education.concepts import CONCEPTS, RISK_QUESTIONS, TAX_ES, risk_profile
from radar.education.finance_math import (
    compound_growth,
    real_return,
    rule_of_72,
    savings_tax,
    years_to_double,
)
from radar.education.glossary import ENTRIES, categories
from radar.formatting import fmt_big, fmt_number, fmt_pct
from radar.news.sentiment import normalize  # minúsculas y sin tildes

st.title("📖 Aprende")
disclaimer()

SECTIONS = ["Glosario", "Conceptos básicos", "Interés compuesto", "Perfil de riesgo", "Fiscalidad"]
section = st.segmented_control("Sección", SECTIONS, default=SECTIONS[0], key="learn") or SECTIONS[0]

if section == "Glosario":
    st.caption(
        "Todas las métricas e indicadores que usa la app: qué son, cómo se calculan, cómo "
        "leerlos y sus limitaciones. Las referencias de 'bueno' o 'malo' son orientativas: "
        "dependen del sector y del momento."
    )
    c1, c2 = st.columns([2, 1])
    query = normalize(c1.text_input("Buscar", placeholder="PER, RSI, deuda, dividendo…").strip())
    cat = c2.selectbox("Categoría", ["Todas", *categories()])
    pool = [e for e in ENTRIES if cat == "Todas" or e.category == cat]
    # Primero por nombre del término; si no hay nada, también en la descripción.
    shown = [e for e in pool if not query or query in normalize(f"{e.term} {e.key}")]
    if query and not shown:
        shown = [e for e in pool if query in normalize(e.what)]
    if not shown:
        st.info("Nada coincide con la búsqueda.")
    for e in shown:
        with st.expander(f"**{e.term}** · {e.category}"):
            st.markdown(
                f"{e.what}\n\n"
                f"**Cómo se calcula:** {e.formula}\n\n"
                f"**Cómo se suele leer:** {e.reading}\n\n"
                f"**Limitaciones:** {e.limits}"
            )

elif section == "Conceptos básicos":
    for title, body in CONCEPTS.items():
        with st.expander(f"**{title}**", expanded=title == "Diversificación"):
            st.markdown(body)

elif section == "Interés compuesto":
    st.caption("Juega con los valores: el objetivo es ver el efecto del tiempo y de los costes.")
    c1, c2, c3 = st.columns(3)
    initial = c1.number_input("Inversión inicial (€)", 0, 1_000_000, 1_000, 500)
    monthly = c2.number_input("Aportación mensual (€)", 0, 100_000, 100, 25)
    years = c3.slider("Años", 1, 50, 25)
    c1, c2, c3, c4 = st.columns(4)
    ret = c1.slider("Rentabilidad bruta anual (%)", 0.0, 12.0, 6.0, 0.5) / 100
    fee_a = c2.slider("Comisión A (%)", 0.0, 3.0, 0.2, 0.05) / 100
    fee_b = c3.slider("Comisión B (%)", 0.0, 3.0, 1.5, 0.05) / 100
    infl = c4.slider("Inflación (%)", 0.0, 6.0, 2.0, 0.5) / 100

    a = compound_growth(initial, monthly, ret, years, fee_a)
    b = compound_growth(initial, monthly, ret, years, fee_b)
    label_a, label_b = f"Comisión {fmt_pct(fee_a, 2)}", f"Comisión {fmt_pct(fee_b, 2)}"
    st.plotly_chart(
        compound_chart({label_a: a["value"], label_b: b["value"]}, a["contributed"]),
        width="stretch",
    )
    final_a, final_b, put = a["value"].iloc[-1], b["value"].iloc[-1], a["contributed"].iloc[-1]
    c1, c2, c3 = st.columns(3)
    c1.metric("Aportado", fmt_big(put, "EUR"))
    c2.metric(f"Final con {label_a.lower()}", fmt_big(final_a, "EUR"))
    c3.metric(
        f"Final con {label_b.lower()}",
        fmt_big(final_b, "EUR"),
        f"{fmt_big(final_b - final_a, 'EUR')} por costes",
        delta_color="off",
    )
    deflator = (1 + infl) ** years
    st.markdown(
        f"- La diferencia de comisiones ({fmt_pct(fee_b - fee_a, 2)} al año) se lleva "
        f"**{fmt_big(final_a - final_b, 'EUR')}** en {years} años: el interés compuesto también "
        "trabaja a favor de quien cobra la comisión.\n"
        f"- Con una inflación del {fmt_pct(infl)}, los {fmt_big(final_a, 'EUR')} equivalen a "
        f"unos **{fmt_big(final_a / deflator, 'EUR')} de hoy** (rentabilidad real ≈ "
        f"{fmt_pct(real_return(ret - fee_a, infl), 1)} al año).\n"
        + (
            f"- Regla del 72: al {fmt_pct(ret - fee_a)} neto, el dinero se duplica en unos "
            f"**{fmt_number(rule_of_72(ret - fee_a), 1)} años** "
            f"(cálculo exacto: {fmt_number(years_to_double(ret - fee_a), 1)})."
            if ret - fee_a > 0
            else ""
        )
    )
    st.caption(
        "Simulación con rentabilidad constante: en la realidad hay años muy buenos y muy malos. "
        "Las rentabilidades pasadas no garantizan las futuras. Sin impuestos."
    )

elif section == "Perfil de riesgo":
    st.caption(
        "Cuestionario orientativo para reflexionar. No sustituye al test de idoneidad que tu "
        "bróker o banco debe hacerte por normativa (MiFID), ni es una recomendación."
    )
    points = []
    for i, q in enumerate(RISK_QUESTIONS):
        labels = [o[0] for o in q.options]
        answer = st.radio(q.text, labels, index=None, key=f"risk_{i}")
        if answer is not None:
            points.append(dict(q.options)[answer])
    if len(points) == len(RISK_QUESTIONS):
        label, text = risk_profile(points)
        st.success(f"**Perfil orientativo: {label}** ({sum(points)}/15 puntos)\n\n{text}")
    else:
        st.caption(f"Respondidas {len(points)} de {len(RISK_QUESTIONS)}.")

else:  # Fiscalidad
    st.markdown(TAX_ES)
    st.markdown("#### Calculadora orientativa de la base del ahorro")
    base = st.number_input(
        "Ganancias netas + dividendos + intereses del año (€)", 0.0, 10_000_000.0, 10_000.0, 500.0
    )
    tax = savings_tax(base)
    c1, c2 = st.columns(2)
    c1.metric("Cuota aproximada", fmt_big(tax, "EUR"))
    c2.metric("Tipo medio efectivo", fmt_pct(tax / base if base else 0, 2))
    st.caption(
        "Orientativo: no tiene en cuenta retenciones ya practicadas, compensaciones de años "
        "anteriores, deducciones por doble imposición ni particularidades autonómicas o forales."
    )
