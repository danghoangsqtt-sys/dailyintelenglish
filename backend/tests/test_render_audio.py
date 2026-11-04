"""FFmpeg audio mux on the composition clock (`backend.media.render_audio`); FFmpeg itself is faked."""

import subprocess
from pathlib import Path

import pytest

from backend.core.exceptions import RemotionRenderFailedError
from backend.media import render_audio
from backend.media.render_audio import mux_timeline_audio, timeline_frame


@pytest.fixture
def public(tmp_path) -> Path:
    root = tmp_path / "public"
    (root / "audio").mkdir(parents=True)
    for name in ("voice.mp3", "bed.wav", "hello.mp3", "bye.mp3"):
        (root / "audio" / name).write_bytes(b"audio")
    return root


@pytest.fixture
def video(tmp_path) -> Path:
    path = tmp_path / "episode.rendering.mp4"
    path.write_bytes(b"remotion video")
    return path


@pytest.fixture
def ffmpeg(monkeypatch):
    """Record each command and write the mux target, as a successful FFmpeg run would."""
    commands = []

    def fake_run(command, **_kwargs):
        commands.append(command)
        Path(command[-1]).write_bytes(b"muxed video")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(render_audio.subprocess, "run", fake_run)
    return commands


def props(**extra) -> dict:
    return {"fps": 30, "introSec": 2.5, "outroSec": 5.0, "audioPath": "audio/voice.mp3",
            "lines": [{"endSec": 10.0}], **extra}


def filter_graph(command: list[str]) -> str:
    return command[command.index("-filter_complex") + 1]


def test_timeline_frame_rounds_half_up_like_javascript():
    assert timeline_frame(2.5, 30) == 75
    assert timeline_frame(0.05, 30) == 2  # 1.5 frames -> 2, not banker's rounding
    assert timeline_frame(0.0, 30) == 0


def test_voice_starts_after_the_intro_and_the_video_is_replaced(video, public, ffmpeg):
    mux_timeline_audio(video, props(), public)

    [command] = ffmpeg
    graph = filter_graph(command)
    assert str(public / "audio" / "voice.mp3") in command
    assert f"adelay={round(2.5 * 48000)}S" in graph
    assert "-c:v" in command and command[command.index("-c:v") + 1] == "copy"
    assert video.read_bytes() == b"muxed video"
    assert not list(video.parent.glob("*.muxing-*"))


def test_soundtrack_replaces_voice_and_brand_sources(video, public, ffmpeg):
    mux_timeline_audio(video, props(soundtrackPath="audio/bed.wav",
                                    brand={"greetingPath": "audio/hello.mp3", "voicesInSoundtrack": True}), public)

    [command] = ffmpeg
    inputs = [command[i + 1] for i, arg in enumerate(command) if arg == "-i"][1:]
    assert inputs == [str(public / "audio" / "bed.wav")]
    assert "adelay=0S" in filter_graph(command)


def test_brand_voices_are_placed_around_the_episode(video, public, ffmpeg):
    brand = {"greetingPath": "audio/hello.mp3", "greetingStartSec": 0.5,
             "farewellPath": "audio/bye.mp3", "farewellStartSec": 1.0}
    mux_timeline_audio(video, props(brand=brand), public)

    graph = filter_graph(ffmpeg[0])
    greeting = timeline_frame(0.5, 30) / 30
    farewell = (timeline_frame(2.5, 30) + timeline_frame(10.0, 30) + timeline_frame(1.0, 30)) / 30
    assert f"adelay={round(greeting * 48000)}S" in graph
    assert f"adelay={round(farewell * 48000)}S" in graph
    assert "amix=inputs=3" in graph


def test_clip_frames_trim_the_timeline_inclusively(video, public, ffmpeg):
    mux_timeline_audio(video, props(), public, frames=(30, 59))

    command = ffmpeg[0]
    assert "atrim=start=1.000000000:end=2.000000000" in filter_graph(command)
    assert command[command.index("-t") + 1] == "1.000000000"


@pytest.mark.parametrize("frames", [(-1, 10), (20, 10), (0, 10_000)])
def test_invalid_frame_range_is_refused_before_ffmpeg(video, public, ffmpeg, frames):
    with pytest.raises(RemotionRenderFailedError, match="frame range"):
        mux_timeline_audio(video, props(), public, frames=frames)
    assert ffmpeg == []


@pytest.mark.parametrize("path", ["audio/missing.mp3", "../outside.mp3"])
def test_sources_must_exist_inside_the_public_directory(video, public, ffmpeg, path):
    (public.parent / "outside.mp3").write_bytes(b"audio")
    with pytest.raises(RemotionRenderFailedError, match="outside the public directory"):
        mux_timeline_audio(video, props(audioPath=path), public)
    assert ffmpeg == []


def test_ffmpeg_failure_keeps_the_staged_video(video, public, monkeypatch):
    def failing_run(command, **_kwargs):
        Path(command[-1]).write_bytes(b"partial")
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="aac encoder exploded")

    monkeypatch.setattr(render_audio.subprocess, "run", failing_run)
    with pytest.raises(RemotionRenderFailedError, match="aac encoder exploded"):
        mux_timeline_audio(video, props(), public)
    assert video.read_bytes() == b"remotion video"
    assert not list(video.parent.glob("*.muxing-*"))
