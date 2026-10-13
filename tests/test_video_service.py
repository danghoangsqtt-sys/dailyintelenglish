"""Tests for VideoService: SRT subtitles, the Remotion-only render (Task 35.5, D89: the Standard ffmpeg renderer, its
templates and the silent fallback were removed) and the persisted video job."""

from pathlib import Path

import pytest

from app.core.config import settings
from app.core.exceptions import RemotionRenderFailedError, VideoRenderError
from app.services import video_renderer_remotion, video_service

AUDIO_JOB = {
    "status": "complete", "mp3_path": "x.mp3", "duration_seconds": 3.0,
    "timestamps": [{"start_sec": 0.0, "end_sec": 1.5, "label": "Alex", "speaker_id": "s1", "text": "Hello there."}],
}


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



async def test_generate_video_raises_when_audio_not_complete():
    with pytest.raises(VideoRenderError, match="audio mix hasn't been generated"):
        await video_service.generate_video("proj-1", None, db=None, project={})

    with pytest.raises(VideoRenderError, match="audio mix hasn't been generated"):
        await video_service.generate_video("proj-1", {"status": "error"}, db=None, project={})



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



@pytest.fixture
def ready_renderer(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr(video_service, "renderer_problem", lambda: None)


async def test_generate_video_renders_with_remotion_and_writes_srt_after_the_intro(ready_renderer, monkeypatch, tmp_path):
    async def fake_render(db, project, audio_job, learning, output_path, **kwargs):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"mp4")
        return {"mp4_path": str(output_path), "srt_path": None, "background_image": None, "mode": "remotion",
                "intro_seconds": 4.0, "soundtrack": False, "activity_uses": [], "kwargs": kwargs}

    monkeypatch.setattr(video_renderer_remotion, "render_via_remotion", fake_render)
    vertical = tmp_path / "video" / "proj-1" / "video_vertical.mp4"
    vertical.parent.mkdir(parents=True)
    vertical.write_bytes(b"vertical episode")
    result = await video_service.generate_video("proj-1", AUDIO_JOB, db=None, project={"id": "proj-1"},
                                                caption_style="box", visual_mode="podcast_sprites")
    assert result["mode"] == "remotion" and result["mp4_path"].endswith("video_remotion.mp4")
    assert result["kwargs"] == {"caption_style": "box", "visual_mode": "podcast_sprites", "still_scene_id": None}
    srt = Path(result["srt_path"]).read_text(encoding="utf-8")
    assert "00:00:04,000 --> 00:00:05,500" in srt and "Alex: Hello there." in srt  # shifted by the intro
    assert vertical.exists()  # Phase 37: the vertical episode is its own render and is kept


async def test_a_remotion_failure_fails_the_render_with_its_reason(ready_renderer, monkeypatch):
    async def failing(*args, **kwargs):
        raise RemotionRenderFailedError("Remotion render timed out after 900s")

    monkeypatch.setattr(video_renderer_remotion, "render_via_remotion", failing)
    with pytest.raises(VideoRenderError, match="timed out after 900s"):
        await video_service.generate_video("proj-1", AUDIO_JOB, db=None, project={"id": "proj-1"})


async def test_a_missing_renderer_is_named_before_any_render(monkeypatch):
    monkeypatch.setattr(video_service, "renderer_problem", lambda: "Node.js not found")

    async def never(*args, **kwargs):
        raise AssertionError("must not render")

    monkeypatch.setattr(video_renderer_remotion, "render_via_remotion", never)
    with pytest.raises(VideoRenderError, match="not ready: Node.js not found"):
        await video_service.generate_video("proj-1", AUDIO_JOB, db=None, project={"id": "proj-1"})


def test_the_srt_can_be_shifted():
    assert video_service.generate_srt(AUDIO_JOB["timestamps"], offset_seconds=2.25).splitlines()[1] ==         "00:00:02,250 --> 00:00:03,750"
