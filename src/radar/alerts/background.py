"""Comprobación de alertas con la app cerrada, mediante un agente de launchd del usuario.

Al activarla se crea `~/Library/LaunchAgents/es.radarbolsa.alertas.plist`, que ejecuta cada
15 minutos la comprobación (con notificación de macOS). Solo corre mientras hay sesión de
usuario iniciada. Al desactivarla se descarga y se borra el fichero. No instala nada más.
"""

import os
import plistlib
import subprocess
import sys
from pathlib import Path

from radar import config

LABEL = "es.radarbolsa.alertas"
INTERVAL_SECONDS = 900


def plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def check_command() -> list[str]:
    """Comando que comprueba las alertas: el motor empaquetado o, en desarrollo, Python."""
    if config.FROZEN:
        return [sys.executable, "--check-alerts"]
    return [sys.executable, "-m", "radar.alerts.checker", "--notify"]


def plist_content(command: list[str], data_dir: str | None, log_file: Path) -> bytes:
    """Contenido del .plist (función pura)."""
    content: dict = {
        "Label": LABEL,
        "ProgramArguments": command,
        "StartInterval": INTERVAL_SECONDS,
        "RunAtLoad": False,
        "StandardOutPath": str(log_file),
        "StandardErrorPath": str(log_file),
    }
    if data_dir:
        content["EnvironmentVariables"] = {"RADAR_DATA_DIR": data_dir}
    return plistlib.dumps(content)


def _launchctl(*args: str) -> None:
    subprocess.run(["launchctl", *args], check=False, capture_output=True)


def is_enabled() -> bool:
    return plist_path().exists()


def enable() -> None:
    path = plist_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    log_file = config.DATA_DIR / "alertas.log"
    path.write_bytes(plist_content(check_command(), os.getenv("RADAR_DATA_DIR"), log_file))
    domain = f"gui/{os.getuid()}"
    _launchctl("bootout", f"{domain}/{LABEL}")  # por si había una versión anterior
    _launchctl("bootstrap", domain, str(path))


def disable() -> None:
    _launchctl("bootout", f"gui/{os.getuid()}/{LABEL}")
    plist_path().unlink(missing_ok=True)
