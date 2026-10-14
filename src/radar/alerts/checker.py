"""Comprobación de alertas contra los datos de mercado.

Se ejecuta en cada refresco de la watchlist (gracias a la caché no multiplica las llamadas
a la API) y también se puede lanzar desde la terminal, p. ej. con cron o launchd:

    python -m radar.alerts.checker --notify

--notify muestra una notificación de macOS por cada alerta disparada.
"""

import argparse
import logging
import platform
import subprocess

from radar import config
from radar.alerts.rules import NEEDS_HISTORY, Alert, Observation, describe, evaluate
from radar.data.service import MarketDataService, default_service
from radar.db.alerts import AlertsRepo
from radar.db.database import Database
from radar.errors import RadarError
from radar.formatting import fmt_number
from radar.indicators.technical import rsi, sma

log = logging.getLogger(__name__)


def observe(svc: MarketDataService, a: Alert) -> Observation:
    if a.metric not in NEEDS_HISTORY:
        q = svc.get_quote(a.ticker)
        if a.metric == "price":
            return Observation(q.price)
        if q.change_pct is None:
            raise RadarError("Sin cierre anterior para calcular la variación diaria")
        return Observation(q.change_pct * 100)
    close = svc.get_history(a.ticker, "2A").data["Close"]
    if a.metric == "rsi":
        return Observation(float(rsi(close).iloc[-1]))
    n = 50 if a.metric == "sma50" else 200
    ref = sma(close, n).iloc[-1]
    if ref != ref:  # NaN: no hay historia suficiente
        raise RadarError(f"No hay suficiente historia para la SMA {n}")
    return Observation(float(close.iloc[-1]), float(ref))


def check_all(svc: MarketDataService, repo: AlertsRepo) -> list[str]:
    """Evalúa las alertas activas, guarda el estado y devuelve los mensajes disparados."""
    messages = []
    for a in repo.list(only_active=True):
        try:
            obs = observe(svc, a)
        except RadarError as e:
            log.warning("Alerta %s sin evaluar: %s", a.id, e)
            continue
        ev = evaluate(a, obs)
        repo.save_check(a.id, ev.state, obs.value)
        if ev.fired:
            msg = f"🔔 {describe(a)} (valor actual: {fmt_number(obs.value)})"
            repo.add_event(a.id, obs.value, msg)
            messages.append(msg)
    return messages


def notify_macos(message: str) -> None:
    if platform.system() != "Darwin":
        return
    # El texto va dentro de un literal de AppleScript: escapamos \ y " para no romperlo
    safe = message.replace("\\", "\\\\").replace('"', '\\"')
    subprocess.run(
        ["osascript", "-e", f'display notification "{safe}" with title "Radar Bolsa"'],
        check=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Comprueba las alertas de Radar Bolsa.")
    parser.add_argument("--notify", action="store_true", help="Notificación de macOS")
    args = parser.parse_args()
    msgs = check_all(default_service(), AlertsRepo(Database(config.DB_PATH)))
    for m in msgs:
        print(m)
        if args.notify:
            notify_macos(m)
    if not msgs:
        print("Ninguna alerta disparada.")


if __name__ == "__main__":
    main()
