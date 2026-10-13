"""Task 19.7: `VideoService`'s Remotion render path -- renderer resolution, prop
building, the subprocess contract, and in-memory fallback-rate counters.

The only place `app/` ever invokes the `renderer/` subprocess in production. Mirrors
the proven pattern of the Phase 19 spike runner (removed in Phase 35) (temp props file, `time.monotonic()` wall
time, strict output-path validation, `cwd=renderer/`) rather than importing that
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
import os
import platform
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

import aiosqlite

from backend.core.config import settings
from backend.core.constants import VIDEO_FPS, VIDEO_HEIGHT_STANDARD, VIDEO_WIDTH_STANDARD
from backend.core.exceptions import AudioMixError, NotFoundError, RemotionRenderFailedError, TTSError, ValidationError
from backend.core.paths import get_project_root
from backend.media import audio_service, brand_service
from backend.content import youtube_service
from backend.library import activity_library_service as activity_library
from backend.library import (
    activity_matcher, library_service, project_visuals_service, sprite_plan, sprite_service, storyboard_service,
)

VIDEO_RENDERER_DIR = get_project_root() / "renderer"
REMOTION_AUDIO_DIR = VIDEO_RENDERER_DIR / "public" / "remotion-render" / "audio"
REMOTION_BRAND_DIR = VIDEO_RENDERER_DIR / "public" / "remotion-render" / "brand"
# The owner-signed intro/outro timings (types.ts defaults, task-19.6.md), now sent explicitly so the
# Task 22.4 soundtrack and the composition always agree on the video's length.
logger = logging.getLogger(__name__)
REMOTION_INTRO_SEC = 2.5
REMOTION_OUTRO_SEC = 5.0
REMOTION_AVATARS_DIR = VIDEO_RENDERER_DIR / "public" / "remotion-render" / "avatars"
REMOTION_VISUALS_DIR = VIDEO_RENDERER_DIR / "public" / "remotion-render" / "visuals"
REMOTION_SPRITES_DIR = VIDEO_RENDERER_DIR / "public" / "remotion-render" / "sprites"


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
# pattern as backend/main.py's `_ai_circuits: dict[str, CircuitBreaker] = {}` (Phase 18). Reset
# on server restart; no DB persistence, owner-accepted precedent from that same task.
REMOTION_MIN_NODE_MAJOR = 24  # renderer/package.json's own "engines.node": ">=24.0.0"


def check_node_version() -> tuple[bool, str]:
    """Task 19.7 (D19.7-e): real finding -- this project's own `renderer/package.json`
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
    return major >= REMOTION_MIN_NODE_MAJOR, f"Node.js {version} (renderer requires >={REMOTION_MIN_NODE_MAJOR})"


def check_video_renderer_deps() -> tuple[bool, str]:
    """`renderer/node_modules/` must exist and be at least as fresh as
    `package-lock.json` -- a stale install (lockfile changed since the last `npm install`)
    would otherwise silently report GREEN."""
    node_modules = VIDEO_RENDERER_DIR / "node_modules"
    lockfile = VIDEO_RENDERER_DIR / "package-lock.json"
    if not node_modules.is_dir():
        return False, f"{node_modules} not found -- run `npm install` in renderer/"
    # npm (v7+) rewrites node_modules/.package-lock.json on every install; the folder's own time only changes when a
    # package is added or removed, so a lockfile-only change (Phase 38 rename) read as a stale install.
    installed = node_modules / ".package-lock.json"
    installed_at = (installed if installed.is_file() else node_modules).stat().st_mtime
    if lockfile.is_file() and lockfile.stat().st_mtime > installed_at:
        return False, "renderer/package-lock.json is newer than node_modules/ -- run `npm install` again"
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


def _parse_chapters_text(chapters_text: str) -> list[dict[str, Any]]:
    """Task 19.6/19.7 (D19.6-e): `youtube_service.real_chapters_from_timestamps` returns a
    plain-text "MM:SS Label" block, not the structured `Array<{title, startSec}>` the
    renderer props schema needs. Duplicated from the Phase 19 spike runner
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
    renderer props shape (`startSec`/`endSec`)."""
    return [{"text": word["text"], "startSec": word["start_sec"], "endSec": word["end_sec"]} for word in words]


def _copy_audio_into_public(project_id: str, mp3_path: str) -> None:
    """Remotion can't read an absolute filesystem path as an asset src -- every asset must
    live under `renderer/public/` and be loaded via `staticFile()` (same constraint
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


def _copy_if_changed(source: Path, destination: Path) -> None:
    """A sprite set is about 30 MB: an unchanged picture is not copied again for every render."""
    if destination.is_file() and destination.stat().st_size == source.stat().st_size \
            and destination.stat().st_mtime >= source.stat().st_mtime:
        return
    _copy_visual_source(source, destination)


def _figure_top(path: Path) -> float:
    from PIL import Image

    with Image.open(path) as picture:
        box = picture.convert("RGBA").getchannel("A").point(lambda value: 255 if value > 20 else 0).getbbox()
    return box[1] / sprite_service.SIZE[1] if box else 0.15


def _beat_scene_per_line(beats: list[dict], line_count: int) -> list[str | None]:
    """The place of each line from the approved storyboard: a scene beat's scene; an insert keeps the place before it (or the next
    place when the story opens on an insert)."""
    places: list[str | None] = [None] * line_count
    for beat in beats:
        for index in range(beat["line_from"], min(beat["line_to"], line_count - 1) + 1):
            places[index] = beat["scene_id"] if beat["kind"] == "scene" else None
    last = None
    for index, place in enumerate(places):
        last = place or last
        places[index] = last
    following = next((place for place in places if place), None)
    return [place or following for place in places]


async def _scene_plate(db: aiosqlite.Connection, scene_id: str, project_id: str = "") -> Path | None:
    """A storyboard scene's plate, or None when the scene, its plate or the file is missing (the line then keeps the
    video's other places). BUG-025: only those expected misses fall back, and they are logged; a database or disk
    failure is raised, so the render fails with its real reason instead of quietly showing another place."""
    try:
        scene = await library_service.get_scene_row(db, scene_id)
        if not scene.get("preview_path"):
            logger.warning("sprite_scene_without_plate project_id=%s scene_id=%s", project_id, scene_id)
            return None
        return await asyncio.to_thread(library_service.resolve_library_content, scene["preview_path"], "library/scenes")
    except NotFoundError as exc:
        logger.warning("sprite_scene_plate_missing project_id=%s scene_id=%s reason=%s", project_id, scene_id, exc)
        return None


def sprite_placement(members: list[tuple[int, str]]) -> dict[int, int]:
    """Phase 33 (D81): the screen slot (0 = left, 1 = right) of each visible speaker. A man and a woman: the man on the left,
    the woman on the right, whoever speaks first. Two of the same gender: speaker order. One person: a woman on the right."""
    if len(members) == 2 and {members[0][1], members[1][1]} == {"male", "female"}:
        return {index: 0 if gender == "male" else 1 for index, gender in members}
    if len(members) == 1:
        index, gender = members[0]
        return {index: 1 if gender == "female" else 0}
    return {index: slot for slot, (index, _gender) in enumerate(sorted(members))}


def sprite_segments(line_speakers: list[int | None]) -> list[dict[str, Any]]:
    """Task 33.8: who stands on screen for each line, as runs of lines with the same pair. A line's pair is its speaker and
    the last other speaker before it (else the next other speaker), so a dialogue between two of five people shows those
    two. Lines without a known speaker keep the pair before them. Returns [{"pair": frozenset, "first": i, "last": j}]."""
    known = [index for index in line_speakers if index is not None]
    if not known:
        return []
    pairs: list[frozenset | None] = []
    for position, speaker in enumerate(line_speakers):
        if speaker is None:
            pairs.append(None)
            continue
        before = next((other for other in reversed(line_speakers[:position]) if other is not None and other != speaker), None)
        after = next((other for other in line_speakers[position + 1:] if other is not None and other != speaker), None)
        partner = before if before is not None else after
        pairs.append(frozenset({speaker} if partner is None else {speaker, partner}))
    first_known = next(pair for pair in pairs if pair is not None)
    for position, pair in enumerate(pairs):  # a line with no known speaker keeps the pair before it (the first pair at the start)
        if pair is None:
            pairs[position] = pairs[position - 1] if position else first_known
    segments: list[dict[str, Any]] = []
    for position, pair in enumerate(pairs):
        if segments and segments[-1]["pair"] == pair:
            segments[-1]["last"] = position
        else:
            segments.append({"pair": pair, "first": position, "last": position})
    return segments


def sprite_mirrored(slot: int, sprite_facing: str, gender: str) -> bool:
    """Phase 33 (D82): the left figure looks right and the right figure looks left, so the two face each other; a pack that
    looks the other way is mirrored. A pack with no recorded facing faces like its gender's default."""
    facing = sprite_facing or ("right" if gender == "male" else "left")
    return facing != ("right" if slot == 0 else "left")


async def _build_sprite_props(db: aiosqlite.Connection, project: dict, lines: list[dict], audio_job: dict,
                              still_scene_id: str | None) -> dict[str, Any]:
    """Phase 32 (Task 32.4): the props of the "podcast_sprites" mode -- the two cast characters' sprite sets (copied under public/),
    the plan of each line (`sprite_plan`) and the scene plate of each line. Raises ValidationError when a speaker's character has no
    usable sprite set (D32-i)."""
    project_id = project["id"]
    cast_by_index = {member["speaker_index"]: member for member in await project_visuals_service.cast_rows(db, project_id)}
    speaker_indexes = {speaker["id"]: speaker.get("speaker_index", index) for index, speaker in enumerate(project["speakers"])}
    line_speakers = [speaker_indexes.get(line["speakerId"]) for line in lines]
    segments = sprite_segments(line_speakers)
    for speaker_index in sorted({index for segment in segments for index in segment["pair"]}):
        if speaker_index not in cast_by_index:
            speaker_name = next(s["name"] for s in project["speakers"] if speaker_indexes[s["id"]] == speaker_index)
            raise ValidationError(f"{speaker_name} has no library character: cast one in Step 4 before the talking characters video.")

    sets: dict[str, dict] = {}  # character_id -> its copied pack, prepared once even when it stands in several segments
    for speaker_index in sorted({index for segment in segments for index in segment["pair"]}):
        member = cast_by_index[speaker_index]
        sprite_set = await asyncio.to_thread(sprite_service.load_set, member["character_id"])
        if not sprite_service.usable(sprite_set):
            raise ValidationError(f"{member['name']} has no talking sprites yet: import the sprite pictures on the Shot Library page "
                                  "(Talking sprites), or choose another video picture mode.")
        folder = Path(sprite_set["folder"])
        pictures: dict[str, str] = {}
        for name in sprite_set["names"]:
            await asyncio.to_thread(_copy_if_changed, folder / f"{name}.png",
                                    REMOTION_SPRITES_DIR / project_id / member["character_id"] / f"{name}.png")
            pictures[name] = f"remotion-render/sprites/{project_id}/{member['character_id']}/{name}.png"
        sets[member["character_id"]] = {
            "pictures": pictures, "names": set(sprite_set["names"]), "faceEllipse": sprite_set["face_ellipse"],
            "offsets": {name: [value["head_dx"], value["head_dy"]] for name, value in sprite_set["pictures"].items()},
            "topFraction": await asyncio.to_thread(_figure_top, folder / f"{sprite_service.BASE}.png"),
        }

    # Task 33.8: each segment shows its own pair, placed (D81) and mirrored (D82) for that pair, inside a time window
    characters: list[dict[str, Any]] = []
    segment_plans: list[tuple[dict, dict[int, int], dict[int, set[str]]]] = []
    for number, segment in enumerate(segments):
        placement = sprite_placement([(index, cast_by_index[index]["gender"]) for index in sorted(segment["pair"])])
        from_sec = 0.0 if number == 0 else lines[segment["first"]]["startSec"]
        to_sec = None if number == len(segments) - 1 else lines[segments[number + 1]["first"]]["startSec"]
        available: dict[int, set[str]] = {}
        for speaker_index, slot in placement.items():
            member = cast_by_index[speaker_index]
            pack = sets[member["character_id"]]
            characters.append({
                "slot": slot, "name": member["name"], "pictures": pack["pictures"], "faceEllipse": pack["faceEllipse"],
                "mirror": sprite_mirrored(slot, member.get("sprite_facing") or "", member.get("gender") or ""),
                "offsets": pack["offsets"], "topFraction": pack["topFraction"], "fromSec": from_sec, "toSec": to_sec,
            })
            available[slot] = pack["names"]
        segment_plans.append((segment, placement, available))

    # the place of each line: the approved storyboard's scenes that have a plate, else one plate for the whole video
    beats = await storyboard_service.approved_beats(db, project_id)
    backgrounds: dict[str, str] = {}
    line_backgrounds: list[str | None] = [None] * len(lines)
    if beats:
        for index, scene_id in enumerate(_beat_scene_per_line(beats, len(lines))):
            if scene_id is None:
                continue
            if scene_id not in backgrounds:
                plate = await _scene_plate(db, scene_id, project_id)
                if plate is None:
                    continue
                await asyncio.to_thread(_copy_visual_source, plate, REMOTION_SPRITES_DIR / project_id / "bg" / f"{scene_id}.png")
                backgrounds[scene_id] = f"remotion-render/sprites/{project_id}/bg/{scene_id}.png"
            line_backgrounds[index] = scene_id
    if not backgrounds:
        plate = await _resolve_still_plate(db, project_id, still_scene_id)
        await asyncio.to_thread(_copy_visual_source, plate, REMOTION_SPRITES_DIR / project_id / "bg" / "still.png")
        backgrounds = {"still": f"remotion-render/sprites/{project_id}/bg/still.png"}
        line_backgrounds = ["still"] * len(lines)

    beat_expressions: list[str | None] = [None] * len(lines)
    for beat in beats or []:
        for index in range(beat["line_from"], min(beat["line_to"], len(lines) - 1) + 1):
            beat_expressions[index] = beat.get("expression")
    try:
        loudness = await asyncio.to_thread(sprite_plan.loudness_per_frame, audio_job["mp3_path"], VIDEO_FPS)
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        logger.warning("sprite_loudness_unavailable project_id=%s reason=%s -- mouths follow the words", project_id, exc)
        loudness = None
    plan: list[dict] = []
    for segment, placement, available in segment_plans:  # each segment's lines point at that segment's screen slots
        span = range(segment["first"], segment["last"] + 1)
        slots = [placement.get(line_speakers[index]) for index in span]
        plan += sprite_plan.build_plan([lines[index] for index in span], [slot if slot in available else None for slot in slots],
                                       [beat_expressions[index] for index in span], available, loudness, VIDEO_FPS)
    candidates, cutaways, activity_uses = await activity_library.approved_candidates(db), [], []
    all_line_speakers = [speaker_indexes.get(line["speakerId"]) for line in lines]
    line_texts = [line["text"] for line in lines]
    for beat in beats or []:
        if beat["kind"] != "insert" or beat["line_from"] >= len(lines):
            continue
        speaker = activity_matcher.beat_speaker_index(beat, all_line_speakers, line_texts)
        character_id = cast_by_index.get(speaker, {}).get("character_id") if speaker is not None else None
        dialogue = " ".join(line["text"] for line in lines[beat["line_from"]:beat["line_to"] + 1])
        selected = activity_matcher.match_activity(candidates, character_id, beat.get("action") or "", dialogue)
        if selected is None:
            continue
        source = await activity_library.content_path(db, selected["activity_id"])
        destination = REMOTION_SPRITES_DIR / project_id / "activities" / f"{selected['activity_id']}{source.suffix.lower()}"
        await asyncio.to_thread(_copy_visual_source, source, destination)
        start, last = lines[beat["line_from"]]["startSec"], lines[min(beat["line_to"], len(lines) - 1)]["endSec"]
        end = min(last, start + 6.0)
        if end > start:
            cutaways.append({"startSec": start, "endSec": end,
                             "url": f"remotion-render/sprites/{project_id}/activities/{destination.name}"})
            activity_uses.append({"activity_id": selected["activity_id"], "beat_id": beat["id"]})
    return {"characters": characters, "lines": plan, "backgrounds": backgrounds, "lineBackgrounds": line_backgrounds,
            "cutaways": cutaways, "_activityUses": activity_uses}


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
    the Phase 19 spike runner's `_build_input_props`, extended with real avatar
    resolution (via the service layer, not a raw DB column) and real learning-content
    camelCase conversion (D19.2/19.4/19.5/19.6 field shapes, unchanged)."""
    word_timestamps_by_line = (
        [_words_to_props(entry["words"]) for entry in audio_job["word_timestamps"]]
        if audio_job["word_timestamps"]
        else [[] for _ in audio_job["timestamps"]]
    )
    without_words = sum(1 for words in word_timestamps_by_line if not words)
    if without_words:  # Task 32.8c (BUG-030): those lines get plain captions, not karaoke
        logger.warning("karaoke_words_missing project_id=%s lines=%d/%d -- regenerate the audio to restore karaoke",
                       project["id"], without_words, len(word_timestamps_by_line))
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
        if podcast:  # no picture of anyone in the podcast modes
            speakers_props.append(speaker_props)
            continue
        if speaker_indexes[speaker["id"]] in cast_by_index:  # Task 35.4: the cast character's face is the only picture
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
    if visual_mode == "podcast_sprites":
        props["sprites"] = await _build_sprite_props(db, project, lines, audio_job, still_scene_id)
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


def _render_via_remotion_sync(input_props: dict[str, Any], output_path: Path,
                              frames: tuple[int, int] | None = None) -> dict[str, Any]:
    """Blocking subprocess call -- must run in a thread (`asyncio.to_thread`), never on the
    event loop directly, same "Forbidden Scope" rule as every blocking render call. Temp-props-file + `time.monotonic()` wall time + strict
    output-path validation, mirroring the Phase 19 spike runner's `_run_render`.
    """
    # Remotion runs with cwd=renderer/, so a relative path (DATA_DIR is the relative "data" in a
    # dev checkout) made it write renderer/data/... while this check looked under data/ -- every
    # Enhanced render then "produced no output" and fell back to ffmpeg (found 2026-10-06 on a real
    # end-to-end episode). Always hand Remotion an absolute path.
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _remove_leftovers(output_path)
    # Render to a staging file, then publish it (Gate B-26 finding, 2026-10-14): Remotion's last step renames its file onto
    # the target, which Windows refuses while the old video is open (the Step 5 player streams it) -- the whole render failed.
    staging = output_path.with_name(f"{output_path.stem}.rendering-{uuid.uuid4().hex[:8]}{output_path.suffix}")
    npx = shutil.which("npx.cmd") or shutil.which("npx") or "npx"
    props_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
    try:
        json.dump(input_props, props_file)
        props_file.close()
        command = [npx, "remotion", "render", "src/index.ts", "Episode", str(staging), f"--props={props_file.name}"]
        if frames is not None:  # Phase 37 (D99): a highlight clip is a frame range of the vertical episode
            command.append(f"--frames={frames[0]}-{frames[1]}")
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
            _remove_leftovers(output_path)
            raise RemotionRenderFailedError(
                f"Remotion render timed out after {REMOTION_RENDER_TIMEOUT_SECONDS:g}s"
            ) from None
        wall_time_seconds = time.monotonic() - start
    finally:
        Path(props_file.name).unlink(missing_ok=True)

    if result.returncode != 0:
        _remove_leftovers(output_path)
        raise RemotionRenderFailedError(f"Remotion render failed: {_error_summary(result.stderr)}")
    if not staging.is_file():
        raise RemotionRenderFailedError("Remotion render exited 0 but produced no output file")
    published = _publish(staging, output_path)

    return {
        "mp4_path": str(published),
        "srt_path": None,
        "background_image": None,
        "mode": "remotion",
        "wall_time_seconds": round(wall_time_seconds, 3),
    }


_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _error_summary(stderr: str) -> str:
    """The error line(s) of Remotion's stderr without colour codes and stack frames (the raw tail cut the message)."""
    lines = [_ANSI.sub("", line).strip() for line in (stderr or "").splitlines()]
    lines = [line for line in lines if line and not line.startswith("at ")]
    errors = [line for line in lines if "error" in line.lower()]
    return " | ".join((errors or lines)[-3:])[:600] or "no error output"


def _remove_leftovers(output_path: Path) -> None:
    """Staging files and Remotion's `*.remotion-in-progress` files left by an earlier failed render of this output."""
    for pattern in (f"{output_path.stem}.rendering-*{output_path.suffix}", f"{output_path.name}.*.remotion-in-progress",
                    f"{output_path.stem}.rendering-*{output_path.suffix}.*.remotion-in-progress"):
        for leftover in output_path.parent.glob(pattern):
            try:
                leftover.unlink()
            except OSError:
                logger.warning("remotion_leftover_locked path=%s", leftover)


def _publish(staging: Path, target: Path, attempts: int = 10, wait_s: float = 0.5) -> Path:
    """Move the finished render onto `target`, retrying while the old file is locked; if it stays locked (open in a
    player), keep the new video under a timestamped name instead of failing the render. Returns the final path."""
    for attempt in range(attempts):
        try:
            os.replace(staging, target)
            for older in target.parent.glob(f"{target.stem}-*{target.suffix}"):  # earlier timestamped copies
                try:
                    older.unlink()
                except OSError:
                    pass
            return target
        except PermissionError:
            if attempt < attempts - 1:
                time.sleep(wait_s)
    fallback = target.with_name(f"{target.stem}-{time.strftime('%Y%m%d-%H%M%S')}{target.suffix}")
    os.replace(staging, fallback)
    logger.warning("remotion_output_locked target=%s saved_as=%s", target, fallback.name)
    return fallback


async def render_via_remotion(
    db: aiosqlite.Connection,
    project: dict,
    audio_job: dict,
    learning: dict | None,
    output_path: Path,
    caption_style: str = "outline",
    visual_mode: str = "illustrated",
    still_scene_id: str | None = None,
    layout: str = "horizontal",
    clip: dict | None = None,
) -> dict[str, Any]:
    """Phase 37: `layout="vertical"` renders 1080x1920 (D100); `clip` ({line_from, line_to, hook}) renders only that passage
    of the vertical episode, opening on its hook banner (D99).

    D19.7-c: builds real props (async -- resolves avatars via the DB), then hands off to
    `_render_via_remotion_sync` in a thread for the actual blocking subprocess call. Raises
    `RemotionRenderFailedError` on timeout, non-zero exit, or a missing output file -- the
    caller (`video_service.generate_video`) fails the job with that reason (Task 35.5: there is no other renderer).
    """
    project_id = project["id"]
    input_props = await _build_input_props(db, project, audio_job, learning, caption_style,
                                           visual_mode=visual_mode, still_scene_id=still_scene_id)
    # Private backend metadata is not part of the Remotion schema. Preserve it for
    # the caller, but never write it into the props JSON consumed by the renderer.
    activity_uses = input_props.get("sprites", {}).pop("_activityUses", [])
    await asyncio.to_thread(_copy_audio_into_public, project_id, audio_job["mp3_path"])
    voices = await _add_brand(project_id, input_props)
    soundtrack = await _build_soundtrack(project_id, audio_job, input_props, voices)
    if soundtrack is not None:
        input_props["soundtrackPath"] = soundtrack
        if "brand" in input_props:
            input_props["brand"]["voicesInSoundtrack"] = bool(voices)
    frames = None
    if layout == "vertical":
        input_props.update(layout="vertical", width=VERTICAL_WIDTH, height=VERTICAL_HEIGHT)
    if clip is not None:
        frames = clip_frames(input_props, clip["line_from"], clip["line_to"])
        input_props.update(hook=clip.get("hook") or "", hookAtSec=input_props["lines"][clip["line_from"]]["startSec"])
    result = await asyncio.to_thread(_render_via_remotion_sync, input_props, output_path, frames)
    return {**result, "soundtrack": soundtrack is not None, "brand_voice": bool(voices),
            "activity_uses": activity_uses, "intro_seconds": float(input_props.get("introSec") or 0.0)}


def _copy_brand_voice(source: str) -> str:
    REMOTION_BRAND_DIR.mkdir(parents=True, exist_ok=True)
    destination = REMOTION_BRAND_DIR / Path(source).name
    shutil.copyfile(source, destination)
    return f"remotion-render/brand/{destination.name}"


VERTICAL_WIDTH, VERTICAL_HEIGHT = 1080, 1920
CLIP_LEAD_S, CLIP_TAIL_S = 0.6, 0.8


def clip_frames(input_props: dict[str, Any], line_from: int, line_to: int) -> tuple[int, int]:
    """Phase 37 (D99): the composition frames of a passage -- from just before its first line to just after its last."""
    lines, fps = input_props["lines"], input_props["fps"]
    if not 0 <= line_from <= line_to < len(lines):
        raise ValidationError("The clip's lines are outside the script")
    start = input_props["introSec"] + lines[line_from]["startSec"] - CLIP_LEAD_S
    end = input_props["introSec"] + lines[line_to]["endSec"] + CLIP_TAIL_S
    last = math.ceil(composition_seconds(input_props) * fps) - 1
    return max(0, round(start * fps)), min(last, round(end * fps))


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
