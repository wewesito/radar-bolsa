"""Configuración central: rutas, TTLs de caché y variables de entorno."""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = Path(os.getenv("RADAR_DATA_DIR", PROJECT_ROOT / "data"))
DB_PATH = DATA_DIR / "radar.db"
CACHE_PATH = DATA_DIR / "cache.db"

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY") or None

# Mínimo 30 s para no saturar a Yahoo con una watchlist grande.
REFRESH_SECONDS = max(30, int(os.getenv("REFRESH_SECONDS", "60")))

# Cuánto tiempo (en segundos) se considera "fresco" cada tipo de dato.
TTL_QUOTE = 60
TTL_HISTORY_INTRADAY = 120
TTL_HISTORY_DAILY = 6 * 3600
TTL_FUNDAMENTALS = 24 * 3600

DISPLAY_TZ = "Europe/Madrid"
