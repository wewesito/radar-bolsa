"""Cartera de ejemplo: reglas de reparto y diversificación con recomendaciones sintéticas."""

import pytest

from radar.portfolio.model import (
    BUCKET_BONDS,
    BUCKET_CASH,
    BUCKET_ETF,
    BUCKET_STOCK,
    build_model_portfolio,
    pick_stocks,
)
from radar.profile.investor import Answers, compute_profile
from radar.recommend.engine import Recommendation


def rec(ticker, label="buy", score=70.0, kind="stock", sector="Industrials", country="Germany",
        etf_role=None, spain=None) -> Recommendation:  # fmt: skip
    return Recommendation(
        ticker=ticker, name=ticker, kind=kind, label=label, score=score, risk_level=1,
        price=10.0, currency="EUR", summary="motivo", fit="", pros=[], cons=[], checks=[],
        components=[], entry=None, entry_note="", risk_detail="", sector=sector,
        country=country, spain_index=spain, etf_role=etf_role,
    )  # fmt: skip


ETFS = [
    rec("VWCE.DE", kind="etf", etf_role="core", sector=None),
    rec("VHYL.AS", kind="etf", etf_role="dividend", sector=None),
    rec("EUNA.DE", kind="etf", etf_role="bonds", sector=None),
    rec("XEON.DE", kind="etf", etf_role="cash", sector=None),
]

MODERATE = compute_profile(Answers(2, 2, 2, "growth", 2))  # 70/25/5, 10 acciones
CONSERVATIVE = compute_profile(Answers(1, 1, 2, "growth", 2))  # 55/10/35
DIVIDENDS = compute_profile(Answers(2, 2, 2, "dividends", 2))
SMALL = compute_profile(Answers(2, 2, 0, "growth", 2))  # < 1.000 €: solo ETFs


def many_stocks() -> list[Recommendation]:
    sectors = [
        "Industrials",
        "Utilities",
        "Energy",
        "Healthcare",
        "Technology",
        "Financial Services",
    ]
    out = []
    for i in range(30):
        country = "United States" if i % 2 else "Spain"
        out.append(rec(f"S{i}", score=90 - i, sector=sectors[i % 6], country=country))
    return out


def test_weights_add_up_and_follow_profile_allocation():
    mp = build_model_portfolio(many_stocks() + ETFS, MODERATE)
    assert sum(p.weight for p in mp.positions) == pytest.approx(1)
    assert mp.by_bucket[BUCKET_STOCK] == pytest.approx(0.25)
    assert mp.by_bucket[BUCKET_ETF] == pytest.approx(0.70)
    assert mp.by_bucket[BUCKET_BONDS] == pytest.approx(0.05)
    assert sum(p.amount_eur for p in mp.positions) == pytest.approx(MODERATE.amount_eur)


def test_stock_selection_respects_sector_and_region_limits():
    chosen = pick_stocks(many_stocks(), 10)
    assert len(chosen) == 10
    per_sector = {}
    for r in chosen:
        per_sector[r.sector] = per_sector.get(r.sector, 0) + 1
    assert max(per_sector.values()) <= 2
    us = sum(r.country == "United States" for r in chosen)
    assert us <= 5


def test_only_buy_signals_and_leftover_goes_to_core_etf():
    stocks = [rec("A"), rec("B", label="watch", score=99), rec("C", label="avoid", score=98)]
    mp = build_model_portfolio(stocks + ETFS, MODERATE)
    tickers = {p.ticker for p in mp.positions}
    assert "A" in tickers and "B" not in tickers and "C" not in tickers
    core = next(p for p in mp.positions if p.ticker == "VWCE.DE")
    assert core.weight == pytest.approx(0.70 + 0.25 - 0.025)  # 1 de 10 acciones
    assert any("Hoy solo 1 acciones" in n for n in mp.notes)


def test_conservative_splits_safe_part_into_bonds_and_cash():
    mp = build_model_portfolio(many_stocks() + ETFS, CONSERVATIVE)
    assert mp.by_bucket[BUCKET_BONDS] == pytest.approx(0.35 * 0.7)
    assert mp.by_bucket[BUCKET_CASH] == pytest.approx(0.35 * 0.3)


def test_dividend_objective_adds_dividend_etf():
    mp = build_model_portfolio(many_stocks() + ETFS, DIVIDENDS)
    div = next(p for p in mp.positions if p.ticker == "VHYL.AS")
    assert div.weight == pytest.approx(0.70 * 0.3)


def test_small_amount_is_all_etfs_and_regions_add_up():
    mp = build_model_portfolio(many_stocks() + ETFS, SMALL)
    assert BUCKET_STOCK not in mp.by_bucket
    assert sum(mp.by_region.values()) == pytest.approx(1)
    assert sum(mp.by_sector.values()) == pytest.approx(1)


def test_core_etf_skips_avoid():
    etfs = [rec("VWCE.DE", kind="etf", etf_role="core", label="avoid"),
            rec("IUSQ.DE", kind="etf", etf_role="core")] + ETFS[2:]  # fmt: skip
    mp = build_model_portfolio(etfs, SMALL)
    assert mp.positions[0].ticker == "IUSQ.DE"
