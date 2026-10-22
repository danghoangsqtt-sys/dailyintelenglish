"""Phase 65 (ENH-047): the interactive Shorts -- quiz and listening (one narrator), chat and would you rather (two)."""
import pytest
from pydantic import ValidationError as SchemaError

from backend.ai.llm.prompt_loader import load_presentation_block, render_explainer_prompt
from backend.automation.runner import Producer
from backend.content import script_pipeline
from backend.media import video_service
from backend.schemas.project import CONVERSATION_SHORT_STYLES, SHORT_STYLES, VOICE_ONLY_STYLES, ScriptConfig
from tests.test_explainer_project import config, solo_config
from tests.test_visuals_project_api import client, data, locked_character  # noqa: F401

PLAN_FIELDS = dict(cefr_level="B1", structure="why", lines=[], previous=None, assets=[], previous_error=None, source_text="",
                   scenes=[], activities=[], output_schema="{}", previous_output="")


def test_the_styles_belong_to_their_family():
    for style in ("quiz", "listen"):
        assert style in VOICE_ONLY_STYLES and style in SHORT_STYLES
        assert ScriptConfig(**{**solo_config(), "explainer_style": style, "duration_minutes": 0.75}).explainer_style == style
    for style in CONVERSATION_SHORT_STYLES:
        assert style in SHORT_STYLES and style not in VOICE_ONLY_STYLES
        two = ScriptConfig(**{**config(), "explainer_style": style, "duration_minutes": 0.75})
        assert (two.presentation_mode, two.explainer_style, two.num_speakers) == ("classic", style, 2)
        with pytest.raises(SchemaError, match="conversation of two characters"):
            ScriptConfig(**{**solo_config(), "explainer_style": style, "duration_minutes": 0.75})
        with pytest.raises(SchemaError, match="at most 60 seconds"):
            ScriptConfig(**{**config(), "explainer_style": style, "duration_minutes": 2})
    # a plain conversation still has no style
    assert ScriptConfig(**config()).explainer_style is None


async def test_the_script_prompts_describe_each_format():
    quiz = await load_presentation_block("solo_explainer", "why", 1, "topic", "quiz")
    assert "Three, two, one." in quiz and "The answer is <letter>" in quiz
    listen = await load_presentation_block("solo_explainer", "why", 1, "topic", "listen")
    assert '"One more time."' in listen and '"Here is the' in listen
    chat = await load_presentation_block("classic", None, 2, None, "chat")
    assert "ONE chat message" in chat and "8–14 messages" in chat
    wyr = await load_presentation_block("classic", None, 2, None, "wyr")
    assert '"Would you rather <option A> or <option B>?"' in wyr and "Never invent statistics" in wyr
    assert await load_presentation_block("classic", None, 2, None, None) == ""
    assert script_pipeline._source_context({"explainer_style": "chat"})["short_style"] == "chat"


async def test_the_plan_prompts_map_quiz_and_listen():
    quiz = await render_explainer_prompt(vox=True, style="quiz", topic="Bored or boring", **PLAN_FIELDS)
    assert "COUNTDOWN QUIZ" in quiz and '"emphasis" is the right option' in quiz
    listen = await render_explainer_prompt(vox=True, style="listen", topic="Coffee orders", **PLAN_FIELDS)
    assert "LISTENING CHALLENGE" in listen and "hardest to hear" in listen


async def test_a_conversation_short_renders_vertical_without_sprites(monkeypatch, tmp_path):
    seen = {}

    async def fake_render(db, project, audio_job, learning, output, **kwargs):
        seen.clear()
        seen.update(kwargs)
        return {"intro_seconds": 0}

    monkeypatch.setattr(video_service, "renderer_problem", lambda: None)
    monkeypatch.setattr(video_service.video_renderer_remotion, "render_via_remotion", fake_render)
    monkeypatch.setattr(video_service.settings, "DATA_DIR", tmp_path)
    audio = {"status": "complete", "timestamps": []}
    await video_service.generate_video("p", audio, db=None, project={"id": "p", "presentation_mode": "classic", "explainer_style": "chat"})
    assert (seen["layout"], seen["visual_mode"]) == ("vertical", "podcast_black")
    await video_service.generate_video("p", audio, db=None, project={"id": "p", "presentation_mode": "classic", "explainer_style": None})
    assert "layout" not in seen and seen["visual_mode"] == "podcast_sprites"


async def test_automation_skips_the_storyboard_of_a_conversation_short():
    class NoCalls:
        async def call(self, *args):
            raise AssertionError("no storyboard call")

    assert await Producer(NoCalls()).has_visual_plan("p", False, "wyr") is True


def test_a_channel_series_can_be_a_chat_short(client):  # noqa: F811
    first, second = locked_character("Mai", "green"), locked_character("Tom", "blue")
    topic = data(client.post("/api/channel/topics", json={"name": "Texting English"}))
    series = data(client.post(f"/api/channel/topics/{topic['id']}/series", json={
        "name": "Weekend Plans by Text", "presentation_mode": "classic", "explainer_style": "chat", "cast": [first, second]}))
    data(client.post(f"/api/channel/series/{series['id']}/episodes", json={"title": "Movie night"}))
    created = data(client.post(f"/api/channel/series/{series['id']}/projects"))["created"]
    project = data(client.get(f"/api/projects/{created[0]['project_id']}"))
    assert (project["presentation_mode"], project["explainer_style"], project["duration_minutes"]) == ("classic", "chat", 0.75)


def test_a_listening_challenge_may_repeat_its_sentences():
    from backend.content.script_pipeline import SectionLineOut

    said = "I would like a large coffee with oat milk please"
    lines = [SectionLineOut(speaker_id="s", text=text) for text in ("Listen.", said, "One more time.", said, "Here is the sentence:", said)]
    strict, _ = script_pipeline.validate_global(lines, 40, {"s"}, 1, "coffee")
    assert any("duplicate" in error or "8-gram" in error for error in strict)
    relaxed, _ = script_pipeline.validate_global(lines, 40, {"s"}, 1, "coffee", allow_repeats=True)
    assert not any("duplicate" in error or "8-gram" in error for error in relaxed)
    assert script_pipeline._repeats_by_design({"explainer_style": "listen"}) and not script_pipeline._repeats_by_design({})
