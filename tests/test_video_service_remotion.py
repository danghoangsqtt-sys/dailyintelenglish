"""Tests for `video_renderer_remotion` (Task 19.7).

Subprocess-mocked (no real Remotion/Node/Chromium invocation) but the real wire-up path
through `video_service.generate_video` is exercised end-to-end -- same convention as
`tests/test_video_service.py`'s own ffmpeg-side timeout/non-zero-exit tests
(`_install_sleepy_subprocess_run`, `fake_run`).
"""

import subprocess
from pathlib import Path

import pytest

from app.core.exceptions import RemotionRenderFailedError
from app.services import video_renderer_remotion, video_service


# --- D19.7-b: renderer resolution (pure, no I/O) -------------------------------------


def test_resolve_renderer_kill_switch_off_forces_ffmpeg_regardless_of_request(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "VIDEO_RENDERER", "ffmpeg")
    assert video_renderer_remotion._resolve_renderer(None) == "ffmpeg"
    assert video_renderer_remotion._resolve_renderer("ffmpeg") == "ffmpeg"
    assert video_renderer_remotion._resolve_renderer("remotion") == "ffmpeg"


def test_resolve_renderer_kill_switch_on_request_none_uses_remotion(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "VIDEO_RENDERER", "remotion")
    assert video_renderer_remotion._resolve_renderer(None) == "remotion"


def test_resolve_renderer_kill_switch_on_request_remotion_uses_remotion(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "VIDEO_RENDERER", "remotion")
    assert video_renderer_remotion._resolve_renderer("remotion") == "remotion"


def test_resolve_renderer_request_may_always_downgrade_to_ffmpeg(monkeypatch):
    """The other direction (D19.7-b): env says remotion, request wants ffmpeg -- the safer
    path is always allowed."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "VIDEO_RENDERER", "remotion")
    assert video_renderer_remotion._resolve_renderer("ffmpeg") == "ffmpeg"


# --- D19.7-e: chapter text parsing (pure) ---------------------------------------------


def test_parse_chapters_text_real_shape():
    text = "00:00 Introduction\n00:20 Well, the first thing I do…"
    assert video_renderer_remotion._parse_chapters_text(text) == [
        {"title": "Introduction", "startSec": 0},
        {"title": "Well, the first thing I do…", "startSec": 20},
    ]


def test_parse_chapters_text_empty_string_returns_empty_list():
    assert video_renderer_remotion._parse_chapters_text("") == []


# --- D19.7-c: subprocess contract (mocked) --------------------------------------------


def _fake_input_props() -> dict:
    return {"episodeId": "p1", "lines": [], "speakers": [], "audioPath": "x.mp3", "fps": 30, "width": 1280, "height": 720}


def test_render_via_remotion_sync_success_produces_real_output(tmp_path, monkeypatch):
    output_path = tmp_path / "out.mp4"

    def fake_run(command, cwd=None, capture_output=True, text=True, timeout=None):
        Path(command[5]).write_bytes(b"fake-mp4-bytes")  # command[5] == output_path
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(video_renderer_remotion.subprocess, "run", fake_run)

    result = video_renderer_remotion._render_via_remotion_sync(_fake_input_props(), output_path)

    assert result["mp4_path"] == str(output_path)
    assert result["mode"] == "remotion"
    assert result["fallback_used"] is False
    assert isinstance(result["wall_time_seconds"], float)
    assert output_path.is_file()


def test_render_via_remotion_sync_raises_on_timeout(tmp_path, monkeypatch):
    def fake_run(command, cwd=None, capture_output=True, text=True, timeout=None):
        raise subprocess.TimeoutExpired(cmd=command, timeout=timeout)

    monkeypatch.setattr(video_renderer_remotion.subprocess, "run", fake_run)

    with pytest.raises(RemotionRenderFailedError, match="timed out"):
        video_renderer_remotion._render_via_remotion_sync(_fake_input_props(), tmp_path / "out.mp4")


def test_render_via_remotion_sync_raises_on_non_zero_exit(tmp_path, monkeypatch):
    def fake_run(command, cwd=None, capture_output=True, text=True, timeout=None):
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="remotion blew up")

    monkeypatch.setattr(video_renderer_remotion.subprocess, "run", fake_run)

    with pytest.raises(RemotionRenderFailedError, match="remotion blew up"):
        video_renderer_remotion._render_via_remotion_sync(_fake_input_props(), tmp_path / "out.mp4")


def test_render_via_remotion_sync_raises_on_missing_output_despite_exit_zero(tmp_path, monkeypatch):
    def fake_run(command, cwd=None, capture_output=True, text=True, timeout=None):
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")  # never wrote the file

    monkeypatch.setattr(video_renderer_remotion.subprocess, "run", fake_run)

    with pytest.raises(RemotionRenderFailedError, match="no output file"):
        video_renderer_remotion._render_via_remotion_sync(_fake_input_props(), tmp_path / "out.mp4")


# --- D19.7-d: fallback-rate counters ---------------------------------------------------


def test_fallback_rate_counters_track_calls_and_failures(tmp_path, monkeypatch):
    monkeypatch.setattr(
        video_renderer_remotion, "_remotion_stats", {"total_calls": 0, "fallback_count": 0, "last_fallback_reason": None}
    )

    def fake_run_success(command, cwd=None, capture_output=True, text=True, timeout=None):
        Path(command[5]).write_bytes(b"ok")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    def fake_run_failure(command, cwd=None, capture_output=True, text=True, timeout=None):
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="boom")

    monkeypatch.setattr(video_renderer_remotion.subprocess, "run", fake_run_success)
    video_renderer_remotion._render_via_remotion_sync(_fake_input_props(), tmp_path / "a.mp4")
    video_renderer_remotion._render_via_remotion_sync(_fake_input_props(), tmp_path / "b.mp4")

    monkeypatch.setattr(video_renderer_remotion.subprocess, "run", fake_run_failure)
    with pytest.raises(RemotionRenderFailedError):
        video_renderer_remotion._render_via_remotion_sync(_fake_input_props(), tmp_path / "c.mp4")

    stats = video_renderer_remotion.get_remotion_stats()
    assert stats["remotion_total_calls"] == 3
    assert stats["remotion_fallback_count"] == 1
    assert stats["fallback_rate"] == pytest.approx(1 / 3, abs=1e-4)
    assert stats["last_fallback_reason"] == "non_zero_exit"


# --- D19.7-a/I36-a: generate_video's kill switch + fallback integration --------------


async def _real_audio_job(tmp_path) -> dict:
    from pydub.generators import Sine

    audio_path = tmp_path / "mix.mp3"
    Sine(440).to_audio_segment(duration=500).apply_gain(-20).export(str(audio_path), format="mp3", bitrate="192k")
    return {
        "status": "complete",
        "mp3_path": str(audio_path),
        "duration_seconds": 0.5,
        "timestamps": [{"start_sec": 0.0, "end_sec": 0.5, "label": "Alex", "speaker_id": "sp1", "text": "Hi"}],
        "word_timestamps": [],
    }


def _real_project() -> dict:
    return {
        "id": "proj-remotion",
        "name": "Test Episode",
        "topic": "Testing",
        "cefr_level": "B1",
        "speakers": [{"id": "sp1", "name": "Alex", "gender": "male", "avatar_image_path": None}],
    }


async def test_kill_switch_forces_ffmpeg_even_when_request_wants_remotion(tmp_path, monkeypatch, db):
    """D19.7-b's safety direction: DIE_VIDEO_RENDERER unset (default "ffmpeg") must force
    ffmpeg regardless of what the request asks for -- render_via_remotion must never even
    be attempted."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr(settings, "VIDEO_RENDERER", "ffmpeg")

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("render_via_remotion must never be called when the kill switch is off")

    monkeypatch.setattr(video_renderer_remotion, "render_via_remotion", _fail_if_called)

    audio_job = await _real_audio_job(tmp_path)
    result = await video_service.generate_video(
        "proj-remotion", audio_job, "midnight", renderer="remotion", db=db, project=_real_project()
    )

    assert result.get("fallback_used") in (None, False)
    assert Path(result["mp4_path"]).is_file()


async def test_remotion_selected_without_db_or_project_falls_back_to_ffmpeg(tmp_path, monkeypatch):
    """Defensive branch: if a caller ever resolves to "remotion" without passing `db`/
    `project` (the route always passes both, but `generate_video`'s own signature makes
    them optional to preserve every pre-Phase-19 positional call site), this must degrade
    to ffmpeg rather than crash -- `render_via_remotion` needs both to build real props."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr(settings, "VIDEO_RENDERER", "remotion")

    audio_job = await _real_audio_job(tmp_path)
    result = await video_service.generate_video("proj-no-db", audio_job, "midnight", renderer="remotion")

    assert result["fallback_used"] is True
    assert result["mode"] == "background"
    assert Path(result["mp4_path"]).is_file()


async def test_remotion_failure_falls_back_to_ffmpeg_and_records_fallback_used(tmp_path, monkeypatch, db):
    """I36-a: any Remotion failure must still produce a playable video via ffmpeg, with
    `fallback_used=True` recorded."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr(settings, "VIDEO_RENDERER", "remotion")

    async def _always_fails(*args, **kwargs):
        raise RemotionRenderFailedError("simulated failure")

    monkeypatch.setattr(video_renderer_remotion, "render_via_remotion", _always_fails)

    audio_job = await _real_audio_job(tmp_path)
    result = await video_service.generate_video(
        "proj-remotion-fail", audio_job, "midnight", renderer="remotion", db=db, project=_real_project()
    )

    assert result["fallback_used"] is True
    assert result["mode"] == "background"
    assert Path(result["mp4_path"]).is_file()


async def test_remotion_success_returns_remotion_result_without_touching_ffmpeg(tmp_path, monkeypatch, db):
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr(settings, "VIDEO_RENDERER", "remotion")

    async def _fake_success(db_, project_, audio_job_, learning_, output_path, caption_style="outline"):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake-remotion-mp4")
        return {
            "mp4_path": str(output_path),
            "srt_path": None,
            "background_image": None,
            "mode": "remotion",
            "fallback_used": False,
            "wall_time_seconds": 1.23,
        }

    monkeypatch.setattr(video_renderer_remotion, "render_via_remotion", _fake_success)

    def _fail_if_ffmpeg_called(*args, **kwargs):
        raise AssertionError("ffmpeg must not run when Remotion succeeds")

    monkeypatch.setattr(video_service, "_render_video_sync", _fail_if_ffmpeg_called)

    audio_job = await _real_audio_job(tmp_path)
    result = await video_service.generate_video(
        "proj-remotion-ok", audio_job, "midnight", renderer="remotion", db=db, project=_real_project()
    )

    assert result["mode"] == "remotion"
    assert result["fallback_used"] is False
    assert Path(result["mp4_path"]).read_bytes() == b"fake-remotion-mp4"


# --- Task 20.2d: caption style reaches the Remotion props --------------------------------


@pytest.mark.parametrize("caption_style", ["outline", "box", "shade"])
async def test_generate_video_forwards_caption_style_to_remotion(tmp_path, monkeypatch, db, caption_style):
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr(settings, "VIDEO_RENDERER", "remotion")
    seen = {}

    async def _fake_success(db_, project_, audio_job_, learning_, output_path, caption_style="outline"):
        seen["caption_style"] = caption_style
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake")
        return {"mp4_path": str(output_path), "srt_path": None, "background_image": None, "mode": "remotion",
                "fallback_used": False, "wall_time_seconds": 0.1}

    monkeypatch.setattr(video_renderer_remotion, "render_via_remotion", _fake_success)
    audio_job = await _real_audio_job(tmp_path)
    await video_service.generate_video(
        "proj-caption", audio_job, "midnight", renderer="remotion", db=db, project=_real_project(),
        caption_style=caption_style,
    )

    assert seen["caption_style"] == caption_style


async def test_build_input_props_carries_caption_style_with_outline_default(tmp_path, db):
    audio_job = await _real_audio_job(tmp_path)

    default_props = await video_renderer_remotion._build_input_props(db, _real_project(), audio_job, None)
    box_props = await video_renderer_remotion._build_input_props(db, _real_project(), audio_job, None, "box")

    assert default_props["captionStyle"] == "outline"
    assert box_props["captionStyle"] == "box"


def test_render_via_remotion_sync_hands_remotion_an_absolute_path(tmp_path, monkeypatch):
    """Regression (2026-10-06, real end-to-end episode): Remotion runs with cwd=video-renderer/, and
    DATA_DIR is the relative "data" in a dev checkout. A relative output path made it write under
    video-renderer/data/ while the check looked under data/, so every Enhanced render fell back."""
    monkeypatch.chdir(tmp_path)
    renderer_dir = tmp_path / "video-renderer"
    renderer_dir.mkdir()
    seen = {}

    def fake_run(command, cwd=None, capture_output=True, text=True, timeout=None):
        seen["output"], seen["cwd"] = command[5], cwd
        target = Path(command[5]) if Path(command[5]).is_absolute() else Path(cwd) / command[5]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"fake-mp4-bytes")  # what Remotion does: relative to its own cwd
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(video_renderer_remotion, "VIDEO_RENDERER_DIR", renderer_dir)
    monkeypatch.setattr(video_renderer_remotion.subprocess, "run", fake_run)
    relative = Path("data") / "video" / "p1" / "video_remotion.mp4"
    result = video_renderer_remotion._render_via_remotion_sync(_fake_input_props(), relative)

    assert Path(seen["output"]).is_absolute()
    assert Path(result["mp4_path"]) == (tmp_path / relative).resolve()
    assert (tmp_path / relative).is_file()
    assert not (renderer_dir / "data").exists()
