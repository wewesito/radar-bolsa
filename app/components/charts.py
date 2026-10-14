"""Gráficos Plotly: precio + volumen, análisis técnico y series comparadas."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from radar.config import DISPLAY_TZ
from radar.formatting import fmt_number
from radar.indicators.technical import Level, bollinger, macd, rsi, sma
from radar.models import PriceHistory

# Azul (sube) / rojo (baja): distinguibles con daltonismo, a diferencia de verde/rojo.
UP = "#2a78d6"
DOWN = "#e34948"
LINE = "#2a78d6"
# Paleta categórica en orden fijo (nunca se reordena): la serie 1 siempre es azul, etc.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
MUTED = "rgba(128,128,128,0.6)"
BAND_FILL = "rgba(128,128,128,0.12)"


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


def technical_chart(close: pd.Series, levels: list[Level], show_last_days: int = 365) -> go.Figure:
    """Precio + SMA 50/200 + Bollinger + soportes/resistencias; debajo RSI y MACD.

    Los indicadores se calculan sobre toda la serie (p. ej. 2 años) y se muestra solo el
    último tramo, para que la SMA 200 tenga valores desde el primer día visible.
    """
    ind = (
        pd.DataFrame(
            {
                "close": close,
                "sma50": sma(close, 50),
                "sma200": sma(close, 200),
                "rsi": rsi(close),
            }
        )
        .join(bollinger(close))
        .join(macd(close))
    )
    ind = ind.loc[ind.index[-1] - pd.Timedelta(days=show_last_days) :]
    ind.index = ind.index.tz_convert(DISPLAY_TZ).tz_localize(None)
    x = ind.index

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.6, 0.2, 0.2],
        vertical_spacing=0.04,
        subplot_titles=("Precio, medias y bandas de Bollinger", "RSI (14)", "MACD (12, 26, 9)"),
    )
    # Bandas de Bollinger como zona sombreada (primero, para que quede debajo)
    fig.add_trace(
        go.Scatter(
            x=x,
            y=ind["upper"],
            line=dict(color=MUTED, width=1),
            name="Bollinger sup.",
            hovertemplate="%{y:,.2f}",
        ),
        1,
        1,
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=ind["lower"],
            line=dict(color=MUTED, width=1),
            fill="tonexty",
            fillcolor=BAND_FILL,
            name="Bollinger inf.",
            hovertemplate="%{y:,.2f}",
        ),
        1,
        1,
    )
    for col, name, color in (
        ("close", "Cierre", SERIES[0]),
        ("sma50", "SMA 50", SERIES[1]),
        ("sma200", "SMA 200", SERIES[2]),
    ):
        fig.add_trace(
            go.Scatter(
                x=x,
                y=ind[col],
                name=name,
                line=dict(color=color, width=2),
                hovertemplate="%{y:,.2f}",
            ),
            1,
            1,
        )
    for lv in levels:
        tag = "S" if lv.kind == "soporte" else "R"
        fig.add_hline(
            y=lv.price,
            line=dict(color=MUTED, width=1, dash="dash"),
            row=1,
            col=1,
            annotation_text=f"{tag} {fmt_number(lv.price)} ({lv.touches} toques)",
            annotation_position="top left",
            annotation_font_size=10,
        )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=ind["rsi"],
            name="RSI",
            line=dict(color=SERIES[0], width=2),
            hovertemplate="%{y:.0f}",
        ),
        2,
        1,
    )
    for level in (30, 70):
        fig.add_hline(y=level, line=dict(color=MUTED, width=1, dash="dot"), row=2, col=1)

    fig.add_trace(
        go.Bar(
            x=x,
            y=ind["hist"],
            name="Histograma MACD",
            opacity=0.5,
            marker_color=[UP if v >= 0 else DOWN for v in ind["hist"].fillna(0)],
            marker_line_width=0,
            hovertemplate="%{y:.3f}",
        ),
        3,
        1,
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=ind["macd"],
            name="MACD",
            line=dict(color=SERIES[0], width=2),
            hovertemplate="%{y:.3f}",
        ),
        3,
        1,
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=ind["signal"],
            name="Señal",
            line=dict(color=SERIES[1], width=2),
            hovertemplate="%{y:.3f}",
        ),
        3,
        1,
    )

    if len(x) > 1:
        fig.update_xaxes(rangebreaks=[dict(values=missing_days(pd.DatetimeIndex(x)))])
    fig.update_yaxes(range=[0, 100], row=2, col=1)
    fig.update_layout(
        height=760,
        margin=dict(l=10, r=10, t=30, b=10),
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.05),
        separators=",.",
    )
    fig.update_annotations(font_size=12)
    return fig


def normalized_chart(series: dict[str, pd.Series], log_scale: bool = False) -> go.Figure:
    """Varias series rebasadas a 100 en la primera fecha común (para comparar evolución)."""
    df = pd.concat(series, axis=1).dropna()
    base = df / df.iloc[0] * 100
    base.index = base.index.tz_convert(DISPLAY_TZ).tz_localize(None)
    fig = go.Figure()
    for i, col in enumerate(base.columns):
        color = SERIES[i % len(SERIES)]
        fig.add_trace(
            go.Scatter(
                x=base.index,
                y=base[col],
                name=col,
                line=dict(color=color, width=2),
                hovertemplate=f"{col}: %{{y:.1f}}<extra></extra>",
            )
        )
        # Etiqueta directa al final de cada línea (además de la leyenda)
        fig.add_annotation(
            x=base.index[-1],
            y=base[col].iloc[-1],
            text=f" {col}",
            showarrow=False,
            xanchor="left",
            font=dict(size=11),
        )
    fig.add_hline(y=100, line=dict(color=MUTED, width=1, dash="dot"))
    fig.update_layout(
        height=420,
        margin=dict(l=10, r=80, t=10, b=10),
        hovermode="x unified",
        yaxis_title="Base 100",
        yaxis_type="log" if log_scale else "linear",
        legend=dict(orientation="h", y=-0.15),
        separators=",.",
    )
    return fig


def portfolio_chart(values: pd.DataFrame, shadow: pd.Series | None, bench_name: str) -> go.Figure:
    """Valor de la cartera frente a su cartera sombra en el índice y el dinero aportado."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=values.index,
            y=values["value"],
            name="Tu cartera",
            line=dict(color=SERIES[0], width=2),
            hovertemplate="%{y:,.0f} €",
        )
    )
    if shadow is not None and not shadow.empty:
        fig.add_trace(
            go.Scatter(
                x=shadow.index,
                y=shadow,
                name=f"Mismo dinero en {bench_name}",
                line=dict(color=SERIES[1], width=2),
                hovertemplate="%{y:,.0f} €",
            )
        )
    fig.add_trace(
        go.Scatter(
            x=values.index,
            y=values["contributed"],
            name="Dinero neto aportado",
            line=dict(color=MUTED, width=1.5, dash="dash", shape="hv"),
            hovertemplate="%{y:,.0f} €",
        )
    )
    fig.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=10, b=10),
        hovermode="x unified",
        yaxis_title="€",
        legend=dict(orientation="h", y=-0.15),
        separators=",.",
    )
    return fig


def allocation_bars(weights: pd.Series) -> go.Figure:
    """Barras horizontales de pesos (una sola serie, un solo color, valores etiquetados)."""
    w = weights.sort_values()
    fig = go.Figure(
        go.Bar(
            x=w * 100,
            y=w.index,
            orientation="h",
            marker_color=SERIES[0],
            marker_line_width=0,
            text=[f"{v * 100:.1f} %".replace(".", ",") for v in w],
            textposition="outside",
            hovertemplate="%{y}: %{x:.1f} %<extra></extra>",
        )
    )
    fig.update_layout(
        height=max(160, 34 * len(w) + 40),
        margin=dict(l=10, r=40, t=10, b=10),
        xaxis=dict(range=[0, min(110, w.max() * 100 + 15)], title="% de la cartera"),
        separators=",.",
    )
    return fig


def compound_chart(series: dict[str, pd.Series], contributed: pd.Series) -> go.Figure:
    """Evolución de una inversión (una línea por escenario) frente al dinero aportado."""
    fig = go.Figure()
    for i, (name, s) in enumerate(series.items()):
        fig.add_trace(
            go.Scatter(
                x=s.index,
                y=s,
                name=name,
                line=dict(color=SERIES[i], width=2),
                hovertemplate="%{y:,.0f} €",
            )
        )
    fig.add_trace(
        go.Scatter(
            x=contributed.index,
            y=contributed,
            name="Dinero aportado",
            line=dict(color=MUTED, width=1.5, dash="dash"),
            hovertemplate="%{y:,.0f} €",
        )
    )
    fig.update_layout(
        height=380,
        margin=dict(l=10, r=10, t=10, b=10),
        hovermode="x unified",
        xaxis_title="Años",
        yaxis_title="€",
        legend=dict(orientation="h", y=-0.2),
        separators=",.",
    )
    return fig
