"""Walkthrough 2026-10-14: the Shorts / vertical section opens as soon as the first render on the page finishes (it used to
need a page reload)."""

from backend.core.paths import PROJECT_ROOT

JS = PROJECT_ROOT / "frontend" / "static" / "js"


def test_the_video_page_announces_a_finished_render_and_the_shorts_section_listens():
    video = (JS / "step5_video.js").read_text(encoding="utf-8")
    shorts = (JS / "step5_shorts.js").read_text(encoding="utf-8")
    assert 'new CustomEvent("video:rendered")' in video
    assert 'addEventListener("video:rendered", init, { once: true })' in shorts
