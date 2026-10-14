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
- Las respuestas se guardan en una caché local (SQLite) para no saturar la API. Si la fuente falla, se muestran los últimos datos guardados, marcados como antiguos.

## Desarrollo

```bash
pytest                          # tests
ruff check . && ruff format .   # lint y formato
```

La arquitectura y las convenciones están en [CLAUDE.md](CLAUDE.md).
