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
    assert "SLOW ENGLISH PODCAST" in slow and "translation_vi" in slow and "OPENING (the first section only): begin the episode" not in slow
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


def test_flashcard_lines_are_clean_cards():
    from backend.content.script_pipeline import flashcard_lines

    lines = flashcard_lines("daily routines", ["to wash up", "Make the bed.", "make the bed", '"brush teeth"', ""] + [f"w{n}" for n in range(12)], "s1")
    texts = [line["text"] for line in lines]
    assert texts[0] == "Vocabulary: daily routines." and texts[-1].startswith("Follow Daily Beyond English")
    assert texts[1:4] == ["wash up. wash up.", "Make the bed. Make the bed.", "brush teeth. brush teeth."]
    assert len(texts) == 12  # name + at most ten cards + follow
    assert flashcard_words("\n".join(texts))[:3] == ["wash up", "Make the bed", "brush teeth"]


async def test_a_flashcard_script_job_builds_cards_from_the_ai_deck(db):
    """Real run 2026-10-28: the prose pipeline wrote a paragraph instead of cards; the job now asks only for a deck."""
    from backend.ai.llm import ai_job_service
    from backend.ai.llm.ai_worker import AIWorker
    from backend.content import project_service, script_pipeline, script_service
    from backend.schemas.project import ScriptConfig, SpeakerConfig
    from tests.test_script_pipeline import _build_router, _result

    project = await project_service.create_project(db, ScriptConfig(
        name="Deck", topic="Sinh hoạt hằng ngày (P1)", cefr_level="A2", duration_minutes=0.75, num_speakers=1, genre="informational",
        accent="american", presentation_mode="solo_explainer", explainer_style="flashcards",
        speakers=[SpeakerConfig(name="Lina", gender="female", accent="american")]))
    deck = {"deck_name": "daily routines", "words": ["wake up", "wash up", "make the bed", "brush your teeth", "get dressed"]}
    router, provider, _ = _build_router([_result(json.dumps(deck))])
    job, _ = await ai_job_service.create_job(db, project["id"], "script", {"project": project, "operation": "script"})
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    await script_pipeline.make_handler(router)(claimed, AIWorker(db_getter=lambda: db))
    final = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final["status"] == "complete", final.get("error_message")
    texts = [line["text"] for line in await script_service.get_script(db, project["id"])]
    assert texts[0] == "Vocabulary: daily routines." and texts[1] == "wake up. wake up." and len(texts) == 7
    assert provider.call_count == 1


def test_message_shorts_get_a_full_minute_and_a_message_structure(client):  # noqa: F811
    """Phase 82 (owner 2026-10-28): knowledge / news Shorts were too short to carry their message."""
    from backend.schemas.project import short_minutes

    assert short_minutes("news") == short_minutes("presenter") == 0.95 and short_minutes("wordday") == short_minutes(None) == 0.75
    news = _render_presentation_block_sync("solo_explainer", "why", 1, "topic", "news")
    assert "MESSAGE FIRST" in news and "takeaway that answers the hook" in news and "three or four short facts" in news
    assert "MESSAGE FIRST" in _render_presentation_block_sync("solo_explainer", "why", 1, "topic", "presenter", short=True)
    assert "MESSAGE FIRST" not in _render_presentation_block_sync("solo_explainer", "why", 1, "topic", "wordday")
    narrator = locked_character("Anchor", "red")
    result = data(client.post("/api/shorts-batch/create", json={
        "topic_name": "Shorts", "series_name": "News week", "template": "news", "cast": [narrator], "cefr_level": "B1",
        "start_date": "2026-10-29", "every_days": 1, "make_projects": True, "items": [{"title": "Storm", "brief": ""}]}))
    tree = data(client.get("/api/channel"))
    series = next(s for topic in tree["topics"] for s in topic["series"] if s["id"] == result["series_id"])
    assert data(client.get(f"/api/projects/{series['episodes'][0]['project_id']}"))["duration_minutes"] == 0.95


async def test_missing_slow_podcast_translations_are_filled_in_one_call():
    """Phase 84 (real run 2026-10-28): the AI left out every translation_vi and the slow podcast played without Vietnamese."""
    from backend.content.script_pipeline import SectionLineOut, fill_translations
    from backend.content.script_service import LanguageNotesOut
    from tests.test_script_pipeline import _build_router, _result

    lines = [SectionLineOut(speaker_id="s", text="I drink water first.", language_notes=LanguageNotesOut()),
             SectionLineOut(speaker_id="s", text="Then I stretch.", language_notes=LanguageNotesOut(translation_vi="Rồi tôi giãn cơ.")),
             SectionLineOut(speaker_id="s", text="It helps me wake up.", language_notes=LanguageNotesOut())]
    router, provider, _ = _build_router([_result(json.dumps({"translations": ["Tôi uống nước trước.", "Nó giúp tôi tỉnh táo."]}))])
    filled = await fill_translations(router, lines)
    assert [line.language_notes.translation_vi for line in filled] == ["Tôi uống nước trước.", "Rồi tôi giãn cơ.", "Nó giúp tôi tỉnh táo."]
    assert provider.call_count == 1 and "Then I stretch." not in provider.calls[0].prompt
    wrong, _, _ = _build_router([_result(json.dumps({"translations": ["only one"]}))])
    assert await fill_translations(wrong, lines) == lines  # a wrong count changes nothing
