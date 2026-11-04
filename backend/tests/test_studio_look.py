"""Phase 93 (D139): direction E's tokens and fonts reach every page."""
from pathlib import Path

import pytest

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
PAGES = sorted((FRONTEND / "pages").glob("*.html"))


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_every_page_loads_the_tokens_before_the_main_stylesheet(page):
    html = page.read_text(encoding="utf-8")
    assert "/static/css/tokens.css" in html
    assert html.index("/static/css/tokens.css") < html.index("/static/css/style.css")


@pytest.mark.parametrize("name", ["Baloo2-Variable.ttf", "BeVietnamPro-Regular.ttf", "BeVietnamPro-Medium.ttf",
                                  "BeVietnamPro-SemiBold.ttf", "BeVietnamPro-Bold.ttf", "OFL-baloo2.txt", "OFL-bevietnampro.txt"])
def test_the_fonts_ship_with_their_licences(name):
    path = FRONTEND / "static" / "fonts" / name
    assert path.is_file() and path.stat().st_size > 1000
    if name.endswith(".ttf"):
        assert path.read_bytes()[:4] == b"\x00\x01\x00\x00"  # a TrueType file, not an HTML error page


def test_the_type_uses_the_bundled_faces():
    css = (FRONTEND / "static" / "css" / "style.css").read_text(encoding="utf-8")
    tokens = (FRONTEND / "static" / "css" / "tokens.css").read_text(encoding="utf-8")
    assert '--font: "Be Vietnam Pro"' in css and '--font-display: "Baloo 2"' in css
    for face in ("Baloo2-Variable.ttf", "BeVietnamPro-Regular.ttf", "BeVietnamPro-Bold.ttf"):
        assert f"/static/fonts/{face}" in tokens
    assert "fonts.googleapis.com" not in tokens + css  # offline: no font CDN
