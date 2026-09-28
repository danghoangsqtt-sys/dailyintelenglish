"""Tests for AudioService (Task 1.6, Sub-task 1.6b).

Unlike TTS/Gemini calls (network, mocked everywhere in this suite), ffmpeg is a required
local system binary this project cannot function without — so these tests exercise the
real `pydub` + `ffmpeg`/`ffprobe` pipeline on real, tiny, tone-generated audio files, the
same "exercise the real local library" philosophy already used for Pillow rendering in
tests/test_thumbnail_service.py. No fake byte strings stand in for audio anywhere here.
"""

import json

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


def _write_word_sidecar(audio_cache_path: str, words: list[dict]) -> None:
    from pathlib import Path

    Path(audio_cache_path).with_suffix(".words.json").write_text(json.dumps(words), encoding="utf-8")


async def test_mix_project_aggregates_word_boundaries_onto_mixed_timeline(tmp_path):
    """Task 19.2 (D19.2-c): word boundaries are read from each line's sidecar file and
    aggregated using the exact same `start_ms` offset already used for `timestamps_json`
    (not a second computation) -- and a missing sidecar (no edge_tts capture for that line)
    produces an empty word list, never `null`."""
    lines = _lines_for(tmp_path, [("sp1", 440), ("sp2", 550)])  # both default to a 600ms tone

    # Line 0's sidecar deliberately has a nonzero leading offset (0.05s) -- real Edge TTS
    # output has leading silence before the first word (D19.2-a probe), so the aggregation
    # must add this onto start_ms rather than assuming the first word starts at 0.
    _write_word_sidecar(lines[0]["audio_cache_path"], [{"text": "Hi", "offset_sec": 0.05, "duration_sec": 0.3}])
    # Line 1 (the last line) has one word spanning its whole 0.6s clip, so its aggregated
    # end lands exactly on the line's own end_sec.
    _write_word_sidecar(lines[1]["audio_cache_path"], [{"text": "Bye", "offset_sec": 0.0, "duration_sec": 0.6}])

    result = await audio_service.mix_project(PROJECT, lines)

    word_timestamps = result["word_timestamps"]
    assert len(word_timestamps) == 2
    assert word_timestamps[0]["line_id"] == lines[0]["id"]
    assert word_timestamps[1]["line_id"] == lines[1]["id"]

    first_word = word_timestamps[0]["words"][0]
    assert first_word["text"] == "Hi"
    assert first_word["start_sec"] == pytest.approx(result["timestamps"][0]["start_sec"] + 0.05, abs=0.001)

    last_word = word_timestamps[1]["words"][-1]
    assert last_word["text"] == "Bye"
    assert last_word["end_sec"] == pytest.approx(result["timestamps"][1]["end_sec"], abs=0.02)


async def test_mix_project_word_timestamps_empty_for_line_with_no_sidecar(tmp_path):
    """No `.words.json` sidecar (omnivoice line, or a line synthesized before Task 19.2)
    produces an empty `words` array for that line -- never `null`, never a crash."""
    lines = _lines_for(tmp_path, [("sp1", 440)])

    result = await audio_service.mix_project(PROJECT, lines)

    assert result["word_timestamps"] == [{"line_id": lines[0]["id"], "words": []}]


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

    # The final mix (speech + ducked music) is normalized as a whole, so the delivered
    # file must land within ROADMAP.md's declared ±1dB tolerance even with music present
    # (Task 2.5a fix — previously only the pre-music voice stem was normalized, leaving
    # the actually-delivered with-music file's loudness unmeasured/unnormalized).
    assert result["loudness_lufs"] == pytest.approx(TARGET_LOUDNESS_LUFS, abs=1.0)


async def test_mix_project_raises_on_missing_background_music_file(tmp_path):
    lines = _lines_for(tmp_path, [("sp1", 440)])

    with pytest.raises(AudioMixError, match="Background music file not found"):
        await audio_service.mix_project(PROJECT, lines, background_music_filename="does-not-exist.mp3")


@pytest.mark.parametrize(
    "malicious_filename",
    [
        "../../../../Windows/win.ini",
        "..\\..\\secrets.txt",
        "/etc/passwd",
        "C:/Windows/win.ini",
        "subdir/file.mp3",
        "..",
    ],
)
async def test_mix_project_rejects_path_traversal_in_background_music(tmp_path, malicious_filename):
    """A background_music value must never escape data/music_library/ (real bug, see PM audit
    2026-09-14): pathlib silently discards the base path entirely when joined with an
    absolute path, and "../" segments escape it just as easily when unvalidated."""
    lines = _lines_for(tmp_path, [("sp1", 440)])

    with pytest.raises(AudioMixError, match="Invalid background music filename"):
        await audio_service.mix_project(PROJECT, lines, background_music_filename=malicious_filename)


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


async def test_mark_audio_job_failed_preserves_every_existing_non_failure_column(db, monkeypatch):
    await db.execute(
        "INSERT INTO projects (id, name, status, created_at, updated_at) "
        "VALUES ('p1', 'Test', 'audio_generated', 't', 't')"
    )
    timestamps = [{"start_sec": 0.0, "end_sec": 1.0, "label": "Alex", "speaker_id": "sp1"}]
    times = iter(["successful-at", "failed-at"])
    monkeypatch.setattr(audio_service, "_now", lambda: next(times))
    await audio_service.save_audio_job(
        db,
        "p1",
        status="complete",
        mp3_path="prior.mp3",
        wav_path="prior.wav",
        timestamps=timestamps,
        background_music="music.mp3",
        duration_seconds=12.5,
        loudness_lufs=-16.0,
    )
    cursor = await db.execute("SELECT * FROM audio_jobs WHERE project_id = 'p1'")
    before = dict(await cursor.fetchone())

    failed = await audio_service.mark_audio_job_failed(db, "p1", "regeneration failed")

    cursor = await db.execute("SELECT * FROM audio_jobs WHERE project_id = 'p1'")
    after = dict(await cursor.fetchone())
    preserved_columns = set(before) - {"status", "error_message", "completed_at"}
    assert {column: after[column] for column in preserved_columns} == {
        column: before[column] for column in preserved_columns
    }
    assert after["status"] == "error"
    assert after["error_message"] == "regeneration failed"
    assert after["completed_at"] == "failed-at"
    assert failed["mp3_path"] == "prior.mp3"
    assert failed["wav_path"] == "prior.wav"
    assert failed["timestamps"] == timestamps


async def test_mark_audio_job_failed_inserts_error_only_row_on_first_attempt(db, monkeypatch):
    await db.execute(
        "INSERT INTO projects (id, name, status, created_at, updated_at) "
        "VALUES ('p1', 'Test', 'script_generated', 't', 't')"
    )
    await db.commit()
    monkeypatch.setattr(audio_service, "_now", lambda: "failed-at")

    failed = await audio_service.mark_audio_job_failed(db, "p1", "first attempt failed")

    assert failed["status"] == "error"
    assert failed["error_message"] == "first attempt failed"
    assert failed["started_at"] == "failed-at"
    assert failed["completed_at"] == "failed-at"
    for column in (
        "mp3_path",
        "wav_path",
        "background_music",
        "duration_seconds",
        "loudness_lufs",
    ):
        assert failed[column] is None
    assert failed["timestamps"] == []
