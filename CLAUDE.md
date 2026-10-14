# Radar Bolsa

App personal y **educativa** de seguimiento y análisis bursátil. Su prioridad son los mercados españoles y europeos (IBEX 35, Euro Stoxx) y también cubre EE. UU. y los ETFs. Funciona solo en local.

**No es asesoramiento financiero.** No ejecuta operaciones ni se conecta a ningún bróker.

## Reglas de producto (no negociables)
- Nunca generar recomendaciones imperativas ("compra X", "vende Y"). Mostrar datos, puntuaciones y argumentos a favor y en contra.
- Aviso visible en todas las páginas: "Herramienta educativa, no asesoramiento financiero".
- Todo dato mostrado lleva **fuente** y **fecha/hora** (con zona horaria) y, si aplica, el **retraso** estimado.
- El score (0–100) es transparente: cada componente muestra su fórmula, sus entradas y su peso.
- Nada de cajas negras: cada indicador enlaza a su explicación en el glosario.

## Stack
- Python ≥ 3.11 (desarrollo en 3.14), entorno virtual `.venv`.
- UI: Streamlit (multipágina). Gráficos: Plotly.
- Cálculo: pandas, numpy.
- Datos: `yfinance` como fuente principal (la mejor cobertura gratuita de Europa: `.MC`, `.DE`, `.PA`, `.AS`, `.MI`…). Noticias: Google News RSS; Finnhub (plan gratuito, opcional) para noticias de EE. UU.
- Persistencia: SQLite (watchlist, cartera simulada, alertas y caché de datos).
- Tests: pytest. Lint/format: ruff.
- Secretos en `.env` (en `.gitignore`), cargados con `python-dotenv`. Se versiona `.env.example` sin valores.

## Estructura
```
src/radar/
  config.py          # rutas, TTLs de caché, carga de .env
  models.py          # Quote, PriceHistory, Fundamentals (siempre con source + as_of)
  errors.py          # TickerNotFoundError, ProviderUnavailableError, RateLimitError
  formatting.py      # números, %, importes y fechas en formato español
  universe_list.py   # tickers del universo de referencia (~140)
  universe.py        # foto del universo: fundamentales + estadísticas de precio
  data/              # lo único que habla con Yahoo
    base.py          # Protocol DataProvider
    yahoo.py         # proveedor yfinance: normaliza unidades y limpia históricos
    cache.py         # caché SQLite con TTL (JSON, no pickle)
    service.py       # proveedor + caché (+ copia antigua si la fuente falla)
    markets.py       # sufijos, bolsas, horarios, rangos de gráfico
  fundamentals/      # catálogo de métricas (MetricDef) y comparación sectorial
  indicators/        # technical.py, risk.py, summary.py (lecturas neutras)
  scoring/           # score.py (score 0–100) y screen.py (screener/comparador)
  news/              # sources.py (Google News RSS, Finnhub opcional), sentiment.py
  portfolio/         # calc.py (FIFO, valoración, cartera sombra), market.py (precios/FX)
  alerts/            # rules.py (edge-triggered), checker.py (también CLI)
  education/         # glossary.py, concepts.py (contenido), finance_math.py
  db/                # database.py (migraciones), watchlist.py, trades.py, alerts.py
app/
  Home.py            # punto de entrada: st.navigation con las páginas
  views/             # una página por funcionalidad (NO llamarla pages/: Streamlit la
                     # trataría como su sistema antiguo de páginas e ignoraría st.navigation)
  components/        # vistas reutilizables y gráficos (charts.py)
tests/               # pytest sin red
data/                # radar.db y cache.db (ignorado en git)
```

## Convenciones
- Separación estricta: `app/` solo presenta. Nunca llama a `yfinance` directamente: pasa por `radar.data`. Los cálculos (`indicators`, `scoring`, `fundamentals`) son funciones puras sin E/S, por lo que se pueden testear sin red.
- Tipado con type hints en todas las funciones públicas y docstrings breves en español.
- Código (identificadores) en inglés; textos de UI, docstrings y comentarios en español.
- Errores de datos: excepciones propias (`TickerNotFoundError`, `ProviderUnavailableError`, `RateLimitError`). La UI las muestra como mensajes amables, nunca como trazas.
- Cachés versionadas: al cambiar la estructura de un modelo o el parseo, subir `CACHE_VERSION` en `data/service.py`; al cambiar las columnas del universo, `SNAPSHOT_KEY` en `universe.py`; al cambiar la búsqueda de noticias, `CACHE_VERSION` en `news/sources.py`.
- Migraciones de BD: solo se añaden al final de `MIGRATIONS` en `db/database.py`; nunca se editan las existentes.
- Toda métrica nueva en `fundamentals/metrics.py` necesita su entrada en `education/glossary.py` (lo comprueba un test).
- Lenguaje neutro: hay tests que comprueban que las lecturas técnicas y los argumentos del score no contienen "compra", "vende", "recomend"...
- Textos externos (titulares) se muestran sin HTML y con Markdown escapado.
- Yahoo mezcla unidades (márgenes en fracción; dividendYield, debtToEquity y netExpenseRatio en %). Normalizar en `data/yahoo.py`, nunca en la UI.
- Respetar los límites de las APIs: toda llamada externa pasa por la caché con TTL (cotización 60 s, histórico diario 6 h, fundamentales 24 h, noticias 30 min). Ante un error 429 o de red se sirve la copia antigua marcada como `stale`; no se reintenta en bucle.
- Fechas en UTC internamente; en la UI se muestran en Europe/Madrid indicando la zona.
- Tests obligatorios para `indicators/`, `scoring/` y `portfolio/` con datos sintéticos de resultado conocido.
- Colores de gráficos: paleta categórica fija de `components/charts.py` (azul sube / rojo baja, nunca verde/rojo); sin gráficos de doble eje.
- Commits pequeños en español y modo imperativo (`Añade cálculo de RSI`).

## Comandos
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
streamlit run app/Home.py   # reiniciar tras cambiar src/ (Streamlit solo recarga app/)
pytest
ruff check . && ruff format .
```
