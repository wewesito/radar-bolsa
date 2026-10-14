from datetime import UTC, datetime

import pytest

from radar.news.sources import parse_google_rss, search_name

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>x</title>
<item>
  <title>Inditex dispara su beneficio - Expansión</title>
  <link>https://news.google.com/a1</link>
  <pubDate>Wed, 14 Oct 2026 08:30:00 GMT</pubDate>
  <source url="https://expansion.com">Expansión</source>
</item>
<item>
  <title>Titular sin fecha</title>
  <link>https://news.google.com/a2</link>
</item>
</channel></rss>"""


def test_parse_google_rss():
    items = parse_google_rss(RSS)
    assert len(items) == 2
    first = items[0]
    assert first.title == "Inditex dispara su beneficio"  # sin " - Expansión"
    assert first.publisher == "Expansión"
    assert first.published == datetime(2026, 10, 14, 8, 30, tzinfo=UTC)
    assert items[1].published is None


@pytest.mark.parametrize(
    ("ticker", "name", "expected"),
    [
        ("ITX.MC", "Industria de Diseño Textil, S.A.", "Inditex"),
        ("AAPL", "Apple Inc.", "Apple"),
        ("SAP.DE", "SAP SE", "SAP"),
        ("SAN", "Banco Santander, S.A. Sponsored ADR", "Banco Santander"),
        ("MSFT", "Microsoft Corporation", "Microsoft"),
    ],
)
def test_search_name(ticker, name, expected):
    assert search_name(ticker, name) == expected
