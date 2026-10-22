"""Phase 63 (ENH-045): the viral Shorts -- English news and text on a blurred background, on the VOX pipeline."""
import copy

import httpx
import pytest
from pydantic import ValidationError as SchemaError

from backend import main
from backend.ai.llm.prompt_loader import load_presentation_block, render_explainer_prompt
from backend.content import link_reader, script_pipeline
from backend.core.exceptions import ValidationError
from backend.library import explainer_service
from backend.media import video_service
from backend.schemas.project import ScriptConfig
from tests.test_explainer_api import synthetic_audio, wait
from tests.test_explainer_project import solo_config
from tests.test_visuals_project_api import client, data, locked_character  # noqa: F401
from tests.test_vox_explainer import SCRIPT, VoxRouter, wire

ARTICLE = ("A strong storm reached the coast of Vietnam on Monday. Schools in three provinces closed for two days. "
           "Officials asked people to stay inside and to keep their phones charged. ") * 3


def short_config(style="news", **extra):
    return {**solo_config(), "explainer_style": style, "duration_minutes": 0.75, **extra}


# ---------------------------------------------------------------- contracts

def test_a_short_is_a_voice_only_solo_video_of_at_most_a_minute():
    config = ScriptConfig(**short_config())
    assert (config.presentation_mode, config.explainer_style, config.duration_minutes) == ("solo_explainer", "news", 0.75)
    with pytest.raises(SchemaError, match="at most 60 seconds"):
        ScriptConfig(**short_config(duration_minutes=2))
    article = ScriptConfig(**short_config(source_kind="article", source_text=ARTICLE))
    assert article.source_kind == "article"
    with pytest.raises(SchemaError, match="news Short only"):
        ScriptConfig(**short_config("blur", source_kind="article", source_text=ARTICLE))
    for style, voice_only, short in (("vox", True, False), ("news", True, True), ("blur", True, True), ("presenter", False, False)):
        assert explainer_service.is_vox({"explainer_style": style}) is voice_only
        assert explainer_service.is_short({"explainer_style": style}) is short


# ---------------------------------------------------------------- prompts

async def test_the_short_script_prompts_open_with_a_hook_and_report_only_the_article():
    news = await load_presentation_block("solo_explainer", "why", 1, "topic", "news")
    assert "SHORT — ENGLISH NEWS" in news and "OPENING: begin the episode" not in news
    blur = await load_presentation_block("solo_explainer", "why", 1, "topic", "blur")
    assert "TEXT ON A BLURRED BACKGROUND" in blur and "Never attribute a quote" in blur
    presenter = await load_presentation_block("solo_explainer", "why", 1, "topic", "presenter")
    assert "OPENING: begin the episode" in presenter and "SHORT —" not in presenter
    context = script_pipeline._source_context({"explainer_style": "news", "source_kind": "article", "source_text": ARTICLE})
    assert context["short_style"] == "news" and context["source_kind"] == "article"
    section = script_pipeline._env.get_template("section.txt")
    common = dict(topic="Storm", cefr_level="B1", min_words=30, max_words=40, num_speakers=1, speakers=[{"name": "Lina", "alias": "Lina", "gender": "female", "accent": "american"}], prior_summary="",
                  is_last_section=True, language_features={}, cefr_constraints="", genre_instructions="", objective="x",
                  section_number=1, num_sections=1, accent="american", genre="small_talk",
                  outline_title="Storm", avoid_phrases=[], max_consecutive_lines=3, presentation_mode="solo_explainer",
                  section_count=1, section_index=0, solo_instructions="")
    text = section.render(**common, **context)
    assert "FIRST section of a SHORT" in text and "never copy its sentences" in text and "follow Daily Beyond English" in text
    assert "greet the viewers warmly" not in text
    plain = section.render(**common, **script_pipeline._source_context({"explainer_style": "vox"}))
    assert "greet the viewers warmly" in plain and "SHORT" not in plain
    plan = await render_explainer_prompt(vox=True, style="news", topic="Storm", cefr_level="B1", structure="why", lines=[],
                                         previous=None, assets=[], previous_error=None, source_text="", scenes=[], activities=[], output_schema="{}", previous_output="")
    assert "VERTICAL ENGLISH NEWS SHORT" in plan and "realistic news-style photo" in plan
    blur_plan = await render_explainer_prompt(vox=True, style="blur", topic="Hope", cefr_level="B1", structure="why", lines=[],
                                              previous=None, assets=[], previous_error=None, source_text="", scenes=[], activities=[], output_schema="{}", previous_output="")
    assert "TEXT ON A BLURRED BACKGROUND" in blur_plan and "Thanks for watching" not in blur_plan


# ---------------------------------------------------------------- the link reader

PAGE = """<html><head><title> Storm hits the coast | News </title><script>var x = 1;</script></head><body>
<nav><p>Home News Sport Weather and more links here</p></nav>
<article><h1>Storm hits the coast</h1><p>A strong storm reached the coast of Vietnam on Monday morning, officials said.</p>
<p>Schools in three provinces closed for two days while workers cleared the roads.</p>
<p>People were asked to stay inside and keep their phones charged until the wind drops.</p>
<p>Ad</p></article><footer><p>Copyright and many other footer words that are not news.</p></footer></body></html>"""


def test_the_article_paragraphs_are_extracted_without_menus_or_scripts():
    page = link_reader.extract(PAGE)
    assert page["title"] == "Storm hits the coast | News"
    assert page["text"].startswith("Storm hits the coast") and "Schools in three provinces" in page["text"]
    assert "Home News" not in page["text"] and "Copyright" not in page["text"] and "var x" not in page["text"] and "Ad" not in page["text"].split()


async def test_read_link_follows_a_redirect_and_refuses_bad_pages():
    long_page = PAGE.replace("</article>", "<p>" + "More words about the storm and the people affected by it. " * 8 + "</p></article>")

    def handler(request):
        if request.url.path == "/old":
            return httpx.Response(301, headers={"location": "/news/storm"})
        if request.url.path == "/news/storm":
            return httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"}, text=long_page)
        if request.url.path == "/file.pdf":
            return httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF")
        if request.url.path == "/empty":
            return httpx.Response(200, headers={"content-type": "text/html"}, text="<html><body><p>Hi</p></body></html>")
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    page = await link_reader.read_link("https://news.example/old", transport=transport)
    assert page["url"] == "https://news.example/news/storm" and "Schools in three provinces" in page["text"]
    for path, reason in (("/file.pdf", "not a web page"), ("/empty", "No article text"), ("/missing", r"error \(404\)")):
        with pytest.raises(ValidationError, match=reason):
            await link_reader.read_link(f"https://news.example{path}", transport=transport)
    with pytest.raises(ValidationError, match="http"):
        await link_reader.read_link("ftp://news.example/a", transport=transport)
    with pytest.raises(ValidationError, match="public"):
        link_reader._check_host("http://127.0.0.1:8000/")
    with pytest.raises(ValidationError, match="public"):
        link_reader._check_host("http://192.168.1.10/")


def test_the_read_link_route_checks_the_address(client):  # noqa: F811
    response = client.post("/api/projects/read-link", json={"url": "http://127.0.0.1:9/secret"})
    assert response.status_code == 422 and "public" in response.json()["error"]


# ---------------------------------------------------------------- the pipeline

def test_a_news_short_plan_is_vertical_only_and_previews_as_news(client, monkeypatch):  # noqa: F811
    project = data(client.post("/api/projects", json=short_config()))
    pid, sid = project["id"], project["speakers"][0]["id"]
    assert project["explainer_style"] == "news"
    cid = locked_character("Newsreader", "red")
    data(client.put(f"/api/projects/{pid}/visuals/cast", json=[{"speaker_index": 0, "character_id": cid}]))
    lines = data(client.put(f"/api/projects/{pid}/script", json={"lines": [{"speaker_id": sid, "text": t} for t in SCRIPT]}))
    synthetic_audio(client, pid, lines)
    router = VoxRouter(wire(lines))
    monkeypatch.setattr(main, "_build_ai_router", lambda: router)
    job = wait(client, pid, client.post(f"/api/projects/{pid}/explainer-plan/propose", json={"expected_revision": 0}))
    assert job["status"] == "complete", job
    assert "VERTICAL ENGLISH NEWS SHORT" in router.prompts[0]
    view = data(client.get(f"/api/projects/{pid}/explainer-plan"))
    assert view["plan"]["aspects"] == ["9:16"]
    body = {"expected_revision": view["plan"]["revision"], "expected_source_fingerprint": view["current_source_fingerprint"],
            "segments": copy.deepcopy(view["plan"]["segments"]), "aspects": ["9:16"]}
    for item in body["segments"]:
        item["needs_fact_review"] = False
    reviewed = data(client.patch(f"/api/projects/{pid}/explainer-plan", json=body))["plan"]
    approved = data(client.post(f"/api/projects/{pid}/explainer-plan/approve", json={
        "expected_revision": reviewed["revision"], "source_fingerprint": reviewed["source_fingerprint"]}))["plan"]
    assert approved["status"] == "approved"
    solo = data(client.get(f"/api/projects/{pid}/explainer-plan/preview?aspect=9:16"))["props"]["solo"]
    assert solo["style"] == "news" and solo["pictures"] == {} and solo["geometry"]["style"] == "vox"


async def test_a_short_main_video_is_rendered_vertical(monkeypatch, tmp_path):
    seen = {}

    async def fake_render(db, project, audio_job, learning, output, **kwargs):
        seen.update(kwargs)
        return {"intro_seconds": 0}

    monkeypatch.setattr(video_service, "renderer_problem", lambda: None)
    monkeypatch.setattr(video_service.video_renderer_remotion, "render_via_remotion", fake_render)
    monkeypatch.setattr(video_service.settings, "DATA_DIR", tmp_path)
    audio = {"status": "complete", "timestamps": []}
    await video_service.generate_video("p", audio, db=None, project={"id": "p", "presentation_mode": "solo_explainer",
                                                                       "explainer_style": "blur"})
    assert seen["layout"] == "vertical"
    seen.clear()
    await video_service.generate_video("p", audio, db=None, project={"id": "p", "presentation_mode": "solo_explainer",
                                                                       "explainer_style": "vox"})
    assert "layout" not in seen  # every other video keeps its default (horizontal) main render


def test_a_channel_series_of_shorts_makes_short_news_projects(client):  # noqa: F811
    cid = locked_character("Anchor", "green")
    topic = data(client.post("/api/channel/topics", json={"name": "World News"}))
    series = data(client.post(f"/api/channel/topics/{topic['id']}/series", json={
        "name": "Daily English News", "presentation_mode": "solo_explainer", "explainer_style": "news", "cast": [cid]}))
    assert series["explainer_style"] == "news"
    data(client.post(f"/api/channel/series/{series['id']}/episodes", json={"title": "Storm on the coast"}))
    created = data(client.post(f"/api/channel/series/{series['id']}/projects"))["created"]
    project = data(client.get(f"/api/projects/{created[0]['project_id']}"))
    assert (project["explainer_style"], project["duration_minutes"]) == ("news", 0.75)
    patched = data(client.patch(f"/api/channel/series/{series['id']}", json={"explainer_style": "blur"}))
    assert patched["explainer_style"] == "blur"


def test_numbers_said_in_words_count_for_a_chart():
    numbers = explainer_service._spoken_numbers("Twelve kilometres took eight months; bikes cost ten thousand dong at "
                                                "six stations, and twenty-five or two hundred and five people came.")
    assert {12.0, 8.0, 10000.0, 6.0, 25.0, 205.0} <= numbers
    assert 7.0 not in numbers
