"""Phase 64 (ENH-046): the quick-learning Shorts -- Don't say / Say, Word of the day, Top 5 phrases."""
import pytest
from pydantic import ValidationError as SchemaError

from backend.ai.llm.prompt_loader import load_presentation_block, render_explainer_prompt
from backend.content import script_pipeline
from backend.library import explainer_service
from backend.schemas.project import SHORT_STYLES, VOICE_ONLY_STYLES, ScriptConfig
from tests.test_explainer_project import solo_config
from tests.test_visuals_project_api import client, data, locked_character  # noqa: F401

STYLES = ("mistakes", "wordday", "top5")
PLAN_FIELDS = dict(cefr_level="B1", structure="why", lines=[], previous=None, assets=[], previous_error=None, source_text="",
                   scenes=[], activities=[], output_schema="{}", previous_output="")


@pytest.mark.parametrize("style", STYLES)
def test_each_learning_short_is_a_voice_only_short(style):
    assert style in SHORT_STYLES and style in VOICE_ONLY_STYLES
    config = ScriptConfig(**{**solo_config(), "explainer_style": style, "duration_minutes": 0.5})
    assert config.explainer_style == style
    assert explainer_service.is_vox({"explainer_style": style}) and explainer_service.is_short({"explainer_style": style})
    with pytest.raises(SchemaError, match="at most 60 seconds"):
        ScriptConfig(**{**solo_config(), "explainer_style": style, "duration_minutes": 3})
    assert script_pipeline._source_context({"explainer_style": style})["short_style"] == style


async def test_the_script_prompts_describe_each_format():
    mistakes = await load_presentation_block("solo_explainer", "why", 1, "topic", "mistakes")
    assert "Don't say: <wrong phrase>. Say: <right phrase>." in mistakes and "only real, common learner mistakes" in mistakes
    word = await load_presentation_block("solo_explainer", "why", 1, "topic", "wordday")
    assert "WORD OF THE DAY" in word and "pronunciation tip" in word and "memory tip" in word
    top5 = await load_presentation_block("solo_explainer", "why", 1, "topic", "top5")
    assert "Number five" in top5 and "Number one" in top5
    for text in (mistakes, word, top5):
        assert "OPENING: begin the episode" not in text and "replaces the structure above" in text


async def test_the_plan_prompts_map_each_format_to_existing_visuals():
    mistakes = await render_explainer_prompt(vox=True, style="mistakes", topic="Feelings", **PLAN_FIELDS)
    assert '"id": "dont", "label": "Don\'t say"' in mistakes and 'template "comparison"' in mistakes
    word = await render_explainer_prompt(vox=True, style="wordday", topic="Resilient", **PLAN_FIELDS)
    assert "WORD OF THE DAY" in word and "part of speech" in word and '"highlight" = the word' in word
    top5 = await render_explainer_prompt(vox=True, style="top5", topic="Small talk", **PLAN_FIELDS)
    assert "countdown order" in top5 and "Follow for more phrases" in top5


def test_a_channel_series_can_be_a_learning_short(client):  # noqa: F811
    cid = locked_character("Teacher", "green")
    topic = data(client.post("/api/channel/topics", json={"name": "English Tips"}))
    series = data(client.post(f"/api/channel/topics/{topic['id']}/series", json={
        "name": "Common Mistakes", "presentation_mode": "solo_explainer", "explainer_style": "mistakes", "cast": [cid]}))
    data(client.post(f"/api/channel/series/{series['id']}/episodes", json={"title": "Bored or boring"}))
    created = data(client.post(f"/api/channel/series/{series['id']}/projects"))["created"]
    project = data(client.get(f"/api/projects/{created[0]['project_id']}"))
    assert (project["explainer_style"], project["duration_minutes"]) == ("mistakes", 0.75)
    for style in ("wordday", "top5"):
        assert data(client.patch(f"/api/channel/series/{series['id']}", json={"explainer_style": style}))["explainer_style"] == style
