# Radar Bolsa

> ℹ️ **Las recomendaciones las genera un modelo propio a partir de datos públicos. No garantizan rentabilidad y no sustituyen a un asesor financiero.** La app no ejecuta operaciones ni se conecta a ningún bróker.

App de escritorio para macOS que analiza acciones y ETFs de España, Europa y EE. UU. y propone en qué invertir según tu perfil. Cada recomendación explica por qué: su puntuación, 3 razones a favor, 3 riesgos, el nivel de riesgo y un rango de precio de entrada. Todo dato muestra su fuente y su fecha.

## Funcionalidades

| Sección | Qué hace |
|---|---|
| **Test de perfil** | 5 preguntas (horizonte, tolerancia al riesgo, cantidad, objetivo y experiencia) → perfil conservador, moderado o dinámico, con un reparto orientativo entre ETFs, acciones y renta fija. Se puede repetir cuando quieras. |
| **Mis recomendaciones** | Ranking de unos 225 valores (acciones y ETFs UCITS) con la señal **Comprar / Vigilar / Evitar** ajustada a tu perfil. Cada tarjeta muestra la puntuación, el riesgo, el precio frente al rango de entrada y el motivo principal. |
| **Detalle** | Gráfico de precio, las condiciones que cumple o no para la señal, 3 razones y 3 riesgos en lenguaje sencillo, rango de entrada con sus cálculos, nivel de riesgo, desglose de la puntuación y «Cómo comprar esto». |
| **España** | IBEX 35 y Mercado Continuo (unas 108 empresas): Top 10 combinado y rankings ordenables por rentabilidad en bolsa (año, 1, 3 y 5 años, con y sin dividendos), negocio (ROE, ROIC, márgenes, crecimiento), dividendo (rentabilidad, años seguidos, payout, sostenibilidad) y valoración (PER y P/VC frente al sector). Con filtro por sector. |
| **Inicio** | Índices (IBEX 35, Euro Stoxx 50, S&P 500, EUR/USD), tus mejores oportunidades y el estado de los datos. |
| **Mi cartera** | Cartera de **operaciones ficticias**: valoración en euros con FIFO, evolución frente a un índice («cartera sombra»), señal del modelo de cada posición y diversificación por sector y país. |
| **Alertas** | Avisos de precio, variación diaria, RSI o cruce de medias, con notificación de macOS mientras la app está abierta. |
| **Cómo invertir** | Guías: elegir bróker en España, tipos de órdenes, aportaciones periódicas, fondo de emergencia y fiscalidad, con calculadoras. |
| **Metodología** | Reglas del modelo y backtest de la parte de precio (con sus límites: sin fundamentales históricos y con sesgo de supervivencia). |
| **Aprender** | Glosario de todas las métricas, conceptos básicos y calculadoras (interés compuesto e impuestos del ahorro). |
| **Buscador** | Por nombre o ticker, sin tildes («telefonica» encuentra Telefónica). Si el valor no está en el universo, se busca en Yahoo y se puntúa al momento. |

Cada métrica tiene un icono **?** con una explicación sencilla. Modo claro y oscuro, números en formato español (1.234,56 €) y horas de Madrid con su zona.

## Instalación

Ver la guía paso a paso: **[docs/INSTALACION.md](docs/INSTALACION.md)**. Explica cómo instalar el `.dmg`, crear el acceso directo en el Dock o el Escritorio y volver a generar la app.

En resumen, para generarla desde el código:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
bash desktop/scripts/build_app.sh     # → desktop/src-tauri/target/release/bundle/dmg/*.dmg
```

## Cómo funciona

```
┌──────────────────────── Radar Bolsa.app ─────────────────────────┐
│  Ventana (Tauri + React)  ──HTTP 127.0.0.1 + token──▶  Motor      │
│  desktop/src                                     (Python, FastAPI)│
│  - pantallas, formato es-ES                      src/radar        │
│  - nunca habla con Yahoo                         - datos + caché  │
│                                                  - puntuación     │
│  Rust (desktop/src-tauri) arranca el motor       - señal y perfil │
│  con puerto libre y token aleatorio, y lo        - SQLite local   │
│  cierra al salir.                                                 │
└───────────────────────────────────────────────────────────────────┘
```

- La interfaz no ve a Yahoo: todo pasa por el motor, que cachea cada llamada con su TTL.
- El motor solo escucha en `127.0.0.1` y exige el token que genera la app al arrancar.
- Las API keys se guardan en el Llavero de macOS (`keyring`).
- Los datos del usuario están en `~/Library/Application Support/Radar Bolsa/` (en desarrollo, en `data/`).

## Metodología (resumen)

- **Puntuación (0–100):** cada métrica se convierte en un percentil frente a sus comparables.
  - Valoración, salud, crecimiento y dividendo se comparan con el sector (mediana, misma región si hay al menos 5 empresas).
  - Momentum y riesgo se comparan con todo el universo.
  - Los pesos dependen del perfil: el conservador pesa más salud y riesgo; el dinámico, crecimiento y momentum. El componente de dividendo solo cuenta si tu objetivo es cobrar dividendos.
- **Señal (acciones):**
  - **Comprar** si se cumplen todas estas condiciones: puntuación ≥ 65, precio dentro o por debajo del rango de entrada, riesgo dentro de tu tolerancia, beneficio positivo y al menos 200 M de capitalización.
  - **Evitar** si la puntuación es < 40, si el riesgo está dos niveles por encima de tu tolerancia o si el valor no cotiza desde hace más de 10 días.
  - **Vigilar** en el resto de casos.
- **Señal (ETFs):** se comparan con los ETFs de referencia en coste, tamaño, riesgo y momentum. Un ETF «base de cartera» dentro de tu tolerancia sale como Comprar. La renta fija sale como Comprar si eres conservador o buscas conservar capital.
- **Riesgo:**
  - **Bajo:** volatilidad < 20 % y caída máxima < 20 % en un año.
  - **Medio:** volatilidad < 32 % y caída < 35 %.
  - **Alto:** el resto.
  - Las empresas de menos de 1.000 M suben al menos a medio, y las de menos de 200 M, a alto.
- **Rango de entrada:** el precio que tendría el valor con el PER, el P/VC y la rentabilidad FCF medianos de su sector, desde la estimación más baja hasta la mediana. No se da rango si hay menos de dos estimaciones o si discrepan más de 2,5 veces.

Todas las reglas están en el código con sus constantes (`src/radar/recommend/engine.py`, `src/radar/profile/investor.py`) y la app las muestra en cada recomendación.

## Fuentes de datos y limitaciones

- **Yahoo Finance** (`yfinance`, no oficial): cotizaciones, históricos, fundamentales y cuentas anuales. Gratuita y con la mejor cobertura de Europa, pero sin garantías. Las bolsas europeas llegan con unos 15 min de retraso.
- **Google News RSS** y **Finnhub** (opcional): noticias (las usa la versión anterior).
- **Caché:** cotizaciones 60 s, históricos diarios 6 h, fundamentales 24 h. Si la fuente falla, se muestra la última copia guardada, marcada como «copia antigua».
- **Limitaciones:**
  - A las empresas pequeñas del Continuo les faltan a veces fundamentales, y la app muestra «n/d».
  - A Yahoo le falta la comisión (TER) de algunos ETFs, y la app remite a su KID.
  - El historial de dividendos empieza como pronto en 2000.
  - Los fundamentales son la foto actual: no hay series históricas fiables en fuentes gratuitas, por eso el backtest solo prueba la parte de precio.

## Estructura

```
src/radar/        motor en Python (sin interfaz)
  api/            API local (FastAPI) que usa la app de escritorio
  data/           proveedor Yahoo, caché SQLite, servicio, bolsas y horarios
  recommend/      señal Comprar/Vigilar/Evitar, riesgo, rango de entrada, textos
  profile/        test de perfil inversor y sus reglas
  scoring/        puntuación 0–100 (y screener de la versión anterior)
  fundamentals/   catálogo de métricas y comparación sectorial
  indicators/     técnicos, riesgo, rentabilidades por plazos, ROIC
  spain.py        tabla de la sección España
  etfs.py         ETFs UCITS de referencia
  universe*.py    universo de ~225 valores y su foto
  education/ portfolio/ alerts/ news/ db/
desktop/          app de escritorio
  src/            interfaz React + TypeScript
  src-tauri/      ventana nativa (Rust) que arranca el motor
  scripts/        empaquetado (motor con PyInstaller, app con Tauri), icono
docs/             guía de instalación
tests/            pytest sin red
```

## Desarrollo

```bash
export PATH="$HOME/.local/node/bin:$HOME/.cargo/bin:$PATH"   # Node y Rust de usuario
cd desktop && npm install

npx tauri dev             # ventana de escritorio con recarga en caliente (usa el Python de .venv)

# o, en el navegador:
python -m radar.api --token dev --port 8765   # en una terminal (desde la raíz)
npm run dev                                   # en otra → http://127.0.0.1:1420

pytest                          # tests del motor, sin red
npm test                        # tests de la interfaz (formato español)
ruff check . && ruff format .
```

Tras cambiar código en `src/radar`, reinicia el motor (o `tauri dev`).

Las convenciones del proyecto están en [CLAUDE.md](CLAUDE.md).
