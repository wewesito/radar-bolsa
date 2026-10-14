from datetime import date

import pandas as pd
import pytest

from radar.portfolio.calc import (
    PortfolioError,
    Trade,
    allocation,
    build_positions,
    effective_positions,
    fx_pair,
    shadow_benchmark,
    summarize,
    to_eur_rate,
    validate_new_trade,
    value_series,
)


def buy(tk, q, p, d, fee=0.0, cur="EUR", fx=1.0, id=None):
    return Trade(tk, "BUY", q, p, fee, cur, d, fx, id)


def sell(tk, q, p, d, fee=0.0, cur="EUR", fx=1.0, id=None):
    return Trade(tk, "SELL", q, p, fee, cur, d, fx, id)


def test_fifo_realized_uses_oldest_lots_first():
    trades = [
        buy("SAN.MC", 10, 4.0, date(2026, 1, 2)),
        buy("SAN.MC", 10, 6.0, date(2026, 2, 2)),
        sell("SAN.MC", 15, 8.0, date(2026, 3, 2)),
    ]
    positions, realized = build_positions(trades)
    # FIFO: vende 10 a coste 4 y 5 a coste 6 → coste 70; ingreso 120 → +50
    assert realized[0].cost_eur == pytest.approx(70)
    assert realized[0].pnl_eur == pytest.approx(50)
    assert realized[0].holding_days == 59
    pos = positions["SAN.MC"]
    assert pos.quantity == 5
    assert pos.avg_price_local == pytest.approx(6.0)  # quedan las de 6 €


def test_fees_are_part_of_cost_and_reduce_proceeds():
    trades = [
        buy("X.MC", 10, 10.0, date(2026, 1, 2), fee=5),
        sell("X.MC", 10, 12.0, date(2026, 1, 3), fee=5),
    ]
    _, realized = build_positions(trades)
    assert realized[0].pnl_eur == pytest.approx(120 - 5 - 105)


def test_cannot_sell_more_than_held_at_that_date():
    trades = [buy("X.MC", 10, 10.0, date(2026, 3, 1))]
    with pytest.raises(PortfolioError):
        validate_new_trade(trades, sell("X.MC", 5, 10.0, date(2026, 2, 1)))  # antes de comprar
    with pytest.raises(PortfolioError):
        validate_new_trade(trades, sell("X.MC", 11, 10.0, date(2026, 4, 1)))
    validate_new_trade(trades, sell("X.MC", 10, 10.0, date(2026, 4, 1)))  # todo: OK


def test_fx_conversion():
    assert fx_pair("USD") == ("EURUSD=X", 1.0)
    assert to_eur_rate("USD", 1.25) == pytest.approx(0.8)  # 1,25 $/€ → 0,80 € por $
    assert to_eur_rate("GBp", 0.8) == pytest.approx(1 / 0.8 / 100)  # peniques
    assert to_eur_rate("EUR", None) == 1.0
    with pytest.raises(PortfolioError):
        to_eur_rate("USD", None)


def test_summarize_in_eur_with_usd_position():
    trades = [buy("AAPL", 10, 100.0, date(2026, 1, 2), cur="USD", fx=0.9)]  # coste 900 €
    s, df = summarize(trades, {"AAPL": 110.0}, {"USD": 0.8})  # el dólar se deprecia
    assert s.market_value_eur == pytest.approx(880)  # 10·110·0,8
    assert s.unrealized_eur == pytest.approx(-20)  # sube la acción, pero pierdes por divisa
    assert s.total_return == pytest.approx(-20 / 900)
    assert df.loc[0, "weight"] == 1


def days(start, n):
    return pd.date_range(start, periods=n, freq="D")


def test_value_series_and_contributions():
    idx = days("2026-01-01", 5)
    closes = {"A.MC": pd.Series([10, 11, 12, 13, 14], index=idx, dtype=float)}
    trades = [buy("A.MC", 2, 10.0, date(2026, 1, 1)), sell("A.MC", 1, 12.0, date(2026, 1, 3))]
    vs = value_series(trades, closes, {})
    assert list(vs["value"]) == [20, 22, 12, 13, 14]
    assert list(vs["contributed"]) == [20, 20, 8, 8, 8]


def test_shadow_benchmark_invests_same_euros_same_day():
    idx = days("2026-01-01", 4)
    bench = pd.Series([100, 110, 121, 121], index=idx, dtype=float)
    trades = [buy("A.MC", 1, 100.0, date(2026, 1, 1)), buy("A.MC", 1, 110.0, date(2026, 1, 2))]
    shadow = shadow_benchmark(trades, bench)
    # día 1: 1 unidad; día 2: +1 unidad (110 €/110); día 3: 2 × 121
    assert list(shadow.round(6)) == [100, 220, 242, 242]


def test_allocation_and_effective_positions():
    df = pd.DataFrame({"sector": ["A", "A", "B"], "value_eur": [50.0, 25.0, 25.0]})
    alloc = allocation(df, "sector")
    assert alloc["A"] == pytest.approx(0.75)
    assert effective_positions(pd.Series([0.25] * 4)) == pytest.approx(4)
    assert effective_positions(pd.Series([0.9, 0.1])) == pytest.approx(1 / 0.82)


def test_trades_repo_roundtrip_and_validation(tmp_path):
    from radar.db.database import Database
    from radar.db.trades import TradesRepo

    repo = TradesRepo(Database(tmp_path / "r.db"))
    bid = repo.add(buy("SAN.MC", 10, 5.0, date(2026, 1, 2)))
    repo.add(sell("SAN.MC", 4, 6.0, date(2026, 1, 5)))
    with pytest.raises(PortfolioError):
        repo.add(sell("SAN.MC", 7, 6.0, date(2026, 1, 6)))  # solo quedan 6
    assert [t.side for t in repo.list()] == ["BUY", "SELL"]
    with pytest.raises(PortfolioError):
        repo.delete(bid)  # dejaría la venta sin compra previa
