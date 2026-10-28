"""Phase 81 (owner 2026-10-28): the slow English podcast and vocabulary flashcard Shorts -- backend."""

import asyncio
import json

import aiosqlite
import pytest

from backend.ai.llm.prompt_loader import _render_presentation_block_sync
from backend.content.learning_pipeline import _required_vocabulary, flashcard_words
from backend.core.config import settings
from backend.media import video_renderer_remotion as remotion
from backend.schemas.project import LINE_DRAWN_STYLES, SHORT_STYLES, SLOWPOD_SPEED, is_short_video
from tests.test_visuals_project_api import client, data, locked_character  # noqa: F401


def _project(client, style):  # noqa: F811
    return data(client.post("/api/projects", json={
        "name": f"{style} test", "topic": "Daily routines", "cefr_level": "B1", "duration_minutes": 0.75, "num_speakers": 1,
        "genre": "informational", "accent": "american", "presentation_mode": "solo_explainer", "explainer_style": style,
        "speakers": [{"name": "Lina", "gender": "female", "accent": "american"}]}))


def test_both_styles_are_line_drawn_vertical_shorts():
    for style in ("slowpod", "flashcards"):
        assert style in SHORT_STYLES and style in LINE_DRAWN_STYLES
        assert is_short_video({"explainer_style": style, "duration_minutes": 0.75})


def test_flashcard_card_words_and_required_vocabulary():
    transcript = "Vocabulary: daily routines.\nwash up. wash up.\nbrush your teeth. Brush your teeth.\nmake the bed. make the bed\n" \
                 "Follow Daily Beyond English for more words."
    assert flashcard_words(transcript) == ["wash up", "brush your teeth", "make the bed"]
    assert _required_vocabulary({"explainer_style": "flashcards"}, transcript) == ["wash up", "brush your teeth", "make the bed"]


def test_the_prompts_describe_both_formats():
    slow = _render_presentation_block_sync("solo_explainer", "why", 1, "topic", "slowpod")
    assert "SLOW ENGLISH PODCAST" in slow and "translation_vi" in slow and "OPENING: begin the episode" not in slow
    cards = _render_presentation_block_sync("solo_explainer", "why", 1, "topic", "flashcards")
    assert "VOCABULARY FLASHCARDS" in cards and '"wash up. wash up."' in cards


def test_a_slow_podcast_narrator_is_slow_and_flashcards_are_not(client):  # noqa: F811
    slow = _project(client, "slowpod")
    cards = _project(client, "flashcards")
    assert slow["speakers"][0]["speed"] == SLOWPOD_SPEED
    assert cards["speakers"][0]["speed"] != SLOWPOD_SPEED


def test_translations_survive_the_step2_save_and_reach_the_video_props(client, monkeypatch):  # noqa: F811
    project = _project(client, "slowpod")
    speaker = project["speakers"][0]["id"]
    data(client.put(f"/api/projects/{project['id']}/script", json={"lines": [
        {"speaker_id": speaker, "text": "Hi everyone, and welcome back to my slow English podcast.",
         "language_notes": {"translation_vi": "Chào mọi người, chào mừng trở lại với podcast tiếng Anh nói chậm."}},
        {"speaker_id": speaker, "text": "Today I talk about my morning.", "language_notes": {"translation_vi": "Hôm nay tôi nói về buổi sáng."}}]}))
    saved = data(client.get(f"/api/projects/{project['id']}/script"))
    assert saved[1]["language_notes"]["translation_vi"] == "Hôm nay tôi nói về buổi sáng."
    audio = {"mp3_path": str(settings.DATA_DIR / "x.mp3"), "word_timestamps": [{"words": []}, {"words": []}],
             "timestamps": [{"start_sec": 0.0, "end_sec": 3.0, "label": "Lina", "speaker_id": speaker, "text": saved[0]["text"]},
                            {"start_sec": 3.0, "end_sec": 5.0, "label": "Lina", "speaker_id": speaker, "text": saved[1]["text"]}]}

    async def props():
        async with aiosqlite.connect(settings.db_path) as db:
            db.row_factory = aiosqlite.Row
            full = data(client.get(f"/api/projects/{project['id']}"))
            return await remotion._build_input_props(db, full, audio, None, visual_mode="podcast_black", layout="vertical")

    built = asyncio.run(props())
    assert built["shortStyle"] == "slowpod" and "solo" not in built
    assert [line["translation"] for line in built["lines"]][1] == "Hôm nay tôi nói về buổi sáng."


@pytest.mark.parametrize("template", ["slowpod", "flashcards"])
def test_the_batch_makes_both_kinds(client, template):  # noqa: F811
    narrator = locked_character("Narrator", "red")
    result = data(client.post("/api/shorts-batch/create", json={
        "topic_name": "Shorts", "series_name": f"{template} week", "template": template, "cast": [narrator], "cefr_level": "A2",
        "start_date": "2026-10-29", "every_days": 1, "make_projects": True, "items": [{"title": "Daily routines (P1)", "brief": ""}]}))
    tree = data(client.get("/api/channel"))
    series = next(s for topic in tree["topics"] for s in topic["series"] if s["id"] == result["series_id"])
    project = data(client.get(f"/api/projects/{series['episodes'][0]['project_id']}"))
    assert project["explainer_style"] == template and is_short_video(project)
    assert (project["speakers"][0]["speed"] == SLOWPOD_SPEED) is (template == "slowpod")
    assert json.dumps(project)  # serialisable view
