"""Task 22.2: AI music generation jobs and provenance, with the deterministic fake engine."""

import sqlite3
import time

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.music import engine as music_engine
from app.services.music.engine import FakeMusicEngine
from app.services.music.pipelines import caption_for, slug, track_filename


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr(settings, "MUSIC_ENGINE", "fake")
    monkeypatch.setattr(settings, "AI_MUSIC_ENABLED", True)
    monkeypatch.setattr(settings, "MUSIC_LENGTH_STRATEGY", "full")
    with TestClient(app) as test_client:
        yield test_client


def data(response):
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    return body["data"]


def wait_job(client, job, expect="complete"):
    for _ in range(1500):
        current = data(client.get(f"/api/music/jobs/{job['id']}"))
        if current["status"] in ("complete", "error", "cancelled"):
            assert current["status"] == expect, current["error"]
            return current
        time.sleep(0.02)
    pytest.fail("music job did not finish")


def library_entries():
    folder = settings.DATA_DIR / "music_library"
    return sorted(path.name for path in folder.iterdir() if path.is_file())


def work_files():
    work = settings.DATA_DIR / "music_library" / ".work"
    return list(work.iterdir()) if work.is_dir() else []


def provenance_rows():
    with sqlite3.connect(settings.DATA_DIR / "app.db") as connection:
        return connection.execute("SELECT filename, source FROM music_tracks ORDER BY filename").fetchall()


def test_options_list_the_three_style_families(client):
    options = data(client.get("/api/music/options"))
    assert [style["id"] for style in options["styles"]] == ["lofi", "acoustic", "upbeat"]
    assert (options["min_duration_s"], options["max_duration_s"]) == (10, 1200)
    assert options["available"] is True and options["unavailable_reason"] is None


def test_generate_lands_an_mp3_with_provenance(client):
    job = data(client.post("/api/music/generate", json={
        "style": "acoustic", "brief": "  calm   morning study ", "duration_s": 480, "seed": 42,
    }))
    assert job["kind"] == "music_track"
    finished = wait_job(client, job)
    assert '"filename": "acoustic-calm-morning-study-42.mp3"' in finished["result_json"]
    assert library_entries() == ["acoustic-calm-morning-study-42.mp3"]
    stored = settings.DATA_DIR / "music_library" / "acoustic-calm-morning-study-42.mp3"
    header = stored.read_bytes()[:3]
    assert header == b"ID3" or header[0] == 0xFF  # a real MP3 from ffmpeg, not the WAV
    assert work_files() == []

    [track] = data(client.get("/api/music"))
    assert track["source"] == "ai"
    provenance = track["provenance"]
    assert provenance["style"] == "acoustic"
    assert provenance["brief"] == "calm morning study"
    assert provenance["caption"].startswith("calm morning study, acoustic guitar")
    assert provenance["caption"].endswith("instrumental")
    assert provenance["seed"] == 42
    assert provenance["duration_s"] == 480
    assert provenance["model"] == "fake music engine"
    assert provenance["licence"] == "MIT"
    assert provenance["strategy"] == "full"
    assert provenance["created_at"]


def test_a_seed_is_fixed_at_enqueue_and_long_tracks_loop(client):
    job = data(client.post("/api/music/generate", json={"style": "lofi", "duration_s": 900}))
    seed = __import__("json").loads(job["payload_json"])["seed"]
    assert 1 <= seed <= 2**31 - 1
    wait_job(client, job)
    [track] = data(client.get("/api/music"))
    assert track["filename"] == f"lofi-{seed}.mp3"
    assert track["provenance"]["seed"] == seed
    assert track["provenance"]["strategy"] == "loop"  # over ACE-Step's 600 s limit


def test_loop_strategy_setting_is_passed_to_the_engine(client, monkeypatch):
    monkeypatch.setattr(settings, "MUSIC_LENGTH_STRATEGY", "loop")
    wait_job(client, data(client.post("/api/music/generate", json={"style": "upbeat", "duration_s": 300, "seed": 3})))
    assert data(client.get("/api/music"))[0]["provenance"]["strategy"] == "loop"


def test_same_name_never_overwrites(client):
    body = {"style": "lofi", "brief": "rainy cafe", "duration_s": 60, "seed": 7}
    wait_job(client, data(client.post("/api/music/generate", json=body)))
    wait_job(client, data(client.post("/api/music/generate", json=body)))
    assert library_entries() == ["lofi-rainy-cafe-7 (1).mp3", "lofi-rainy-cafe-7.mp3"]
    assert [row[1] for row in provenance_rows()] == ["ai", "ai"]


@pytest.mark.parametrize("body", [
    {"style": "jazz", "duration_s": 60},
    {"style": "lofi", "duration_s": 9},
    {"style": "lofi", "duration_s": 1201},
    {"style": "lofi", "duration_s": 60, "seed": 0},
    {"style": "lofi", "duration_s": 60, "brief": "x" * 201},
    {"style": "lofi", "duration_s": 60, "vocals": True},
])
def test_generate_rejects_invalid_input(client, body):
    assert client.post("/api/music/generate", json=body).status_code == 422


def test_generation_unavailable_is_a_conflict(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "MUSIC_ENGINE", "worker")
    monkeypatch.setattr(music_engine, "MUSIC_PYTHON", tmp_path / "missing" / "python.exe")
    options = data(client.get("/api/music/options"))
    assert options["available"] is False
    assert "venv-music" in options["unavailable_reason"]
    response = client.post("/api/music/generate", json={"style": "lofi", "duration_s": 60})
    assert response.status_code == 409
    monkeypatch.setattr(settings, "MUSIC_ENGINE", "fake")
    monkeypatch.setattr(settings, "AI_MUSIC_ENABLED", False)
    assert client.post("/api/music/generate", json={"style": "lofi", "duration_s": 60}).status_code == 409


def test_engine_failure_leaves_no_files(client, monkeypatch):
    async def broken(self, payload):
        raise RuntimeError("worker crashed")

    monkeypatch.setattr(FakeMusicEngine, "request", broken)
    job = wait_job(client, data(client.post("/api/music/generate", json={"style": "lofi", "duration_s": 60})),
                   expect="error")
    assert "worker crashed" in job["error"]
    assert library_entries() == []
    assert work_files() == []
    assert provenance_rows() == []


def test_music_job_routes_only_serve_music_jobs(client):
    assert client.get("/api/music/jobs/not-a-job").status_code == 404
    assert client.post("/api/music/jobs/not-a-job/cancel").status_code == 404
    job = data(client.post("/api/music/generate", json={"style": "lofi", "duration_s": 60, "seed": 1}))
    wait_job(client, job)
    assert data(client.post(f"/api/music/jobs/{job['id']}/cancel"))["status"] == "complete"


def test_upload_and_delete_keep_provenance_in_step(client):
    upload = client.post("/api/music", files={"file": ("theme.mp3", b"ID3\x04\x00\x00\x00\x00\x00\x00music")})
    uploaded = data(upload)
    assert uploaded["source"] == "upload" and uploaded["provenance"] is None
    assert provenance_rows() == [("theme.mp3", "upload")]
    wait_job(client, data(client.post("/api/music/generate", json={"style": "lofi", "duration_s": 60, "seed": 9})))
    data(client.delete("/api/music/lofi-9.mp3"))
    assert provenance_rows() == [("theme.mp3", "upload")]
    data(client.delete("/api/music/theme.mp3"))
    assert provenance_rows() == []


def test_names_and_captions():
    assert slug("Buổi sáng đầu tuần ở Đà Lạt!") == "buoi-sang-dau-tuan-o-da-lat"
    assert slug("   ") == ""
    assert track_filename("lofi", "!!!", 5) == "lofi-5.mp3"
    assert len(track_filename("lofi", "word " * 30, 5)) <= len("lofi--5.mp3") + 40
    assert caption_for("upbeat", "").startswith("bright upbeat corporate pop")
