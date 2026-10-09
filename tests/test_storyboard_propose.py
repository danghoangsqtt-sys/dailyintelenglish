"""Task 24.2: AI storyboard proposal -- validated, one repair, deterministic fallback."""

import json
import re

import pytest

from app.core.exceptions import ProviderError
from app.core.paths import get_project_root
from app.services.ai.contracts import AIMode, GenerationResult
from app.services.ai.fake_provider import FakeProvider
from app.services.ai.router import AIRouter
from app.services.visuals import storyboard_service
from tests.test_storyboard_api import project_with_script
from tests.test_visuals_project_api import client, data  # noqa: F401


def _result(payload) -> GenerationResult:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return GenerationResult(text=text, provider="fake", model="fake-model", latency_ms=1.0, attempt=1,
                            prompt_hash="abc123")


@pytest.fixture
def fake_ai(monkeypatch):
    """Route the API's router to one scripted FakeProvider (zero network); returns the provider."""
    holder = {}

    def install(outcomes):
        provider = FakeProvider("fake-local", outcomes)
        holder["provider"] = provider
        monkeypatch.setattr(storyboard_service, "build_ai_router_from_settings",
                            lambda: AIRouter(primary=None, fallback=provider, mode=AIMode.LOCAL))
        return provider

    return install


GOOD = {"beats": [
    {"line_from": 0, "line_to": 2, "kind": "scene", "scene_id": "builtin-cafe", "speakers": [0, 1],
     "action": "drinking coffee", "expression": "smile"},
    {"line_from": 3, "line_to": 3, "kind": "insert", "speakers": [], "action": "", "expression": "calm"},
    {"line_from": 4, "line_to": 5, "kind": "scene", "scene_id": "builtin-park", "speakers": [0, 1],
     "action": "walking along the path", "expression": "calm"},
]}


def test_valid_ai_answer_is_saved(client, fake_ai):  # noqa: F811
    project = project_with_script(client)
    provider = fake_ai([_result(GOOD)])
    saved = data(client.post(f"/api/projects/{project['id']}/storyboard/propose"))
    assert saved["proposal"] == {"path": "ai", "reason": None}
    assert saved["source"] == "ai" and saved["status"] == "draft"
    assert [beat["kind"] for beat in saved["beats"]] == ["scene", "insert", "scene"]
    assert saved["estimate"]["images"] == 9
    prompt = provider.calls[0].prompt
    assert "[0] (speaker 0) Line number 0 of the lesson." in prompt
    assert "builtin-rice-fields | Rice fields | green rice fields | countryside" in prompt
    assert "Every insert must target 3 to 6 seconds" in prompt
    assert "action-led and useful for comprehension, never" in prompt and "decorative" in prompt
    assert "reusable plain activity" in prompt
    assert "Your previous answer was rejected" not in prompt and provider.calls[0].purpose == "storyboard"


def test_locked_d72_prompt_pack_has_exactly_the_twenty_canonical_import_names_and_constraints():
    text = (get_project_root() / "docs" / "operations" / "activity-library-prompt-pack.md").read_text(encoding="utf-8")
    expected = {
        "generic__exercise__morning__01.png", "generic__walking__outdoors__01.png",
        "generic__jogging__outdoors__01.png", "generic__cycling__outdoors__01.png",
        "generic__cooking__kitchen__01.png", "generic__baking__kitchen__01.png",
        "generic__eating__cafe__01.png", "generic__drinking-coffee__cafe__01.png",
        "generic__grocery-shopping__store__01.png", "generic__cleaning__home__01.png",
        "generic__gardening__balcony__01.png", "generic__reading__library__01.png",
        "generic__studying__desk__01.png", "generic__laptop-work__home-office__01.png",
        "generic__meeting__office__01.png", "generic__commuting__train__01.png",
        "generic__driving__city__01.png", "generic__packing__bedroom__01.png",
        "generic__relaxing__living-room__01.png", "generic__morning-routine__bedroom__01.png",
    }
    filenames = re.findall(r"`(generic__[a-z0-9-]+__[a-z0-9-]+__01\.png)`", text)
    assert len(filenames) == 20 and set(filenames) == expected
    assert "16:9 landscape 1280x720" in text and "calm lower-centre space for subtitles" in text
    assert "No text, captions, readable signs, logo, watermark" in text
    assert len(re.findall(r"^\| \d+ \|", text, flags=re.MULTILINE)) == 20


def test_invalid_json_then_repair(client, fake_ai):  # noqa: F811
    project = project_with_script(client)
    provider = fake_ai([_result("not json at all"), _result(GOOD)])
    saved = data(client.post(f"/api/projects/{project['id']}/storyboard/propose"))
    assert saved["proposal"]["path"] == "ai_repaired" and len(provider.calls) == 2
    assert "Your previous answer was rejected: the answer is not valid JSON" in provider.calls[1].prompt


def test_rule_violations_twice_fall_back_to_rule(client, fake_ai):  # noqa: F811
    project = project_with_script(client)
    gap = {"beats": [{**GOOD["beats"][0]}, {**GOOD["beats"][2]}]}  # lines 3 missing
    short = {"beats": [{"line_from": 0, "line_to": 4, "kind": "scene", "scene_id": "builtin-cafe"}]}
    provider = fake_ai([_result(gap), _result(short)])
    saved = data(client.post(f"/api/projects/{project['id']}/storyboard/propose"))
    assert saved["proposal"]["path"] == "rule" and saved["source"] == "rule"
    assert "gap at line 3" in provider.calls[1].prompt
    assert "they end at 4" in saved["proposal"]["reason"]
    assert [(b["line_from"], b["line_to"], b["scene_id"]) for b in saved["beats"]] == [(0, 5, "builtin-cafe")]


def test_provider_error_falls_back_to_project_scenes(client, fake_ai):  # noqa: F811
    project = project_with_script(client)
    data(client.put(f"/api/projects/{project['id']}/visuals/scenes",
                    json=["builtin-classroom", "builtin-park", "builtin-farm"]))
    fake_ai([ProviderError("down")])
    saved = data(client.post(f"/api/projects/{project['id']}/storyboard/propose"))
    assert saved["proposal"] == {"path": "rule", "reason": "AI unavailable (ProviderError)"}
    assert [(b["line_from"], b["line_to"], b["scene_id"]) for b in saved["beats"]] == [
        (0, 1, "builtin-classroom"), (2, 3, "builtin-park"), (4, 5, "builtin-farm")]
    assert saved["estimate"]["images"] == 12


def test_rule_beats_tile_cap_and_talkers(monkeypatch):
    beats = storyboard_service.rule_beats([0, 0, 0, 1, 1, 1, 1], {0, 1}, ["a", "b"])
    assert [(b.line_from, b.line_to, b.speakers) for b in beats] == [(0, 3, [0, 1]), (4, 6, [1])]
    monkeypatch.setattr(storyboard_service.settings, "VISUALS_IMAGE_CAP", 8)
    assert len(storyboard_service.rule_beats([0, 1] * 5, {0, 1}, ["a", "b", "c"])) == 2  # 3 places x 4 > 8
    assert [b.scene_id for b in storyboard_service.rule_beats([0], set(), [])] == ["builtin-cafe"]


def test_propose_needs_a_script(client, fake_ai):  # noqa: F811
    project = data(client.post("/api/projects", json={
        "name": "Empty", "topic": "Nothing yet", "cefr_level": "B1", "duration_minutes": 2, "num_speakers": 1,
        "genre": "small_talk", "accent": "american",
        "speakers": [{"name": "Lan", "gender": "female", "accent": "american"}],
    }))
    fake_ai([])
    response = client.post(f"/api/projects/{project['id']}/storyboard/propose")
    assert response.status_code == 422 and "no script lines" in response.text


def test_loose_real_ai_shape_is_normalized(client, fake_ai):  # noqa: F811
    """The shape Gemini Flash-Lite really returned (2026-10-05): no `kind`, inserts as place-only
    beats, punctuation in actions, an unknown expression, both scene_id and new_place."""
    project = project_with_script(client)
    loose = {"beats": [
        {"line_from": 0, "line_to": 2, "scene_id": "builtin-office", "new_place": "an office", "speakers": [0, 1],
         "action": "discussing charts, on a tablet!", "expression": "focused"},
        {"line_from": 3, "line_to": 3, "scene_id": None, "new_place": "crowded subway station", "speakers": [],
         "action": "", "expression": "worried"},
        {"line_from": 4, "line_to": 5, "scene_id": "builtin-office", "new_place": "", "speakers": [0, 1, 1],
         "action": "", "expression": "smile"},
    ]}
    provider = fake_ai([_result(loose)])
    saved = data(client.post(f"/api/projects/{project['id']}/storyboard/propose"))
    assert saved["proposal"]["path"] == "ai"
    first, insert, last = saved["beats"]
    assert (first["kind"], first["new_place"], first["action"], first["expression"]) == (
        "scene", None, "discussing charts on a tablet", "calm")
    assert (insert["kind"], insert["new_place"]) == ("insert", "crowded subway station")
    assert last["speakers"] == [0, 1]
    schema = provider.calls[0].json_schema
    assert "kind" in schema["$defs"]["BeatInput"]["required"] and "status" not in schema.get("properties", {})


def _covers(beats, total):
    ordered = sorted(beats, key=lambda beat: beat.line_from)
    return ordered[0].line_from == 0 and ordered[-1].line_to == total - 1 and all(
        later.line_from == earlier.line_to + 1 for earlier, later in zip(ordered, ordered[1:]))


def test_fit_to_cap_trims_in_order_and_keeps_coverage(monkeypatch):
    from app.models.storyboard import BeatInput

    monkeypatch.setattr(storyboard_service.settings, "VISUALS_IMAGE_CAP", 12)
    over = [
        BeatInput(line_from=0, line_to=3, scene_id="office", action="sitting at desks"),
        BeatInput(line_from=4, line_to=4, kind="insert", new_place="crowded street"),
        BeatInput(line_from=5, line_to=8, scene_id="cafe", action="drinking coffee"),
        BeatInput(line_from=9, line_to=9, kind="insert", new_place="empty shops"),
        BeatInput(line_from=10, line_to=12, scene_id="cafe", action="reading plans"),
        BeatInput(line_from=13, line_to=15, scene_id="park", action="walking"),
    ]
    assert storyboard_service.estimate_images(over, 2) == 15
    fitted, steps = storyboard_service.fit_to_cap(over, 2)
    assert storyboard_service.estimate_images(fitted, 2) <= 12 and _covers(fitted, 16)
    # the cafe's second action goes first (15 -> 14), then the last insert (13), then the first (12)
    assert steps == 3 and [beat.kind for beat in fitted] == ["scene"] * 4
    assert [(beat.scene_id, beat.action) for beat in fitted] == [
        ("office", "sitting at desks"), ("cafe", "drinking coffee"), ("cafe", "drinking coffee"), ("park", "walking")]
    keeps_insert, _ = storyboard_service.fit_to_cap(over[:5], 2)  # 13 images: one action is enough
    assert [beat.kind for beat in keeps_insert].count("insert") == 2
    many = [BeatInput(line_from=i, line_to=i, scene_id=f"s{i}") for i in range(5)]
    squeezed, _ = storyboard_service.fit_to_cap(many, 2)
    assert len({beat.scene_id for beat in squeezed}) == 3 and _covers(squeezed, 5)


def test_over_cap_ai_answer_is_trimmed_not_discarded(client, fake_ai):  # noqa: F811
    project = project_with_script(client)
    over = {"beats": [
        {"line_from": 0, "line_to": 1, "kind": "scene", "scene_id": "builtin-office", "speakers": [0, 1],
         "action": "", "expression": "calm"},
        {"line_from": 2, "line_to": 2, "kind": "scene", "scene_id": "builtin-cafe", "speakers": [0, 1],
         "action": "", "expression": "calm"},
        {"line_from": 3, "line_to": 3, "kind": "scene", "scene_id": "builtin-park", "speakers": [0, 1],
         "action": "", "expression": "calm"},
        {"line_from": 4, "line_to": 5, "kind": "scene", "scene_id": "builtin-farm", "speakers": [0, 1],
         "action": "", "expression": "calm"},
    ]}
    provider = fake_ai([_result(over)])
    saved = data(client.post(f"/api/projects/{project['id']}/storyboard/propose"))
    assert saved["proposal"] == {"path": "ai", "reason": "trimmed to the image cap in 1 step(s)"}
    assert saved["estimate"]["images"] == 12 and len(provider.calls) == 1
    assert "at most 3 places" in provider.calls[0].prompt
