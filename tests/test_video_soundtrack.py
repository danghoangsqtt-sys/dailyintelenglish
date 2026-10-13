"""Task 22.4 (D51): the full-video music soundtrack of the Remotion render (the ffmpeg renderer went in Task 35.5)."""

import json

import pytest
from pydub.generators import Sine

from app.core.config import settings
from app.services import audio_service, music_bed, video_renderer_remotion
from app.services.music_bed import SAMPLE_RATE

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

    async def fake_props(db, project, audio_job, learning, caption_style, **_options):
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
