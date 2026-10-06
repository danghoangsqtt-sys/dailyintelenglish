"""Task 22.8 (D51): auto-select a library track by topic and length."""

import json
import sqlite3
import subprocess

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.exceptions import ProviderError
from app.main import app
from app.services import music_select_service as select
from app.services.ai.contracts import AIMode, GenerationResult
from app.services.ai.fake_provider import FakeProvider
from app.services.ai.router import AIRouter


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def fake_ai(monkeypatch):
    def install(outcomes):
        provider = FakeProvider("fake-local", outcomes)
        monkeypatch.setattr(select, "build_ai_router_from_settings",
                            lambda: AIRouter(primary=None, fallback=provider, mode=AIMode.LOCAL))
        return provider

    return install


def answer(payload) -> GenerationResult:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return GenerationResult(text=text, provider="fake", model="fake", latency_ms=1.0, attempt=1, prompt_hash="x")


def data(response):
    assert response.status_code == 200, response.text
    return response.json()["data"]


def add_track(client, filename, seconds, **details):
    path = settings.DATA_DIR / "music_library" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([settings.FFMPEG_PATH, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"anullsrc=r=8000:cl=mono", "-t", str(seconds), "-b:a", "16k", str(path)], check=True)
    data(client.get("/api/music"))
    if details:
        data(client.patch(f"/api/music/{filename}", json=details))


def make_project(client, genre="interview", minutes=2, topic="Weekend markets and street food in Hanoi"):
    return data(client.post("/api/projects", json={
        "name": "Auto music", "topic": topic, "cefr_level": "B1", "duration_minutes": minutes,
        "num_speakers": 2, "genre": genre, "accent": "american",
        "speakers": [{"name": "Lan", "gender": "female", "accent": "american"},
                     {"name": "Minh", "gender": "male", "accent": "american"}],
    }))


# --- pure scoring ---------------------------------------------------------------------------

def track(filename="a.mp3", mood="acoustic", tags=None, duration=200.0, title="A"):
    return {"filename": filename, "title": title, "mood": mood, "tags": tags, "duration_s": duration}


def test_mood_rank_follows_the_genre():
    assert select.score(track(mood="acoustic"), "interview", "", 100, set())["parts"]["mood"] == 3
    assert select.score(track(mood="lofi"), "interview", "", 100, set())["parts"]["mood"] == 2
    assert select.score(track(mood="upbeat"), "interview", "", 100, set())["parts"]["mood"] == 0
    assert select.score(track(mood=None), "interview", "", 100, set())["parts"]["mood"] == 0


def test_topic_words_match_tags_and_title_with_a_cap():
    scored = select.score(track(tags="street food, markets, travel", title="Hanoi mornings"), "news",
                          "Weekend markets and street food in Hanoi", 100, set())
    assert scored["matched_words"] == ["food", "hanoi", "market", "street"]
    assert scored["parts"]["topic"] == 3  # capped


def test_length_fit_prefers_covering_the_video():
    covers = select.score(track(duration=300), "news", "", 290, set())
    two_loops = select.score(track(duration=150), "news", "", 290, set())
    many = select.score(track(duration=30), "news", "", 290, set())
    unknown = select.score(track(duration=None), "news", "", 290, set())
    assert (covers["parts"]["length"], covers["loops"]) == (2.0, 1)
    assert (two_loops["parts"]["length"], two_loops["loops"]) == (-0.5, 2)
    assert many["parts"]["length"] == -3.0 and unknown["parts"]["length"] == -2.0  # 30 s x10: capped at -3


def test_recently_used_tracks_are_penalised():
    assert select.score(track(), "news", "", 100, {"a.mp3"})["parts"]["recent"] == -1.5


# --- the endpoint ---------------------------------------------------------------------------

def test_empty_library_and_unknown_project(client):
    project = make_project(client)
    result = data(client.post(f"/api/projects/{project['id']}/music/suggest"))
    assert (result["path"], result["filename"]) == ("none", None)
    assert result["target_s"] == 2 * 60 + 7.5
    assert client.post("/api/projects/missing/music/suggest").status_code == 404


def test_a_single_track_is_picked_without_the_ai(client, fake_ai):
    provider = fake_ai([])
    project = make_project(client)
    add_track(client, "only.mp3", 30)
    result = data(client.post(f"/api/projects/{project['id']}/music/suggest"))
    assert (result["path"], result["filename"]) == ("single", "only.mp3")
    assert "loops 5 times" in result["reason"]
    assert provider.calls == []


def test_ai_picks_among_the_top_candidates(client, fake_ai):
    project = make_project(client)
    add_track(client, "market_walk.mp3", 140, mood="acoustic", tags="market, street food")
    add_track(client, "sleepy.mp3", 140, mood="calm")
    add_track(client, "party.mp3", 20, mood="upbeat")
    provider = fake_ai([answer({"filename": "sleepy.mp3", "reason": "Calm and gentle for a relaxed chat."})])
    result = data(client.post(f"/api/projects/{project['id']}/music/suggest"))
    assert (result["path"], result["filename"], result["reason"]) == (
        "ai", "sleepy.mp3", "Calm and gentle for a relaxed chat.")
    assert [item["filename"] for item in result["candidates"]][0] == "market_walk.mp3"  # the rule's top score
    prompt = provider.calls[0].prompt
    assert "market_walk.mp3 | Market walk | acoustic | unknown pace | tempo unknown | market, street food | 2:20 | covers the video" in prompt
    assert "Topic: Weekend markets and street food in Hanoi" in prompt and provider.calls[0].purpose == "music_pick"


def test_invalid_pick_gets_one_repair_then_the_rule(client, fake_ai):
    project = make_project(client)
    add_track(client, "market_walk.mp3", 140, mood="acoustic", tags="market")
    add_track(client, "sleepy.mp3", 140, mood="calm")
    provider = fake_ai([answer({"filename": "not-in-library.mp3", "reason": "x"}),
                        answer({"filename": "sleepy.mp3", "reason": "Fits."})])
    result = data(client.post(f"/api/projects/{project['id']}/music/suggest"))
    assert (result["path"], result["filename"]) == ("ai_repaired", "sleepy.mp3")
    assert "previous answer was rejected" in provider.calls[1].prompt

    fake_ai([answer("nope"), answer({"filename": "ghost.mp3", "reason": "x"})])
    result = data(client.post(f"/api/projects/{project['id']}/music/suggest"))
    assert (result["path"], result["filename"]) == ("rule", "market_walk.mp3")
    assert "Acoustic / warm suits interview episodes" in result["reason"]

    fake_ai([ProviderError("offline")])
    result = data(client.post(f"/api/projects/{project['id']}/music/suggest"))
    assert result["path"] == "rule" and "AI unavailable" in result["ai_error"]


def test_recent_episodes_and_real_audio_length(client, fake_ai):
    fake_ai([ProviderError("offline")])
    project = make_project(client, minutes=10)
    other = make_project(client)
    add_track(client, "a.mp3", 90, mood="acoustic")
    add_track(client, "b.mp3", 90, mood="acoustic")
    with sqlite3.connect(settings.DATA_DIR / "app.db") as connection:
        connection.execute("INSERT INTO audio_jobs (id, project_id, status, background_music, completed_at) "
                           "VALUES ('j1', ?, 'complete', 'a.mp3', '2026-10-06T00:00:00Z')", (other["id"],))
        connection.execute("INSERT INTO audio_jobs (id, project_id, status, duration_seconds) "
                           "VALUES ('j2', ?, 'complete', 80.0)", (project["id"],))
    result = data(client.post(f"/api/projects/{project['id']}/music/suggest"))
    assert result["target_s"] == 87.5  # the real mix (80 s) + intro/outro, not the planned 10 min
    assert result["filename"] == "b.mp3"  # a.mp3 was just used by another episode
    assert "used recently" not in result["reason"]
