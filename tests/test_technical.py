import numpy as np
import pandas as pd
import pytest

from radar.indicators.technical import (
    bollinger,
    ema,
    last_ma_cross,
    macd,
    rsi,
    sma,
    support_resistance,
    suspicious_jumps,
)


def series(values, start="2026-01-01"):
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="D"), dtype=float)


def test_sma():
    out = sma(series([1, 2, 3, 4, 5]), 3)
    assert out.isna().sum() == 2
    assert list(out.dropna()) == [2, 3, 4]


def test_ema_weights_recent_more():
    s = series([1] * 10 + [2])
    assert sma(s, 5).iloc[-1] < ema(s, 5).iloc[-1] < 2


# Ejemplo clásico de Wilder publicado por StockCharts: RSI(14) = 70,53 y luego 66,32.
# Su hoja redondea los promedios intermedios a 2 decimales; nosotros no, de ahí ~0,07 de
# diferencia. Con la fórmula de pandas ewm (semilla distinta) saldría ~50: muy lejos.
WILDER = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89,
          46.03, 45.61, 46.28, 46.28, 46.00]  # fmt: skip


def test_rsi_matches_reference_example():
    out = rsi(series(WILDER), 14)
    assert out.iloc[14] == pytest.approx(70.53, abs=0.1)
    assert out.iloc[15] == pytest.approx(66.32, abs=0.1)
    assert out.iloc[:14].isna().all()


def test_rsi_limits():
    assert rsi(series(range(1, 31)), 14).iloc[-1] == 100  # solo sube
    assert rsi(series(range(30, 0, -1)), 14).iloc[-1] == pytest.approx(0)  # solo baja
    assert rsi(series([5] * 30), 14).iloc[-1] == 50  # plano


def test_macd_zero_on_flat_series():
    out = macd(series([10] * 60))
    assert out.dropna().abs().max().max() == pytest.approx(0)


def test_macd_positive_in_uptrend():
    out = macd(series(np.linspace(10, 20, 60)))
    assert out["macd"].iloc[-1] > 0


def test_bollinger_known_values():
    out = bollinger(series([1, 2, 3]), n=3, k=2)
    std = np.sqrt(2 / 3)  # desviación poblacional de [1, 2, 3]
    assert out["mid"].iloc[-1] == 2
    assert out["upper"].iloc[-1] == pytest.approx(2 + 2 * std)
    assert out["lower"].iloc[-1] == pytest.approx(2 - 2 * std)


def test_support_resistance_on_oscillating_price():
    # Oscila entre ~90 y ~110 varias veces y termina en 100
    t = np.arange(120)
    close = 100 + 10 * np.sin(t / 5)
    close[-1] = 100
    df = pd.DataFrame({"High": close + 0.5, "Low": close - 0.5, "Close": close},
                      index=pd.date_range("2026-01-01", periods=120))
    levels = support_resistance(df)
    sup = [lv for lv in levels if lv.kind == "soporte"]
    res = [lv for lv in levels if lv.kind == "resistencia"]
    assert sup[0].price == pytest.approx(89.5, abs=1)
    assert res[0].price == pytest.approx(110.5, abs=1)
    assert sup[0].touches >= 3  # tocado en cada valle


def test_last_ma_cross_golden():
    s = series([10, 9, 8, 7, 6, 5, 6, 8, 10, 12, 14])
    cross = last_ma_cross(s, fast=2, slow=4)
    assert cross.kind == "cruce dorado"


def test_last_ma_cross_none_without_cross():
    assert last_ma_cross(series(range(1, 30)), fast=2, slow=4) is None


def test_suspicious_jumps():
    jumps = suspicious_jumps(series([10, 10.5, 21, 21]))
    assert len(jumps) == 1
    assert jumps.iloc[0] == pytest.approx(1.0)
