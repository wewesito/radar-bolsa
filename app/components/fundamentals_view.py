"""Sección de fundamentales con comparación frente a la mediana del sector."""

import pandas as pd
import streamlit as st

from components.common import source_line
from radar.formatting import fmt_big, fmt_dt, fmt_number, fmt_pct, fmt_price
from radar.fundamentals.metrics import MetricDef, metrics_for
from radar.fundamentals.sector import (
    MIN_PEERS,
    compare_metric,
    region_for,
    sector_es,
    select_peers,
)
from radar.models import Fundamentals
from radar.universe import UniverseSnapshot, fundamentals_row


def fmt_metric(m: MetricDef, value: float | None, currency: str | None) -> str:
    if value is None or pd.isna(value):
        return "n/d"
    if m.kind == "pct":
        return fmt_pct(value)
    if m.kind == "money":
        return fmt_big(value, currency)
    if m.kind == "per_share":
        return fmt_price(value, currency)
    return fmt_number(value)


def render_fundamentals(f: Fundamentals, snap: UniverseSnapshot | None) -> None:
    row = fundamentals_row(f)  # incluye métricas derivadas (FCF yield, margen FCF)
    is_fund = f.quote_type in ("ETF", "MUTUALFUND")
    info_bits = [
        b
        for b in (sector_es(f.sector) if f.sector else None, f.industry, f.country, f.fund_family)
        if b
    ]
    if info_bits:
        st.caption(" · ".join(info_bits))

    peers, scope = pd.DataFrame(), ""
    if snap is not None and not is_fund:
        peers, scope = select_peers(snap.df, f.sector, region_for(f.ticker), exclude=f.ticker)
        if len(peers) >= MIN_PEERS:
            st.markdown(f"Comparado con **{len(peers)} empresas** del grupo **{scope}**.")
        else:
            st.caption("No hay suficientes comparables del mismo sector en el universo.")

    defs = metrics_for(f.quote_type)
    groups: dict[str, list[MetricDef]] = {}
    for m in defs:
        groups.setdefault(m.group, []).append(m)

    for group, items in groups.items():
        st.markdown(f"**{group}**")
        records = []
        for m in items:
            value = row.get(m.key)
            # Las métricas "por acción" (BPA) dependen del nº de acciones: no se comparan.
            comparable = len(peers) and m.kind != "per_share"
            cmp = compare_metric(m.key, value, peers, m.better) if comparable else None
            stats = cmp.stats if cmp else None
            records.append(
                {
                    "Métrica": m.label,
                    "Valor": fmt_metric(m, value, f.currency),
                    "Mediana sector": fmt_metric(m, stats.median, f.currency) if stats else "—",
                    "Rango típico (P25–P75)": (
                        f"{fmt_metric(m, stats.p25, f.currency)} – "
                        f"{fmt_metric(m, stats.p75, f.currency)}"
                        if stats
                        else "—"
                    ),
                    "Posición": (
                        round(cmp.percentile * 100)
                        if cmp and cmp.percentile is not None and m.better
                        else None
                    ),
                    "Lectura": cmp.reading if cmp else "—",
                    "Qué es": m.help,
                }
            )
        st.dataframe(
            pd.DataFrame(records),
            hide_index=True,
            width="stretch",
            column_config={
                "Posición": st.column_config.ProgressColumn(
                    min_value=0,
                    max_value=100,
                    format="%d",
                    help="Percentil frente al sector, ya orientado: 100 = mejor que todos los "
                    "comparables en esta métrica (más barato en valoración, más margen en "
                    "rentabilidad…). Vacío en métricas descriptivas.",
                ),
                "Qué es": st.column_config.TextColumn(width="large"),
            },
        )

    notes = [source_line(f.source, f.as_of, stale=f.stale).replace("dato de", "descargado")]
    if f.last_report:
        notes.append(f"último trimestre reportado: {fmt_dt(f.last_report).split()[0]}")
    missing = sum(row.get(m.key) is None for m in defs)
    if missing:
        notes.append(
            f"{missing} métrica(s) n/d: la fuente no la publica o no aplica a este tipo de "
            "empresa (p. ej. deuda/patrimonio o margen bruto en bancos)"
        )
    st.caption(" · ".join(notes))
    if not is_fund:
        st.caption(
            "Método: se compara con la MEDIANA del sector (robusta ante valores extremos) de "
            "la misma región si hay al menos 5 empresas; si no, con el sector mundial. "
            "Una métrica 'favorable' no implica que la empresa sea una buena inversión: es "
            "una pieza más del análisis."
        )
    else:
        st.caption(
            "Los ETFs no se comparan con sectores: compara costes y patrimonio entre "
            "ETFs que repliquen el mismo índice."
        )
