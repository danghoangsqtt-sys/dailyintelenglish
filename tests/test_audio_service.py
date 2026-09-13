"""Tests for AudioService (Task 1.6, Sub-task 1.6b).

Unlike TTS/Gemini calls (network, mocked everywhere in this suite), ffmpeg is a required
local system binary this project cannot function without — so these tests exercise the
real `pydub` + `ffmpeg`/`ffprobe` pipeline on real, tiny, tone-generated audio files, the
same "exercise the real local library" philosophy already used for Pillow rendering in
tests/test_thumbnail_service.py. No fake byte strings stand in for audio anywhere here.
"""

import pytest
from pydub import AudioSegment
from pydub.generators import Sine

from app.core.constants import (
    MUSIC_DUCKING_MAX_DBFS,
    SILENCE_DIFFERENT_SPEAKER_MS,
    SILENCE_SAME_SPEAKER_MS,
    TARGET_LOUDNESS_LUFS,
)
from app.core.exceptions import AudioMixError
from app.services import audio_service

PROJECT = {"id": "proj-audio-1", "speakers": [{"id": "sp1", "name": "Alex"}, {"id": "sp2", "name": "Sam"}]}


def _make_tone_mp3(path, *, freq: int = 440, duration_ms: int = 600, gain_db: float = -20.0) -> str:
    Sine(freq).to_audio_segment(duration=duration_ms).apply_gain(gain_db).export(str(path), format="mp3", bitrate="192k")
    return str(path)


@pytest.fixture(autouse=True)
def _isolate_data_dir(tmp_path, monkeypatch):
    """Every test gets its own DATA_DIR so audio_output/music_library never collide."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    yield


def _lines_for(tmp_path, specs: list[tuple[str, int]]) -> list[dict]:
    lines = []
    for i, (speaker_id, freq) in enumerate(specs):
        path = _make_tone_mp3(tmp_path / f"line{i}.mp3", freq=freq)
        lines.append({"id": f"line-{i}", "speaker_id": speaker_id, "audio_cache_path": path})
    return lines


async def test_mix_project_raises_on_unsynthesized_line():
    with pytest.raises(AudioMixError, match="not yet synthesized"):
        await audio_service.mix_project(PROJECT, [{"id": "line-0", "speaker_id": "sp1", "audio_cache_path": None}])


async def test_mix_project_raises_on_empty_lines():
    with pytest.raises(AudioMixError, match="no script lines"):
        await audio_service.mix_project(PROJECT, [])


async def test_mix_project_inserts_correct_silence_gaps(tmp_path):
    lines = _lines_for(tmp_path, [("sp1", 440), ("sp1", 440), ("sp2", 550)])

    result = await audio_service.mix_project(PROJECT, lines)

    timestamps = result["timestamps"]
    assert len(timestamps) == 3
    same_speaker_gap = round((timestamps[1]["start_sec"] - timestamps[0]["end_sec"]) * 1000)
    different_speaker_gap = round((timestamps[2]["start_sec"] - timestamps[1]["end_sec"]) * 1000)
    assert same_speaker_gap == SILENCE_SAME_SPEAKER_MS
    assert different_speaker_gap == SILENCE_DIFFERENT_SPEAKER_MS
    assert timestamps[0]["label"] == "Alex"
    assert timestamps[2]["label"] == "Sam"


async def test_mix_project_timestamps_are_monotonic_and_match_duration(tmp_path):
    lines = _lines_for(tmp_path, [("sp1", 440), ("sp2", 330), ("sp1", 660)])

    result = await audio_service.mix_project(PROJECT, lines)

    timestamps = result["timestamps"]
    for earlier, later in zip(timestamps, timestamps[1:]):
        assert later["start_sec"] >= earlier["end_sec"]
    assert timestamps[-1]["end_sec"] == pytest.approx(result["duration_seconds"])


async def test_mix_project_normalizes_loudness_near_target(tmp_path):
    lines = _lines_for(tmp_path, [("sp1", 440)])

    result = await audio_service.mix_project(PROJECT, lines)

    assert result["loudness_lufs"] == pytest.approx(TARGET_LOUDNESS_LUFS, abs=0.5)


async def test_mix_project_exports_playable_mp3_and_wav(tmp_path):
    lines = _lines_for(tmp_path, [("sp1", 440), ("sp2", 550)])

    result = await audio_service.mix_project(PROJECT, lines)

    mp3 = AudioSegment.from_file(result["mp3_path"])
    wav = AudioSegment.from_file(result["wav_path"])
    assert len(mp3) > 0
    assert len(wav) > 0
    assert wav.frame_rate == 44100
    assert wav.sample_width == 2


async def test_mix_project_with_background_music_caps_at_ducking_ceiling(tmp_path):
    lines = _lines_for(tmp_path, [("sp1", 440)])
    from app.core.config import settings

    music_dir = settings.DATA_DIR / "music_library"
    music_dir.mkdir(parents=True, exist_ok=True)
    # Loud music (0 dB gain) that must be ducked down to the ceiling, never left as-is.
    Sine(220).to_audio_segment(duration=3000).export(str(music_dir / "bg.mp3"), format="mp3", bitrate="192k")

    result = await audio_service.mix_project(PROJECT, lines, background_music_filename="bg.mp3")

    # The final mix includes speech (normalized to -16) overlaid with music capped at -18,
    # so the combined loudness should not spike far above either component.
    assert result["loudness_lufs"] < TARGET_LOUDNESS_LUFS + 3


async def test_mix_project_raises_on_missing_background_music_file(tmp_path):
    lines = _lines_for(tmp_path, [("sp1", 440)])

    with pytest.raises(AudioMixError, match="Background music file not found"):
        await audio_service.mix_project(PROJECT, lines, background_music_filename="does-not-exist.mp3")


async def test_duck_music_caps_loud_track_at_ceiling():
    loud = Sine(220).to_audio_segment(duration=1000)  # near 0 dBFS
    ducked = audio_service._duck_music(loud, MUSIC_DUCKING_MAX_DBFS)
    assert ducked.dBFS <= MUSIC_DUCKING_MAX_DBFS + 0.1


async def test_duck_music_never_boosts_quiet_track():
    quiet = Sine(220).to_audio_segment(duration=1000).apply_gain(-40)
    ducked = audio_service._duck_music(quiet, MUSIC_DUCKING_MAX_DBFS)
    assert ducked.dBFS == pytest.approx(quiet.dBFS)


async def test_loop_to_length_produces_exact_duration():
    short = Sine(220).to_audio_segment(duration=200)
    looped = audio_service._loop_to_length(short, 1000)
    assert len(looped) == 1000


async def test_save_and_get_audio_job_roundtrip(db):
    await db.execute(
        "INSERT INTO projects (id, name, status, created_at, updated_at) "
        "VALUES ('p1', 'Test', 'script_generated', 't', 't')"
    )
    await db.commit()

    saved = await audio_service.save_audio_job(
        db,
        "p1",
        status="complete",
        mp3_path="a.mp3",
        wav_path="a.wav",
        timestamps=[{"start_sec": 0.0, "end_sec": 1.0, "label": "Alex", "speaker_id": "sp1"}],
        background_music=None,
        duration_seconds=1.0,
        loudness_lufs=-16.0,
    )
    assert saved["status"] == "complete"
    assert saved["timestamps"][0]["label"] == "Alex"

    fetched = await audio_service.get_audio_job(db, "p1")
    assert fetched == saved

    # A second save (regenerate) replaces the row rather than duplicating it.
    replaced = await audio_service.save_audio_job(db, "p1", status="error", error_message="boom")
    assert replaced["status"] == "error"
    assert replaced["error_message"] == "boom"

    cursor = await db.execute("SELECT COUNT(*) as n FROM audio_jobs WHERE project_id = 'p1'")
    row = await cursor.fetchone()
    assert row["n"] == 1


async def test_get_audio_job_returns_none_when_never_generated(db):
    result = await audio_service.get_audio_job(db, "no-such-project")
    assert result is None
