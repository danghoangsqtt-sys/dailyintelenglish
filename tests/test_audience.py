"""Phase 72 (ENH-054): the audience -- international, Vietnamese or both -- and how the vocabulary is explained."""

from __future__ import annotations

import asyncio

from backend.ai.llm import prompt_loader
from backend.content import audience
from backend.content import youtube_service as yt
from tests.test_channel_api import PLAN
from tests.test_visuals_project_api import client, data, locked_character  # noqa: F401

LEARNING = {
    "vocabulary": [{"word": "cabin", "part_of_speech": "noun", "ipa": "/x/", "definition_en": "a small wooden house",
                    "definition_vi": "nhà gỗ nhỏ", "example_sentence": "e"}],
    "idioms": [{"phrase": "a piece of cake", "meaning_en": "very easy", "meaning_vi": "dễ như ăn bánh", "example_sentence": "e"}],
    "collocations": [], "phrasal_verbs": [], "patterns": [], "grammar": [], "questions": [],
}
PACKAGE = {"hook": "Hook.", "description": "Summary.", "chapters_text": "00:00 Intro", "hashtags": ["LearnEnglish"], "tags": [], "titles": []}


def test_a_video_follows_its_series_and_the_series_follows_the_channel(client):  # noqa: F811
    alex, lina = locked_character("Alex", "navy"), locked_character("Lina", "white")
    tree = data(client.post("/api/channel/plan/apply", json={"plan": PLAN, "cast": [alex, lina]}))
    series = tree["topics"][0]["series"][0]
    project_id = data(client.post(f"/api/channel/series/{series['id']}/projects"))["created"][0]["project_id"]
    view = data(client.get(f"/api/projects/{project_id}/audience"))
    assert view == {"audience": None, "series": None, "channel": "both", "effective": "both"}  # the default
    assert data(client.put("/api/audience", json={"audience": "international"}))["audience"] == "international"
    assert data(client.get(f"/api/projects/{project_id}/audience"))["effective"] == "international"
    data(client.patch(f"/api/channel/series/{series['id']}", json={"audience": "vietnamese"}))
    assert data(client.get(f"/api/projects/{project_id}/audience"))["effective"] == "vietnamese"
    assert data(client.get(f"/api/projects/{project_id}"))["audience_effective"] == "vietnamese"
    view = data(client.put(f"/api/projects/{project_id}/audience", json={"audience": "both"}))
    assert view["audience"] == "both" and view["effective"] == "both"
    # back to inheriting: the video, then the series
    assert data(client.put(f"/api/projects/{project_id}/audience", json={}))["effective"] == "vietnamese"
    data(client.patch(f"/api/channel/series/{series['id']}", json={"audience": "channel"}))
    assert data(client.get(f"/api/projects/{project_id}/audience"))["effective"] == "international"
    assert client.put("/api/audience", json={"audience": "martian"}).status_code == 422


def test_a_shorts_batch_sets_its_series_audience(client):  # noqa: F811
    kim = locked_character("Kim", "white")
    result = data(client.post("/api/shorts-batch/create", json={
        "topic_name": "Shorts", "series_name": "Words", "template": "wordday", "cast": [kim], "start_date": "2026-11-01",
        "items": [{"title": "Resilient", "brief": "a word"}], "audience": "international"}))
    channel = data(client.get("/api/channel"))
    series = next(item for topic in channel["topics"] for item in topic["series"] if item["id"] == result["series_id"])
    assert series["audience"] == "international"


def test_the_prompts_name_the_audience():
    line = audience.line("international")
    learning = asyncio.run(prompt_loader.render_learning_prompt(topic="t", cefr_level="B1", genre="small_talk",
                                                                transcript_text="A: hi", audience_line=line))
    assert "international learners of English" in learning and "Vietnamese learners of English who" not in learning
    assert "Vietnamese translation" in learning  # the pack still has both languages
    default = asyncio.run(prompt_loader.render_learning_prompt(topic="t", cefr_level="B1", genre="small_talk", transcript_text="A: hi"))
    assert "international and Vietnamese learners of English" in default
    kwargs = {"project_name": "p", "topic": "t", "genre": "small_talk", "cefr_level": "B1", "transcript_text": "A: hi"}
    vietnamese = asyncio.run(prompt_loader.render_youtube_prompt(**kwargs, audience="vietnamese"))
    assert "natural Vietnamese" in vietnamese and "Write everything in English." not in vietnamese
    assert "Write everything in English." in asyncio.run(prompt_loader.render_youtube_prompt(**kwargs, audience="international"))
    both = asyncio.run(prompt_loader.render_youtube_prompt(**kwargs, audience="both"))
    assert "then the same summary in natural Vietnamese" in both


def test_the_description_explains_the_words_for_the_audience():
    international = yt.compose_description(PACKAGE, LEARNING, None, audience="international")
    assert "• cabin (noun) — a small wooden house" in international and "nhà gỗ" not in international
    assert "📚 Vocabulary" in international and yt.SUBSCRIBE_LINE in international
    vietnamese = yt.compose_description(PACKAGE, LEARNING, None, audience="vietnamese")
    assert "• cabin (noun) — nhà gỗ nhỏ" in vietnamese and "📚 Từ vựng" in vietnamese and "💬 Thành ngữ" in vietnamese
    assert yt.VI_LINES["subscribe"] in vietnamese and yt.SUBSCRIBE_LINE not in vietnamese
    assert "⏱ Mục lục" in vietnamese and "⏱ Chapters" in international
    both = yt.compose_description(PACKAGE, LEARNING, None, audience="both")
    assert "• cabin (noun) — a small wooden house / nhà gỗ nhỏ" in both and "• a piece of cake — very easy / dễ như ăn bánh" in both
    # a missing Vietnamese meaning never leaves the line empty
    no_vi = {**LEARNING, "vocabulary": [{**LEARNING["vocabulary"][0], "definition_vi": ""}]}
    assert "• cabin (noun) — a small wooden house" in yt.compose_description(PACKAGE, no_vi, None, audience="vietnamese")
