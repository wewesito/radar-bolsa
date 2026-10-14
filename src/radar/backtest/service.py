"""Ejecución del backtest en segundo plano y su resultado en caché (única parte con E/S)."""

import threading
from dataclasses import dataclass
from datetime import UTC, datetime

from radar.backtest.data import load_benchmarks, load_prices
from radar.backtest.engine import BacktestResult, drop_suspect, run_backtest
from radar.data.service import MarketDataService
from radar.universe import UniverseSnapshot

CACHE_KEY = "backtest:result:v2"  # v2: sin valores con datos sospechosos


@dataclass
class BacktestStatus:
    running: bool = False
    error: str | None = None


def result_to_dict(res: BacktestResult, failed: list[str], built_at: str) -> dict:
    """Resultado en JSON (fechas ISO; los dataclasses los convierte la API)."""
    return {
        "built_at": built_at,
        "source": "Yahoo Finance",
        "dates": [d.date().isoformat() for d in res.dates],
        "series": res.series,
        "metrics": res.metrics,
        "yearly": {str(y): v for y, v in sorted(res.yearly.items())},
        "last_selection": {
            "date": res.selections[-1][0].date().isoformat(),
            "picks": [{"ticker": t, "score": s} for t, s in res.selections[-1][1]],
        }
        if res.selections
        else None,
        "rebalances": len(res.selections),
        "config": res.config,
        "universe_size": res.universe_size,
        "failed": failed,
    }


class BacktestRunner:
    def __init__(self, svc: MarketDataService):
        self.svc = svc
        self.status = BacktestStatus()
        self._lock = threading.Lock()

    def cached(self) -> dict | None:
        entry = self.svc.cache.get_any(CACHE_KEY)
        return entry.value if entry else None

    def start(self, snapshot: UniverseSnapshot) -> bool:
        """Lanza el cálculo. False si ya había uno en marcha."""
        with self._lock:
            if self.status.running:
                return False
            self.status = BacktestStatus(running=True)
        threading.Thread(target=self._run, args=(snapshot,), daemon=True).start()
        return True

    def _run(self, snapshot: UniverseSnapshot) -> None:
        try:
            df = snapshot.df
            stocks = df[df["quote_type"] == "EQUITY"]
            currencies = dict(zip(stocks["ticker"], stocks["price_currency"], strict=True))
            prices, failed = load_prices(self.svc, currencies)
            prices, suspect = drop_suspect(prices)
            res = run_backtest(prices, load_benchmarks(self.svc))
            failed = failed + suspect
            payload = result_to_dict(res, failed, datetime.now(UTC).isoformat())
            self.svc.cache.set(CACHE_KEY, _plain(payload))
        except Exception as e:  # el hilo no debe morir en silencio: se informa a la UI
            self.status.error = f"No se pudo calcular el backtest: {e}"
        finally:
            self.status.running = False


def _plain(obj):
    """Dataclasses y escalares a tipos JSON puros para la caché."""
    from dataclasses import asdict, is_dataclass

    if is_dataclass(obj) and not isinstance(obj, type):
        return _plain(asdict(obj))
    if isinstance(obj, dict):
        return {k: _plain(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [_plain(v) for v in obj]
    return obj
