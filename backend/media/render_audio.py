"""Publish sample-timed AAC audio independently of Remotion's video encoder.

Remotion's muxed AAC lacked the encoder skip samples in the measured output.
Re-encoding from the source (never from that AAC) lets FFmpeg write its normal
priming metadata. The video frames are copied without another video encode.
"""

from __future__ import annotations

import math
import os
import subprocess
import uuid
from pathlib import Path

from backend.core.config import settings
from backend.core.constants import (
    RENDER_AUDIO_BITRATE, RENDER_AUDIO_MUX_TIMEOUT_SECONDS, RENDER_AUDIO_SAMPLE_RATE,
)
from backend.core.exceptions import RemotionRenderFailedError


def _public_asset(public_dir: Path, relative: str) -> Path:
    root = public_dir.resolve()
    path = (root / relative).resolve()
    if root not in path.parents or not path.is_file():
        raise RemotionRenderFailedError(f"Render audio source is missing or outside the public directory: {relative}")
    return path


def timeline_frame(seconds: float, fps: float) -> int:
    """Match JavaScript Math.round for nonnegative Sequence frame positions."""
    return math.floor(seconds * fps + 0.5)


def mux_timeline_audio(video: Path, props: dict, public_dir: Path,
                       frames: tuple[int, int] | None = None) -> None:
    """Replace staging audio on the exact composition clock, including clip trims.

    Source positions match Episode/Brand Sequence frame rounding. Clip bounds are
    inclusive, like Remotion -- trim the full timeline before resetting its PTS.
    Any failure leaves the caller's staging file and last published video intact.
    """
    fps = props["fps"]
    intro_frame = timeline_frame(props.get("introSec", 0), fps)
    duration = props.get("durationSeconds", props["lines"][-1]["endSec"] if props["lines"] else 0)
    audio_frames = timeline_frame(duration, fps)
    total_frames = max(1, math.ceil((props.get("introSec", 0) + duration + props.get("outroSec", 0)) * fps))
    first, last = frames if frames is not None else (0, total_frames - 1)
    if first < 0 or last < first or last >= total_frames:
        raise RemotionRenderFailedError("Invalid audio timeline frame range")
    if props.get("soundtrackPath"):
        sources = [(props["soundtrackPath"], 0.0)]
    else:
        sources = [(props["audioPath"], intro_frame / fps)]
        brand = props.get("brand") or {}
        if not brand.get("voicesInSoundtrack"):
            for key, base in (("greeting", 0), ("farewell", intro_frame + audio_frames)):
                if brand.get(f"{key}Path"):
                    frame = base + timeline_frame(brand.get(f"{key}StartSec", 0), fps)
                    sources.append((brand[f"{key}Path"], frame / fps))
    target = video.with_name(f"{video.stem}.muxing-{uuid.uuid4().hex[:8]}.mp4")
    command = [settings.FFMPEG_PATH, "-v", "error", "-nostdin", "-y", "-i", str(video)]
    filters = []
    for index, (relative, start) in enumerate(sources, 1):
        command.extend(["-i", str(_public_asset(public_dir, relative))])
        samples = round(start * RENDER_AUDIO_SAMPLE_RATE)
        filters.append(f"[{index}:a:0]aresample={RENDER_AUDIO_SAMPLE_RATE},asetpts=PTS-STARTPTS,adelay={samples}S:all=1[a{index}]")
    labels = "".join(f"[a{i}]" for i in range(1, len(sources) + 1))
    length = (last - first + 1) / fps
    filters.append(f"{labels}amix=inputs={len(sources)}:normalize=0:dropout_transition=0,"
                   f"apad,atrim=start={first / fps:.9f}:end={(last + 1) / fps:.9f},asetpts=PTS-STARTPTS[outa]")
    command.extend(["-filter_complex", ";".join(filters), "-map", "0:v:0", "-map", "[outa]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", RENDER_AUDIO_BITRATE,
                    "-t", f"{length:.9f}", "-movflags", "+faststart", str(target)])
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=RENDER_AUDIO_MUX_TIMEOUT_SECONDS)
        if result.returncode or not target.is_file():
            raise RemotionRenderFailedError(f"Final audio mux failed: {result.stderr[-1600:]}")
        os.replace(target, video)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RemotionRenderFailedError(f"Final audio mux failed: {exc}") from exc
    finally:
        target.unlink(missing_ok=True)
