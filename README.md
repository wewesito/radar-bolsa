# Radar Bolsa

> ⚠️ **Herramienta educativa. No es asesoramiento financiero.** No ejecuta operaciones ni se conecta a ningún bróker. Presenta datos, puntuaciones y argumentos a favor y en contra; las decisiones son tuyas.

App personal de seguimiento y análisis bursátil, centrada en los mercados español y europeo (IBEX 35, Euro Stoxx) y con cobertura también de EE. UU. y de los ETFs. Está hecha con Python y Streamlit como proyecto de aprendizaje de análisis de datos, y todo cálculo es transparente: cada número muestra su fuente, su fecha y cómo se ha obtenido.

## Funcionalidades

| Página | Qué hace |
|---|---|
| 👀 **Watchlist** | Seguimiento de acciones, ETFs e índices con refresco automático. Muestra el estado del mercado, el retraso declarado por la fuente y la antigüedad real del dato, y comprueba las alertas en cada refresco. |
| 🏢 **Empresa** | Ficha con cinco secciones: **Gráfico** (velas o línea, de 1D a Máx, escala logarítmica), **Fundamentales** (comparados con la mediana del sector), **Técnico** (SMA 50/200, RSI, MACD, Bollinger, soportes y resistencias), **Score** (0–100 con desglose y fórmula) y **Noticias** (con sentimiento). |
| 🔎 **Screener** | Filtra ~140 empresas por región, sector, score y métricas. |
| ⚖️ **Comparador** | De 2 a 4 empresas lado a lado: evolución en base 100, métricas y score. |
| 💼 **Cartera simulada** | Operaciones ficticias con FIFO, valoradas en euros (incluido el efecto divisa), comparadas con una "cartera sombra" en el MSCI World, el S&P 500 o el IBEX, y con su diversificación por posición, sector y país. |
| 🔔 **Alertas** | Avisos al cruzar un umbral de precio, de variación diaria o de RSI, o un cruce con las medias de 50 o 200 sesiones. Se pueden comprobar también desde la terminal. |
| 📖 **Aprende** | Glosario de todas las métricas, conceptos básicos, calculadora de interés compuesto y del efecto de las comisiones, perfil de riesgo orientativo y fiscalidad general en España. |

## Instalación

Requisitos: Python 3.11 o superior (desarrollado con 3.14).

```bash
git clone <url-del-repo> radar-bolsa
cd radar-bolsa
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # opcional: clave gratuita de Finnhub para noticias de EE. UU.
```

## Uso

```bash
streamlit run app/Home.py
```

Se abre en http://localhost:8501. La primera vez que ejecutas Streamlit te pide un email (opcional): pulsa Enter para saltarlo, o arranca con `--server.headless true` y abre la dirección a mano. Para pararla, `Ctrl+C` en la terminal.

La primera vez que entres en **Fundamentales**, **Score**, **Screener** o **Comparador**, pulsa *Construir universo* para descargar el universo de referencia (~140 empresas, ~30 s). Conviene actualizarlo una vez por semana.

### Tickers

Se escribe el ticker con el sufijo de su bolsa (formato de Yahoo Finance):

| Bolsa | Sufijo | Ejemplo |
|---|---|---|
| Madrid (BME) | `.MC` | `SAN.MC`, `ITX.MC`, `IBE.MC` |
| Xetra (Alemania) | `.DE` | `SAP.DE`, `EUNL.DE` |
| París · Ámsterdam · Milán | `.PA` · `.AS` · `.MI` | `MC.PA`, `ASML.AS`, `ENI.MI` |
| Londres (precios en peniques) | `.L` | `SHEL.L` |
| EE. UU. | (ninguno) | `AAPL`, `MSFT` |
| Índices | `^` | `^IBEX`, `^GSPC` |

Ojo: sin sufijo, `SAN` es el **ADR** de Santander en Nueva York (en dólares), no la acción de Madrid.

### Alertas con la app cerrada (opcional)

```bash
.venv/bin/python -m radar.alerts.checker --notify   # notificación de macOS por cada alerta disparada
```

Se puede programar con `cron`, por ejemplo cada 15 minutos en horario de mercado.

## Metodología (resumen)

- **Comparación sectorial:** se usa la **mediana** del sector, que resiste mejor a los valores extremos. Se compara con la misma región (Europa o EE. UU.) si hay al menos 5 empresas; si no, con el sector a nivel mundial.
- **Score (0–100):** cada métrica se convierte en un percentil frente a sus comparables.
  - Valoración, salud y crecimiento se comparan con el sector; momentum y riesgo, con todo el universo.
  - Cada componente es la media de sus percentiles; el total es la media ponderada de los componentes (20 % cada uno por defecto, ajustable).
  - Si falta un componente, su peso se reparte entre los demás. Con menos de 3 componentes no se da total.
- **RSI:** se calcula con el suavizado de Wilder, verificado contra su ejemplo de referencia.
- **Cartera:** se usa FIFO (el método que exige la normativa española) y el tipo de cambio del día de cada operación. La "cartera sombra" invierte en el índice los mismos euros en las mismas fechas.
- **Alertas:** saltan al cruzar el umbral, no mientras se cumple la condición (*edge-triggered*).
- **Sentimiento:** léxico financiero en español e inglés con una regla de negación. Muestra las palabras detectadas en cada titular.

## Fuentes de datos

- **Yahoo Finance** (librería `yfinance`, no oficial): cotizaciones, históricos, fundamentales y tipos de cambio. Gratuita y con la mejor cobertura de Europa, pero sin garantías.
- **Google News RSS**: noticias, para uso personal y no comercial. Las noticias de Yahoo devuelven listas vacías en la versión actual de `yfinance`.
- **Finnhub** (opcional, con clave gratuita): noticias de empresas de EE. UU.
- Para no saturar las APIs, todo pasa por una caché local en SQLite (`data/cache.db`): cotizaciones 60 s, históricos intradía 2 min, históricos diarios 6 h, fundamentales 24 h y noticias 30 min. Si la fuente falla, se muestran los últimos datos guardados, marcados como **antiguos**.

### Limitaciones conocidas de los datos

- **Retraso:** las bolsas europeas llegan con unos 15 min de retraso. La watchlist muestra el retraso *declarado* por la fuente y la *antigüedad real* del dato, que no siempre coinciden.
- **Volumen intradía incompleto** (1D y 1S): Yahoo no incluye las subastas ni todas las operaciones.
- **Históricos antiguos con errores:** Yahoo devuelve a veces precios negativos o saltos falsos por *splits* mal ajustados. La app descarta los precios ≤ 0 y avisa de los saltos de más del 40 % entre velas.
- **Fundamentales:** a los bancos les faltan métricas que no tienen sentido para ellos (deuda/patrimonio, margen bruto). Algunos PER salen sospechosos por ajustes de *splits*. Los ETFs europeos tienen poca información.
- **Sector:** es una categoría gruesa. "Consumo cíclico" mezcla, por ejemplo, el lujo con los coches.

## Estructura

```
src/radar/      lógica sin Streamlit, testeable
  data/         proveedores (Yahoo), caché, servicio, mercados
  fundamentals/ catálogo de métricas y comparación sectorial
  indicators/   indicadores técnicos, riesgo y lecturas neutras
  scoring/      score, screener y comparador
  news/         fuentes de noticias y sentimiento
  portfolio/    cartera simulada (FIFO, valoración, cartera sombra)
  alerts/       reglas y comprobación de alertas
  education/    glosario, conceptos y cálculos educativos
  db/           SQLite con migraciones (watchlist, trades, alerts)
app/            interfaz Streamlit (Home.py + views/ + components/)
tests/          pytest sin red (proveedores falsos y datos sintéticos)
data/           radar.db y cache.db; se crean solos (fuera de git)
```

## Desarrollo

```bash
pytest                          # 147 tests, sin red
ruff check . && ruff format .   # lint y formato
```

> Streamlit solo recarga automáticamente los archivos de `app/`. Si cambias código en `src/`, reinicia `streamlit run`.

Las convenciones del proyecto están en [CLAUDE.md](CLAUDE.md).
