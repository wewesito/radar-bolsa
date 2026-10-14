import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from components.charts import missing_days, price_chart  # noqa: E402
from radar.models import PriceHistory  # noqa: E402


def test_missing_days_skips_weekend_and_holiday():
    # Jue 8, Vie 9, (Sáb 10, Dom 11), Lun 12 festivo, Mar 13
    idx = pd.DatetimeIndex(["2026-10-08", "2026-10-09", "2026-10-13"])
    assert missing_days(idx) == ["2026-10-10", "2026-10-11", "2026-10-12"]


def test_price_chart_builds_with_log_scale():
    idx = pd.date_range("2026-10-01", periods=5, freq="D", tz="UTC")
    df = pd.DataFrame(
        {"Open": 1.0, "High": 2.0, "Low": 0.5, "Close": [1.0, 1.5, 0.9, 1.2, 1.8], "Volume": 10},
        index=idx,
    )
    hist = PriceHistory("X.MC", "1M", "1d", df, datetime.now(UTC), "test")
    fig = price_chart(hist, "Velas", intraday=False, log_scale=True)
    assert fig.layout.yaxis.type == "log"
    assert len(fig.data) == 2  # velas + volumen
