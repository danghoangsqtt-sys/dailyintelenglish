"""Task 24.1: storyboard data model, validation and API."""

import sqlite3

import pytest

from app.core.config import settings
from app.models.storyboard import BeatInput
from app.services.visuals.storyboard_service import estimate_images
from tests.test_visuals_project_api import client, data, locked_character  # noqa: F401


def project_with_script(client, speakers=(0, 1, 0, 1, 0, 1), cast=2):  # noqa: F811
    project = data(client.post("/api/projects", json={
        "name": "Story", "topic": "Remote work and city life", "cefr_level": "B1", "duration_minutes": 2,
        "num_speakers": 2, "genre": "interview", "accent": "american",
        "speakers": [{"name": "Lan", "gender": "female", "accent": "american"},
                     {"name": "Minh", "gender": "male", "accent": "american"}],
    }))
    detail = data(client.get(f"/api/projects/{project['id']}"))
    ids = {speaker["speaker_index"]: speaker["id"] for speaker in detail["speakers"]}
    data(client.put(f"/api/projects/{project['id']}/script", json={"lines": [
        {"speaker_id": ids[index], "text": f"Line number {number} of the lesson."}
        for number, index in enumerate(speakers)
    ]}))
    members = [{"speaker_index": index, "character_id": locked_character(f"C{index}", "yellow")}
               for index in range(cast)]
    data(client.put(f"/api/projects/{project['id']}/visuals/cast", json=members))
    return project


def beat(line_from, line_to, **fields):
    return {"line_from": line_from, "line_to": line_to, "scene_id": fields.pop("scene_id", "builtin-cafe"),
            **fields}


def test_round_trip_estimate_and_warnings(client):  # noqa: F811
    project = project_with_script(client)
    base = f"/api/projects/{project['id']}/storyboard"
    assert data(client.get(base))["beats"] == []
    saved = data(client.put(base, json={"beats": [
        beat(2, 5, scene_id="builtin-park", speakers=[0, 1], action="walking along the path", expression="smile"),
        beat(0, 1, speakers=[0, 1], action="ordering coffee"),
    ]}))
    assert [b["line_from"] for b in saved["beats"]] == [0, 2]  # stored in line order
    assert saved["source"] == "owner" and saved["status"] == "draft"
    assert saved["estimate"] == {"images": 8, "cap": 12, "gpu_minutes": 16}
    assert data(client.get(base))["beats"][1]["action"] == "walking along the path"
    warned = data(client.put(base, json={"beats": [beat(0, 0, speakers=[0, 1]), beat(1, 5, speakers=[0, 1])]}))
    assert warned["warnings"] == ["beat 1: speaker(s) [1] are on screen but do not speak in its lines"]


@pytest.mark.parametrize("beats,message", [
    ([beat(0, 2), beat(4, 5)], "gap at line 3"),
    ([beat(0, 3), beat(3, 5)], "overlap at line 4"),
    ([beat(0, 4)], "they end at 4"),
    ([beat(0, 5, speakers=[3])], "not in the project cast"),
    ([beat(0, 5, scene_id="nope")], "Unknown scene"),
])
def test_invalid_storyboards_are_rejected(client, beats, message):  # noqa: F811
    project = project_with_script(client)
    response = client.put(f"/api/projects/{project['id']}/storyboard", json={"beats": beats})
    assert response.status_code == 422 and message in response.text


def test_shape_validation_and_cap(client, monkeypatch):  # noqa: F811
    project = project_with_script(client)
    base = f"/api/projects/{project['id']}/storyboard"
    both = {"line_from": 0, "line_to": 5, "scene_id": "builtin-cafe", "new_place": "a tea house"}
    assert client.put(base, json={"beats": [both]}).status_code == 422
    assert client.put(base, json={"beats": [beat(0, 5, action="dancing!!")]}).status_code == 422
    assert client.put(base, json={"beats": [beat(0, 5, expression="angry")]}).status_code == 422
    monkeypatch.setattr(settings, "VISUALS_IMAGE_CAP", 5)
    assert data(client.put(base, json={"beats": [beat(0, 5)]}))["estimate"]["images"] == 4  # within the cap
    over = client.put(base, json={"beats": [beat(0, 2), beat(3, 5, scene_id="builtin-park")]})
    assert over.status_code == 422 and "needs 8 images; the cap is 5" in over.text


def test_estimate_examples():
    one = BeatInput(line_from=0, line_to=1, scene_id="a")
    assert estimate_images([one], 2) == 4                     # framing set: 2 singles + 2 duos
    assert estimate_images([one], 1) == 1                     # one single
    assert estimate_images([one, BeatInput(line_from=2, line_to=3, scene_id="a", action="reading a book")], 2) == 5
    assert estimate_images([one, BeatInput(line_from=2, line_to=3, kind="insert")], 2) == 5
    assert estimate_images([one, BeatInput(line_from=2, line_to=3, new_place="a tea house")], 2) == 8


def test_project_delete_cascades(client):  # noqa: F811
    project = project_with_script(client)
    data(client.put(f"/api/projects/{project['id']}/storyboard", json={"beats": [beat(0, 5)]}))
    assert client.delete(f"/api/projects/{project['id']}").status_code == 200
    with sqlite3.connect(settings.db_path) as connection:
        assert connection.execute("SELECT count(*) FROM project_beats").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM project_storyboards").fetchone()[0] == 0
    assert client.get(f"/api/projects/{project['id']}/storyboard").status_code == 404
