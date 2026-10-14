# Radar Bolsa

App personal de escritorio (macOS) de análisis bursátil que **recomienda en qué invertir** según el perfil del usuario, con un modelo propio y transparente. Prioriza España y Europa (IBEX 35, Mercado Continuo, Euro Stoxx) y cubre también EE. UU. y ETFs UCITS. Funciona solo en local.

No ejecuta operaciones ni se conecta a ningún bróker.

## Reglas de producto (no negociables)
- Las recomendaciones usan **solo** las etiquetas «Comprar», «Vigilar» y «Evitar», presentadas como **señal del modelo**. Salen de reglas fijas con constantes visibles (`recommend/engine.py`), y la app muestra qué condiciones cumple o no cada valor. Nada de órdenes fuera de esas etiquetas («compra ya», «vende»…) ni promesas de rentabilidad.
- Aviso visible en todas las pantallas: «Las recomendaciones las genera un modelo propio a partir de datos públicos. No garantizan rentabilidad y no sustituyen a un asesor financiero.»
- Todo dato mostrado lleva **fuente** y **fecha/hora** (con zona horaria) y, si aplica, el **retraso** estimado.
- La puntuación (0–100) es transparente: cada componente muestra sus entradas, su mediana de comparables, su percentil y su peso.
- Cada recomendación muestra su puntuación, 3 razones a favor, 3 riesgos (en lenguaje sencillo y con el dato concreto), el nivel de riesgo y el rango de entrada con sus cálculos.
- No se inventan datos: si la fuente no lo da (p. ej., el TER de un ETF), se muestra «n/d» y se indica dónde consultarlo.
- Nada de cajas negras: cada métrica tiene su «?» enlazado al glosario.

## Stack
- **Motor:** Python ≥ 3.11 (desarrollo en 3.14), entorno virtual `.venv`. pandas, numpy, `yfinance`. API local con FastAPI + uvicorn. SQLite. `keyring` para las API keys (Llavero de macOS).
- **App de escritorio:** Tauri 2 (Rust) + React 19 + TypeScript + Vite, en `desktop/`. Gráficos en SVG propio (sin librerías).
- **Empaquetado:** PyInstaller (motor, formato carpeta, sin pyarrow) + `tauri build` → `.app` y `.dmg` (firma ad hoc, sin notarizar).
- **Tests:** pytest (motor) y vitest (interfaz). Lint/format: ruff.
- Node y Rust están instalados en la carpeta del usuario (`~/.local/node`, `~/.cargo`): `export PATH="$HOME/.local/node/bin:$HOME/.cargo/bin:$PATH"`.
- Versión anterior en Streamlit (`app/`): sigue funcionando hasta la fase 4; no se le añaden funcionalidades.

## Estructura
```
src/radar/
  config.py          # rutas (data/ en desarrollo; ~/Library/Application Support/Radar Bolsa empaquetada), TTLs
  secrets.py         # API keys en el Llavero (keyring); .env solo como respaldo en desarrollo
  models.py          # Quote, PriceHistory, Fundamentals, Financials, SearchResult (con source + as_of)
  errors.py          # TickerNotFoundError, ProviderUnavailableError, RateLimitError
  formatting.py      # formato español (textos generados en Python)
  universe_list.py   # IBEX35, CONTINUO, Europa, EE. UU.; UNIVERSE = acciones + ETFs
  etfs.py            # ETFs UCITS de referencia con su papel (core, complement, dividend, bonds, cash)
  universe.py        # foto del universo: fundamentales + precios (+ plazos, dividendos y ROIC en España)
  spain.py           # tabla de la sección España (medianas del sector, lecturas, Top 10)
  api/               # FastAPI: app.py (rutas), state.py (Engine: universo, perfil, caché), __main__.py
  data/              # lo único que habla con Yahoo (yahoo.py, cache.py, service.py, markets.py)
  recommend/         # engine.py (señal, riesgo, rango de entrada, razones), texts.py (frases)
  profile/           # investor.py (test de perfil → nivel, reparto, pesos)
  scoring/           # score.py (puntuación 0–100) y screen.py
  fundamentals/      # catálogo de métricas (MetricDef) y comparación sectorial
  indicators/        # technical.py, risk.py, performance.py (plazos, dividendos, ROIC), summary.py
  education/ portfolio/ alerts/ news/ db/
desktop/
  src/               # React: App.tsx, api.ts (conexión con el motor), format.ts, pages/, components/
  src-tauri/         # Rust: lanza el motor (puerto libre + token), lo cierra al salir; iconos; config
  scripts/           # build_engine.sh (PyInstaller), build_app.sh (todo), make_icon.py
app/                 # Streamlit (versión anterior)
docs/INSTALACION.md  # guía de instalación para el usuario
tests/               # pytest sin red
data/                # radar.db y cache.db en desarrollo (ignorado en git: la regla es /data/)
```

## Convenciones
- Separación estricta: la interfaz (`desktop/src`) solo presenta y **solo habla con la API local**. Nunca llama a Yahoo. La API traduce HTTP a llamadas al motor. Los cálculos (`indicators`, `scoring`, `recommend`, `profile`, `fundamentals`, `spain.py`) son funciones puras sin E/S y se testean sin red.
- La API devuelve números en bruto y fechas ISO en UTC. El formato español (`1.234,56 €`, con `useGrouping: "always"`) y la hora de Madrid con su zona se aplican en `desktop/src/format.ts`. Las frases generadas en Python usan `formatting.py`.
- La API solo escucha en `127.0.0.1` y exige la cabecera `X-Radar-Token`. Al añadir un origen nuevo para la interfaz, actualizar `ALLOWED_ORIGINS` y la CSP de `tauri.conf.json`.
- Tipado con type hints en todas las funciones públicas y docstrings breves en español. TypeScript en modo estricto.
- Código (identificadores) en inglés; textos de UI, docstrings y comentarios en español.
- Errores de datos: excepciones propias. La API las convierte en JSON con `detail` y `code` (404 `not_found`, 503 `unavailable`, 409 `no_universe` / `no_profile`). La UI los muestra como mensajes amables, nunca como trazas.
- Cachés versionadas: al cambiar la estructura de un modelo o el parseo, subir `CACHE_VERSION` en `data/service.py`; al cambiar las columnas del universo, `SNAPSHOT_KEY` en `universe.py` (la app vuelve a descargar sola); al cambiar la búsqueda de noticias, `CACHE_VERSION` en `news/sources.py`.
- Migraciones de BD: solo se añaden al final de `MIGRATIONS` en `db/database.py`; nunca se editan las existentes.
- Toda métrica nueva en `fundamentals/metrics.py` necesita su entrada en `education/glossary.py` (lo comprueba un test).
- Las reglas de la señal y del perfil viven como constantes con nombre y se describen en el docstring del módulo (la API `/api/methodology` lo muestra). Al cambiar una regla: constante + docstring + entrada del glosario (`model_label`, `risk_level`, `entry_range`) + test.
- Las razones y los riesgos (`recommend/texts.py`) son frases descriptivas: un test comprueba que no contienen «compra», «vende» ni «recomend». Las etiquetas son el único sitio donde aparece «Comprar».
- Calidad mínima para «Comprar» y el Top 10: beneficio positivo, al menos 200 M de capitalización y cotizando con normalidad (último cierre de hace menos de 10 días).
- Textos externos (titulares) se muestran sin HTML y con Markdown escapado.
- Yahoo mezcla unidades (márgenes en fracción; dividendYield, debtToEquity y netExpenseRatio en %). Se normalizan en `data/yahoo.py`, nunca en la UI. El histórico trae `Close` (ajustado por dividendos: rentabilidad total e indicadores), `PriceClose` (precio real: rentabilidad bursátil y gráficos) y `Dividends`.
- Respetar los límites de las APIs: toda llamada externa pasa por la caché con TTL (cotización 60 s, histórico diario 6 h, fundamentales y cuentas 24 h, noticias 30 min). Ante un 429 o un error de red se sirve la copia antigua marcada como `stale`; no se reintenta en bucle.
- Fechas en UTC internamente; en la UI, Europe/Madrid indicando la zona.
- Tests obligatorios para `indicators/`, `scoring/`, `recommend/`, `profile/`, `portfolio/` y el backtest, con datos sintéticos de resultado conocido. La API se testea con un proveedor falso (`tests/test_api.py`).
- Colores: semáforo verde/ámbar/rojo (tokens `--buy`, `--watch`, `--avoid` en `styles.css`), **siempre** con icono y texto, nunca solo color. Sin gráficos de doble eje. Modo claro y oscuro con los mismos tokens.
- La interfaz sigue los bocetos aprobados en la fase 0 (https://claude.ai/artifact/Xj81yKmKZxuDPqFb2brN6Q).
- Trabajo por fases; cada una queda funcionando (tests en verde y app empaquetada) antes de pasar a la siguiente. Commits pequeños en español y modo imperativo (`Añade cálculo de RSI`).

## Comandos
```bash
# Motor
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check . && ruff format .
python -m radar.api --token dev --port 8765     # API para desarrollo en el navegador

# App de escritorio
export PATH="$HOME/.local/node/bin:$HOME/.cargo/bin:$PATH"
cd desktop && npm install
npx tauri dev                                   # ventana con recarga (usa el Python de .venv)
npm run dev                                     # solo la interfaz → http://127.0.0.1:1420 (con el motor en 8765)
npm test && npx tsc --noEmit
bash desktop/scripts/build_app.sh               # (desde la raíz) motor + .app + .dmg
```
