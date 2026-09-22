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
        "duration_seconds": 0.8,
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


async def test_generate_video_duration_matches_audio_exactly(tmp_path, monkeypatch):
    """Task 14.10 (D14): `-t {duration}` replaces `-shortest`, which measurably
    overshot at real (~300s) durations (Gate B-3 measured a 2.48s tail, root-caused
    and reproduced directly against this exact command shape -- see task-14.10.md).
    A short fixture can't reproduce the overshoot itself (it only appeared at real
    scale), but it can and does prove `-t` -- not `-shortest` -- is what's actually
    driving the render, since the rendered video's own stream duration now comes
    from the passed `duration_seconds`, not from wherever the audio input happens
    to end."""
    import subprocess
    from pathlib import Path

    from app.core.config import settings

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    audio_path = tmp_path / "mix.mp3"
    Sine(440).to_audio_segment(duration=800).apply_gain(-20).export(str(audio_path), format="mp3", bitrate="192k")
    audio_job = {
        "status": "complete",
        "mp3_path": str(audio_path),
        "duration_seconds": 0.8,
        "timestamps": [{"start_sec": 0.0, "end_sec": 0.8, "label": "Alex", "speaker_id": "sp1", "text": "Hi"}],
    }

    result = await video_service.generate_video("proj-av-match", audio_job, "midnight")

    probe = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=duration", "-of", "default=nw=1:nk=1",
            str(Path(result["mp4_path"])),
        ],
        capture_output=True, text=True, timeout=30,
    )
    assert float(probe.stdout.strip()) == pytest.approx(0.8, abs=0.05)


async def test_generate_video_default_aspect_ratio_does_not_render_vertical(tmp_path, monkeypatch):
    """Task 2.5b: default (`"16:9"`) must be byte-for-byte the existing behavior --
    no vertical file, no `mp4_path_vertical` key, zero extra ffmpeg calls."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    audio_path = tmp_path / "mix.mp3"
    Sine(440).to_audio_segment(duration=500).apply_gain(-20).export(str(audio_path), format="mp3", bitrate="192k")
    audio_job = {
        "status": "complete",
        "mp3_path": str(audio_path),
        "duration_seconds": 0.5,
        "timestamps": [{"start_sec": 0.0, "end_sec": 0.5, "label": "Alex", "speaker_id": "sp1", "text": "Hi"}],
    }

    result = await video_service.generate_video("proj-default-ratio", audio_job, "midnight")

    assert "mp4_path_vertical" not in result


async def test_generate_video_16x9_regenerate_deletes_stale_vertical_file(tmp_path, monkeypatch):
    """Task 2.6b: a vertical file from an earlier `"9:16"` call must not linger as an
    orphan on disk once a later regenerate call doesn't ask for it again -- it was
    derived from the 16:9 render/subtitles that call just replaced, so it's stale."""
    from pathlib import Path

    from app.core.config import settings

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    audio_path = tmp_path / "mix.mp3"
    Sine(440).to_audio_segment(duration=500).apply_gain(-20).export(str(audio_path), format="mp3", bitrate="192k")
    audio_job = {
        "status": "complete",
        "mp3_path": str(audio_path),
        "duration_seconds": 0.5,
        "timestamps": [{"start_sec": 0.0, "end_sec": 0.5, "label": "Alex", "speaker_id": "sp1", "text": "Hi"}],
    }

    first = await video_service.generate_video("proj-stale-vertical", audio_job, "midnight", "9:16")
    vertical_path = Path(first["mp4_path_vertical"])
    assert vertical_path.is_file()

    second = await video_service.generate_video("proj-stale-vertical", audio_job, "midnight")

    assert "mp4_path_vertical" not in second
    assert not vertical_path.exists()


async def test_generate_video_9x16_produces_a_real_playable_vertical_mp4(tmp_path, monkeypatch):
    """Task 2.5b, closing the real gap Task 2.1c found: real ffprobe confirms the
    rendered vertical MP4 is genuinely 9:16 (VIDEO_WIDTH_SHORTS x VIDEO_HEIGHT_SHORTS),
    not the same 16:9 file relabeled."""
    import subprocess
    from pathlib import Path

    from app.core.config import settings
    from app.core.constants import VIDEO_HEIGHT_SHORTS, VIDEO_WIDTH_SHORTS

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    audio_path = tmp_path / "mix.mp3"
    Sine(440).to_audio_segment(duration=800).apply_gain(-20).export(str(audio_path), format="mp3", bitrate="192k")
    audio_job = {
        "status": "complete",
        "mp3_path": str(audio_path),
        "duration_seconds": 0.8,
        "timestamps": [{"start_sec": 0.0, "end_sec": 0.8, "label": "Alex", "speaker_id": "sp1", "text": "Hello!"}],
    }

    result = await video_service.generate_video("proj-vertical", audio_job, "midnight", "9:16")

    assert "mp4_path_vertical" in result
    vertical_path = Path(result["mp4_path_vertical"])
    assert vertical_path.is_file() and vertical_path.stat().st_size > 0
    # The 16:9 output must still exist and be untouched by the second ffmpeg pass.
    assert Path(result["mp4_path"]).is_file()

    probe = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0",
            str(vertical_path),
        ],
        capture_output=True, text=True, timeout=30,
    )
    assert probe.stdout.strip() == f"{VIDEO_WIDTH_SHORTS}x{VIDEO_HEIGHT_SHORTS}"


async def test_generate_video_invalid_aspect_ratio_does_not_render_vertical(tmp_path, monkeypatch):
    """`generate_video` itself doesn't validate aspect_ratio (the API layer's Pydantic
    validator does) -- confirms only the exact `"9:16"` string triggers the second pass,
    so an unrecognized value degrades to the safe default rather than silently rendering."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    audio_path = tmp_path / "mix.mp3"
    Sine(440).to_audio_segment(duration=500).apply_gain(-20).export(str(audio_path), format="mp3", bitrate="192k")
    audio_job = {
        "status": "complete",
        "mp3_path": str(audio_path),
        "duration_seconds": 0.5,
        "timestamps": [{"start_sec": 0.0, "end_sec": 0.5, "label": "Alex", "speaker_id": "sp1", "text": "Hi"}],
    }

    result = await video_service.generate_video("proj-bad-ratio", audio_job, "midnight", "not-a-ratio")

    assert "mp4_path_vertical" not in result


async def test_save_and_get_video_job_roundtrip(db):
    await db.execute(
        "INSERT INTO projects (id, name, status, created_at, updated_at) "
        "VALUES ('p1', 'Test', 'audio_generated', 't', 't')"
    )
    await db.commit()

    saved = await video_service.save_video_job(
        db,
        "p1",
        status="complete",
        mp4_path="v.mp4",
        mp4_path_vertical="v_vertical.mp4",
        srt_path="v.srt",
        background_image="midnight",
    )
    assert saved["status"] == "complete"
    assert saved["background_image"] == "midnight"
    assert saved["mp4_path_vertical"] == "v_vertical.mp4"

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


async def test_mark_video_job_failed_preserves_every_existing_non_failure_column(db, monkeypatch):
    await db.execute(
        "INSERT INTO projects (id, name, status, created_at, updated_at) "
        "VALUES ('p1', 'Test', 'video_generated', 't', 't')"
    )
    times = iter(["successful-at", "failed-at"])
    monkeypatch.setattr(video_service, "_now", lambda: next(times))
    await video_service.save_video_job(
        db,
        "p1",
        status="complete",
        mode="avatar_lipssync",
        mp4_path="prior.mp4",
        mp4_path_vertical="prior_vertical.mp4",
        srt_path="prior.srt",
        background_image="midnight",
    )
    await db.execute(
        "UPDATE video_jobs SET subtitle_style_json = ? WHERE project_id = 'p1'",
        ('{"font":"Inter","size":48}',),
    )
    await db.commit()
    cursor = await db.execute("SELECT * FROM video_jobs WHERE project_id = 'p1'")
    before = dict(await cursor.fetchone())

    failed = await video_service.mark_video_job_failed(db, "p1", "regeneration failed")

    cursor = await db.execute("SELECT * FROM video_jobs WHERE project_id = 'p1'")
    after = dict(await cursor.fetchone())
    preserved_columns = set(before) - {"status", "error_message", "completed_at"}
    assert {column: after[column] for column in preserved_columns} == {
        column: before[column] for column in preserved_columns
    }
    assert after["status"] == "error"
    assert after["error_message"] == "regeneration failed"
    assert after["completed_at"] == "failed-at"
    assert failed["mp4_path"] == "prior.mp4"
    assert failed["mp4_path_vertical"] == "prior_vertical.mp4"
    assert failed["srt_path"] == "prior.srt"


async def test_mark_video_job_failed_inserts_error_only_row_on_first_attempt(db, monkeypatch):
    await db.execute(
        "INSERT INTO projects (id, name, status, created_at, updated_at) "
        "VALUES ('p1', 'Test', 'audio_generated', 't', 't')"
    )
    await db.commit()
    monkeypatch.setattr(video_service, "_now", lambda: "failed-at")

    failed = await video_service.mark_video_job_failed(db, "p1", "first attempt failed")

    assert failed["status"] == "error"
    assert failed["error_message"] == "first attempt failed"
    assert failed["started_at"] == "failed-at"
    assert failed["completed_at"] == "failed-at"
    assert failed["mode"] == "background"
    for column in (
        "mp4_path",
        "mp4_path_vertical",
        "srt_path",
        "background_image",
        "subtitle_style_json",
    ):
        assert failed[column] is None
