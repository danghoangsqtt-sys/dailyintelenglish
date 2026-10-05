"""Task 22.3: a project's AI music brief, 3 previews, the pick and the attached full-length track."""

import json
import sqlite3
import time

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.exceptions import ProviderError
from app.main import app
from app.services.ai.contracts import AIMode, GenerationResult
from app.services.ai.fake_provider import FakeProvider
from app.services.ai.router import AIRouter
from app.services.music import brief_service
from app.services.music.engine import FakeMusicEngine


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr(settings, "MUSIC_ENGINE", "fake")
    monkeypatch.setattr(settings, "AI_MUSIC_ENABLED", True)
    monkeypatch.setattr(settings, "MUSIC_LENGTH_STRATEGY", "full")
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def fake_ai(monkeypatch):
    def install(outcomes):
        provider = FakeProvider("fake-local", outcomes)
        monkeypatch.setattr(brief_service, "build_ai_router_from_settings",
                            lambda: AIRouter(primary=None, fallback=provider, mode=AIMode.LOCAL))
        return provider

    return install


def result(payload) -> GenerationResult:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return GenerationResult(text=text, provider="fake", model="fake-model", latency_ms=1.0, attempt=1,
                            prompt_hash="abc123")


def data(response):
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    return body["data"]


def make_project(client, genre="interview", minutes=2):
    project = data(client.post("/api/projects", json={
        "name": "Music", "topic": "Weekend markets in Hanoi", "cefr_level": "B1", "duration_minutes": minutes,
        "num_speakers": 2, "genre": genre, "accent": "american",
        "speakers": [{"name": "Lan", "gender": "female", "accent": "american"},
                     {"name": "Minh", "gender": "male", "accent": "american"}],
    }))
    detail = data(client.get(f"/api/projects/{project['id']}"))
    ids = [speaker["id"] for speaker in sorted(detail["speakers"], key=lambda s: s["speaker_index"])]
    data(client.put(f"/api/projects/{project['id']}/script", json={"lines": [
        {"speaker_id": ids[number % 2], "text": f"Line {number} about the market."} for number in range(15)
    ]}))
    return project


def wait_job(client, job, expect="complete"):
    for _ in range(1500):
        current = data(client.get(f"/api/music/jobs/{job['id']}"))
        if current["status"] in ("complete", "error", "cancelled"):
            assert current["status"] == expect, current["error"]
            return current
        time.sleep(0.02)
    pytest.fail("music job did not finish")


GOOD = {"style": "acoustic", "brief": "warm and curious, calm tempo, soft guitar"}


# --- brief proposal ---------------------------------------------------------------------------

def test_ai_brief_is_saved_with_the_episode_length(client, fake_ai):
    project = make_project(client)
    base = f"/api/projects/{project['id']}/music"
    view = data(client.get(base))
    assert view["saved"] is False and view["default_duration_s"] == 2 * 60 + 15
    provider = fake_ai([result(GOOD)])
    view = data(client.post(f"{base}/brief"))
    assert view["proposal"] == {"path": "ai", "reason": None}
    assert (view["style"], view["brief"], view["source"]) == ("acoustic", GOOD["brief"], "ai")
    assert view["duration_s"] == 135
    prompt = provider.calls[0].prompt
    assert "Topic: Weekend markets in Hanoi" in prompt and "Genre: interview" in prompt
    assert "- Lan: Line 0 about the market." in prompt
    assert "Line 11 about" in prompt and "Line 12 about" not in prompt  # the opening only
    assert provider.calls[0].purpose == "music_brief"
    assert "previous answer was rejected" not in prompt


def test_bad_answer_gets_one_repair(client, fake_ai):
    project = make_project(client)
    provider = fake_ai([result({"style": "jazz", "brief": "smooth"}), result({**GOOD, "style": " Lofi "})])
    view = data(client.post(f"/api/projects/{project['id']}/music/brief"))
    assert view["proposal"]["path"] == "ai_repaired"
    assert view["style"] == "lofi"
    repair = provider.calls[1].prompt
    assert "previous answer was rejected" in repair and "style" in repair


def test_rule_fallback_after_two_bad_answers_or_no_ai(client, fake_ai):
    project = make_project(client, genre="small_talk")
    fake_ai([result("not json"), result({"style": "lofi", "brief": "x" * 201})])
    view = data(client.post(f"/api/projects/{project['id']}/music/brief"))
    assert view["proposal"]["path"] == "rule" and "schema" in view["proposal"]["reason"]
    assert (view["style"], view["source"]) == ("upbeat", "rule")

    other = make_project(client, genre="news")
    fake_ai([ProviderError("offline")])
    view = data(client.post(f"/api/projects/{other['id']}/music/brief"))
    assert view["proposal"]["path"] == "rule" and "AI unavailable" in view["proposal"]["reason"]
    assert view["style"] == "acoustic"


def test_episode_length_uses_real_audio_and_is_clamped(client):
    project = make_project(client, minutes=30)
    assert data(client.get(f"/api/projects/{project['id']}/music"))["default_duration_s"] == 1200
    with sqlite3.connect(settings.DATA_DIR / "app.db") as connection:
        connection.execute("INSERT INTO audio_jobs (id, project_id, status, duration_seconds) VALUES "
                           "('a1', ?, 'complete', 401.6)", (project["id"],))
    assert data(client.get(f"/api/projects/{project['id']}/music"))["default_duration_s"] == 417


# --- edit, previews, pick, attach ---------------------------------------------------------------

def test_previews_pick_and_attach(client):
    project = make_project(client)
    base = f"/api/projects/{project['id']}/music"
    assert client.post(f"{base}/previews").status_code == 409  # no brief yet
    view = data(client.put(base, json={"style": "lofi", "brief": "rainy  market morning", "duration_s": 150}))
    assert (view["source"], view["brief"]) == ("owner", "rainy market morning")

    job = data(client.post(f"{base}/previews"))
    assert data(client.post(f"{base}/previews"))["id"] == job["id"]  # no duplicate while queued
    wait_job(client, job)
    view = data(client.get(base))
    assert len(view["previews"]) == 3 and view["preview_job"] is None
    seeds = [item["seed"] for item in view["previews"]]
    assert len(set(seeds)) == 3
    preview = client.get(view["previews"][0]["url"])
    assert preview.status_code == 200 and preview.headers["content-type"] == "audio/mpeg"
    assert client.get(f"{base}/previews/12345").status_code == 404

    assert client.post(f"{base}/full", json={"seed": 12345}).status_code == 422
    full = data(client.post(f"{base}/full", json={"seed": seeds[1]}))
    assert json.loads(full["payload_json"]) == {"style": "lofi", "brief": "rainy market morning", "duration_s": 150,
                                                 "seed": seeds[1], "project_id": project["id"]}
    wait_job(client, full)
    view = data(client.get(base))
    assert view["picked_seed"] == seeds[1]
    assert view["track_filename"] == f"lofi-rainy-market-morning-{seeds[1]}.mp3" and view["track_exists"]
    [track] = data(client.get("/api/music"))
    assert track["filename"] == view["track_filename"] and track["provenance"]["duration_s"] == 150


def test_new_mood_clears_previews_but_new_length_does_not(client):
    project = make_project(client)
    base = f"/api/projects/{project['id']}/music"
    data(client.put(base, json={"style": "lofi", "brief": "calm", "duration_s": 120}))
    wait_job(client, data(client.post(f"{base}/previews")))
    data(client.put(base, json={"style": "lofi", "brief": "calm", "duration_s": 300}))
    assert len(data(client.get(base))["previews"]) == 3
    view = data(client.put(base, json={"style": "lofi", "brief": "excited", "duration_s": 300}))
    assert view["previews"] == [] and view["picked_seed"] is None


def test_previews_for_a_changed_brief_are_discarded(client, monkeypatch):
    project = make_project(client)
    base = f"/api/projects/{project['id']}/music"
    data(client.put(base, json={"style": "lofi", "brief": "calm", "duration_s": 120}))
    original = FakeMusicEngine.request

    async def edit_midway(self, payload):
        # The owner saves a new mood while the previews are being made.
        with sqlite3.connect(settings.DATA_DIR / "app.db") as connection:
            connection.execute("UPDATE project_music SET brief = 'excited' WHERE project_id = ?", (project["id"],))
        return await original(self, payload)

    monkeypatch.setattr(FakeMusicEngine, "request", edit_midway)
    finished = wait_job(client, data(client.post(f"{base}/previews")))
    assert json.loads(finished["result_json"])["stale"] is True
    assert data(client.get(base))["previews"] == []
    assert list(brief_service.previews_dir(project["id"]).glob("*.mp3")) == []


def test_failed_previews_leave_no_files(client, monkeypatch):
    project = make_project(client)
    base = f"/api/projects/{project['id']}/music"
    data(client.put(base, json={"style": "upbeat", "brief": "", "duration_s": 60}))
    calls = {"n": 0}
    original = FakeMusicEngine.request

    async def fail_third(self, payload):
        calls["n"] += 1
        if calls["n"] == 3:
            raise RuntimeError("worker crashed")
        return await original(self, payload)

    monkeypatch.setattr(FakeMusicEngine, "request", fail_third)
    wait_job(client, data(client.post(f"{base}/previews")), expect="error")
    assert list(brief_service.previews_dir(project["id"]).glob("*.mp3")) == []
    assert data(client.get(base))["previews"] == []


def test_validation_and_unknown_project(client):
    project = make_project(client)
    base = f"/api/projects/{project['id']}/music"
    for body in ({"style": "jazz", "duration_s": 60}, {"style": "lofi", "duration_s": 5},
                 {"style": "lofi", "duration_s": 60, "extra": 1}):
        assert client.put(base, json=body).status_code == 422
    assert client.get("/api/projects/missing/music").status_code == 404
    assert client.put("/api/projects/missing/music", json={"style": "lofi", "duration_s": 60}).status_code == 404
    assert client.post(f"{base}/full", json={"seed": 5}).status_code == 404  # no brief yet


def test_project_delete_removes_previews_and_row(client):
    project = make_project(client)
    base = f"/api/projects/{project['id']}/music"
    data(client.put(base, json={"style": "lofi", "brief": "calm", "duration_s": 60}))
    wait_job(client, data(client.post(f"{base}/previews")))
    folder = brief_service.previews_dir(project["id"])
    assert len(list(folder.glob("*.mp3"))) == 3
    data(client.delete(f"/api/projects/{project['id']}"))
    assert not folder.exists()
    with sqlite3.connect(settings.DATA_DIR / "app.db") as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        assert connection.execute("SELECT count(*) FROM project_music").fetchone()[0] == 0
