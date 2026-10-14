# Radar Bolsa

> ⚠️ **Herramienta educativa. No es asesoramiento financiero.** No ejecuta operaciones ni se conecta a ningún bróker.

App personal de seguimiento y análisis bursátil centrada en los mercados españoles y europeos (IBEX 35, Euro Stoxx) y que también cubre EE. UU. y los ETFs. Está construida con Python y Streamlit como proyecto de aprendizaje de análisis de datos.

## Funcionalidades

- [x] Watchlist persistente (acciones de España, Europa y EE. UU., y ETFs)
- [x] Cotizaciones con refresco automático, indicando la fuente, la hora y el retraso
- [x] Gráficos de velas y de línea (1D, 1S, 1M, 6M, 1A, 5A, Máx)
- [x] Métricas fundamentales básicas
- [ ] Comparación sectorial completa
- [ ] Análisis técnico (SMA, RSI, MACD, Bollinger)
- [ ] Score transparente 0–100
- [ ] Screener y comparador
- [ ] Noticias y sentimiento
- [ ] Cartera simulada
- [ ] Alertas
- [ ] Sección educativa

## Instalación

Requisitos: Python 3.11 o superior.

```bash
git clone <url-del-repo> radar-bolsa
cd radar-bolsa
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # opcional: añade tu clave de Finnhub
```

## Uso

```bash
streamlit run app/Home.py
```

Se abre en http://localhost:8501. Para añadir empresas a la watchlist, escribe su ticker con el sufijo de la bolsa:

| Bolsa | Sufijo | Ejemplo |
|---|---|---|
| Madrid (BME) | `.MC` | `SAN.MC`, `ITX.MC`, `IBE.MC` |
| Xetra (Alemania) | `.DE` | `SAP.DE` |
| París | `.PA` | `MC.PA` |
| Ámsterdam | `.AS` | `ASML.AS` |
| Milán | `.MI` | `ENI.MI` |
| Londres | `.L` | `SHEL.L` |
| EE. UU. | (ninguno) | `AAPL`, `MSFT` |
| Índices | `^` | `^IBEX`, `^GSPC` |

## Fuentes de datos

- **Yahoo Finance** (librería `yfinance`, no oficial) es la fuente principal. Las bolsas europeas llegan con unos **15 minutos de retraso**, y la app muestra en cada dato su hora y su retraso.
- Las respuestas se guardan en una caché local (`data/cache.db`, SQLite) para no saturar la API: las cotizaciones durante 60 s, los históricos diarios 6 h y los fundamentales 24 h. Si la fuente falla, se muestran los últimos datos guardados, marcados como **antiguos**.

### Limitaciones conocidas de los datos

- **Retraso declarado frente a real**: la watchlist muestra el retraso que declara Yahoo y la antigüedad real de la última cotización. No siempre coinciden: algunos ETFs europeos se declaran "tiempo real" y llegan con 15 min de retraso.
- **Volumen intradía incompleto**: en los rangos 1D y 1S, Yahoo no incluye las subastas ni todas las operaciones. Para comparar volúmenes, usa rangos diarios.
- **Históricos largos con errores**: algunos valores europeos tienen saltos falsos en los datos antiguos, por ajustes de *split* mal aplicados. La escala logarítmica los hace visibles.
- **ETFs europeos**: Yahoo publica pocas métricas (a menudo solo la comisión TER).
- **ADRs**: un ticker sin sufijo, como `SAN`, es el certificado en dólares que cotiza en Nueva York, no la acción de Madrid (`SAN.MC`).

## Estructura

```
src/radar/   lógica (datos, caché, BD, formato): sin Streamlit y testeable
app/         interfaz Streamlit (Home.py + views/ + components/)
tests/       pytest, sin red (proveedores falsos y datos sintéticos)
data/        radar.db (watchlist) y cache.db; se crean solos (fuera de git)
```

## Desarrollo

```bash
pytest                          # tests
ruff check . && ruff format .   # lint y formato
```

> Streamlit solo recarga automáticamente los archivos de `app/`. Si cambias código en `src/`, reinicia `streamlit run`.

La arquitectura y las convenciones están en [CLAUDE.md](CLAUDE.md).
