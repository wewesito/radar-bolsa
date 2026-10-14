"""Configuración central: rutas, TTLs de caché y variables de entorno."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
# Empaquetada (PyInstaller) no hay proyecto: los datos van a la carpeta de la app del usuario.
FROZEN = getattr(sys, "frozen", False)
if not FROZEN:
    load_dotenv(PROJECT_ROOT / ".env")

_DEFAULT_DATA_DIR = (
    Path.home() / "Library" / "Application Support" / "Radar Bolsa"
    if FROZEN
    else PROJECT_ROOT / "data"
)
DATA_DIR = Path(os.getenv("RADAR_DATA_DIR", _DEFAULT_DATA_DIR))
DB_PATH = DATA_DIR / "radar.db"
CACHE_PATH = DATA_DIR / "cache.db"

# Mínimo 30 s para no saturar a Yahoo con una watchlist grande.
REFRESH_SECONDS = max(30, int(os.getenv("REFRESH_SECONDS", "60")))

# Cuánto tiempo (en segundos) se considera "fresco" cada tipo de dato.
TTL_QUOTE = 60
TTL_HISTORY_INTRADAY = 120
TTL_HISTORY_DAILY = 6 * 3600
TTL_FUNDAMENTALS = 24 * 3600

DISPLAY_TZ = "Europe/Madrid"
