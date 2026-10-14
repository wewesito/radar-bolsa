"""Noticias por empresa: Google News RSS (sin clave) y Finnhub (opcional, solo EE. UU.).

Google News RSS: gratuito para uso personal y no comercial (según sus condiciones), con muy
buena cobertura en español. Yahoo (vía yfinance) devuelve listas vacías en esta versión.
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import requests

from radar import config
from radar.data.cache import Cache
from radar.data.markets import US, exchange_for
from radar.errors import ProviderUnavailableError

TTL_NEWS = 30 * 60
FINANCE_TERMS = {
    "es": "(bolsa OR acciones OR resultados OR beneficio OR dividendo)",
    "en": "(stock OR shares OR earnings OR dividend)",
}
TIMEOUT = 10
CACHE_VERSION = "v2"  # v2: búsqueda con términos financieros

# Nombre con el que la prensa llama a las empresas del IBEX (el legal no sirve para buscar)
COMMON_NAMES = {
    "ITX.MC": "Inditex",
    "SAN.MC": "Banco Santander",
    "TEF.MC": "Telefónica",
    "IBE.MC": "Iberdrola",
    "BBVA.MC": "BBVA",
    "REP.MC": "Repsol",
    "CABK.MC": "CaixaBank",
    "AMS.MC": "Amadeus",
    "FER.MC": "Ferrovial",
    "ELE.MC": "Endesa",
    "NTGY.MC": "Naturgy",
    "IAG.MC": "IAG Iberia",
    "AENA.MC": "Aena",
    "GRF.MC": "Grifols",
    "MAP.MC": "Mapfre",
    "ACS.MC": "ACS Florentino",
    "SAB.MC": "Banco Sabadell",
    "BKT.MC": "Bankinter",
    "UNI.MC": "Unicaja",
    "CLNX.MC": "Cellnex",
    "RED.MC": "Redeia",
    "ENG.MC": "Enagás",
    "ACX.MC": "Acerinox",
    "ANA.MC": "Acciona",
    "ANE.MC": "Acciona Energía",
    "COL.MC": "Inmobiliaria Colonial",
    "FDR.MC": "Fluidra",
    "IDR.MC": "Indra",
    "LOG.MC": "Logista",
    "MRL.MC": "Merlin Properties",
    "MTS.MC": "ArcelorMittal",
    "PUIG.MC": "Puig",
    "ROVI.MC": "Laboratorios Rovi",
    "SCYR.MC": "Sacyr",
    "SLR.MC": "Solaria",
    "^IBEX": "Ibex 35",
}

_LEGAL_SUFFIX = re.compile(
    r"[,.]?\s+(S\.?A\.?U?|S\.?E\.?|Inc|Corp(oration)?|Co|Ltd|plc|AG|N\.?V\.?|SpA|S\.p\.A|"
    r"SE|Group|Holdings?|Company|Sponsored.*|ADR.*)\.?\s*$",
    re.IGNORECASE,
)


def search_name(ticker: str, name: str) -> str:
    """Nombre para buscar: alias conocido o nombre legal sin la forma jurídica."""
    if ticker in COMMON_NAMES:
        return COMMON_NAMES[ticker]
    clean = name
    for _ in range(3):  # "Banco X, S.A. Sponsored ADR" → varias pasadas
        clean = _LEGAL_SUFFIX.sub("", clean).strip(" ,.")
    return clean or ticker


@dataclass(frozen=True)
class NewsItem:
    title: str
    url: str
    publisher: str
    published: datetime | None
    provider: str


def parse_google_rss(xml_text: str) -> list[NewsItem]:
    """Convierte el RSS de Google News en noticias (función pura, testeable)."""
    root = ET.fromstring(xml_text)
    items = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        publisher = (it.findtext("source") or "").strip()
        # Google añade " - Medio" al final del título: lo quitamos para analizar solo el titular
        if publisher and title.endswith(f" - {publisher}"):
            title = title[: -len(publisher) - 3]
        pub = it.findtext("pubDate")
        try:
            published = parsedate_to_datetime(pub).astimezone(UTC) if pub else None
        except (TypeError, ValueError):
            published = None
        items.append(
            NewsItem(title, it.findtext("link") or "", publisher, published, "Google News")
        )
    return items


def google_news(query: str, lang: str = "es", days: int = 30) -> list[NewsItem]:
    region = {"es": ("es", "ES", "ES:es"), "en": ("en-US", "US", "US:en")}[lang]
    # Términos financieros: sin ellos salen sobre todo noticias de productos (iPhone, ERP...)
    q = f'"{query}" {FINANCE_TERMS[lang]} when:{days}d'
    url = (
        f"https://news.google.com/rss/search?q={quote_plus(q)}"
        f"&hl={region[0]}&gl={region[1]}&ceid={region[2]}"
    )
    try:
        r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "radar-bolsa/0.1"})
        r.raise_for_status()
    except requests.RequestException as e:
        raise ProviderUnavailableError(f"Google News no responde: {e}") from e
    return parse_google_rss(r.text)


def finnhub_news(ticker: str, api_key: str, days: int = 14) -> list[NewsItem]:
    today = datetime.now(UTC).date()
    try:
        r = requests.get(
            "https://finnhub.io/api/v1/company-news",
            params={
                "symbol": ticker,
                "from": str(today - timedelta(days=days)),
                "to": str(today),
                "token": api_key,
            },
            timeout=TIMEOUT,
        )
        r.raise_for_status()
    except requests.RequestException as e:
        raise ProviderUnavailableError(f"Finnhub no responde: {e}") from e
    return [
        NewsItem(
            d.get("headline", ""),
            d.get("url", ""),
            d.get("source", ""),
            datetime.fromtimestamp(d["datetime"], UTC) if d.get("datetime") else None,
            "Finnhub",
        )
        for d in r.json()[:30]
    ]


def get_news(cache: Cache, ticker: str, name: str, limit: int = 25) -> list[NewsItem]:
    """Noticias recientes (caché de 30 min), sin duplicados, de la más nueva a la más antigua."""
    key = f"{CACHE_VERSION}:news:{ticker}"
    if entry := cache.get(key, TTL_NEWS):
        return [_decode(d) for d in entry.value]

    is_us = exchange_for(ticker) is US
    items: list[NewsItem] = []
    errors: list[Exception] = []
    try:
        items += google_news(search_name(ticker, name), "en" if is_us else "es")
    except ProviderUnavailableError as e:
        errors.append(e)
    if is_us and config.FINNHUB_API_KEY:
        try:
            items += finnhub_news(ticker, config.FINNHUB_API_KEY)
        except ProviderUnavailableError as e:
            errors.append(e)
    if not items and errors:
        if old := cache.get_any(key):
            return [_decode(d) for d in old.value]
        raise errors[0]

    seen, unique = set(), []
    for it in sorted(
        items, key=lambda i: i.published or datetime.min.replace(tzinfo=UTC), reverse=True
    ):
        norm = it.title.lower().strip()
        if norm and norm not in seen:
            seen.add(norm)
            unique.append(it)
    unique = unique[:limit]
    cache.set(key, [_encode(i) for i in unique])
    return unique


def _encode(i: NewsItem) -> dict:
    d = asdict(i)
    d["published"] = i.published.isoformat() if i.published else None
    return d


def _decode(d: dict) -> NewsItem:
    pub = datetime.fromisoformat(d["published"]) if d.get("published") else None
    return NewsItem(d["title"], d["url"], d["publisher"], pub, d["provider"])
