"""Task 22.9: automatic track classification and the rhythm part of auto-select."""

import sqlite3
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydub import AudioSegment

from app.core.config import settings
from app.main import app
from app.services import music_analysis
from app.services import music_select_service as select

SR = 22050


def click_track(path: Path, clicks_per_second: float, seconds: float = 100.0, bright: bool = False) -> Path:
    """Short decaying bursts at a known rate: a test signal with a known onset density."""
    rng = np.random.default_rng(1)
    t = np.arange(int(0.04 * SR)) / SR
    burst = (rng.standard_normal(t.size) if bright else np.sin(2 * np.pi * 160 * t)) * np.exp(-t * 90)
    audio = np.zeros(int(seconds * SR))
    for start in np.arange(0, seconds - 0.05, 1 / clicks_per_second):
        index = int(start * SR)
        audio[index:index + burst.size] += burst
    pcm = (np.clip(audio / max(1e-9, np.abs(audio).max()) * 0.6, -1, 1) * 32767).astype(np.int16)
    AudioSegment(pcm.tobytes(), frame_rate=SR, sample_width=2, channels=1).export(str(path), format="wav")
    return path


# --- pure rules -----------------------------------------------------------------------------

def test_pace_thresholds():
    assert music_analysis.classify_pace(3.9) == "calm"
    assert music_analysis.classify_pace(4.2) == "medium"
    assert music_analysis.classify_pace(5.79) == "medium"
    assert music_analysis.classify_pace(5.8) == "lively"


def test_mood_suggestion_rules():
    assert music_analysis.suggest_mood("lively", 2500) == "upbeat"
    assert music_analysis.suggest_mood("lively", 1200) == "inspiring"
    assert music_analysis.suggest_mood("medium", 2500) == "inspiring"
    assert music_analysis.suggest_mood("medium", 1200) == "acoustic"
    assert music_analysis.suggest_mood("calm", 2500) == "calm"
    assert music_analysis.suggest_mood("calm", 700) == "lofi"


def test_rhythm_part_of_the_score():
    track = {"filename": "a.mp3", "title": "A", "mood": None, "tags": None, "duration_s": 300.0}
    assert select.score({**track, "pace": "lively"}, "small_talk", "", 200, set())["parts"]["rhythm"] == 2
    assert select.score({**track, "pace": "medium"}, "small_talk", "", 200, set())["parts"]["rhythm"] == 1
    assert select.score({**track, "pace": "calm"}, "small_talk", "", 200, set())["parts"]["rhythm"] == 0
    assert select.score({**track, "pace": None}, "news", "", 200, set())["parts"]["rhythm"] == 0
    auto = select.score({**track, "effective_mood": "upbeat", "pace": "lively"}, "small_talk", "", 200, set())
    assert auto["parts"]["mood"] == 3  # the analysed mood counts when the owner set none
    assert "lively pace fits the rhythm of the talk" in select.rule_reason(auto, "small_talk")


# --- analysis on synthetic signals ----------------------------------------------------------

@pytest.mark.parametrize(("rate", "pace"), [(2.5, "calm"), (5.0, "medium"), (8.0, "lively")])
def test_known_onset_rates_give_the_expected_pace(tmp_path, rate, pace):
    result = music_analysis.analyse(click_track(tmp_path / f"c{rate}.wav", rate))
    assert result["onset_rate"] == pytest.approx(rate, abs=0.4)
    assert result["pace"] == pace and result["mood_auto"] in ("lofi", "calm", "acoustic", "inspiring", "upbeat")
    assert result["bpm"] and result["energy_db"] < 0


def test_brightness_separates_noise_bursts_from_low_tones(tmp_path):
    dark = music_analysis.analyse(click_track(tmp_path / "dark.wav", 8.0))
    bright = music_analysis.analyse(click_track(tmp_path / "bright.wav", 8.0, bright=True))
    assert bright["brightness_hz"] > music_analysis.BRIGHT_FROM_HZ > dark["brightness_hz"]
    assert (dark["mood_auto"], bright["mood_auto"]) == ("inspiring", "upbeat")


def test_silence_and_garbage_are_not_analysed(tmp_path):
    AudioSegment.silent(duration=10000, frame_rate=SR).export(str(tmp_path / "s.wav"), format="wav")
    (tmp_path / "x.mp3").write_bytes(b"ID3 not audio")
    assert music_analysis.analyse(tmp_path / "s.wav") is None
    assert music_analysis.analyse(tmp_path / "x.mp3") is None


# --- through the API ------------------------------------------------------------------------

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with TestClient(app) as test_client:
        yield test_client


def data(response):
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_analyse_once_and_owner_choices_win(client):
    library = settings.DATA_DIR / "music_library"
    library.mkdir(parents=True, exist_ok=True)
    click_track(library / "busy.wav", 8.0, bright=True)
    [track] = data(client.get("/api/music"))
    assert track["needs_analysis"] is True and track["pace"] is None

    result = data(client.post("/api/music/analyse"))
    assert result["analysed"] == 1
    [track] = result["tracks"]
    assert (track["pace"], track["pace_is_auto"], track["effective_mood"], track["mood_is_auto"]) == (
        "lively", True, "upbeat", True)
    assert track["mood"] is None and track["mood_label"] == "Upbeat / bright" and track["bpm"]
    assert data(client.post("/api/music/analyse"))["analysed"] == 0  # not analysed twice

    track = data(client.patch("/api/music/busy.wav", json={"mood": "calm", "pace": "calm"}))
    assert (track["effective_mood"], track["mood_is_auto"], track["pace"], track["pace_is_auto"]) == (
        "calm", False, "calm", False)
    with sqlite3.connect(settings.DATA_DIR / "app.db") as connection:
        connection.execute("UPDATE music_tracks SET analysed_at = NULL")
    [track] = data(client.post("/api/music/analyse"))["tracks"]
    assert track["pace"] == "calm"  # a re-analysis keeps the owner's pace
    track = data(client.patch("/api/music/busy.wav", json={"pace": ""}))
    assert (track["pace"], track["pace_is_auto"]) == ("lively", True)  # back to the measured pace
    assert client.patch("/api/music/busy.wav", json={"pace": "frantic"}).status_code == 422
    assert [pace["id"] for pace in data(client.get("/api/music/options"))["paces"]] == ["calm", "medium", "lively"]


def test_an_unreadable_file_is_marked_and_not_retried(client):
    library = settings.DATA_DIR / "music_library"
    library.mkdir(parents=True, exist_ok=True)
    (library / "broken.mp3").write_bytes(b"ID3 not audio")
    assert data(client.post("/api/music/analyse"))["analysed"] == 1
    [track] = data(client.get("/api/music"))
    assert track["needs_analysis"] is False and track["pace"] is None
    assert data(client.post("/api/music/analyse"))["analysed"] == 0
