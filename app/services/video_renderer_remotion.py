"""Task 19.7: `VideoService`'s Remotion render path -- renderer resolution, prop
building, the subprocess contract, and in-memory fallback-rate counters.

The only place `app/` ever invokes the `video-renderer/` subprocess in production. Mirrors
`scripts/run_remotion_spike.py`'s proven pattern (temp props file, `time.monotonic()` wall
time, strict output-path validation, `cwd=video-renderer/`) rather than importing that
script directly -- it's a standalone measurement tool with its own `sys.path` setup, not a
module meant to be imported by `app/`.

Real per-word timestamps (Task 19.2's `audio_jobs.word_timestamps_json`) are used exactly
as captured when present; unlike the spike runner, this module never re-synthesizes via a
fresh TTS call for missing word data -- that was a spike-only measurement-continuity
convenience for a pre-Task-19.2 demo episode, not something a real render should pay for on
every call. A line with no captured words simply renders the Task 19.3 (D19.3-c) plain-text
fallback -- no karaoke highlight for that line, not an error.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import platform
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import aiosqlite

from app.core.config import settings
from app.core.constants import VIDEO_FPS, VIDEO_HEIGHT_STANDARD, VIDEO_WIDTH_STANDARD
from app.core.exceptions import AudioMixError, NotFoundError, RemotionRenderFailedError, TTSError, ValidationError
from app.core.paths import get_project_root
from app.services import audio_service, avatar_service, brand_service, youtube_service
from app.services.visuals import library_service, project_visuals_service, storyboard_service

VIDEO_RENDERER_DIR = get_project_root() / "video-renderer"
REMOTION_AUDIO_DIR = VIDEO_RENDERER_DIR / "public" / "remotion-render" / "audio"
REMOTION_BRAND_DIR = VIDEO_RENDERER_DIR / "public" / "remotion-render" / "brand"
# The owner-signed intro/outro timings (types.ts defaults, task-19.6.md), now sent explicitly so the
# Task 22.4 soundtrack and the composition always agree on the video's length.
logger = logging.getLogger(__name__)
REMOTION_INTRO_SEC = 2.5
REMOTION_OUTRO_SEC = 5.0
REMOTION_AVATARS_DIR = VIDEO_RENDERER_DIR / "public" / "remotion-render" / "avatars"
REMOTION_VISUALS_DIR = VIDEO_RENDERER_DIR / "public" / "remotion-render" / "visuals"


def _copy_visual_source(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)

# Task 19.7 (D19.7-c): cross-checked against every real Phase 19 wall-time measurement so
# far -- the worst real reading across 19.1-19.6 was 19.6's own transient-load outlier at
# 85.07s (docs/operations/phase19-t6-intro-outro.md §7); Task 19.1's linear extrapolation to
# a genuine 8-minute episode was ~166s. 600s is a ~3.6x margin over the extrapolated 8-min
# case and a ~7x margin over the worst real measurement seen so far.
REMOTION_RENDER_TIMEOUT_SECONDS = 600.0

# Task 19.7 (D19.7-d): module-level, process-lifetime counters -- same in-memory-only
# pattern as app/main.py's `_ai_circuits: dict[str, CircuitBreaker] = {}` (Phase 18). Reset
# on server restart; no DB persistence, owner-accepted precedent from that same task.
_remotion_stats: dict[str, Any] = {
    "total_calls": 0,
    "fallback_count": 0,
    "last_fallback_reason": None,
}


REMOTION_MIN_NODE_MAJOR = 24  # video-renderer/package.json's own "engines.node": ">=24.0.0"


def check_node_version() -> tuple[bool, str]:
    """Task 19.7 (D19.7-e): real finding -- this project's own `video-renderer/package.json`
    pins `>=24.0.0` for its installed Remotion 4.0.529, not a generic "Remotion 4.0.x needs
    >=20" figure; the owner's real installed Node is v24.20.0 (confirmed 2026-09-28)."""
    node = shutil.which("node")
    if node is None:
        return False, "Node.js not found in PATH"
    try:
        result = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=10)
    except (subprocess.SubprocessError, OSError) as exc:
        return False, f"Node.js found but failed to run: {exc}"
    version = result.stdout.strip().lstrip("v")
    try:
        major = int(version.split(".")[0])
    except (ValueError, IndexError):
        return False, f"Could not parse Node.js version from {result.stdout.strip()!r}"
    return major >= REMOTION_MIN_NODE_MAJOR, f"Node.js {version} (video-renderer requires >={REMOTION_MIN_NODE_MAJOR})"


def check_video_renderer_deps() -> tuple[bool, str]:
    """`video-renderer/node_modules/` must exist and be at least as fresh as
    `package-lock.json` -- a stale install (lockfile changed since the last `npm install`)
    would otherwise silently report GREEN."""
    node_modules = VIDEO_RENDERER_DIR / "node_modules"
    lockfile = VIDEO_RENDERER_DIR / "package-lock.json"
    if not node_modules.is_dir():
        return False, f"{node_modules} not found -- run `npm install` in video-renderer/"
    if lockfile.is_file() and lockfile.stat().st_mtime > node_modules.stat().st_mtime:
        return False, "video-renderer/package-lock.json is newer than node_modules/ -- run `npm install` again"
    return True, f"{node_modules} present and up to date"


def check_remotion_browser() -> tuple[bool, str]:
    """GREEN if Chrome Headless Shell is already downloaded, or if
    `settings.REMOTION_ALLOW_DOWNLOAD` will let Remotion's own CLI fetch it on first real
    use (confirmed via a real probe, D19.7-h: `remotion render`/`remotion still` call
    `ensureBrowser()` internally -- ~113 MB compressed download, ~270 MB on disk once
    extracted). Real platform gap (found during the probe, not assumed): Chrome Headless
    Shell has no Windows-on-arm64 build at all -- always YELLOW there regardless of the
    download setting."""
    if platform.system() == "Windows" and platform.machine().lower() in ("arm64", "aarch64"):
        return False, "Chrome Headless Shell has no Windows-on-arm64 build -- Remotion path unavailable on this machine"
    already_downloaded = (VIDEO_RENDERER_DIR / "node_modules" / ".remotion").is_dir()
    if already_downloaded:
        return True, "Chrome Headless Shell already downloaded"
    if settings.REMOTION_ALLOW_DOWNLOAD:
        return True, "not yet downloaded -- will download automatically on first Remotion render (~113 MB, ~270 MB on disk)"
    return False, "not downloaded and REMOTION_ALLOW_DOWNLOAD is false"


def is_remotion_configured() -> bool:
    """`GET /api/video/health`'s `remotion_configured` -- true only when all 3 real checks
    above pass, computed live (not cached) since availability can change mid-first-download."""
    return all(passed for passed, _ in (check_node_version(), check_video_renderer_deps(), check_remotion_browser()))


def _resolve_renderer(requested: str | None) -> str:
    """D19.7-b: exactly two real backend tiers. `settings.VIDEO_RENDERER` is the kill
    switch -- any value other than the literal string `"remotion"` (unset, `"ffmpeg"`, or
    anything else) forces ffmpeg regardless of what the request asks for (I36's safety
    direction). A request may always downgrade `"remotion"` -> `"ffmpeg"` (the safer path
    is always allowed); it can only ever reach `"remotion"` when the kill switch already
    permits it."""
    if settings.VIDEO_RENDERER != "remotion":
        return "ffmpeg"
    if requested == "ffmpeg":
        return "ffmpeg"
    return "remotion"


def get_remotion_stats() -> dict[str, Any]:
    """Snapshot of the fallback-rate counters for `GET /api/video/health` (D19.7-d)."""
    total = _remotion_stats["total_calls"]
    fallback = _remotion_stats["fallback_count"]
    return {
        "remotion_total_calls": total,
        "remotion_fallback_count": fallback,
        "fallback_rate": round(fallback / total, 4) if total else 0.0,
        "last_fallback_reason": _remotion_stats["last_fallback_reason"],
    }


def _record_call(fallback_reason: str | None) -> None:
    _remotion_stats["total_calls"] += 1
    if fallback_reason is not None:
        _remotion_stats["fallback_count"] += 1
        _remotion_stats["last_fallback_reason"] = fallback_reason


def _parse_chapters_text(chapters_text: str) -> list[dict[str, Any]]:
    """Task 19.6/19.7 (D19.6-e): `youtube_service.real_chapters_from_timestamps` returns a
    plain-text "MM:SS Label" block, not the structured `Array<{title, startSec}>` the
    video-renderer props schema needs. Duplicated from `scripts/run_remotion_spike.py`
    rather than imported (that script is a standalone tool, not a module `app/` imports) --
    same small-helper-duplication convention already used elsewhere in this codebase (e.g.
    every browser test file owns its own `_envelope()`). Only reformats fields the function
    already computed; never decides which lines become chapters."""
    chapters: list[dict[str, Any]] = []
    for line in chapters_text.splitlines():
        if not line.strip():
            continue
        timestamp, _, title = line.partition(" ")
        minutes_str, _, seconds_str = timestamp.partition(":")
        chapters.append({"title": title, "startSec": int(minutes_str) * 60 + int(seconds_str)})
    return chapters


def _words_to_props(words: list[dict]) -> list[dict]:
    """`audio_jobs.word_timestamps_json`'s per-word shape (`start_sec`/`end_sec`) to the
    video-renderer props shape (`startSec`/`endSec`)."""
    return [{"text": word["text"], "startSec": word["start_sec"], "endSec": word["end_sec"]} for word in words]


async def _copy_avatar_into_public(db: aiosqlite.Connection, project_id: str, speaker_id: str) -> str | None:
    """Resolves the speaker's real avatar file via `avatar_service.resolve_avatar_path`
    (NOT `project["speakers"]`'s own `avatar_image_path` field, which
    `project_service.get_project` already rewrites into a served URL, not a filesystem
    path -- a real finding: the spike runner's raw-DB read never hit this, since it reads
    the column directly, but this production path goes through the normal service layer).
    Returns `None` (not an error) when the speaker has no avatar."""
    try:
        avatar_path = await avatar_service.resolve_avatar_path(db, project_id, speaker_id)
    except Exception:
        return None
    REMOTION_AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    destination = REMOTION_AVATARS_DIR / f"{speaker_id}{avatar_path.suffix or '.png'}"
    shutil.copyfile(avatar_path, destination)
    return f"remotion-render/avatars/{destination.name}"


def _copy_audio_into_public(project_id: str, mp3_path: str) -> None:
    """Remotion can't read an absolute filesystem path as an asset src -- every asset must
    live under `video-renderer/public/` and be loaded via `staticFile()` (same constraint
    the spike runner works around)."""
    REMOTION_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(mp3_path, REMOTION_AUDIO_DIR / f"{project_id}.mp3")


async def _resolve_still_plate(db: aiosqlite.Connection, project_id: str, still_scene_id: str | None) -> Path:
    """Phase 30: the plate of the scene a `podcast_still` video shows. The chosen scene (it must have a plate); else the
    first of the project's scenes that has one; else the first library scene that has one. Raises ValidationError."""
    async def plate_of(scene: dict) -> Path | None:
        if not scene.get("preview_path"):
            return None
        try:
            return await asyncio.to_thread(library_service.resolve_library_content, scene["preview_path"], "library/scenes")
        except Exception:
            return None

    if still_scene_id:
        try:
            scene = await library_service.get_scene_row(db, still_scene_id)
        except NotFoundError as exc:  # a bad choice in the request is a 422, not a missing page
            raise ValidationError("Choose a scene from the library: that scene does not exist.") from exc
        plate = await plate_of(scene)
        if plate is None:
            raise ValidationError(f"The scene \"{scene['name']}\" has no plate yet: make its plate in the Character Library first.")
        return plate
    candidates = list(await project_visuals_service.scene_rows(db, project_id))
    cursor = await db.execute("SELECT * FROM scenes ORDER BY is_builtin DESC, name")
    candidates += [dict(row) for row in await cursor.fetchall()]
    for scene in candidates:
        plate = await plate_of(scene)
        if plate is not None:
            return plate
    raise ValidationError("No scene has a plate yet: make a scene plate in the Character Library, or choose another video picture mode.")


async def _portrait_for(db: aiosqlite.Connection, character_id: str, speaker_id: str) -> str | None:
    """Phase 30: the cast character's full-body sheet view (else its face) as a card picture, copied under public/."""
    assets = await library_service.list_assets(db, character_id)
    for kind in ("full_body", "face"):
        asset = next((a for a in assets if a["kind"] == kind), None)
        if not asset:
            continue
        try:
            source = await asyncio.to_thread(library_service.resolve_library_content, asset["path"], "library/characters")
        except Exception:
            continue
        destination = REMOTION_AVATARS_DIR / f"{speaker_id}_portrait.png"
        await asyncio.to_thread(_copy_visual_source, source, destination)
        return f"remotion-render/avatars/{destination.name}"
    return None


async def _build_input_props(
    db: aiosqlite.Connection,
    project: dict,
    audio_job: dict,
    learning: dict | None,
    caption_style: str = "outline",
    visual_mode: str = "illustrated",
    still_scene_id: str | None = None,
) -> dict[str, Any]:
    """Real per-project props for the `Episode`/`StillFrame` compositions -- mirrors
    `scripts/run_remotion_spike.py::_build_input_props`, extended with real avatar
    resolution (via the service layer, not a raw DB column) and real learning-content
    camelCase conversion (D19.2/19.4/19.5/19.6 field shapes, unchanged)."""
    word_timestamps_by_line = (
        [_words_to_props(entry["words"]) for entry in audio_job["word_timestamps"]]
        if audio_job["word_timestamps"]
        else [[] for _ in audio_job["timestamps"]]
    )
    lines = [
        {
            "startSec": entry["start_sec"],
            "endSec": entry["end_sec"],
            "speaker": entry["label"],
            "speakerId": entry["speaker_id"],
            "text": entry["text"],
            "words": words,
        }
        for entry, words in zip(audio_job["timestamps"], word_timestamps_by_line, strict=True)
    ]

    project_id = project["id"]
    cast = await project_visuals_service.cast_rows(db, project_id)
    cast_by_index = {member["speaker_index"]: member for member in cast}
    scenes = await project_visuals_service.scene_rows(db, project_id)
    podcast = visual_mode != "illustrated"
    still_plate = await _resolve_still_plate(db, project_id, still_scene_id) if visual_mode == "podcast_still" else None
    shot_rows = [] if podcast else await project_visuals_service.shot_rows(db, project_id)  # a podcast needs no drawn shots
    complete_shots = [shot for shot in shot_rows if shot["status"] == "complete" and shot["final_path"]]
    shot_props: dict[str, dict[str, str]] = {}
    for shot in complete_shots:
        try:
            source = await asyncio.to_thread(project_visuals_service.resolve_shot_content, project_id, shot["final_path"])
        except Exception:
            continue
        destination = REMOTION_VISUALS_DIR / project_id / f"{shot['id']}.png"
        await asyncio.to_thread(_copy_visual_source, source, destination)
        shot_props[shot["id"]] = {
            "url": f"remotion-render/visuals/{project_id}/{shot['id']}.png", "kind": shot["kind"],
        }
    speaker_indexes = {speaker["id"]: speaker.get("speaker_index", index)
                       for index, speaker in enumerate(project["speakers"])}
    assignment_lines = [{**line, "speaker_index": speaker_indexes.get(line["speakerId"])} for line in lines]

    speakers_props: list[dict[str, Any]] = []
    for speaker in project["speakers"]:
        speaker_props: dict[str, Any] = {"id": speaker["id"], "name": speaker["name"], "gender": speaker["gender"]}
        if visual_mode in ("podcast_black", "podcast_still"):  # no picture of anyone in these two modes
            speakers_props.append(speaker_props)
            continue
        if visual_mode == "podcast_characters":
            member = cast_by_index.get(speaker_indexes[speaker["id"]])
            portrait = await _portrait_for(db, member["character_id"], speaker["id"]) if member else None
            if portrait is None and speaker.get("avatar_image_path"):
                portrait = await _copy_avatar_into_public(db, project["id"], speaker["id"])
            if portrait is not None:
                speaker_props["portraitUrl"] = portrait
            speakers_props.append(speaker_props)
            continue
        if speaker.get("avatar_image_path"):
            avatar_url = await _copy_avatar_into_public(db, project["id"], speaker["id"])
            if avatar_url is not None:
                speaker_props["avatarUrl"] = avatar_url
        if "avatarUrl" not in speaker_props and speaker_indexes[speaker["id"]] in cast_by_index:
            member = cast_by_index[speaker_indexes[speaker["id"]]]
            assets = await library_service.list_assets(db, member["character_id"])
            face = next((asset for asset in assets if asset["kind"] == "face"), None)
            if face:
                try:
                    face_path = await asyncio.to_thread(
                        library_service.resolve_library_content, face["path"], "library/characters",
                    )
                except Exception:
                    face_path = None
                if face_path:
                    destination = REMOTION_AVATARS_DIR / f"{speaker['id']}_cast.png"
                    await asyncio.to_thread(_copy_visual_source, face_path, destination)
                    speaker_props["avatarUrl"] = f"remotion-render/avatars/{destination.name}"
        speakers_props.append(speaker_props)

    chapters_text = youtube_service.real_chapters_from_timestamps(audio_job["timestamps"])

    chapters = _parse_chapters_text(chapters_text)
    props: dict[str, Any] = {
        "episodeId": project["id"],
        "lines": lines,
        "speakers": speakers_props,
        "audioPath": f"remotion-render/audio/{project['id']}.mp3",
        "fps": VIDEO_FPS,
        "width": VIDEO_WIDTH_STANDARD,
        "height": VIDEO_HEIGHT_STANDARD,
        "title": project["name"],
        "topic": project["topic"],
        "cefrLevel": project["cefr_level"],
        "chapters": chapters,
        "captionStyle": caption_style,
        "introSec": REMOTION_INTRO_SEC,
        "outroSec": REMOTION_OUTRO_SEC,
        "visualMode": visual_mode,
    }
    if still_plate is not None:
        destination = REMOTION_VISUALS_DIR / project_id / "still.png"
        await asyncio.to_thread(_copy_visual_source, still_plate, destination)
        props["stillUrl"] = f"remotion-render/visuals/{project_id}/still.png"
    if shot_props:
        # Task 24.5b: the approved storyboard drives the pictures when its shots exist.
        beats = await storyboard_service.approved_beats(db, project_id)
        if project_visuals_service.storyboard_timeline_ready(beats, complete_shots):
            line_shots = project_visuals_service.assign_beat_shots(assignment_lines, beats, complete_shots)
        else:
            line_shots = project_visuals_service.assign_line_shots(assignment_lines, chapters, scenes, complete_shots)
        props["visuals"] = {
            "shots": shot_props,
            "lineShots": [shot_id if shot_id in shot_props else None for shot_id in line_shots],
        }
    if learning is not None:
        props["learning"] = {
            "vocab": [
                {
                    "word": item["word"],
                    "partOfSpeech": item["part_of_speech"],
                    "ipa": item["ipa"],
                    "definitionEn": item["definition_en"],
                    "definitionVi": item["definition_vi"],
                    "exampleSentence": item["example_sentence"],
                }
                for item in learning["vocabulary"]
            ],
            "idioms": [
                {
                    "phrase": item["phrase"],
                    "meaningEn": item["meaning_en"],
                    "meaningVi": item["meaning_vi"],
                    "exampleSentence": item["example_sentence"],
                }
                for item in learning["idioms"]
            ],
        }
    return props


def _render_via_remotion_sync(input_props: dict[str, Any], output_path: Path) -> dict[str, Any]:
    """Blocking subprocess call -- must run in a thread (`asyncio.to_thread`), never on the
    event loop directly, same "Forbidden Scope" rule `video_service._render_video_sync`
    already documents. Temp-props-file + `time.monotonic()` wall time + strict
    output-path validation, mirroring `scripts/run_remotion_spike.py::_run_render` exactly.
    """
    # Remotion runs with cwd=video-renderer/, so a relative path (DATA_DIR is the relative "data" in a
    # dev checkout) made it write video-renderer/data/... while this check looked under data/ -- every
    # Enhanced render then "produced no output" and fell back to ffmpeg (found 2026-10-06 on a real
    # end-to-end episode). Always hand Remotion an absolute path.
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    npx = shutil.which("npx.cmd") or shutil.which("npx") or "npx"
    props_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
    try:
        json.dump(input_props, props_file)
        props_file.close()
        command = [npx, "remotion", "render", "src/index.ts", "Episode", str(output_path), f"--props={props_file.name}"]
        start = time.monotonic()
        try:
            result = subprocess.run(
                command,
                cwd=VIDEO_RENDERER_DIR,
                capture_output=True,
                text=True,
                timeout=REMOTION_RENDER_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            _record_call("timeout")
            raise RemotionRenderFailedError(
                f"Remotion render timed out after {REMOTION_RENDER_TIMEOUT_SECONDS:g}s"
            ) from None
        wall_time_seconds = time.monotonic() - start
    finally:
        Path(props_file.name).unlink(missing_ok=True)

    if result.returncode != 0:
        _record_call("non_zero_exit")
        raise RemotionRenderFailedError(f"Remotion render failed: {result.stderr[-500:]}")
    if not output_path.is_file():
        _record_call("missing_output")
        raise RemotionRenderFailedError("Remotion render exited 0 but produced no output file")

    _record_call(None)
    return {
        "mp4_path": str(output_path),
        "srt_path": None,
        "background_image": None,
        "mode": "remotion",
        "fallback_used": False,
        "wall_time_seconds": round(wall_time_seconds, 3),
    }


async def render_via_remotion(
    db: aiosqlite.Connection,
    project: dict,
    audio_job: dict,
    learning: dict | None,
    output_path: Path,
    caption_style: str = "outline",
    visual_mode: str = "illustrated",
    still_scene_id: str | None = None,
) -> dict[str, Any]:
    """D19.7-c: builds real props (async -- resolves avatars via the DB), then hands off to
    `_render_via_remotion_sync` in a thread for the actual blocking subprocess call. Raises
    `RemotionRenderFailedError` on timeout, non-zero exit, or a missing output file -- the
    caller (`video_service.generate_video`) always catches this and falls back to ffmpeg
    (I36-a); this function itself never falls back to anything.
    """
    project_id = project["id"]
    input_props = await _build_input_props(db, project, audio_job, learning, caption_style,
                                           visual_mode=visual_mode, still_scene_id=still_scene_id)
    await asyncio.to_thread(_copy_audio_into_public, project_id, audio_job["mp3_path"])
    voices = await _add_brand(project_id, input_props)
    soundtrack = await _build_soundtrack(project_id, audio_job, input_props, voices)
    if soundtrack is not None:
        input_props["soundtrackPath"] = soundtrack
        if "brand" in input_props:
            input_props["brand"]["voicesInSoundtrack"] = bool(voices)
    result = await asyncio.to_thread(_render_via_remotion_sync, input_props, output_path)
    return {**result, "soundtrack": soundtrack is not None, "brand_voice": bool(voices)}


def _copy_brand_voice(source: str) -> str:
    REMOTION_BRAND_DIR.mkdir(parents=True, exist_ok=True)
    destination = REMOTION_BRAND_DIR / Path(source).name
    shutil.copyfile(source, destination)
    return f"remotion-render/brand/{destination.name}"


def outro_start_seconds(input_props: dict[str, Any]) -> float:
    """Where Episode.tsx starts the outro: intro frames + speech frames, in seconds."""
    fps = input_props["fps"]
    lines = input_props["lines"]
    audio_seconds = lines[-1]["endSec"] if lines else 0
    return (round(input_props["introSec"] * fps) + round(audio_seconds * fps)) / fps


async def _add_brand(project_id: str, input_props: dict[str, Any]) -> list[tuple[str, float]]:
    """Phase 25 (D52/D53): Jenny's greeting + wish and farewell, and slide lengths that follow
    them. If Edge TTS is unreachable the branded slides still render, silent, at the minimum
    length -- a missing voice must never cost the whole video. Returns the voices on the video
    timeline (path, start seconds) for the soundtrack."""
    lines = brand_service.brand_lines(project_id)
    brand: dict[str, Any] = {"wish": lines["wish"], "farewellLine": lines["farewell_line"]}
    try:
        audio = await brand_service.brand_audio(project_id)
    except TTSError as exc:
        logger.warning("brand_voice_unavailable project_id=%s reason=%s", project_id, exc)
        timing = brand_service.brand_timing(None, None)
        input_props.update(introSec=timing["intro_s"], outroSec=timing["outro_s"], brand=brand)
        return []
    brand.update(
        greetingPath=await asyncio.to_thread(_copy_brand_voice, audio["greeting"]["path"]),
        farewellPath=await asyncio.to_thread(_copy_brand_voice, audio["farewell"]["path"]),
        greetingStartSec=audio["greeting_start_s"], farewellStartSec=audio["farewell_start_s"],
        voicesInSoundtrack=False,
    )
    input_props.update(introSec=audio["intro_s"], outroSec=audio["outro_s"], brand=brand)
    return [(audio["greeting"]["path"], audio["greeting_start_s"]),
            (audio["farewell"]["path"], outro_start_seconds(input_props) + audio["farewell_start_s"])]


def composition_seconds(input_props: dict[str, Any]) -> float:
    """The exact length Root.tsx's calculateMetadata gives the Episode composition."""
    lines = input_props["lines"]
    audio_seconds = lines[-1]["endSec"] if lines else 3
    total = input_props["introSec"] + audio_seconds + input_props["outroSec"]
    return max(1, math.ceil(total * input_props["fps"])) / input_props["fps"]


async def _build_soundtrack(project_id: str, audio_job: dict, input_props: dict[str, Any],
                            voices: list[tuple[str, float]] | None = None) -> str | None:
    """Task 22.4 (D51): with music, one soundtrack covers intro + speech + outro and fades out on the
    composition's last frame. Returns its public path, or None (no music / an old audio job)."""
    output = REMOTION_AUDIO_DIR / f"{project_id}_soundtrack.mp3"
    try:
        built = await audio_service.build_soundtrack(
            audio_job, input_props["introSec"], composition_seconds(input_props), output, voices,
        )
    except AudioMixError as exc:
        raise RemotionRenderFailedError(str(exc)) from exc
    return f"remotion-render/audio/{output.name}" if built else None
