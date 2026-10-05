"""Task 22.4 (D51): the Step 4 mix with a music bed, the voice stem, and the full-video soundtrack."""

import math

import numpy as np
import pytest
from pydub import AudioSegment
from pydub.generators import Sine

from app.core.config import settings
from app.core.constants import MUSIC_DUCK_DB, TARGET_LOUDNESS_LUFS
from app.services import audio_service, music_bed

PROJECT = {"id": "proj-bed", "speakers": [{"id": "sp1", "name": "Lan"}, {"id": "sp2", "name": "Minh"}]}
SR = music_bed.SAMPLE_RATE


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path / "data")
    (tmp_path / "data" / "music_library").mkdir(parents=True)


def line_files(tmp_path, specs):
    lines = []
    for index, (speaker_id, frequency, ms) in enumerate(specs):
        path = tmp_path / f"line{index}.mp3"
        if frequency:
            Sine(frequency).to_audio_segment(duration=ms).apply_gain(-12).export(str(path), format="mp3")
        else:
            AudioSegment.silent(duration=ms, frame_rate=24000).export(str(path), format="mp3")
        lines.append({"id": f"line-{index}", "speaker_id": speaker_id, "audio_cache_path": str(path), "text": "x"})
    return lines


def music(name="bed.mp3", seconds=5.0, frequency=110):
    Sine(frequency).to_audio_segment(duration=int(seconds * 1000)).apply_gain(-3).export(
        str(settings.DATA_DIR / "music_library" / name), format="mp3")
    return name


def rms_db(audio: np.ndarray, start_s: float, end_s: float) -> float:
    window = audio[:, int(start_s * SR):int(end_s * SR)]
    return 20 * math.log10(max(float(np.sqrt(np.mean(window ** 2))), 1e-9))


async def test_mix_with_music_keeps_timing_and_writes_the_voice_stem(tmp_path):
    lines = line_files(tmp_path, [("sp1", 440, 2000), ("sp2", 330, 1500)])
    plain = await audio_service.mix_project(PROJECT, lines)
    with_music = await audio_service.mix_project(PROJECT, lines, background_music_filename=music())
    assert with_music["timestamps"] == plain["timestamps"]
    assert with_music["duration_seconds"] == pytest.approx(plain["duration_seconds"], abs=0.002)
    assert with_music["loudness_lufs"] == pytest.approx(TARGET_LOUDNESS_LUFS, abs=1.0)
    stem = audio_service.voice_stem_path(PROJECT["id"])
    assert stem.is_file()
    assert len(AudioSegment.from_file(stem)) == pytest.approx(plain["duration_seconds"] * 1000, abs=2)


async def test_mix_without_music_is_unchanged_except_the_stem(tmp_path):
    lines = line_files(tmp_path, [("sp1", 440, 1500)])
    result = await audio_service.mix_project(PROJECT, lines)
    mixed = AudioSegment.from_file(result["wav_path"])
    stem = AudioSegment.from_file(audio_service.voice_stem_path(PROJECT["id"]))
    assert result["loudness_lufs"] == pytest.approx(TARGET_LOUDNESS_LUFS, abs=1.0)
    assert stem.channels == 1  # the plain voice, not the stereo music path
    assert len(mixed) == pytest.approx(len(stem), abs=2)


async def test_soundtrack_covers_the_whole_video_ducks_under_speech_and_fades_out(tmp_path):
    # A silent "voice" isolates the bed: open in the intro and outro, ducked under the lines.
    lines = line_files(tmp_path, [("sp1", 0, 4000), ("sp2", 0, 4000)])
    job = await audio_service.mix_project(PROJECT, lines, background_music_filename=music(seconds=30.0))  # no loop: levels only
    audio_job = {**job, "project_id": PROJECT["id"], "background_music": "bed.mp3"}
    intro, outro = 2.5, 5.0
    total = intro + job["duration_seconds"] + outro
    output = settings.DATA_DIR / "audio" / PROJECT["id"] / audio_service.SOUNDTRACK_NAME
    result = await audio_service.build_soundtrack(audio_job, intro, total, output)
    assert result["duration_seconds"] == pytest.approx(total, abs=0.001)
    track = music_bed.decode(output)
    assert track.shape[1] / SR == pytest.approx(total, abs=0.06)  # mp3 framing only

    first_line = job["timestamps"][0]
    speech_db = rms_db(track, intro + first_line["start_sec"] + 1.0, intro + first_line["end_sec"] - 0.2)
    intro_open_db = rms_db(track, 1.1, 1.8)  # after the 1 s fade-in, before the attack ramp
    outro_open_db = rms_db(track, total - 4.1, total - 3.1)  # past the release, before the fade-out
    assert speech_db - intro_open_db == pytest.approx(MUSIC_DUCK_DB, abs=1.5)
    assert speech_db - outro_open_db == pytest.approx(MUSIC_DUCK_DB, abs=1.5)
    assert rms_db(track, total - 0.08, total - 0.03) < outro_open_db - 25  # faded out at the end


async def test_soundtrack_is_skipped_without_music_or_for_old_jobs(tmp_path):
    lines = line_files(tmp_path, [("sp1", 440, 1000)])
    job = await audio_service.mix_project(PROJECT, lines)
    output = settings.DATA_DIR / "out.mp3"
    no_music = {**job, "project_id": PROJECT["id"], "background_music": None}
    assert await audio_service.build_soundtrack(no_music, 0, 5, output) is None
    audio_service.voice_stem_path(PROJECT["id"]).unlink()  # a job mixed before Task 22.4
    old = {**job, "project_id": PROJECT["id"], "background_music": music()}
    assert await audio_service.build_soundtrack(old, 0, 5, output) is None
    assert not output.exists()
