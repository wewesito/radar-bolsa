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
- Datos: `yfinance` como fuente principal (la mejor cobertura gratuita de Europa: `.MC`, `.DE`, `.PA`, `.AS`, `.MI`…). Finnhub (plan gratuito) es opcional y secundario, para cotizaciones o noticias de EE. UU.
- Persistencia: SQLite (watchlist, cartera simulada, alertas y caché de datos).
- Tests: pytest. Lint/format: ruff.
- Secretos en `.env` (en `.gitignore`), cargados con `python-dotenv`. Se versiona `.env.example` sin valores.

## Estructura
```
src/radar/
  config.py          # settings, rutas, TTLs de caché, carga de .env
  models.py          # dataclasses: Quote, PriceHistory, Fundamentals... (siempre con source + as_of)
  data/              # obtención de datos (lo único que habla con APIs externas)
    base.py          # Protocol DataProvider
    yahoo.py         # proveedor yfinance
    finnhub.py       # proveedor opcional
    cache.py         # caché SQLite con TTL
    markets.py       # sufijos, bolsas, horarios, retrasos, ¿mercado abierto?
  indicators/        # funciones puras: SMA, RSI, MACD, Bollinger, soportes/resistencias, riesgo
  fundamentals/      # métricas y comparación con la media del sector
  scoring/           # score 0–100 por componentes, con desglose explicable
  db/                # esquema SQLite y repositorios (watchlist, portfolio, alerts)
  news/              # noticias y sentimiento por léxico
  portfolio/         # lógica de la cartera simulada y benchmarks
  alerts/            # evaluación de reglas de alerta
  education/         # contenido del glosario (datos, no lógica)
app/
  Home.py            # punto de entrada de Streamlit
  pages/             # una página por funcionalidad
  components/        # widgets reutilizables (badge de fuente/retraso, disclaimer…)
tests/               # espejo de src/radar/
data/                # radar.db y la caché (ignorado en git)
```

## Convenciones
- Separación estricta: `app/` solo presenta. Nunca llama a `yfinance` directamente: pasa por `radar.data`. Los cálculos (`indicators`, `scoring`, `fundamentals`) son funciones puras sin E/S, por lo que se pueden testear sin red.
- Tipado con type hints en todas las funciones públicas y docstrings breves en español.
- Código (identificadores) en inglés; textos de UI, docstrings y comentarios en español.
- Errores de datos: excepciones propias (`TickerNotFoundError`, `ProviderUnavailableError`, `RateLimitError`). La UI las muestra como mensajes amables, nunca como trazas.
- Respetar los límites de las APIs: toda llamada externa pasa por la caché con TTL (cotización ~60 s, histórico diario ~6 h, fundamentales ~24 h). Backoff ante los errores 429.
- Fechas en UTC internamente; en la UI se muestran en Europe/Madrid indicando la zona.
- Tests obligatorios para `indicators/` y `scoring/` con datos sintéticos de resultado conocido.
- Commits pequeños en español y modo imperativo (`Añade cálculo de RSI`).

## Comandos
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
streamlit run app/Home.py
pytest
ruff check . && ruff format .
```
