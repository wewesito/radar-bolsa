"""API keys guardadas de forma segura: Llavero de macOS (o el almacén del sistema).

Nunca se guardan en el código ni en la base de datos. En desarrollo también se aceptan
desde `.env` (variable de entorno), que tiene prioridad más baja que el Llavero.
"""

import contextlib
import os

import keyring
from keyring.errors import KeyringError

SERVICE = "Radar Bolsa"

# Nombre interno → variable de entorno equivalente
KNOWN_SECRETS = {"finnhub": "FINNHUB_API_KEY"}


def get_secret(name: str) -> str | None:
    """Valor de la clave `name`, o None si no está configurada."""
    try:
        value = keyring.get_password(SERVICE, name)
    except KeyringError:
        value = None
    return value or os.getenv(KNOWN_SECRETS.get(name, ""), "") or None


def set_secret(name: str, value: str) -> None:
    """Guarda (o borra, si `value` está vacío) la clave en el Llavero."""
    if name not in KNOWN_SECRETS:
        raise ValueError(f"Clave desconocida: {name}")
    if value.strip():
        keyring.set_password(SERVICE, name, value.strip())
    else:
        with contextlib.suppress(keyring.errors.PasswordDeleteError):
            keyring.delete_password(SERVICE, name)


def secret_status() -> dict[str, bool]:
    """Qué claves están configuradas (sin revelar su valor)."""
    return {name: get_secret(name) is not None for name in KNOWN_SECRETS}
