"""Phase 59 (ENH-041): the VOX explainer -- voice-over only, motion graphics, the owner's numbers and places only."""
import copy
import json

import pytest
from pydantic import ValidationError as SchemaError

from backend import main
from backend.ai.llm.contracts import GenerationResult
from backend.library import explainer_service as service
from backend.schemas.explainer import ChartVisual, ExplainerSegment, MapVisual, QuoteVisual
from backend.tests.test_explainer_api import synthetic_audio, wait
from backend.tests.test_explainer_project import solo_config
from backend.tests.test_visuals_project_api import client, data, locked_character  # noqa: F401

SCRIPT = ["45 percent fail, 55 percent last.", "Japan and Brazil test steps."]


class VoxRouter:
    """Answers every proposal with the given outputs, in turn, and keeps the prompts."""

    def __init__(self, *outputs):
        self.outputs, self.prompts = list(outputs), []

    async def generate(self, request):
        assert "VoxProposedSegment" in request.json_schema["$defs"]
        self.prompts.append(request.prompt)
        text = self.outputs[min(len(self.prompts), len(self.outputs)) - 1]
        return GenerationResult(text=text, provider="test", model="fixture", latency_ms=1, attempt=1, prompt_hash="a" * 64)


def vox_project(client, style="vox"):  # noqa: F811
    project = data(client.post("/api/projects", json={**solo_config(), "explainer_style": style}))
    pid, sid = project["id"], project["speakers"][0]["id"]
    cid = locked_character("Narrator", "blue")
    data(client.put(f"/api/projects/{pid}/visuals/cast", json=[{"speaker_index": 0, "character_id": cid}]))
    lines = data(client.put(f"/api/projects/{pid}/script", json={"lines": [{"speaker_id": sid, "text": t} for t in SCRIPT]}))
    return project, lines


def segment(line, ident, visual, tokens):
    return {"id": ident, "intent": "Explain a practical idea", "line_ids": [line["id"]],
            "start": {"line_id": line["id"], "token_index": 0}, "end": {"line_id": line["id"], "token_index": tokens},
            "visual": visual, "scene": None, "gestures": [], "source_notes": ""}


def wire(lines, chart_value=45):
    return json.dumps({"segments": [
        segment(lines[0], "idea-1", {"kind": "chart", "chart_type": "bar", "title": "New habits", "unit": "%",
                                     "items": [{"label": "Fail", "value": chart_value}, {"label": "Last", "value": 55}]}, 6),
        segment(lines[1], "idea-2", {"kind": "map", "title": "Where", "places": [
            {"name": "Japan", "lat": 36.2, "lon": 138.3}, {"name": "Brazil", "lat": -14.2, "lon": -51.9}],
            "highlight_countries": ["Japan", "Brazil"], "route": [0, 1]}, 5),
    ]})


# ---------------------------------------------------------------------------- contracts


def test_vox_visuals_are_bounded_plain_data():
    QuoteVisual(kind="quote", text="Small steps win.", highlight="steps")
    with pytest.raises(SchemaError, match="part of the quote"):
        QuoteVisual(kind="quote", text="Small steps win.", highlight="big leaps")
    with pytest.raises(SchemaError):
        ChartVisual(kind="chart", items=[{"label": "Only one", "value": 1}])
    with pytest.raises(SchemaError, match="route"):
        MapVisual(kind="map", places=[{"name": "Hanoi", "lat": 21, "lon": 105.8}], route=[0, 1])
    with pytest.raises(SchemaError):
        QuoteVisual(kind="quote", text="<script>alert(1)</script>")


def test_the_style_is_stored_for_solo_only_and_copied(client):  # noqa: F811
    vox, _ = vox_project(client)
    assert vox["explainer_style"] == "vox"
    solo = data(client.post("/api/projects", json=solo_config()))
    assert solo["explainer_style"] == "presenter"
    classic = data(client.post("/api/projects", json={**solo_config(), "presentation_mode": "classic", "explainer_structure": None,
                                                      "explainer_style": "vox"}))
    assert classic["explainer_style"] is None
    assert data(client.post(f"/api/projects/{vox['id']}/copy-settings"))["explainer_style"] == "vox"


def test_a_presenter_plan_reports_vox_kinds_and_a_vox_fact_guard_reports_invented_data():
    source = {"project": {"explainer_style": "vox", "source_text": "Vietnam grew 7 percent."},
              "lines": [{"text": text} for text in SCRIPT]}
    line = {"id": "l1"}
    chart = ExplainerSegment.model_validate({**segment(line, "c", {"kind": "chart", "items": [
        {"label": "Fail", "value": 45}, {"label": "Growth", "value": 7}, {"label": "Made up", "value": 12}]}, 3), "locks": {}})
    places = ExplainerSegment.model_validate({**segment(line, "m", {"kind": "map", "places": [
        {"name": "Japan", "lat": 36, "lon": 138}, {"name": "Atlantis", "lat": 0, "lon": 0}]}, 3), "locks": {}})
    issues = service.vox_fact_issues(source, [chart, places])
    assert issues == ["Segment c: the chart values for Made up are not numbers said in the narration; use only numbers from the script",
                      "Segment m: the map places Atlantis are not named in the narration"]


# ---------------------------------------------------------------------------- the VOX pipeline


def test_a_vox_plan_is_proposed_approved_and_previewed_without_a_presenter_pack(client, monkeypatch):  # noqa: F811
    project, lines = vox_project(client)
    pid = project["id"]
    synthetic_audio(client, pid, lines)
    router = VoxRouter(wire(lines, chart_value=12), wire(lines))  # the first chart invents a number: one repair round
    monkeypatch.setattr(main, "_build_ai_router", lambda: router)
    job = wait(client, pid, client.post(f"/api/projects/{pid}/explainer-plan/propose", json={"expected_revision": 0}))
    assert job["status"] == "complete", job
    assert len(router.prompts) == 2 and "VOX-style" in router.prompts[0] and "token_count" in router.prompts[0]
    assert "## Output Format" in router.prompts[0] and "not numbers said in the narration" in router.prompts[1]
    view = data(client.get(f"/api/projects/{pid}/explainer-plan"))
    assert not any("front21" in issue for issue in view["issues"])  # nobody is on screen
    body = {"expected_revision": 1, "expected_source_fingerprint": view["current_source_fingerprint"],
            "segments": copy.deepcopy(view["plan"]["segments"])}
    for item in body["segments"]:
        item["needs_fact_review"] = False
    reviewed = data(client.patch(f"/api/projects/{pid}/explainer-plan", json=body))["plan"]
    approval = {"expected_revision": reviewed["revision"], "source_fingerprint": reviewed["source_fingerprint"]}
    approved = data(client.post(f"/api/projects/{pid}/explainer-plan/approve", json=approval))["plan"]
    assert approved["status"] == "approved"
    props = data(client.get(f"/api/projects/{pid}/explainer-plan/preview?aspect=16:9"))["props"]
    solo = props["solo"]
    assert solo["style"] == "vox" and solo["pictures"] == {}
    board = solo["geometry"]["aspects"]["16:9"]["board"]
    assert solo["geometry"]["style"] == "vox" and 0 < board["y"] and board["y"] + board["height"] < 0.735
    assert [item["visual"]["kind"] for item in solo["plan"]["segments"]] == ["chart", "map"]
    vertical = data(client.get(f"/api/projects/{pid}/explainer-plan/preview?aspect=9:16"))["props"]["solo"]
    assert vertical["geometry"]["aspects"]["9:16"]["board"]["height"] > 0.15


def test_a_presenter_project_keeps_its_solo_prompt_and_schema(client, monkeypatch):  # noqa: F811
    project, lines = vox_project(client, style="presenter")
    seen = []

    class SoloRouter:
        async def generate(self, request):
            seen.append(request)
            raise RuntimeError("stop after the prompt")

    monkeypatch.setattr(main, "_build_ai_router", lambda: SoloRouter())
    wait(client, project["id"], client.post(f"/api/projects/{project['id']}/explainer-plan/propose", json={"expected_revision": 0}))
    assert seen and "ProposedExplainerSegment" in seen[0].json_schema["$defs"]
    assert "VoxProposedSegment" not in seen[0].json_schema["$defs"] and "Solo Explainer" in seen[0].prompt
    kinds = seen[0].json_schema["$defs"]["ProposedExplainerSegment"]["properties"]["visual"]["discriminator"]["mapping"]
    assert set(kinds) == {"photo", "diagram", "text_card", "activity"}


def test_the_vox_plan_shows_the_welcome_and_the_thanks():
    """Phase 60 (ENH-042): the first VOX card shows the topic, the last one thanks the viewers."""
    from backend.core.paths import PROMPTS_DIR

    prompt = (PROMPTS_DIR / "storyboard" / "explainer_vox.txt").read_text(encoding="utf-8")
    assert "Thanks for watching" in prompt and "Subscribe" in prompt


def test_a_vox_script_follows_the_viral_explainer_formula():
    """Phase 86 (owner 2026-10-28): cold open on an English example and one question, evidence blocks, a callback with
    the answer, a tip and one follow line -- no greeting, no 'thanks for watching' speech."""
    from jinja2 import Environment, FileSystemLoader

    from backend.ai.llm.prompt_loader import _render_presentation_block_sync
    from backend.core.paths import PROMPTS_DIR

    episode = _render_presentation_block_sync("solo_explainer", "why", 1, "topic", "vox")
    short = _render_presentation_block_sync("solo_explainer", "why", 1, "topic", "vox", short=True)
    for text in (episode, short):
        assert "COLD OPEN" in text and "CALLBACK" in text and "no greeting" in text and "MESSAGE FIRST" not in text
    assert "as many blocks as the length needs (three to five)" in episode and "two blocks" in short
    assert "Fill the planned length" in episode and "Fill the planned length" not in short
    section = Environment(loader=FileSystemLoader(str(PROMPTS_DIR / "script")))

    def render(index, last, voice_over):
        return section.get_template("section.txt").render(
            presentation_mode="solo_explainer", section_index=index, section_count=3, is_last_section=last, voice_over=voice_over,
            speakers=[{"name": "Lina", "gender": "female", "accent": "american"}], num_speakers=1, language_features={},
            avoid_phrases=[], prior_summary="" if index == 1 else "before")

    assert "first line is the COLD OPEN" in render(1, False, True) and "greet the viewers warmly" not in render(1, False, True)
    assert "greet the viewers warmly" in render(1, False, False)
    assert "CALLBACK to the opening example" in render(3, True, True) and "thank them" not in render(3, True, True)
    middle = render(2, False, True)  # Phase 86 sandbox run: each section wrote the whole formula
    assert "continue with the NEXT evidence blocks" in middle and "no callback, no tip, no follow line yet" in middle
    assert "ONCE" in episode and "only the first section has the cold open" in episode


def test_the_vox_plan_asks_for_evidence_pace_and_a_recap():
    from backend.core.paths import PROMPTS_DIR

    text = (PROMPTS_DIR / "storyboard" / "explainer_vox.txt").read_text(encoding="utf-8")
    assert "PACE AND EVIDENCE" in text and "never more than about 20 spoken words" in text
    assert "never a title alone" in text and 'never a "Thanks for' in text and "paper cut-out OBJECTS" in text


def test_a_vox_script_gets_named_blocks_that_fill_its_length_and_a_dense_tolerance():
    """Phase 86 (sandbox runs 2026-10-29): VOX scripts came back short; a number of named blocks fills the length."""
    from backend.content import script_pipeline

    assert [script_pipeline.vox_blocks(words) for words in (119, 375, 500, 750)] == [3, 5, 7, 8]
    assert script_pipeline.word_tolerance({"explainer_style": "vox", "duration_minutes": 3}) == 0.20
    assert script_pipeline.word_tolerance({"explainer_style": "presenter", "duration_minutes": 3}) == 0.10
