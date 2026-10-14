"""Cartera simulada: posiciones FIFO, valoración en euros, histórico y cartera sombra.

Funciones puras (sin red ni BD) para poder testearlas con datos conocidos.

- FIFO (first in, first out): al vender, salen primero las acciones compradas antes.
  Es el método que exige la normativa fiscal española para valores homogéneos.
- Todo se valora en EUR con el tipo de cambio del día: la rentabilidad incluye el efecto
  divisa, que es real para un inversor en euros.
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

import numpy as np
import pandas as pd

Side = Literal["BUY", "SELL"]


class PortfolioError(ValueError):
    """Operación imposible (p. ej. vender más acciones de las que se tienen)."""


@dataclass(frozen=True)
class Trade:
    ticker: str
    side: Side
    quantity: float
    price: float  # en la moneda del valor (GBp = peniques)
    fee: float  # comisión, en la misma moneda
    currency: str
    trade_date: date
    fx_to_eur: float  # euros por 1 unidad de `currency` ese día (ya incluye peniques→libras)
    id: int | None = None
    note: str | None = None

    @property
    def gross_eur(self) -> float:
        return self.quantity * self.price * self.fx_to_eur

    @property
    def fee_eur(self) -> float:
        return self.fee * self.fx_to_eur

    @property
    def cash_eur(self) -> float:
        """Dinero que sale (+) o entra (−) de tu bolsillo con esta operación."""
        if self.side == "BUY":
            return self.gross_eur + self.fee_eur
        return -(self.gross_eur - self.fee_eur)


def fx_pair(currency: str) -> tuple[str | None, float]:
    """Ticker de Yahoo para convertir `currency` a EUR y divisor previo.

    Yahoo cotiza EURUSD=X como "dólares por 1 euro", así que EUR por 1 USD = 1 / cotización.
    Las acciones de Londres cotizan en peniques (GBp): primero /100 para pasar a libras.
    """
    if currency == "EUR":
        return None, 1.0
    if currency == "GBp":
        return "EURGBP=X", 100.0
    return f"EUR{currency}=X", 1.0


def to_eur_rate(currency: str, quote: float | None) -> float:
    """Euros por 1 unidad de `currency`, dado el precio del par EURxxx=X."""
    _, divisor = fx_pair(currency)
    if currency == "EUR":
        return 1.0
    if not quote:
        raise PortfolioError(f"Sin tipo de cambio para {currency}")
    return 1.0 / quote / divisor


def sort_trades(trades: list[Trade]) -> list[Trade]:
    return sorted(trades, key=lambda t: (t.trade_date, t.id or 0))


@dataclass
class Lot:
    quantity: float
    cost_eur_per_share: float  # incluye la parte proporcional de la comisión
    cost_local_per_share: float
    trade_date: date


@dataclass(frozen=True)
class RealizedEvent:
    ticker: str
    sell_date: date
    quantity: float
    proceeds_eur: float  # venta neta de comisión
    cost_eur: float  # coste FIFO de las acciones vendidas
    pnl_eur: float
    holding_days: int  # desde la compra más antigua consumida


@dataclass
class Position:
    ticker: str
    currency: str
    lots: deque[Lot] = field(default_factory=deque)

    @property
    def quantity(self) -> float:
        return sum(lot.quantity for lot in self.lots)

    @property
    def cost_eur(self) -> float:
        return sum(lot.quantity * lot.cost_eur_per_share for lot in self.lots)

    @property
    def avg_price_local(self) -> float | None:
        q = self.quantity
        return sum(lot.quantity * lot.cost_local_per_share for lot in self.lots) / q if q else None


EPS = 1e-9


def build_positions(trades: list[Trade]) -> tuple[dict[str, Position], list[RealizedEvent]]:
    """Recorre las operaciones en orden y aplica FIFO. Lanza PortfolioError si una venta
    supera las acciones disponibles en esa fecha."""
    positions: dict[str, Position] = {}
    realized: list[RealizedEvent] = []
    for t in sort_trades(trades):
        pos = positions.setdefault(t.ticker, Position(t.ticker, t.currency))
        if t.side == "BUY":
            pos.lots.append(
                Lot(
                    t.quantity,
                    (t.gross_eur + t.fee_eur) / t.quantity,
                    (t.quantity * t.price + t.fee) / t.quantity,
                    t.trade_date,
                )
            )
            continue
        if t.quantity > pos.quantity + EPS:
            raise PortfolioError(
                f"Venta de {t.quantity:g} {t.ticker} el {t.trade_date:%d/%m/%Y}: solo había "
                f"{pos.quantity:g} acciones en cartera en esa fecha."
            )
        remaining, cost, first_date = t.quantity, 0.0, None
        while remaining > EPS:
            lot = pos.lots[0]
            first_date = first_date or lot.trade_date
            take = min(remaining, lot.quantity)
            cost += take * lot.cost_eur_per_share
            lot.quantity -= take
            remaining -= take
            if lot.quantity <= EPS:
                pos.lots.popleft()
        proceeds = t.gross_eur - t.fee_eur
        realized.append(
            RealizedEvent(
                t.ticker,
                t.trade_date,
                t.quantity,
                proceeds,
                cost,
                proceeds - cost,
                (t.trade_date - first_date).days,
            )
        )
    return {k: p for k, p in positions.items() if p.quantity > EPS}, realized


def validate_new_trade(existing: list[Trade], new: Trade) -> None:
    """Comprueba que añadir `new` deja una cartera posible (lanza PortfolioError si no)."""
    build_positions([*existing, new])


@dataclass(frozen=True)
class Summary:
    market_value_eur: float
    open_cost_eur: float
    unrealized_eur: float
    realized_eur: float
    total_invested_eur: float  # suma de todas las compras (incl. comisiones)
    net_contributed_eur: float  # compras − ventas: dinero "puesto" que sigue dentro

    @property
    def total_pnl_eur(self) -> float:
        return self.unrealized_eur + self.realized_eur

    @property
    def total_return(self) -> float | None:
        """Ganancia total / total invertido. Simple y fácil de entender, pero no tiene en
        cuenta CUÁNDO entró el dinero (eso lo hace la comparación con la cartera sombra)."""
        return self.total_pnl_eur / self.total_invested_eur if self.total_invested_eur else None


def summarize(
    trades: list[Trade], prices: dict[str, float], fx_now: dict[str, float]
) -> tuple[Summary, pd.DataFrame]:
    """Resumen y tabla de posiciones valoradas a precios actuales.

    prices: ticker → precio actual en su moneda; fx_now: moneda → euros por unidad.
    """
    positions, realized = build_positions(trades)
    rows = []
    for p in positions.values():
        price = prices.get(p.ticker)
        value = p.quantity * price * fx_now.get(p.currency, np.nan) if price else np.nan
        rows.append(
            {
                "ticker": p.ticker,
                "currency": p.currency,
                "quantity": p.quantity,
                "avg_price": p.avg_price_local,
                "price": price,
                "cost_eur": p.cost_eur,
                "value_eur": value,
                "pnl_eur": value - p.cost_eur,
                "pnl_pct": value / p.cost_eur - 1 if p.cost_eur else np.nan,
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df["weight"] = df["value_eur"] / df["value_eur"].sum()
    mv = float(df["value_eur"].sum()) if not df.empty else 0.0
    cost = float(df["cost_eur"].sum()) if not df.empty else 0.0
    summary = Summary(
        market_value_eur=mv,
        open_cost_eur=cost,
        unrealized_eur=mv - cost,
        realized_eur=float(sum(r.pnl_eur for r in realized)),
        total_invested_eur=float(sum(t.cash_eur for t in trades if t.side == "BUY")),
        net_contributed_eur=float(sum(t.cash_eur for t in trades)),
    )
    return summary, df


def holdings_over_time(trades: list[Trade], index: pd.DatetimeIndex) -> pd.DataFrame:
    """Acciones de cada ticker en cada fecha del índice (después de las operaciones del día)."""
    out = pd.DataFrame(0.0, index=index, columns=sorted({t.ticker for t in trades}))
    days = index.normalize().tz_localize(None) if index.tz else index.normalize()
    for t in sort_trades(trades):
        sign = 1 if t.side == "BUY" else -1
        out.loc[days >= pd.Timestamp(t.trade_date), t.ticker] += sign * t.quantity
    return out


def value_series(
    trades: list[Trade], closes: dict[str, pd.Series], fx: dict[str, pd.Series]
) -> pd.DataFrame:
    """Valor diario de la cartera (EUR) y dinero neto aportado acumulado.

    closes: ticker → cierres diarios en su moneda; fx: moneda → euros por unidad, diario.
    Fines de semana y festivos distintos por bolsa: se rellena con el último dato (ffill).
    """
    if not trades:
        return pd.DataFrame(columns=["value", "contributed"])
    start = pd.Timestamp(min(t.trade_date for t in trades))
    prices = pd.DataFrame({k: _daily(v) for k, v in closes.items()}).sort_index().ffill()
    prices = prices.loc[start:]
    idx = prices.index
    hold = holdings_over_time(trades, idx)
    currency = {t.ticker: t.currency for t in trades}
    value = pd.Series(0.0, index=idx)
    for tk in hold.columns:
        rate = 1.0 if currency[tk] == "EUR" else _daily(fx[currency[tk]]).reindex(idx).ffill()
        value += hold[tk] * prices[tk] * rate
    flows = pd.Series(0.0, index=idx)
    for t in trades:
        pos = idx.searchsorted(pd.Timestamp(t.trade_date))
        if pos < len(idx):
            flows.iloc[pos] += t.cash_eur
    return pd.DataFrame({"value": value, "contributed": flows.cumsum()})


def shadow_benchmark(trades: list[Trade], bench_close: pd.Series) -> pd.Series:
    """'Cartera sombra': cada euro que metes (o sacas) en tu cartera se mete (o saca) el
    mismo día en el índice. Así la comparación es justa aunque hayas invertido poco a poco."""
    close = _daily(bench_close).sort_index()
    start = pd.Timestamp(min(t.trade_date for t in trades))
    close = close.loc[close.index >= start - pd.Timedelta(days=7)].ffill()
    units = pd.Series(0.0, index=close.index)
    held = 0.0
    for t in sort_trades(trades):
        pos = close.index.searchsorted(pd.Timestamp(t.trade_date))
        if pos >= len(close):
            continue
        px = close.iloc[pos]
        delta = t.cash_eur / px
        held = max(held + delta, 0.0)  # una venta no puede dejar unidades negativas
        units.iloc[pos:] = held
    return (units * close).loc[start:]


def _daily(s: pd.Series) -> pd.Series:
    """Índice diario sin hora ni zona (fechas de calendario) para alinear bolsas distintas."""
    s = s.copy()
    idx = pd.DatetimeIndex(s.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    s.index = idx.normalize()
    return s[~s.index.duplicated(keep="last")]


def allocation(df: pd.DataFrame, by: str) -> pd.Series:
    """Peso de la cartera por la columna `by` (sector, país...), ordenado de mayor a menor."""
    return df.groupby(by)["value_eur"].sum().div(df["value_eur"].sum()).sort_values(ascending=False)


def effective_positions(weights: pd.Series) -> float:
    """Número efectivo de posiciones = 1 / Σ pesos². Con 10 posiciones iguales sale 10; si
    una pesa el 90 %, sale ~1,2 aunque tengas 10: mide la concentración real."""
    w = weights.dropna()
    return float(1 / (w**2).sum()) if len(w) else 0.0
