"""Tests for VideoService (Task 1.7, Sub-task 1.7a).

Like AudioService (tests/test_audio_service.py), ffmpeg is a required local system binary
this project cannot function without, so the render test exercises the real ffmpeg
subprocess on a real tiny background image + real tiny audio file — not mocked.
"""

import pytest
from pydub.generators import Sine

from app.core.exceptions import VideoRenderError
from app.services import audio_service, video_service  # noqa: F401 -- audio_service import

# ^ audio_service's module-level `_ensure_ffmpeg_dir_on_path` shim is what makes pydub's
# own `shutil.which("ffprobe")` lookup succeed on this machine (DIE_FFMPEG_PATH is an
# absolute path, not on the system PATH) -- video_service itself never needs this since it
# calls ffmpeg via an explicit subprocess path, but this test file uses pydub directly to
# build fixture audio.


def test_generate_srt_formats_cues_with_speaker_label_and_sequential_numbers():
    timestamps = [
        {"start_sec": 0.0, "end_sec": 1.5, "label": "Alex", "speaker_id": "sp1", "text": "Welcome!"},
        {"start_sec": 1.5, "end_sec": 3.25, "label": "Sam", "speaker_id": "sp2", "text": "Thanks for having me."},
    ]

    srt = video_service.generate_srt(timestamps)

    assert srt.startswith("1\n00:00:00,000 --> 00:00:01,500\nAlex: Welcome!\n")
    assert "2\n00:00:01,500 --> 00:00:03,250\nSam: Thanks for having me.\n" in srt


def test_generate_srt_handles_hour_boundary():
    timestamps = [{"start_sec": 3661.234, "end_sec": 3662.0, "label": "Alex", "speaker_id": "sp1", "text": "Hi"}]
    srt = video_service.generate_srt(timestamps)
    assert "01:01:01,234 --> 01:01:02,000" in srt


def test_generate_srt_empty_timestamps_returns_empty_string():
    assert video_service.generate_srt([]) == ""


def test_list_video_templates_returns_all_three_with_preview_urls():
    templates = video_service.list_video_templates()
    ids = {t["id"] for t in templates}
    assert ids == set(video_service.VIDEO_TEMPLATE_IDS)
    for template in templates:
        assert template["preview_url"] == f"/static/video_backgrounds/{template['id']}.png"


async def test_generate_video_raises_when_audio_not_complete():
    with pytest.raises(VideoRenderError, match="audio mix hasn't been generated"):
        await video_service.generate_video("proj-1", None, "midnight")

    with pytest.raises(VideoRenderError, match="audio mix hasn't been generated"):
        await video_service.generate_video("proj-1", {"status": "error"}, "midnight")


async def test_generate_video_raises_on_unknown_template(tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    audio_path = tmp_path / "mix.mp3"
    Sine(440).to_audio_segment(duration=500).export(str(audio_path), format="mp3", bitrate="192k")
    audio_job = {"status": "complete", "mp3_path": str(audio_path), "timestamps": []}

    with pytest.raises(VideoRenderError, match="Background template not found"):
        await video_service.generate_video("proj-1", audio_job, "not-a-real-template")


async def test_generate_video_produces_a_real_playable_mp4(tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    audio_path = tmp_path / "mix.mp3"
    Sine(440).to_audio_segment(duration=800).apply_gain(-20).export(str(audio_path), format="mp3", bitrate="192k")
    audio_job = {
        "status": "complete",
        "mp3_path": str(audio_path),
        "timestamps": [{"start_sec": 0.0, "end_sec": 0.8, "label": "Alex", "speaker_id": "sp1", "text": "Hello!"}],
    }

    result = await video_service.generate_video("proj-real", audio_job, "midnight")

    from pathlib import Path

    mp4_path = Path(result["mp4_path"])
    srt_path = Path(result["srt_path"])
    assert mp4_path.is_file() and mp4_path.stat().st_size > 0
    assert srt_path.is_file()
    assert "Alex: Hello!" in srt_path.read_text(encoding="utf-8")
    assert result["background_image"] == "midnight"


async def test_save_and_get_video_job_roundtrip(db):
    await db.execute(
        "INSERT INTO projects (id, name, status, created_at, updated_at) "
        "VALUES ('p1', 'Test', 'audio_generated', 't', 't')"
    )
    await db.commit()

    saved = await video_service.save_video_job(
        db, "p1", status="complete", mp4_path="v.mp4", srt_path="v.srt", background_image="midnight"
    )
    assert saved["status"] == "complete"
    assert saved["background_image"] == "midnight"

    fetched = await video_service.get_video_job(db, "p1")
    assert fetched == saved

    replaced = await video_service.save_video_job(db, "p1", status="error", error_message="boom")
    assert replaced["status"] == "error"
    assert replaced["error_message"] == "boom"

    cursor = await db.execute("SELECT COUNT(*) as n FROM video_jobs WHERE project_id = 'p1'")
    row = await cursor.fetchone()
    assert row["n"] == 1


async def test_get_video_job_returns_none_when_never_generated(db):
    assert await video_service.get_video_job(db, "no-such-project") is None
