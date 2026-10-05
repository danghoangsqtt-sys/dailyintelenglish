"""Task 22.4 (D51): the full-video music soundtrack on both renderers."""

import json
import subprocess
from pathlib import Path

import pytest
from pydub.generators import Sine

from app.core.config import settings
from app.core.constants import STANDARD_MUSIC_TAIL_S
from app.services import audio_service, music_bed, video_renderer_remotion, video_service
from app.services.music_bed import SAMPLE_RATE
from app.services.music_library_service import ffprobe_path

PROJECT = {"id": "proj-video-bed", "speakers": [{"id": "sp1", "name": "Lan"}]}


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path / "data")
    (tmp_path / "data" / "music_library").mkdir(parents=True)


async def mixed_job(tmp_path, music_name: str | None) -> dict:
    line = tmp_path / "line.mp3"
    Sine(440).to_audio_segment(duration=1500).apply_gain(-12).export(str(line), format="mp3")
    if music_name:
        Sine(110).to_audio_segment(duration=20000).apply_gain(-3).export(
            str(settings.DATA_DIR / "music_library" / music_name), format="mp3")
    lines = [{"id": "l0", "speaker_id": "sp1", "audio_cache_path": str(line), "text": "Hello there."}]
    job = await audio_service.mix_project(PROJECT, lines, background_music_filename=music_name)
    return {**job, "status": "complete", "project_id": PROJECT["id"], "background_music": music_name}


def video_seconds(path: str) -> float:
    out = subprocess.run([ffprobe_path(), "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


async def test_standard_video_with_music_runs_a_tail_and_fades_out(tmp_path):
    job = await mixed_job(tmp_path, "bed.mp3")
    result = await video_service.generate_video(PROJECT["id"], job, "midnight")
    assert result["soundtrack"] is True
    expected = job["duration_seconds"] + STANDARD_MUSIC_TAIL_S
    assert video_seconds(result["mp4_path"]) == pytest.approx(expected, abs=0.15)
    track = music_bed.decode(Path(result["mp4_path"]))
    end = track[:, -int(0.05 * SAMPLE_RATE):]
    assert float(abs(end).max()) < 0.01  # silent on the last frame
    srt = Path(result["srt_path"]).read_text(encoding="utf-8")
    assert "00:00:00,000 -->" in srt  # no lead-in: captions keep their timing


async def test_standard_video_without_music_is_unchanged(tmp_path):
    job = await mixed_job(tmp_path, None)
    result = await video_service.generate_video(PROJECT["id"], job, "midnight")
    assert result["soundtrack"] is False
    assert video_seconds(result["mp4_path"]) == pytest.approx(job["duration_seconds"], abs=0.15)


def props_for(job: dict) -> dict:
    return {"lines": [{"endSec": entry["end_sec"]} for entry in job["timestamps"]], "fps": 30,
            "introSec": video_renderer_remotion.REMOTION_INTRO_SEC,
            "outroSec": video_renderer_remotion.REMOTION_OUTRO_SEC}


async def test_remotion_soundtrack_matches_the_composition_length(tmp_path, monkeypatch):
    monkeypatch.setattr(video_renderer_remotion, "REMOTION_AUDIO_DIR", tmp_path / "public-audio")
    job = await mixed_job(tmp_path, "bed.mp3")
    props = props_for(job)
    public = await video_renderer_remotion._build_soundtrack(PROJECT["id"], job, props)
    assert public == f"remotion-render/audio/{PROJECT['id']}_soundtrack.mp3"
    path = tmp_path / "public-audio" / f"{PROJECT['id']}_soundtrack.mp3"
    seconds = video_renderer_remotion.composition_seconds(props)
    # Root.tsx: ceil((intro + last endSec + outro) * fps) frames.
    assert seconds * 30 == pytest.approx(round(seconds * 30))
    assert seconds >= 2.5 + job["timestamps"][-1]["end_sec"] + 5.0
    assert music_bed.decode(path).shape[1] / SAMPLE_RATE == pytest.approx(seconds, abs=0.06)


async def test_remotion_without_music_has_no_soundtrack(tmp_path, monkeypatch):
    monkeypatch.setattr(video_renderer_remotion, "REMOTION_AUDIO_DIR", tmp_path / "public-audio")
    job = await mixed_job(tmp_path, None)
    assert await video_renderer_remotion._build_soundtrack(PROJECT["id"], job, props_for(job)) is None


async def test_remotion_render_sends_the_soundtrack_prop(tmp_path, monkeypatch):
    monkeypatch.setattr(video_renderer_remotion, "REMOTION_AUDIO_DIR", tmp_path / "public-audio")
    job = await mixed_job(tmp_path, "bed.mp3")
    captured = {}

    async def fake_props(db, project, audio_job, learning, caption_style):
        return {**props_for(audio_job), "episodeId": project["id"]}

    def fake_render(input_props, output_path):
        captured.update(json.loads(json.dumps(input_props)))
        return {"mp4_path": str(output_path), "mode": "remotion", "fallback_used": False}

    monkeypatch.setattr(video_renderer_remotion, "_build_input_props", fake_props)
    monkeypatch.setattr(video_renderer_remotion, "_render_via_remotion_sync", fake_render)
    monkeypatch.setattr(video_renderer_remotion, "_copy_audio_into_public", lambda *args: None)
    result = await video_renderer_remotion.render_via_remotion(None, PROJECT, job, None, tmp_path / "v.mp4")
    assert result["soundtrack"] is True
    assert captured["soundtrackPath"].endswith("_soundtrack.mp3")
