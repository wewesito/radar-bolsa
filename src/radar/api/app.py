"""API HTTP local del motor. Solo escucha en 127.0.0.1 y exige un token por petición.

La ventana de escritorio (Tauri) arranca el motor con un puerto libre y un token aleatorio;
nadie más en el equipo puede usar la API sin ese token. Devuelve números en bruto y fechas
ISO en UTC: el formato español y la zona de Madrid se aplican en la interfaz.
"""

import math
import unicodedata
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from datetime import date as datetime_date
from typing import Any, Literal

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from radar import __version__, recommend, scoring
from radar.alerts.rules import METRIC_LABELS, Alert, describe
from radar.api.state import Engine, NoProfileError, NoUniverseError
from radar.backtest import engine as backtest_engine
from radar.data.markets import exchange_for
from radar.education.concepts import CONCEPTS
from radar.education.finance_math import compound_growth, real_return, savings_tax
from radar.education.glossary import ENTRIES
from radar.education.guides import GUIDES
from radar.errors import ProviderUnavailableError, RadarError, TickerNotFoundError
from radar.etfs import BY_TICKER as ETF_INFO
from radar.portfolio import service as portfolio_service
from radar.portfolio.calc import PortfolioError
from radar.portfolio.market import BENCHMARKS
from radar.profile import investor
from radar.profile.investor import PROFILE_DESCRIPTIONS, QUESTIONS
from radar.recommend.engine import LABEL_ES, Recommendation
from radar.scoring.score import COMPONENTS
from radar.secrets import secret_status, set_secret
from radar.spain import spain_table
from radar.universe import STALE_AFTER_DAYS

# Orígenes de la ventana de Tauri (macOS / Windows) y del servidor de desarrollo de Vite
ALLOWED_ORIGINS = [
    "tauri://localhost",
    "http://tauri.localhost",
    "https://tauri.localhost",
    "http://localhost:1420",
    "http://127.0.0.1:1420",
]

MARKETS = [
    ("^IBEX", "IBEX 35"),
    ("^STOXX50E", "Euro Stoxx 50"),
    ("^GSPC", "S&P 500"),
    ("EURUSD=X", "EUR/USD"),
]
HISTORY_RANGES = {"1M": "1M", "6M": "6M", "1A": "1A", "5A": "5A", "MAX": "Máx"}
SOURCE = "Yahoo Finance"


def clean(obj: Any) -> Any:
    """Convierte a JSON estándar: NaN/inf → None, fechas → ISO, dataclasses → dict."""
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, datetime):
        return obj.isoformat()
    if is_dataclass(obj) and not isinstance(obj, type):
        return clean(asdict(obj))
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [clean(v) for v in obj]
    if hasattr(obj, "item"):  # escalares de numpy
        return clean(obj.item())
    return obj


def _fold(text: str) -> str:
    """Minúsculas y sin tildes, para buscar 'telefonica' y encontrar 'Telefónica'."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def market_info(ticker: str) -> dict:
    ex = exchange_for(ticker)
    if ex is None:
        return {"exchange": None, "country": None, "tz": None, "delay_minutes": None}
    return {
        "exchange": ex.name,
        "country": ex.country,
        "tz": ex.tz,
        "opens": ex.open.strftime("%H:%M"),
        "closes": ex.close.strftime("%H:%M"),
        "delay_minutes": ex.typical_delay_min,
    }


def rec_summary(r: Recommendation) -> dict:
    """Versión ligera para las tarjetas (sin componentes ni estimaciones)."""
    d = r.to_dict()
    entry = d.pop("entry")
    for k in ("components", "checks", "notes"):
        d.pop(k)
    d["pros"] = d["pros"][:1]
    d["entry"] = (
        {k: entry[k] for k in ("low", "high", "position")} if entry and entry["low"] else None
    )
    d["market"] = market_info(r.ticker)
    return d


class ProfileIn(BaseModel):
    horizon: int
    reaction: int
    amount: int
    objective: str
    experience: int


class TradeIn(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    side: Literal["BUY", "SELL"]
    quantity: float = Field(gt=0)
    price: float | None = Field(default=None, gt=0)
    fee: float = Field(default=0, ge=0)
    date: datetime_date
    note: str | None = Field(default=None, max_length=300)


class AlertIn(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    metric: Literal["price", "change_pct", "rsi", "sma50", "sma200"]
    op: Literal["above", "below"]
    threshold: float | None = None


class SecretIn(BaseModel):
    name: str
    value: str


def create_app(engine: Engine, token: str) -> FastAPI:
    app = FastAPI(title="Radar Bolsa", version=__version__, docs_url=None, redoc_url=None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def check_token(x_radar_token: str = Header(default="")) -> None:
        if x_radar_token != token:
            raise HTTPException(401, "Token no válido")

    api = APIRouter(prefix="/api", dependencies=[Depends(check_token)])

    @app.exception_handler(TickerNotFoundError)
    async def not_found(_: Request, e: TickerNotFoundError) -> JSONResponse:
        return JSONResponse({"detail": str(e), "code": "not_found"}, status_code=404)

    @app.exception_handler(ProviderUnavailableError)
    async def unavailable(_: Request, e: ProviderUnavailableError) -> JSONResponse:
        return JSONResponse({"detail": str(e), "code": "unavailable"}, status_code=503)

    @app.exception_handler(RadarError)
    async def radar_error(_: Request, e: RadarError) -> JSONResponse:
        return JSONResponse({"detail": str(e), "code": "error"}, status_code=500)

    @app.exception_handler(NoUniverseError)
    async def no_universe(_: Request, __: NoUniverseError) -> JSONResponse:
        return JSONResponse(
            {"detail": "Todavía no hay datos descargados.", "code": "no_universe"},
            status_code=409,
        )

    @app.exception_handler(NoProfileError)
    async def no_profile(_: Request, __: NoProfileError) -> JSONResponse:
        return JSONResponse(
            {"detail": "Aún no has hecho el test de perfil.", "code": "no_profile"},
            status_code=409,
        )

    @app.exception_handler(PortfolioError)
    async def portfolio_error(_: Request, e: PortfolioError) -> JSONResponse:
        return JSONResponse({"detail": str(e), "code": "invalid"}, status_code=422)

    @app.get("/health")
    def health() -> dict:
        return {"ok": True, "version": __version__}

    # --- Perfil -----------------------------------------------------------------------

    @api.get("/profile/questions")
    def questions() -> list[dict]:
        return QUESTIONS

    @api.get("/profile")
    def get_profile() -> dict:
        a = engine.answers()
        if a is None:
            return {"answers": None, "profile": None}
        p = investor.compute_profile(a)
        return clean(
            {
                "answers": asdict(a),
                "profile": {**p.to_dict(), "description": PROFILE_DESCRIPTIONS[p.level]},
            }
        )

    @api.put("/profile")
    def put_profile(body: ProfileIn) -> dict:
        try:
            p = engine.save_profile(body.model_dump())
        except (ValueError, KeyError) as e:
            raise HTTPException(422, str(e)) from e
        return clean(
            {
                "answers": asdict(p.answers),
                "profile": {**p.to_dict(), "description": PROFILE_DESCRIPTIONS[p.level]},
            }
        )

    # --- Universo ---------------------------------------------------------------------

    @api.get("/universe/status")
    def universe_status() -> dict:
        snap = engine.snapshot
        return clean(
            {
                "built_at": snap.built_at if snap else None,
                "age_days": snap.age_days if snap else None,
                "stale": bool(snap and snap.age_days > STALE_AFTER_DAYS),
                "rows": len(snap.df) if snap else 0,
                "failed": snap.failed if snap else [],
                "build": asdict(engine.build),
                "source": SOURCE,
            }
        )

    @api.post("/universe/build")
    def universe_build() -> dict:
        started = engine.start_build()
        return {"started": started, "build": asdict(engine.build)}

    # --- Backtest ---------------------------------------------------------------------

    @api.get("/backtest")
    def backtest() -> dict:
        """Último resultado en caché (o null) y estado del cálculo en marcha."""
        bt = engine.backtest
        return clean(
            {"result": bt.cached(), "running": bt.status.running, "error": bt.status.error}
        )

    @api.post("/backtest/run")
    def backtest_run() -> dict:
        started = engine.backtest.start(engine.universe())
        return {"started": started}

    # --- Recomendaciones --------------------------------------------------------------

    @api.get("/recommendations")
    def recommendations() -> dict:
        profile = engine.profile()
        recs = engine.recommendations(profile)
        counts = {k: sum(r.label == k for r in recs) for k in LABEL_ES}
        return clean(
            {
                "built_at": engine.universe().built_at,
                "source": SOURCE,
                "profile": profile.to_dict(),
                "counts": counts,
                "items": [rec_summary(r) for r in recs],
            }
        )

    @api.get("/recommendations/{ticker}")
    def recommendation(ticker: str) -> dict:
        profile, is_default = engine.profile_or_default()
        rec = engine.recommendation(ticker.upper(), profile)
        d = rec.to_dict()
        d["market"] = market_info(rec.ticker)
        d["profile"] = profile.to_dict()
        d["profile_is_default"] = is_default
        d["source"] = SOURCE
        d["row"] = engine.universe_row(rec.ticker)
        etf = ETF_INFO.get(rec.ticker)
        d["etf"] = asdict(etf) if etf else None
        return clean(d)

    # --- España -----------------------------------------------------------------------

    @api.get("/spain")
    def spain() -> dict:
        profile, is_default = engine.profile_or_default()
        recs = {r.ticker: r for r in engine.recommendations(profile)}
        return clean(
            {
                "built_at": engine.universe().built_at,
                "source": SOURCE,
                "profile_label": profile.label,
                "profile_is_default": is_default,
                "items": spain_table(engine.universe().df, recs),
            }
        )

    # --- Precios ----------------------------------------------------------------------

    @api.get("/history/{ticker}")
    def history(ticker: str, range: str = "1A") -> dict:  # noqa: A002 (nombre del parámetro)
        if range not in HISTORY_RANGES:
            raise HTTPException(422, "Rango no válido")
        h = engine.svc.get_history(ticker.upper(), HISTORY_RANGES[range])
        col = h.data["PriceClose"] if "PriceClose" in h.data else h.data["Close"]
        return clean(
            {
                "ticker": h.ticker,
                "range": range,
                "interval": h.interval,
                "points": [[ts.isoformat(), float(v)] for ts, v in col.items()],
                "as_of": h.as_of,
                "source": h.source,
                "stale": h.stale,
            }
        )

    def quote_dict(q) -> dict:
        return {
            "ticker": q.ticker,
            "name": q.name,
            "price": q.price,
            "change_pct": q.change_pct,
            "currency": q.currency,
            "exchange": q.exchange,
            "market_state": q.market_state,
            "delay_minutes": q.delay_minutes,
            "as_of": q.as_of,
            "source": q.source,
            "stale": q.stale,
        }

    @api.get("/quote/{ticker}")
    def quote(ticker: str) -> dict:
        return clean(quote_dict(engine.svc.get_quote(ticker.upper())))

    @api.get("/markets")
    def markets() -> list[dict]:
        quotes = engine.svc.get_quotes([t for t, _ in MARKETS])
        out = []
        for ticker, label in MARKETS:
            q = quotes[ticker]
            item: dict = {"ticker": ticker, "label": label}
            if isinstance(q, RadarError):
                item["error"] = str(q)
            else:
                item.update(quote_dict(q))
                try:
                    close = engine.svc.get_history(ticker, "1M").data["Close"]
                    item["spark"] = [float(v) for v in close.tail(22)]
                except RadarError:
                    item["spark"] = []
            out.append(item)
        return clean(out)

    # --- Búsqueda ---------------------------------------------------------------------

    @api.get("/search")
    def search(q: str) -> list[dict]:
        query = _fold(q.strip())
        if len(query) < 2:
            return []
        results: list[dict] = []
        if engine.snapshot is not None:
            df = engine.snapshot.df
            for row in df[["ticker", "name", "quote_type"]].to_dict("records"):
                name, ticker = _fold(str(row["name"] or "")), row["ticker"].lower()
                if ticker.startswith(query) or query in name:
                    rank = (
                        0 if ticker.split(".")[0] == query else 1 if ticker.startswith(query) else 2
                    )
                    results.append(
                        {
                            "ticker": row["ticker"],
                            "name": ETF_INFO[row["ticker"]].short_name
                            if row["ticker"] in ETF_INFO
                            else row["name"],
                            "quote_type": row["quote_type"],
                            "exchange": market_info(row["ticker"])["exchange"],
                            "in_universe": True,
                            "_rank": rank,
                        }
                    )
        results.sort(key=lambda r: (r.pop("_rank"), r["name"] or ""))
        results = results[:8]
        if len(results) < 5:
            known = {r["ticker"] for r in results}
            for s in engine.svc.search(q.strip()):
                if s.ticker not in known and s.quote_type in ("EQUITY", "ETF"):
                    results.append({**asdict(s), "in_universe": False})
        return clean(results[:10])

    # --- Cartera simulada -------------------------------------------------------------

    def holding_info(ticker: str) -> dict:
        row = engine.universe_row(ticker) if engine.snapshot is not None else None
        if row:
            return {
                "name": row.get("name"),
                "sector": row.get("sector"),
                "country": row.get("country"),
            }
        try:
            f = engine.svc.get_fundamentals(ticker)
            return {"name": f.name, "sector": f.sector, "country": f.country}
        except RadarError:
            return {}

    @api.get("/portfolio")
    def portfolio(bench: str = "EUNL.DE") -> dict:
        if bench not in BENCHMARKS.values():
            raise HTTPException(422, "Índice de referencia no válido.")
        trades = engine.trades.list()
        view = portfolio_service.portfolio_view(engine.svc, trades, bench, holding_info)
        labels: dict[str, str] = {}
        if engine.answers() is not None and engine.snapshot is not None:
            recs = {r.ticker: r for r in engine.recommendations(engine.profile())}
            labels = {t: LABEL_ES[r.label] for t, r in recs.items()}
        for p in view["positions"]:
            p["label"] = labels.get(p["ticker"])
        view["benchmarks"] = [{"ticker": t, "name": n} for n, t in BENCHMARKS.items()]
        view["trade_count"] = len(trades)
        return clean(view)

    @api.get("/portfolio/trades")
    def trades_list() -> list[dict]:
        return clean([asdict(t) for t in reversed(engine.trades.list())])

    @api.post("/portfolio/trades")
    def trades_add(body: TradeIn) -> dict:
        if body.date > datetime.now(UTC).date():
            raise HTTPException(422, "La fecha no puede ser futura.")
        ticker = body.ticker.strip().upper()
        trade_id = portfolio_service.add_trade(
            engine.svc, engine.trades, ticker, body.side, body.quantity, body.price,
            body.fee, body.date, body.note,
        )  # fmt: skip
        return {"id": trade_id}

    @api.delete("/portfolio/trades/{trade_id}")
    def trades_delete(trade_id: int) -> dict:
        engine.trades.delete(trade_id)
        return {"ok": True}

    # --- Alertas ----------------------------------------------------------------------

    @api.get("/alerts")
    def alerts_list() -> dict:
        last = engine.alerts.last_values()
        items = []
        for a in engine.alerts.list():
            value, checked = last.get(a.id, (None, None))
            items.append(
                {**asdict(a), "text": describe(a), "last_value": value, "last_checked_at": checked}
            )
        events = [asdict(e) for e in engine.alerts.events()]
        return clean({"alerts": items, "events": events, "metrics": METRIC_LABELS})

    @api.post("/alerts")
    def alerts_add(body: AlertIn) -> dict:
        a = Alert(body.ticker.strip().upper(), body.metric, body.op, body.threshold)
        if a.metric not in ("sma50", "sma200") and a.threshold is None:
            raise HTTPException(422, "Falta el valor del umbral.")
        engine.svc.get_quote(a.ticker)  # comprueba que existe (404 si no)
        return {"id": engine.alerts.add(a)}

    @api.delete("/alerts/{alert_id}")
    def alerts_delete(alert_id: int) -> dict:
        engine.alerts.delete(alert_id)
        return {"ok": True}

    @api.put("/alerts/{alert_id}/active")
    def alerts_active(alert_id: int, active: bool) -> dict:
        engine.alerts.set_active(alert_id, active)
        return {"ok": True}

    @api.post("/alerts/check")
    def alerts_check() -> dict:
        return {"fired": engine.check_alerts()}

    @api.post("/alerts/seen")
    def alerts_seen() -> dict:
        engine.alerts.mark_all_seen()
        return {"ok": True}

    # --- Contenido educativo y metodología --------------------------------------------

    @api.get("/glossary")
    def glossary() -> dict:
        return {
            "entries": [asdict(e) for e in ENTRIES],
            "components": [
                {
                    "key": c.key,
                    "label": c.label,
                    "description": c.description,
                    "inputs": [i.key for i in c.inputs],
                }
                for c in COMPONENTS
            ],
        }

    @api.get("/guides")
    def guides() -> dict:
        """Guías «Cómo invertir» y conceptos básicos, en Markdown."""
        return {
            "guides": [asdict(g) for g in GUIDES],
            "concepts": [{"title": k, "body": v} for k, v in CONCEPTS.items()],
        }

    @api.get("/calc/compound")
    def calc_compound(
        initial: float = 0,
        monthly: float = 0,
        annual_return: float = 0.06,
        years: int = 20,
        fee: float = 0.0,
        inflation: float = 0.02,
    ) -> dict:
        """Interés compuesto con aportaciones. Rentabilidades y comisión en fracción (0,06)."""
        if not (0 <= years <= 60 and initial >= 0 and monthly >= 0 and -0.5 < annual_return < 1):
            raise HTTPException(422, "Revisa los valores: años entre 0 y 60 e importes positivos.")
        df = compound_growth(initial, monthly, annual_return, years, fee)
        real = real_return(annual_return - fee, inflation)
        rows = [
            {"year": int(y), "contributed": float(r.contributed), "value": float(r.value)}
            for y, r in df.iterrows()
        ]
        end = rows[-1]
        return {
            "rows": rows,
            "gain": end["value"] - end["contributed"],
            "real_return": real,
            "real_value": end["value"] / (1 + inflation) ** years,
        }

    @api.get("/calc/tax")
    def calc_tax(base: float = 0) -> dict:
        """Cuota aproximada de la base del ahorro (IRPF, tramos generales)."""
        if base < 0 or base > 1e9:
            raise HTTPException(422, "Introduce una base entre 0 y 1.000 millones de euros.")
        tax = savings_tax(base)
        return {"base": base, "tax": tax, "effective_rate": tax / base if base else 0.0}

    @api.get("/methodology")
    def methodology() -> dict:
        return {
            "score": scoring.score.__doc__,
            "signal": recommend.engine.__doc__,
            "profile": investor.__doc__,
            "backtest": backtest_engine.__doc__,
        }

    # --- Ajustes ----------------------------------------------------------------------

    @api.get("/settings/secrets")
    def secrets() -> dict:
        return secret_status()

    @api.put("/settings/secrets")
    def put_secret(body: SecretIn) -> dict:
        try:
            set_secret(body.name, body.value)
        except ValueError as e:
            raise HTTPException(422, str(e)) from e
        return secret_status()

    app.include_router(api)
    return app
