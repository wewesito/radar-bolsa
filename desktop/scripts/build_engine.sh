#!/usr/bin/env bash
# Empaqueta el motor en Python (src/radar) en desktop/engine-dist/radar-engine/ con PyInstaller.
# Formato carpeta (onedir): arranca en ~1-2 s, frente a los ~5 s de un único ejecutable.
# Uso (desde la raíz del proyecto, con el entorno virtual activado):
#   bash desktop/scripts/build_engine.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

pyinstaller --noconfirm --clean --log-level WARN \
  --onedir --name radar-engine \
  --distpath desktop/engine-dist \
  --workpath build/pyinstaller \
  --specpath build/pyinstaller \
  --paths src \
  --collect-submodules uvicorn \
  --collect-submodules radar \
  --hidden-import keyring.backends.macOS \
  --exclude-module altair \
  --exclude-module pydeck --exclude-module matplotlib --exclude-module tkinter \
  --exclude-module IPython --exclude-module pytest --exclude-module pyarrow \
  src/radar/api/__main__.py

echo "Motor empaquetado en desktop/engine-dist/radar-engine/ ($(du -sh desktop/engine-dist/radar-engine | cut -f1))"
