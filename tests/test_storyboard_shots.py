"""Task 24.5a: shots from the approved storyboard (fake engine)."""

import pytest

from app.core.config import settings
from app.services.visuals import recipes
from app.services.visuals.engine import FakeImageEngine
from app.services.visuals.project_visuals_service import storyboard_shot_specs
from tests.test_storyboard_api import project_with_script
from tests.test_visuals_project_api import client, data, wait_job  # noqa: F401

BEATS = [
    {"line_from": 0, "line_to": 1, "scene_id": "builtin-cafe", "speakers": [0, 1], "action": "drinking coffee",
     "expression": "smile"},
    {"line_from": 2, "line_to": 2, "scene_id": "builtin-cafe", "speakers": [0, 1], "action": "reading city plans",
     "expression": "thinking"},
    {"line_from": 3, "line_to": 3, "kind": "insert", "new_place": "crowded subway at rush hour",
     "expression": "worried"},
    {"line_from": 4, "line_to": 5, "new_place": "a quiet tea house", "speakers": [1], "action": "",
     "expression": "calm"},
]


@pytest.fixture
def requests_log(monkeypatch):
    log = []
    original = FakeImageEngine.request

    async def recording(self, payload):
        log.append(dict(payload))
        return await original(self, payload)

    monkeypatch.setattr(FakeImageEngine, "request", recording)
    monkeypatch.setattr(settings, "VISUALS_COLOUR_RETRIES", 0)
    return log


def test_specs_follow_places_actions_and_inserts():
    cast = [{"speaker_index": 0}, {"speaker_index": 1}]
    beats = [{**beat, "kind": beat.get("kind", "scene"), "scene_id": beat.get("scene_id") or "s-tea"} for beat in BEATS]
    specs = storyboard_shot_specs(beats, cast)
    assert [(spec["scene_id"], spec["kind"], spec["action"]) for spec in specs] == [
        ("builtin-cafe", "single", "drinking coffee"), ("builtin-cafe", "single", "drinking coffee"),
        ("builtin-cafe", "duo_close", "drinking coffee"), ("builtin-cafe", "duo_wide", "drinking coffee"),
        ("builtin-cafe", "duo_wide", "reading city plans"),
        ("", "insert", ""),
        ("s-tea", "single", ""), ("s-tea", "single", ""), ("s-tea", "duo_close", ""), ("s-tea", "duo_wide", ""),
    ]
    assert specs[4]["beat_position"] == 1 and specs[5]["subject"] == "crowded subway at rush hour"
    solo = storyboard_shot_specs([{"kind": "scene", "scene_id": "a", "speakers": [1], "action": "x"},
                                  {"kind": "scene", "scene_id": "a", "speakers": [1], "action": "y"}], cast)
    assert (solo[-1]["kind"], solo[-1]["speakers"]) == ("single", [1])


def test_draft_storyboard_keeps_the_legacy_path(client):  # noqa: F811
    project = project_with_script(client)
    data(client.put(f"/api/projects/{project['id']}/storyboard", json={"beats": BEATS}))  # draft only
    response = client.post(f"/api/projects/{project['id']}/visuals/shots")
    assert response.status_code == 422 and "approve a storyboard" in response.text  # legacy needs scenes


def test_approved_storyboard_generates_beat_shots(client, requests_log):  # noqa: F811
    project = project_with_script(client)
    base = f"/api/projects/{project['id']}"
    data(client.put(f"{base}/storyboard", json={"beats": BEATS, "status": "approved"}))
    wait_job(client, data(client.post(f"{base}/visuals/shots")))
    shots = data(client.get(f"{base}/visuals"))["shots"]
    assert len(shots) == 10 and all(shot["status"] == "complete" for shot in shots)
    insert = next(shot for shot in shots if shot["kind"] == "insert")
    assert (insert["scene_name"], insert["subject"]) == ("Inserts", "crowded subway at rush hour")
    tea = next(scene for scene in data(client.get("/api/visuals/scenes")) if scene["place"] == "a quiet tea house")
    assert tea["name"] == "Quiet tea house" and not tea["is_builtin"] and tea["preview_url"]
    beats = data(client.get(f"{base}/storyboard"))["beats"]
    assert beats[3]["scene_id"] == tea["id"] and beats[3]["new_place"] is None
    insert_calls = [p for p in requests_log if "crowded subway at rush hour" in p.get("prompt", "")]
    assert len(insert_calls) == 1 and insert_calls[0]["negative_prompt"] == recipes.PLATE_NEGATIVE
    assert not any(key.startswith("ip_adapter") for key in insert_calls[0])
    encodes = [p["items"][0]["prompt"] for p in requests_log if p["command"] == "encode"]
    assert any("warm smile, drinking coffee" in prompt for prompt in encodes)
    assert any("thoughtful look, reading city plans" in prompt for prompt in encodes)
    data(client.post(f"{base}/visuals/shots/{insert['id']}/regenerate"))  # an insert can be regenerated


def _shot(shot_id, scene_id, kind, indexes, beat_position=None):
    return {"id": shot_id, "scene_id": scene_id, "kind": kind, "speaker_indexes": indexes, "status": "complete",
            "final_path": "x.png", "beat_position": beat_position}


def test_assign_beat_shots_inserts_actions_speakers_and_fallbacks():
    from app.services.visuals.project_visuals_service import assign_beat_shots, storyboard_timeline_ready

    beats = [
        {"line_from": 0, "line_to": 4, "kind": "scene", "scene_id": "cafe"},
        {"line_from": 5, "line_to": 7, "kind": "scene", "scene_id": "cafe"},
        {"line_from": 8, "line_to": 8, "kind": "insert", "scene_id": None},
        {"line_from": 9, "line_to": 9, "kind": "scene", "scene_id": "park"},
    ]
    lines = [{"speaker_index": i % 2} for i in range(10)]
    shots = [
        _shot("s0", "cafe", "single", [0]), _shot("s1", "cafe", "single", [1]),
        _shot("close", "cafe", "duo_close", [0, 1]), _shot("wide", "cafe", "duo_wide", [0, 1]),
        _shot("act", "cafe", "duo_wide", [0, 1], beat_position=1),
        _shot("ins", "", "insert", [], beat_position=2),
    ]
    assert assign_beat_shots(lines, beats, shots) == [
        "wide", "s1", "s0", "close", "s0",   # beat 1: opens wide, speakers, 4th line duo close
        "act", "s0", "act",                  # beat 2: its action shot alternates with the speaker
        "ins",                               # the insert
        None,                                # park has no shot yet -> midnight
    ]
    assert not storyboard_timeline_ready(beats, shots)       # the park beat has no shot
    assert storyboard_timeline_ready(beats[:3], shots)
    assert not storyboard_timeline_ready(None, shots)


@pytest.mark.asyncio
async def test_remotion_uses_the_beat_timeline_once_storyboard_shots_exist(client, tmp_path, monkeypatch, requests_log):  # noqa: F811,E501
    import aiosqlite

    from app.services import video_renderer_remotion

    project = project_with_script(client)
    base = f"/api/projects/{project['id']}"
    data(client.put(f"{base}/storyboard", json={"beats": BEATS, "status": "approved"}))
    wait_job(client, data(client.post(f"{base}/visuals/shots")))
    shots = data(client.get(f"{base}/visuals"))["shots"]
    detail = data(client.get(base))
    monkeypatch.setattr(video_renderer_remotion, "REMOTION_VISUALS_DIR", tmp_path / "visuals")
    monkeypatch.setattr(video_renderer_remotion, "REMOTION_AVATARS_DIR", tmp_path / "avatars")
    speaker_ids = [speaker["id"] for speaker in sorted(detail["speakers"], key=lambda s: s["speaker_index"])]
    audio_job = {"timestamps": [{"start_sec": float(i), "end_sec": i + 0.9, "label": "x",
                                 "speaker_id": speaker_ids[i % 2], "text": f"Line {i}"} for i in range(6)],
                 "word_timestamps": []}
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        props = await video_renderer_remotion._build_input_props(db, detail, audio_job, None)
    by_id = {shot["id"]: shot for shot in shots}
    kinds = [by_id[shot_id]["kind"] if shot_id else None for shot_id in props["visuals"]["lineShots"]]
    assert kinds[3] == "insert" and props["visuals"]["shots"][props["visuals"]["lineShots"][3]]["kind"] == "insert"
    assert by_id[props["visuals"]["lineShots"][2]]["action"] == "reading city plans"  # beat 2's own action shot
    assert kinds[0] == "duo_wide" and all(kind is not None for kind in kinds)
