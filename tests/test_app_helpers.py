import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from components.news_view import md_escape  # noqa: E402


def test_md_escape_neutralizes_markdown_and_html():
    out = md_escape("Cae [ADR] <b>*hoy*</b>")
    assert "\\[" in out and "\\<" in out and "\\*" in out
    assert "<b>" not in out
