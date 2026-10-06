"""Phase 27 (Task 27.1): the Daily Beyond English brand pack -- logo files, name, palette tokens and contrast."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
PAGES = sorted((FRONTEND / "pages").glob("*.html"))
CSS = (FRONTEND / "static" / "css" / "style.css").read_text(encoding="utf-8")
BRAND_DIR = FRONTEND / "static" / "brand"


def _luminance(hex_colour: str) -> float:
    r, g, b = (int(hex_colour.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    channel = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4  # noqa: E731
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def _contrast(a: str, b: str) -> float:
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _token(name: str, block: str) -> str:
    match = re.search(rf"{re.escape(name)}:\s*(#[0-9a-fA-F]{{6}})\b", block)
    assert match, f"{name} is not defined as a hex colour"
    return match.group(1)


def _blocks() -> tuple[str, str]:
    light = CSS[CSS.index(":root"):CSS.index('[data-theme="dark"]')]
    dark = CSS[CSS.index('[data-theme="dark"]'):CSS.index("* { box-sizing")]
    return light, dark


@pytest.mark.parametrize("name, size", [("logo-64.png", 64), ("logo.png", 512)])
def test_logo_files_exist_with_their_sizes(name, size):
    image = Image.open(BRAND_DIR / name)
    assert image.size == (size, size) and image.mode == "RGBA"


def test_the_full_logo_is_the_owners_file():
    original = Image.open(ROOT / "data" / "Daily Beyond English Avatar Logo.png")
    assert Image.open(BRAND_DIR / "logo-full.png").size == original.size == (1254, 1254)


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_every_page_carries_the_new_name_header_and_favicon(page):
    html = page.read_text(encoding="utf-8")
    title = re.search(r"<title>(.*?)</title>", html).group(1)
    assert title.endswith("Daily Beyond English"), title
    assert "Daily Intel" not in html and ">DI<" not in html and "brand-mark" not in html
    assert html.count('class="brand-logo"') == 1 and 'src="/static/brand/logo-64.png"' in html
    assert "<b>Daily Beyond</b><small>English</small>" in html
    assert 'aria-label="Daily Beyond English dashboard"' in html
    assert '<link rel="icon" href="/static/brand/logo-64.png"' in html


def test_titles_set_by_script_and_the_server_use_the_new_name():
    script = (FRONTEND / "static" / "js" / "step1_config.js").read_text(encoding="utf-8")
    assert "Daily Intel" not in script and script.count("Daily Beyond English") >= 4
    main = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert 'title="Daily Beyond English"' in main and "Daily Intel" not in main


def test_the_palette_is_green_and_yellow_and_the_old_violet_is_gone():
    light, dark = _blocks()
    for name, value in (("--brand-green", "#3a9d3f"), ("--brand-lime", "#9bd13c"), ("--brand-yellow", "#ffd60a"),
                        ("--brand-navy", "#151a5c")):
        assert _token(name, light).lower() == value
    assert "--brand-violet" not in CSS and "--brand-cyan" not in CSS
    for old in ("124, 58, 237", "#7c3aed", "#6d28d9", "#a78bfa", "34, 211, 238"):
        assert old.lower() not in CSS.lower(), old
    for script in ("step2_script.js", "waveform.js"):
        assert "#7c3aed" not in (FRONTEND / "static" / "js" / script).read_text(encoding="utf-8").lower()
    assert "var(--brand-gradient)" in CSS and "--btn-gradient" in light and "--cta" in light and "--cta" in dark


def test_text_and_buttons_meet_aa_contrast_in_both_themes():
    light, dark = _blocks()
    white, ink = "#ffffff", _token("--accent-ink", light)
    assert _contrast(_token("--accent", light), white) >= 4.5            # accent text on the page
    assert _contrast(_token("--accent", light), _token("--accent-soft", light)) >= 4.5   # on its soft chip
    assert _contrast(ink, _token("--accent", light)) >= 4.5              # white on an accent fill
    assert _contrast(white, _token("--cta", light)) >= 4.5               # white on the call-to-action
    for stop in re.findall(r"#[0-9a-fA-F]{6}", re.search(r"--btn-gradient:[^;]+;", light).group(0)):
        assert _contrast(white, stop) >= 4.5, stop                         # white on both ends of the button
    assert _contrast(_token("--accent", dark), _token("--bg", dark)) >= 4.5
    assert _contrast(_token("--accent", dark), _token("--bg-elevated", dark)) >= 4.5
    assert _contrast(_token("--text-muted", dark), _token("--bg", dark)) >= 4.5
    assert _contrast(_token("--text-muted", light), white) >= 4.5


def test_the_character_form_hint_allows_one_colour_for_both_garments():
    html = (FRONTEND / "pages" / "characters.html").read_text(encoding="utf-8")
    assert "different-colour" not in html and "the same colour for both is fine" in html
