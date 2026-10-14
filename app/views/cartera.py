"""Cartera simulada (paper trading): operaciones ficticias, rentabilidad y diversificación."""

from datetime import UTC, datetime

import pandas as pd
import streamlit as st

from components.charts import allocation_bars, portfolio_chart
from components.common import disclaimer, market_data, show_error, watchlist_repo
from radar import config
from radar.data.markets import is_valid_format, normalize_ticker
from radar.db.database import Database
from radar.db.trades import TradesRepo
from radar.errors import RadarError
from radar.formatting import fmt_big, fmt_dt, fmt_number, fmt_pct, fmt_price
from radar.fundamentals.sector import country_es, sector_es
from radar.portfolio.calc import (
    PortfolioError,
    Trade,
    allocation,
    build_positions,
    effective_positions,
    shadow_benchmark,
    summarize,
    value_series,
)
from radar.portfolio.market import (
    BENCHMARKS,
    fx_series_to_eur,
    fx_to_eur_on,
    price_on,
    range_for,
)

st.title("💼 Cartera simulada")
disclaimer()
st.info(
    "Todas las operaciones son **ficticias**: la app no se conecta a ningún bróker ni mueve "
    "dinero. Sirve para practicar y medir tus decisiones sin arriesgar nada.",
    icon="🧪",
)

svc = market_data()


@st.cache_resource
def trades_repo() -> TradesRepo:
    return TradesRepo(Database(config.DB_PATH))


repo = trades_repo()

# --- Registrar operación --------------------------------------------------------
with st.expander("➕ Registrar operación", expanded=not repo.list()):
    c1, c2, c3 = st.columns(3)
    options = watchlist_repo().tickers()
    pick = c1.selectbox("Ticker (watchlist)", options or ["—"], key="trade_pick")
    typed = c1.text_input("…u otro ticker", key="trade_typed", placeholder="p. ej. IWDA.AS")
    ticker = normalize_ticker(typed) if typed else (pick if options else "")
    side = c2.segmented_control("Operación", ["Compra", "Venta"], default="Compra", key="side")
    trade_date = c3.date_input(
        "Fecha",
        value=datetime.now(UTC).date(),
        format="DD/MM/YYYY",
        max_value=datetime.now(UTC).date(),
    )

    suggested, currency, error = None, None, None
    if ticker and is_valid_format(ticker):
        try:
            currency = svc.get_quote(ticker).currency or "EUR"
            suggested = price_on(svc, ticker, trade_date)
        except RadarError as e:
            error = e
    if error:
        show_error(error)

    c1, c2, c3 = st.columns(3)
    qty = c1.number_input("Cantidad (acciones)", min_value=0.0, value=10.0, step=1.0)
    price = c2.number_input(
        f"Precio por acción ({currency or '—'})",
        min_value=0.0,
        value=round(suggested, 4) if suggested else 0.0,
        step=0.01,
        format="%.4f",
        key=f"price_{ticker}_{trade_date}",  # se reinicia al cambiar ticker o fecha
        help="Se rellena con el cierre de esa fecha (o el precio actual si es hoy). Puedes "
        "cambiarlo para simular el precio exacto que habrías obtenido.",
    )
    fee = c3.number_input(
        f"Comisión ({currency or '—'})",
        min_value=0.0,
        value=0.0,
        step=1.0,
        help="Lo que cobraría el bróker. Inclúyela: a largo plazo pesa.",
    )
    note = st.text_input(
        "Nota (opcional)",
        placeholder="¿Por qué haces esta operación?",
        help="Apuntar el motivo te permitirá revisar después si tu "
        "razonamiento era bueno, independientemente del resultado.",
    )

    if st.button("Registrar", type="primary", disabled=not (ticker and currency and qty and price)):
        try:
            fx = fx_to_eur_on(svc, currency, trade_date)
            repo.add(
                Trade(
                    ticker,
                    "BUY" if side == "Compra" else "SELL",
                    qty,
                    price,
                    fee,
                    currency,
                    trade_date,
                    fx,
                    note=note or None,
                )
            )
            st.success(f"{side} de {fmt_number(qty, 2)} {ticker} registrada.")
            st.rerun()
        except PortfolioError as e:
            st.error(str(e), icon="🚫")
        except RadarError as e:
            show_error(e)

trades = repo.list()
if not trades:
    st.caption("Aún no hay operaciones. Registra tu primera compra ficticia arriba.")
    st.stop()

# --- Valoración actual --------------------------------------------------------------
positions, realized = build_positions(trades)
tickers = sorted({t.ticker for t in trades})
quotes = svc.get_quotes(tickers)
prices = {t: q.price for t, q in quotes.items() if not isinstance(q, RadarError)}
currencies = {t.currency for t in trades}
fx_now = {}
for cur in currencies:
    try:
        fx_now[cur] = fx_to_eur_on(svc, cur, datetime.now(UTC).date())
    except RadarError as e:
        show_error(e)
summary, pos_df = summarize(trades, prices, fx_now)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Valor actual", fmt_big(summary.market_value_eur, "EUR"))
c2.metric(
    "Ganancia/pérdida latente",
    fmt_big(summary.unrealized_eur, "EUR"),
    help="De las posiciones abiertas: valor actual − coste FIFO (incl. comisiones).",
)
c3.metric(
    "Ganancia/pérdida realizada",
    fmt_big(summary.realized_eur, "EUR"),
    help="De las ventas ya hechas, calculada con FIFO.",
)
c4.metric(
    "Rentabilidad total",
    fmt_pct(summary.total_return, 2, signed=True),
    help="(Latente + realizada) / total invertido en compras. Simple, pero no tiene "
    "en cuenta cuándo entró el dinero: para eso mira la comparación con el índice.",
)
st.caption(
    f"Valorado en euros con precios y tipos de cambio de Yahoo Finance a las "
    f"{fmt_dt(datetime.now(UTC), with_date=False)} (hora de Madrid; los precios pueden llevar "
    "~15 min de retraso). Incluye el efecto divisa."
)

# --- Posiciones -------------------------------------------------------------------
st.subheader("Posiciones abiertas")
if pos_df.empty:
    st.caption("No tienes posiciones abiertas (todo vendido).")
else:
    meta = {}
    for t in pos_df["ticker"]:
        try:
            f = svc.get_fundamentals(t)
            is_fund = f.quote_type in ("ETF", "MUTUALFUND")
            meta[t] = (
                f.name,
                "ETF / fondo" if is_fund else sector_es(f.sector),
                "ETF / fondo" if is_fund else country_es(f.country),
            )
        except RadarError:
            meta[t] = (t, "Desconocido", "Desconocido")
    pos_df["name"] = pos_df["ticker"].map(lambda t: meta[t][0])
    pos_df["sector"] = pos_df["ticker"].map(lambda t: meta[t][1])
    pos_df["country"] = pos_df["ticker"].map(lambda t: meta[t][2])
    view = pd.DataFrame(
        {
            "Ticker": pos_df["ticker"],
            "Nombre": pos_df["name"],
            "Acciones": pos_df["quantity"],
            "Precio medio": [
                fmt_price(p, c)
                for p, c in zip(pos_df["avg_price"], pos_df["currency"], strict=True)
            ],
            "Precio actual": [
                fmt_price(p, c) for p, c in zip(pos_df["price"], pos_df["currency"], strict=True)
            ],
            "Valor (€)": pos_df["value_eur"],
            "Peso %": pos_df["weight"] * 100,
            "G/P (€)": pos_df["pnl_eur"],
            "G/P %": pos_df["pnl_pct"] * 100,
        }
    )
    st.dataframe(
        view,
        hide_index=True,
        width="stretch",
        column_config={
            "Acciones": st.column_config.NumberColumn(format="%.2f"),
            "Valor (€)": st.column_config.NumberColumn(format="%.2f"),
            "Peso %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
            "G/P (€)": st.column_config.NumberColumn(format="%+.2f"),
            "G/P %": st.column_config.NumberColumn(format="%+.2f"),
        },
    )
    st.caption(
        "Precio medio = coste FIFO por acción de las acciones que quedan (incl. comisiones)."
    )

# --- Evolución vs índice ---------------------------------------------------------
st.subheader("Evolución frente a un índice de referencia")
bench_name = st.selectbox("Índice de referencia", list(BENCHMARKS))
start = min(t.trade_date for t in trades)
rkey = range_for(start)
try:
    closes = {t: svc.get_history(t, rkey).data["Close"] for t in tickers}
    fx_hist = {c: fx_series_to_eur(svc, c, rkey) for c in currencies if c != "EUR"}
    vs = value_series(trades, closes, fx_hist)
    shadow = shadow_benchmark(trades, svc.get_history(BENCHMARKS[bench_name], rkey).data["Close"])
except RadarError as e:
    show_error(e)
else:
    st.plotly_chart(portfolio_chart(vs, shadow, bench_name.split(" (")[0]), width="stretch")
    if not shadow.empty:
        mine, bench = vs["value"].iloc[-1], shadow.iloc[-1]
        st.markdown(
            f"Con las mismas aportaciones en las mismas fechas, el índice valdría hoy "
            f"**{fmt_big(bench, 'EUR')}** frente a los **{fmt_big(mine, 'EUR')}** "
            f"de tu cartera: diferencia de **{fmt_big(mine - bench, 'EUR')}**."
        )
    st.caption(
        "Cartera sombra: cada euro que metes o sacas de tu cartera se mete o saca ese mismo "
        "día en el índice, para que la comparación sea justa aunque hayas invertido poco a "
        "poco. Las ventas que ya cerraste dejan de contar en 'Tu cartera' (el dinero sale); "
        "en la sombra se retira el mismo importe. Fuente: Yahoo Finance."
    )

# --- Diversificación -------------------------------------------------------------
if not pos_df.empty:
    st.subheader("Diversificación")
    n_eff = effective_positions(pos_df["weight"])
    st.markdown(
        f"Tienes **{len(pos_df)}** posiciones, pero por cómo se reparte el dinero equivalen a "
        f"**{fmt_number(n_eff, 1)}** posiciones de igual peso (número efectivo = 1 / Σ peso²)."
    )
    if pos_df["weight"].max() > 0.25:
        top = pos_df.loc[pos_df["weight"].idxmax()]
        st.caption(
            f"ℹ️ {top['ticker']} pesa un {fmt_pct(top['weight'])} de la cartera: lo que le pase "
            "a esa empresa domina tu resultado. Es un dato, no un juicio: decide tú si es lo "
            "que buscas."
        )
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Por posición**")
        st.plotly_chart(allocation_bars(pos_df.set_index("ticker")["weight"]), width="stretch")
    with c2:
        st.markdown("**Por sector**")
        st.plotly_chart(allocation_bars(allocation(pos_df, "sector")), width="stretch")
    with c3:
        st.markdown("**Por país**")
        st.plotly_chart(allocation_bars(allocation(pos_df, "country")), width="stretch")

# --- Operaciones y ventas realizadas ----------------------------------------------
st.subheader("Historial de operaciones")
hist = pd.DataFrame(
    [
        {
            "id": t.id,
            "Fecha": t.trade_date.strftime("%d/%m/%Y"),
            "Ticker": t.ticker,
            "Operación": "Compra" if t.side == "BUY" else "Venta",
            "Cantidad": t.quantity,
            "Precio": fmt_price(t.price, t.currency),
            "Comisión": fmt_price(t.fee, t.currency),
            "Importe (€)": t.gross_eur,
            "Tipo de cambio": t.fx_to_eur,
            "Nota": t.note or "",
        }
        for t in trades
    ]
)
event = st.dataframe(
    hist,
    hide_index=True,
    width="stretch",
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        "id": None,
        "Importe (€)": st.column_config.NumberColumn(format="%.2f"),
        "Tipo de cambio": st.column_config.NumberColumn(
            format="%.4f", help="Euros por unidad de la moneda del valor ese día."
        ),
    },
)
if event.selection.rows and st.button("🗑️ Borrar operación seleccionada"):
    try:
        repo.delete(int(hist.iloc[event.selection.rows[0]]["id"]))
        st.rerun()
    except PortfolioError as e:
        st.error(f"No se puede borrar: {e}")

if realized:
    st.subheader("Ventas realizadas (FIFO)")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Fecha venta": r.sell_date.strftime("%d/%m/%Y"),
                    "Ticker": r.ticker,
                    "Cantidad": r.quantity,
                    "Importe venta (€)": r.proceeds_eur,
                    "Coste FIFO (€)": r.cost_eur,
                    "Ganancia/pérdida (€)": r.pnl_eur,
                    "Días desde la compra": r.holding_days,
                }
                for r in realized
            ]
        ),
        hide_index=True,
        width="stretch",
        column_config={
            c: st.column_config.NumberColumn(format="%.2f")
            for c in ("Importe venta (€)", "Coste FIFO (€)", "Ganancia/pérdida (€)")
        },
    )
    st.caption(
        "FIFO: se venden primero las acciones compradas antes, como exige la normativa fiscal "
        "española para valores homogéneos. Orientativo: la fiscalidad real depende de tu "
        "situación (ver la sección Aprende)."
    )
