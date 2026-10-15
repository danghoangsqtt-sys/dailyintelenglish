"""Tests for `video_renderer_remotion` (Task 19.7).

Subprocess-mocked (no real Remotion/Node/Chromium invocation) but the real wire-up path
through `video_service.generate_video` is exercised end-to-end -- same convention as
`tests/test_video_service.py`'s own ffmpeg-side timeout/non-zero-exit tests
(`_install_sleepy_subprocess_run`, `fake_run`).
"""

import subprocess
import json
from pathlib import Path

import pytest

from backend.core.exceptions import RemotionRenderFailedError
from backend.media import video_renderer_remotion, video_service


# --- D19.7-b: renderer resolution (pure, no I/O) -------------------------------------


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


# --- Task 20.2d: caption style reaches the Remotion props --------------------------------


@pytest.mark.parametrize("caption_style", ["outline", "box", "shade"])
async def test_generate_video_forwards_caption_style_to_remotion(tmp_path, monkeypatch, db, caption_style):
    from backend.core.config import settings

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr(video_service, "renderer_problem", lambda: None)
    seen = {}

    async def _fake_success(db_, project_, audio_job_, learning_, output_path, caption_style="outline",
                            visual_mode="podcast_sprites", still_scene_id=None):
        seen["caption_style"] = caption_style
        seen["visual"] = (visual_mode, still_scene_id)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake")
        return {"mp4_path": str(output_path), "srt_path": None, "background_image": None, "mode": "remotion",
                "wall_time_seconds": 0.1}

    monkeypatch.setattr(video_renderer_remotion, "render_via_remotion", _fake_success)
    audio_job = await _real_audio_job(tmp_path)
    await video_service.generate_video(
        "proj-caption", audio_job, db=db, project=_real_project(),
        caption_style=caption_style, visual_mode="podcast_still", still_scene_id="builtin-cafe",
    )

    assert seen["caption_style"] == caption_style
    assert seen["visual"] == ("podcast_still", "builtin-cafe")  # Phase 30: the mode and the scene reach the renderer


async def test_build_input_props_carries_caption_style_with_outline_default(tmp_path, db):
    audio_job = await _real_audio_job(tmp_path)

    # podcast_black: no cast needed for this check (talking characters, the default, needs library characters)
    default_props = await video_renderer_remotion._build_input_props(db, _real_project(), audio_job, None,
                                                                     visual_mode="podcast_black")
    box_props = await video_renderer_remotion._build_input_props(db, _real_project(), audio_job, None, "box",
                                                                 visual_mode="podcast_black")

    assert default_props["captionStyle"] == "outline"
    assert box_props["captionStyle"] == "box"


def test_render_via_remotion_sync_hands_remotion_an_absolute_path(tmp_path, monkeypatch):
    """Regression (2026-10-06, real end-to-end episode): Remotion runs with cwd=renderer/, and
    DATA_DIR is the relative "data" in a dev checkout. A relative output path made it write under
    renderer/data/ while the check looked under data/, so every Enhanced render fell back."""
    monkeypatch.chdir(tmp_path)
    renderer_dir = tmp_path / "renderer"
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


def test_renderer_deps_follow_npms_own_install_record(tmp_path, monkeypatch):
    """Phase 38: a lockfile-only change (the package rename) rewrites node_modules/.package-lock.json but not the
    folder's own time; the check reads npm's record, so a fresh `npm install` is not reported as stale."""
    import os

    renderer = tmp_path / "renderer"
    (renderer / "node_modules").mkdir(parents=True)
    monkeypatch.setattr(video_renderer_remotion, "VIDEO_RENDERER_DIR", renderer)
    lockfile, record = renderer / "package-lock.json", renderer / "node_modules" / ".package-lock.json"
    lockfile.write_text("{}", encoding="utf-8")
    os.utime(renderer / "node_modules", (1_000, 1_000))
    record.write_text("{}", encoding="utf-8")
    os.utime(lockfile, (2_000, 2_000))
    os.utime(record, (3_000, 3_000))
    assert video_renderer_remotion.check_video_renderer_deps()[0] is True
    os.utime(lockfile, (4_000, 4_000))  # the lockfile changed after the last install
    assert video_renderer_remotion.check_video_renderer_deps()[0] is False


def test_a_locked_old_video_does_not_fail_the_render(tmp_path, monkeypatch):
    """Gate B-26 finding (2026-10-14): the Step 5 player held video_remotion.mp4 open and Remotion's final rename onto it
    failed the whole render. The render now goes to a staging file and is published with retries, else under a new name."""
    import os

    target = tmp_path / "video_remotion.mp4"
    target.write_bytes(b"old video")
    staging = tmp_path / "video_remotion.rendering-abc.mp4"
    staging.write_bytes(b"new video")
    real_replace = os.replace

    def locked(source, destination):
        if Path(destination) == target:
            raise PermissionError("in use")
        return real_replace(source, destination)

    monkeypatch.setattr(video_renderer_remotion.os, "replace", locked)
    published = video_renderer_remotion._publish(staging, target, attempts=2, wait_s=0.0)
    assert published != target and published.name.startswith("video_remotion-") and published.read_bytes() == b"new video"
    assert target.read_bytes() == b"old video" and not staging.exists()
    monkeypatch.setattr(video_renderer_remotion.os, "replace", real_replace)
    second = tmp_path / "video_remotion.rendering-def.mp4"
    second.write_bytes(b"newer video")
    assert video_renderer_remotion._publish(second, target) == target and target.read_bytes() == b"newer video"
    assert not published.exists()  # the earlier timestamped copy is cleaned up once the main name is free


def test_leftovers_of_a_failed_render_are_removed(tmp_path):
    target = tmp_path / "video_remotion.mp4"
    for name in ("video_remotion.mp4.c715.remotion-in-progress", "video_remotion.rendering-1234.mp4", "keep.mp4"):
        (tmp_path / name).write_bytes(b"x")
    video_renderer_remotion._remove_leftovers(target)
    assert sorted(path.name for path in tmp_path.iterdir()) == ["keep.mp4"]


def test_the_error_summary_keeps_the_error_line_without_colours_or_stack():
    stderr = "\x1b[31mError: EPERM: operation not permitted, rename 'a' -> 'b'\x1b[39m\n\x1b[31m    at async Object.rename\x1b[39m"
    assert video_renderer_remotion._error_summary(stderr) == "Error: EPERM: operation not permitted, rename 'a' -> 'b'"


NAVIGATION_FAILURE = 'Error: Visited "http://localhost:3000/index.html" but got no response.'


def test_transient_navigation_retries_with_remaining_budget_and_keeps_diagnostics(tmp_path, monkeypatch):
    """BUG-039: one fresh process can recover null page.goto without replacing the old output early."""
    target = tmp_path / "episode.mp4"
    target.write_bytes(b"old success")
    calls, clock = [], [0.0]
    monkeypatch.setattr(video_renderer_remotion.time, "monotonic", lambda: clock[0])

    def fake_run(command, **kwargs):
        calls.append((command, kwargs["timeout"]))
        assert target.read_bytes() == b"old success"
        clock[0] += 25.0
        if len(calls) == 1:
            Path(command[5]).write_bytes(b"partial output")
            return subprocess.CompletedProcess(command, 1, stdout="startup details", stderr=NAVIGATION_FAILURE)
        assert not Path(command[5]).exists()  # discard the failed attempt before retrying
        Path(command[5]).write_bytes(b"new success")
        return subprocess.CompletedProcess(command, 0, stdout="render complete", stderr="")

    monkeypatch.setattr(video_renderer_remotion.subprocess, "run", fake_run)
    result = video_renderer_remotion._render_via_remotion_sync(_fake_input_props(), target)
    assert target.read_bytes() == b"new success" and len(calls) == 2
    budget = video_renderer_remotion.REMOTION_RENDER_TIMEOUT_SECONDS
    assert [timeout for _, timeout in calls] == [budget, budget - 25.0]
    assert result["wall_time_seconds"] == 50.0
    records = [json.loads(line) for line in Path(result["diagnostics_path"]).read_text(encoding="utf-8").splitlines()]
    assert [record["returncode"] for record in records] == [1, 0]
    assert records[0]["stderr"] == NAVIGATION_FAILURE and records[0]["stdout"] == "startup details"
    assert all("--log=verbose" in command for command, _ in calls)


@pytest.mark.parametrize("error,attempts", [(NAVIGATION_FAILURE, 2), ("Missing font or invalid props", 1),
                                         ('Visited "https://example.com" but got no response.', 1)])
def test_failed_render_attempts_are_bounded_and_keep_previous_video(tmp_path, monkeypatch, error, attempts):
    target = tmp_path / "episode.mp4"
    target.write_bytes(b"old success")
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        Path(command[5]).write_bytes(b"partial output")
        return subprocess.CompletedProcess(command, 1, stdout="diagnostics", stderr=error)

    monkeypatch.setattr(video_renderer_remotion.subprocess, "run", fake_run)
    with pytest.raises(RemotionRenderFailedError, match="log:"):
        video_renderer_remotion._render_via_remotion_sync(_fake_input_props(), target)
    assert len(calls) == attempts and target.read_bytes() == b"old success"
    assert not list(tmp_path.glob("*.rendering-*.mp4"))
    assert len(list(tmp_path.glob("*.render-*.log"))) == 1


def test_navigation_retry_cannot_extend_the_render_timeout(tmp_path, monkeypatch):
    clock, calls = [0.0], []
    monkeypatch.setattr(video_renderer_remotion, "REMOTION_RENDER_TIMEOUT_SECONDS", 90.0)
    monkeypatch.setattr(video_renderer_remotion.time, "monotonic", lambda: clock[0])

    def fake_run(command, **kwargs):
        calls.append(command)
        assert kwargs["timeout"] == 90.0
        clock[0] += 90.0
        return subprocess.CompletedProcess(command, 1, stdout="", stderr=NAVIGATION_FAILURE)

    monkeypatch.setattr(video_renderer_remotion.subprocess, "run", fake_run)
    with pytest.raises(RemotionRenderFailedError, match="timed out"):
        video_renderer_remotion._render_via_remotion_sync(_fake_input_props(), tmp_path / "episode.mp4")
    assert len(calls) == 1


def test_render_budget_is_configurable_and_bounded():
    from pydantic import ValidationError

    from backend.core.config import Settings

    assert Settings(_env_file=None, REMOTION_RENDER_TIMEOUT_SECONDS=2400).REMOTION_RENDER_TIMEOUT_SECONDS == 2400
    for value in (0, 7201):
        with pytest.raises(ValidationError):
            Settings(_env_file=None, REMOTION_RENDER_TIMEOUT_SECONDS=value)


@pytest.mark.parametrize("gl", ["auto", "angle", "swangle"])
def test_render_uses_the_configured_compositor_without_changing_encoder(tmp_path, monkeypatch, gl):
    calls = []
    monkeypatch.setattr(video_renderer_remotion.settings, "REMOTION_GL", gl)

    def fake_run(command, **kwargs):
        calls.append(command)
        Path(command[5]).write_bytes(b"finished")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(video_renderer_remotion.subprocess, "run", fake_run)
    video_renderer_remotion._render_via_remotion_sync(_fake_input_props(), tmp_path / "out.mp4", frames=(30, 59))
    command = calls[0]
    assert [part for part in command if part.startswith("--gl=")] == ([] if gl == "auto" else [f"--gl={gl}"])
    assert "--frames=30-59" in command
    assert not any(part.startswith(("--codec", "--crf", "--video-bitrate")) for part in command)
