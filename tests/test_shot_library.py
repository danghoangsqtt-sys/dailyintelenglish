"""Task 29.4 / 29.5 (ENH-020): the shot library (review, stale, matching) and the library-first project shot job."""

from __future__ import annotations

import sqlite3
import uuid

import aiosqlite
import pytest

from app.core.config import settings
from app.services.visuals import shot_library_service as lib
from app.services.visuals.engine import FakeImageEngine
from tests.test_visuals_project_api import client, data, setup_project, wait_job  # noqa: F401


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


def _make_shots(client, project_id):  # noqa: F811
    wait_job(client, data(client.post(f"/api/projects/{project_id}/visuals/shots")))
    return data(client.get(f"/api/projects/{project_id}/visuals"))["shots"]


def _library(client, **query):  # noqa: F811
    return data(client.get("/api/visuals/library/shots", params=query))


def _approve_all(client, project_id, shots):  # noqa: F811
    for shot in shots:
        added = data(client.post(f"/api/projects/{project_id}/visuals/shots/{shot['id']}/to-library"))
        data(client.patch(f"/api/visuals/library/shots/{added['id']}", json={"review_state": "approved"}))


def _drawing_calls(log):
    return [call for call in log if call.get("command") in ("encode", "generate")]


def _coverage(client, project_id):  # noqa: F811
    return data(client.get(f"/api/projects/{project_id}/visuals/library-coverage"))


def test_a_finished_shot_goes_to_the_library_pending_once_and_its_picture_is_served(client, requests_log):  # noqa: F811
    project, _, _ = setup_project(client, 2, 1)
    shots = _make_shots(client, project["id"])
    base = f"/api/projects/{project['id']}/visuals/shots/{shots[0]['id']}/to-library"
    first = data(client.post(base))
    assert first["review_state"] == "pending" and first["kind"] == shots[0]["kind"] and len(first["character_ids"]) >= 1
    again = data(client.post(base))
    assert again["id"] == first["id"] and len(_library(client)) == 1  # the same picture is never added twice
    assert client.get(first["content_url"]).headers["content-type"] == "image/png"
    assert [row["id"] for row in _library(client, review_state="pending")] == [first["id"]]
    assert _library(client, review_state="approved") == []


def test_an_insert_cannot_go_to_the_library(client, requests_log):  # noqa: F811
    project, _, _ = setup_project(client, 2, 1)
    shots = _make_shots(client, project["id"])
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute("UPDATE project_shots SET kind = 'insert' WHERE id = ?", (shots[0]["id"],))
    assert client.post(f"/api/projects/{project['id']}/visuals/shots/{shots[0]['id']}/to-library").status_code == 422


def test_only_approved_shots_are_reused_and_only_the_missing_ones_are_drawn(client, requests_log):  # noqa: F811
    project, _, _ = setup_project(client, 2, 1)
    shots = _make_shots(client, project["id"])
    assert len(shots) == 4 and all(shot["source"] == "generated" for shot in shots)
    for shot in shots:  # added, but pending: not reused yet
        data(client.post(f"/api/projects/{project['id']}/visuals/shots/{shot['id']}/to-library"))
    requests_log.clear()
    assert all(shot["source"] == "generated" for shot in _make_shots(client, project["id"]))
    assert _drawing_calls(requests_log)
    rows = _library(client)
    for row in rows:  # approve all but one (the owner rejects it)
        state = "rejected" if row["id"] == rows[0]["id"] else "approved"
        data(client.patch(f"/api/visuals/library/shots/{row['id']}", json={"review_state": state}))
    requests_log.clear()
    again = _make_shots(client, project["id"])
    from_library = [shot for shot in again if shot["source"] == "library"]
    assert len(from_library) == 3 and all(shot["library_shot_id"] and shot["status"] == "complete" for shot in from_library)
    assert len(_drawing_calls(requests_log)) > 0  # the rejected one is drawn again
    assert sum(row["use_count"] for row in _library(client)) == 3


def test_everything_covered_means_no_gpu_work_at_all(client, requests_log):  # noqa: F811
    project, _, _ = setup_project(client, 2, 1)
    shots = _make_shots(client, project["id"])
    _approve_all(client, project["id"], shots)
    coverage = _coverage(client, project["id"])
    assert (coverage["total"], coverage["covered"], coverage["missing"]) == (4, 4, 0)
    requests_log.clear()
    again = _make_shots(client, project["id"])
    assert [shot["source"] for shot in again] == ["library"] * 4
    assert _drawing_calls(requests_log) == []
    assert all(client.get(f"/api/projects/{project['id']}/visuals/shots/{shot['id']}/content").status_code == 200
               for shot in again)


def test_a_regenerated_character_makes_its_shots_stale_and_they_are_not_reused(client, requests_log):  # noqa: F811
    project, ids, _ = setup_project(client, 2, 1)
    shots = _make_shots(client, project["id"])
    _approve_all(client, project["id"], shots)
    with sqlite3.connect(settings.db_path) as connection:  # the character's face reference was replaced
        connection.execute("UPDATE character_assets SET id = ? WHERE character_id = ? AND kind = 'face'",
                           (str(uuid.uuid4()), ids[0]))
    stale = [row for row in _library(client) if row["stale"]]
    assert stale and all(ids[0] in row["character_ids"] for row in stale)
    requests_log.clear()
    again = _make_shots(client, project["id"])
    assert any(shot["source"] == "generated" for shot in again) and _drawing_calls(requests_log)
    assert _coverage(client, project["id"])["missing"] >= 1


def test_regenerating_a_library_shot_draws_it_anew(client, requests_log):  # noqa: F811
    project, _, _ = setup_project(client, 2, 1)
    shots = _make_shots(client, project["id"])
    _approve_all(client, project["id"], shots)
    again = _make_shots(client, project["id"])
    assert all(shot["source"] == "library" for shot in again)
    requests_log.clear()
    wait_job(client, data(client.post(f"/api/projects/{project['id']}/visuals/shots/{again[0]['id']}/regenerate")))
    visuals = data(client.get(f"/api/projects/{project['id']}/visuals"))
    redone = next(shot for shot in visuals["shots"] if shot["id"] == again[0]["id"])
    assert redone["source"] == "generated" and redone["library_shot_id"] is None and _drawing_calls(requests_log)


def test_the_library_can_be_switched_off(client, requests_log, monkeypatch):  # noqa: F811
    project, _, _ = setup_project(client, 2, 1)
    _approve_all(client, project["id"], _make_shots(client, project["id"]))
    monkeypatch.setattr(settings, "VISUALS_USE_LIBRARY", False)
    assert all(shot["source"] == "generated" for shot in _make_shots(client, project["id"]))


def test_delete_removes_the_row_and_the_file_and_bad_input_is_refused(client, requests_log):  # noqa: F811
    project, _, _ = setup_project(client, 2, 1)
    shots = _make_shots(client, project["id"])
    added = data(client.post(f"/api/projects/{project['id']}/visuals/shots/{shots[0]['id']}/to-library"))
    assert client.delete(f"/api/visuals/library/shots/{added['id']}").status_code == 200
    assert _library(client) == [] and client.get(added["content_url"]).status_code == 404
    assert client.patch(f"/api/visuals/library/shots/{added['id']}", json={"review_state": "approved"}).status_code == 404
    assert client.patch("/api/visuals/library/shots/x", json={"review_state": "maybe"}).status_code == 422


@pytest.mark.asyncio
async def test_matching_rules_action_expression_gaze_and_no_repeat_in_one_episode(client, requests_log, monkeypatch):  # noqa: F811
    project, ids, scenes = setup_project(client, 2, 1)
    shots = _make_shots(client, project["id"])
    duo = next(shot for shot in shots if shot["kind"] == "duo_wide")
    added = data(client.post(f"/api/projects/{project['id']}/visuals/shots/{duo['id']}/to-library"))
    data(client.patch(f"/api/visuals/library/shots/{added['id']}", json={"review_state": "approved"}))
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute("UPDATE shot_library SET action = 'drinking coffee', expression = 'smile' WHERE id = ?",
                           (added["id"],))
    spec = {"scene_id": scenes[0]["id"], "kind": "duo_wide", "character_ids": added["character_ids"],
            "action": "drinking coffee", "expression": "calm"}
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row

        def find(**changes):
            return lib.find_match(db, **{**spec, **changes})

        assert (await find())["id"] == added["id"]  # calm stands in for smile
        assert await find(action="") is None and await find(action="reading") is None  # the action must be the same
        assert await find(expression="serious") is None
        assert await find(exclude={added["id"]}) is None  # not repeated inside one episode
        flipped = await find(character_ids=added["character_ids"][::-1])
        assert flipped["id"] == added["id"] and flipped["mirror"] is True  # the other way round: reused flipped
        assert (await find())["mirror"] is False
        assert await find(action="drinking coffee and talking") is not None  # every word of the library action is in it
        assert await find(action="reading a book") is None
        monkeypatch.setattr(settings, "VISUALS_GAZE", "off")
        assert await find() is None  # drawn with the gaze fix, the setup now has it off
