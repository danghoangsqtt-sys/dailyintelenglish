"""Mode defaults, merged update validation and strict bounded plan payloads."""
import copy
import json

import pytest
from pydantic import ValidationError as SchemaError

from backend.content import project_service, script_service
from backend.core.exceptions import ValidationError
from backend.core.voice import media_revision
from backend.schemas.explainer import ExplainerPlan
from backend.schemas.project import ProjectUpdate, ScriptConfig
from tests.test_character_voice_selection import config
from tests.test_visuals_project_api import client, data  # noqa: F401


def solo_config():
    payload = config()
    payload.update(presentation_mode="solo_explainer", explainer_structure="how", num_speakers=1)
    payload["speakers"] = payload["speakers"][:1]
    return payload


async def test_single_speaker_legacy_is_classic_and_explicit_solo_round_trips(db):
    payload = solo_config()
    legacy = {key: value for key, value in payload.items() if key not in ("presentation_mode", "explainer_structure")}
    classic = await project_service.create_project(db, ScriptConfig(**legacy))
    assert classic["presentation_mode"] == "classic" and classic["explainer_structure"] is None
    project = await project_service.create_project(db, ScriptConfig(**payload))
    assert project["presentation_mode"] == "solo_explainer" and project["explainer_structure"] == "how"
    snapshot = json.loads(project["config_json"])
    assert snapshot["presentation_mode"] == "solo_explainer" and snapshot["explainer_structure"] == "how"
    assert project["speakers"][0]["voice_id"] == payload["speakers"][0]["voice_id"]
    listing = await project_service.list_projects(db)
    assert next(item for item in listing if item["id"] == project["id"])["presentation_mode"] == "solo_explainer"


@pytest.mark.parametrize("patch", [{"presentation_mode": "unsupported"}, {"explainer_structure": "html"}, {"num_speakers": 2}])
def test_solo_config_rejects_invalid_mode_structure_and_two_presenters(patch):
    with pytest.raises(SchemaError):
        ScriptConfig(**{**solo_config(), **patch})


async def test_partial_update_checks_stored_speaker_count_and_mode_becomes_read_only(db):
    classic = await project_service.create_project(db, ScriptConfig(**config()))
    with pytest.raises(ValidationError, match="one presenter"):
        await project_service.update_project(db, classic["id"], ProjectUpdate(presentation_mode="solo_explainer"))
    project = await project_service.create_project(db, ScriptConfig(**solo_config()))
    await script_service.save_script(db, project["id"], [{"speaker_id": project["speakers"][0]["id"], "text": "A simple example."}])
    for patch in (ProjectUpdate(presentation_mode="classic"), ProjectUpdate(explainer_structure="list")):
        with pytest.raises(ValidationError, match="read-only"):
            await project_service.update_project(db, project["id"], patch)
    unchanged = await project_service.get_project(db, project["id"])
    assert unchanged["presentation_mode"] == "solo_explainer" and unchanged["explainer_structure"] == "how"


def valid_plan():
    return {"project_id": "p", "revision": 1, "source_fingerprint": "a" * 64,
            "presenter": {"speaker_id": "s", "profile_id": "c", "identity_version": 1},
            "segments": [{"id": "segment1", "intent": "Explain the first idea", "line_ids": ["line1"],
                          "start": {"line_id": "line1", "token_index": 0}, "end": {"line_id": "line1", "token_index": 10},
                          "visual": {"kind": "text_card", "title": "A simple idea", "bullets": ["Start small."]}}]}


@pytest.mark.parametrize("visual", [
    {"kind": "text_card", "title": "A simple idea", "bullets": ["Start small."]},
    {"kind": "photo", "prompt": "An everyday example", "asset": {"asset_id": "image1", "version": 1}},
    {"kind": "diagram", "template": "steps", "nodes": [{"id": "a", "label": "Start"}, {"id": "b", "label": "Finish"}],
     "edges": [{"source": "a", "target": "b"}]},
])
def test_plan_accepts_only_supported_plain_data_visuals(visual):
    payload = valid_plan()
    payload["segments"][0]["visual"] = visual
    assert ExplainerPlan.model_validate(payload).segments[0].visual.kind == visual["kind"]


@pytest.mark.parametrize("visual", [
    {"kind": "svg", "code": "<svg/>"}, {"kind": "text_card", "title": "<script>alert(1)</script>"},
    {"kind": "text_card", "title": "Title", "html": "<b>not supported</b>"},
    {"kind": "text_card", "title": "Title", "bullets": ["<svg onload='alert(1)'/>"]},
    {"kind": "photo", "url": "file:///C:/secret"},
    {"kind": "photo", "important_regions": [{"x": .9, "y": 0, "width": .2, "height": .1}]},
    {"kind": "diagram", "template": "steps", "nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
     "edges": [{"source": "a", "target": "missing"}]},
])
def test_plan_rejects_code_unknown_fields_and_invalid_geometry(visual):
    payload = valid_plan()
    payload["segments"][0]["visual"] = visual
    with pytest.raises(SchemaError):
        ExplainerPlan.model_validate(payload)


def test_plan_rejects_duplicate_segments_and_empty_spans():
    payload = valid_plan()
    payload["segments"].append(copy.deepcopy(payload["segments"][0]))
    with pytest.raises(SchemaError, match="unique"):
        ExplainerPlan.model_validate(payload)
    payload = valid_plan()
    payload["segments"][0]["end"]["token_index"] = 0
    with pytest.raises(SchemaError, match="spoken token"):
        ExplainerPlan.model_validate(payload)


def test_mode_is_included_in_inflight_media_revision():
    project = {"speakers": []}
    assert media_revision(project, []) != media_revision({**project, "presentation_mode": "solo_explainer"}, [])


def test_solo_cast_allows_ready_identity_voice_before_front_images(client):  # noqa: F811
    project = data(client.post("/api/projects", json=solo_config()))
    profile = data(client.post("/api/visuals/profiles", json={"name": "New Presenter", "gender": "male", "accent": "american",
                                                          "appearance": "short black hair", "outfit": "green shirt"}))
    assert not profile["readiness"]["video_ready"]
    result = data(client.put(f"/api/projects/{project['id']}/visuals/cast", json=[{"speaker_index": 0, "character_id": profile["id"]}]))
    assert result["cast"][0]["character_id"] == profile["id"]
    classic = data(client.post("/api/projects", json=config()))
    response = client.put(f"/api/projects/{classic['id']}/visuals/cast", json=[{"speaker_index": 0, "character_id": profile["id"]}])
    assert response.status_code == 422
