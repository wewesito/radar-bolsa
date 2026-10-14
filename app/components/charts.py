"""Gráficos Plotly de precio + volumen."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from radar.config import DISPLAY_TZ
from radar.models import PriceHistory

# Azul (sube) / rojo (baja): distinguibles con daltonismo, a diferencia de verde/rojo.
UP = "#2a78d6"
DOWN = "#e34948"
LINE = "#2a78d6"


def missing_days(index: pd.DatetimeIndex) -> list[str]:
    """Días naturales sin datos (fines de semana y festivos) entre el primero y el último."""
    days = pd.DatetimeIndex(index.normalize().unique())
    full = pd.date_range(days.min(), days.max(), freq="D")
    return [d.strftime("%Y-%m-%d") for d in full.difference(days)]


def price_chart(
    history: PriceHistory, kind: str = "Velas", intraday: bool = False, log_scale: bool = False
) -> go.Figure:
    df = history.data.copy()
    # Mostramos en hora de Madrid. Sin esto, la vela diaria del día 14 saldría como
    # "13 a las 22:00" (medianoche de Madrid expresada en UTC).
    df.index = df.index.tz_convert(DISPLAY_TZ).tz_localize(None)

    # Intradía: eje por categorías (una posición por vela) para que no haya huecos nocturnos.
    x = df.index.strftime("%d/%m %H:%M") if intraday else df.index

    up = df["Close"] >= df["Open"]
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, row_heights=[0.78, 0.22], vertical_spacing=0.03
    )

    if kind == "Velas":
        fig.add_trace(
            go.Candlestick(
                x=x,
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                increasing=dict(line=dict(color=UP, width=1), fillcolor=UP),
                decreasing=dict(line=dict(color=DOWN, width=1), fillcolor=DOWN),
                name="Precio",
            ),
            row=1,
            col=1,
        )
    else:
        fig.add_trace(
            go.Scatter(
                x=x,
                y=df["Close"],
                mode="lines",
                line=dict(color=LINE, width=2),
                name="Cierre",
                hovertemplate="%{y:,.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )

    fig.add_trace(
        go.Bar(
            x=x,
            y=df["Volume"],
            marker_color=[UP if u else DOWN for u in up],
            marker_line_width=0,
            opacity=0.6,
            name="Volumen",
            hovertemplate="Vol. %{y:,.0f}<extra></extra>",
        ),
        row=2,
        col=1,
    )

    if intraday:
        fig.update_xaxes(type="category", nticks=8)
    elif history.interval == "1d" and len(df) > 1:
        fig.update_xaxes(rangebreaks=[dict(values=missing_days(df.index))])

    fig.update_layout(
        height=520,
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False,
        hovermode="x unified",
        xaxis_rangeslider_visible=False,
        separators=",.",  # decimales con coma, miles con punto
    )
    # Escala log: la misma distancia vertical = el mismo % de variación.
    fig.update_yaxes(title_text="Precio", type="log" if log_scale else "linear", row=1, col=1)
    fig.update_yaxes(title_text="Volumen", row=2, col=1)
    return fig
