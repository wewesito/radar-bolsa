#!/usr/bin/env bash
# Construye la app de escritorio completa: motor (PyInstaller) + ventana (Tauri) → .app y .dmg.
# Uso (desde la raíz del proyecto):  bash desktop/scripts/build_app.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

# Node y Rust instalados en la carpeta del usuario (ver docs/INSTALACION.md)
export PATH="$HOME/.local/node/bin:$HOME/.cargo/bin:$PATH"

source .venv/bin/activate
bash desktop/scripts/build_engine.sh

cd desktop
npm install --silent
# CI=true: sin el AppleScript que decora la ventana del .dmg (se queda esperando un permiso)
CI=true npx tauri build --config src-tauri/tauri.bundle.json

echo
echo "Listo:"
ls -1 src-tauri/target/release/bundle/dmg/*.dmg
ls -d src-tauri/target/release/bundle/macos/*.app
