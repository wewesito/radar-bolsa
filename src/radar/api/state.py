"""Estado del motor: servicio de datos, base de datos, universo en memoria y su reconstrucción.

La API (app.py) solo traduce peticiones HTTP a llamadas a este objeto.
"""

import logging
import threading
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

import pandas as pd

from radar.alerts.checker import check_all, notify_macos
from radar.backtest.service import BacktestRunner
from radar.data.service import MarketDataService
from radar.db.alerts import AlertsRepo
from radar.db.database import Database
from radar.db.settings import SettingsRepo
from radar.db.trades import TradesRepo
from radar.db.watchlist import WatchlistRepo
from radar.profile.investor import (
    Answers,
    InvestorProfile,
    answers_from_dict,
    compute_profile,
)
from radar.recommend.engine import Recommendation, recommend, recommend_all
from radar.universe import UniverseSnapshot, build_universe, company_row, load_universe

log = logging.getLogger(__name__)
ALERT_CHECK_SECONDS = 300  # las cotizaciones se cachean 60 s: no tiene sentido ir más rápido
PROFILE_KEY = "profile"
# Sin test hecho todavía (p. ej. la sección España): se usa un perfil moderado de referencia
DEFAULT_ANSWERS = Answers(horizon=2, reaction=2, amount=2, objective="growth", experience=2)


class NoUniverseError(Exception):
    """Aún no hay foto del universo: hay que construirla (primera ejecución)."""


class NoProfileError(Exception):
    """El usuario aún no ha hecho el test de perfil."""


@dataclass
class BuildStatus:
    running: bool = False
    done: int = 0
    total: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None


class Engine:
    def __init__(self, svc: MarketDataService, db: Database):
        self.svc = svc
        self.db = db
        self.settings = SettingsRepo(db)
        self.trades = TradesRepo(db)
        self.alerts = AlertsRepo(db)
        self.watchlist = WatchlistRepo(db)
        self.snapshot: UniverseSnapshot | None = load_universe(svc.cache)
        self.build = BuildStatus()
        self.backtest = BacktestRunner(svc)
        self._lock = threading.Lock()
        self._recs: dict[tuple, list[Recommendation]] = {}

    # --- Alertas ----------------------------------------------------------------------

    def check_alerts(self, notify: bool = False) -> list[str]:
        """Evalúa las alertas activas. Con `notify`, avisa con una notificación de macOS."""
        messages = check_all(self.svc, self.alerts)
        if notify:
            for m in messages:
                notify_macos(m)
        return messages

    def start_alert_loop(self, interval_seconds: int = ALERT_CHECK_SECONDS) -> None:
        """Comprueba las alertas cada pocos minutos mientras la app esté abierta."""

        def loop() -> None:
            while True:
                time.sleep(interval_seconds)
                try:
                    if self.alerts.list(only_active=True):
                        self.check_alerts(notify=True)
                except Exception:  # noqa: BLE001 - un fallo de red no debe parar el bucle
                    log.warning("Fallo al comprobar las alertas", exc_info=True)

        threading.Thread(target=loop, daemon=True).start()

    # --- Perfil -----------------------------------------------------------------------

    def answers(self) -> Answers | None:
        d = self.settings.get(PROFILE_KEY)
        return answers_from_dict(d) if d else None

    def profile(self) -> InvestorProfile:
        """Perfil del usuario; NoProfileError si aún no ha hecho el test."""
        a = self.answers()
        if a is None:
            raise NoProfileError
        return compute_profile(a)

    def profile_or_default(self) -> tuple[InvestorProfile, bool]:
        """(perfil, es_el_por_defecto)."""
        a = self.answers()
        return compute_profile(a or DEFAULT_ANSWERS), a is None

    def save_profile(self, d: dict) -> InvestorProfile:
        a = answers_from_dict(d)  # valida
        self.settings.set(PROFILE_KEY, asdict(a))
        return compute_profile(a)

    # --- Universo ---------------------------------------------------------------------

    def universe(self) -> UniverseSnapshot:
        if self.snapshot is None or self.snapshot.df.empty:
            raise NoUniverseError
        return self.snapshot

    def start_build(self) -> bool:
        """Lanza la reconstrucción en segundo plano. False si ya había una en marcha."""
        with self._lock:
            if self.build.running:
                return False
            self.build = BuildStatus(running=True, started_at=datetime.now(UTC).isoformat())
        threading.Thread(target=self._run_build, daemon=True).start()
        return True

    def _run_build(self) -> None:
        def progress(done: int, total: int) -> None:
            self.build.done, self.build.total = done, total

        try:
            snap = build_universe(self.svc, on_progress=progress)
            with self._lock:
                self.snapshot = snap
                self._recs.clear()
        except Exception as e:  # el hilo no debe morir en silencio: se informa a la UI
            self.build.error = f"No se pudo actualizar: {e}"
        finally:
            self.build.running = False
            self.build.finished_at = datetime.now(UTC).isoformat()

    # --- Recomendaciones --------------------------------------------------------------

    def recommendations(self, profile: InvestorProfile) -> list[Recommendation]:
        snap = self.universe()
        key = (snap.built_at, profile.answers)
        if key not in self._recs:
            self._recs = {key: recommend_all(snap.df, profile)}  # solo la última combinación
        return self._recs[key]

    def recommendation(self, ticker: str, profile: InvestorProfile) -> Recommendation:
        """Un valor del universo o, si no está, se descarga y se puntúa frente a él."""
        for r in self.recommendations(profile):
            if r.ticker == ticker:
                return r
        row = company_row(self.svc, ticker)
        return recommend(row, self.universe().df, profile)

    def universe_row(self, ticker: str) -> dict | None:
        if self.snapshot is None:
            return None
        df = self.snapshot.df
        match = df[df["ticker"] == ticker]
        if match.empty:
            return None
        return {k: (None if pd.isna(v) else v) for k, v in match.iloc[0].to_dict().items()}
