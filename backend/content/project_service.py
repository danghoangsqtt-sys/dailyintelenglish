"""Project CRUD and state-machine logic."""

import asyncio
import json
import logging
import shutil
import uuid
from datetime import datetime, timezone

import aiosqlite

from backend.core.config import settings
from backend.core.constants import CEFR_DEFAULT_TTS_SPEED, PROJECT_STATUSES
from backend.core.exceptions import ConflictError, NotFoundError, ValidationError
from backend.core.voice import resolve_voice_id, voice_revision
from backend.schemas.project import ProjectUpdate, ScriptConfig, SpeakerConfig, SpeakerUpdate

logger = logging.getLogger(__name__)

# Every per-project data directory that a real project deletion must also clean up
# (project_service knows none of these services' internals -- this list must stay in
# sync with the "<category>/<project_id>" convention used by tts_service, audio_service, video_service and
# thumbnail_service; "avatars" stays because projects made before Task 35.4 may still hold one).
_PROJECT_ARTIFACT_CATEGORIES = ("avatars", "audio", "video", "thumbnails", "tts_cache", "visuals")
_DOWNSTREAM_STATUSES = frozenset({"audio_generated", "video_generated", "complete"})

_LIST_COLUMNS = "id, name, status, cefr_level, genre, accent, created_at, updated_at"
_DETAIL_COLUMNS = (
    "id, name, status, topic, cefr_level, duration_minutes, num_speakers, "
    "genre, accent, language_features, config_json, created_at, updated_at"
)


def _now() -> str:
    """Current UTC timestamp in ISO8601, used for created_at/updated_at."""
    return datetime.now(timezone.utc).isoformat()


def _row_to_project(row: aiosqlite.Row) -> dict:
    """Convert a projects row to a dict, decoding the language_features JSON blob."""
    project = dict(row)
    if project.get("language_features"):
        project["language_features"] = json.loads(project["language_features"])
    return project


def _validate_status_transition(current_status: str, new_status: str) -> None:
    """Enforce the forward-only state machine: draft -> script_generated -> audio_generated ->
    video_generated -> complete. No skipping steps and no going backward.
    """
    if new_status == current_status:
        return
    if current_status not in PROJECT_STATUSES or new_status not in PROJECT_STATUSES:
        raise ValidationError(f"unknown status: {current_status!r} or {new_status!r}")
    current_index = PROJECT_STATUSES.index(current_status)
    new_index = PROJECT_STATUSES.index(new_status)
    if new_index != current_index + 1:
        raise ValidationError(
            f"invalid status transition: {current_status} -> {new_status} "
            f"(must advance one step at a time through {' -> '.join(PROJECT_STATUSES)})"
        )


def _resolve_speaker_speeds(speakers: list[SpeakerConfig], cefr_level: str) -> list[SpeakerConfig]:
    """A speaker with no explicit `speed` (Task 14.10) gets the CEFR level's default.

    Called once, before a speaker list is used for both the `config_json` snapshot
    and `_replace_speakers`, so the two never disagree. A speaker that already has a
    stored `speed` (round-tripped from an existing project) is returned unchanged --
    this only ever fills in a `None`, never overwrites a real value.
    """
    default_speed = CEFR_DEFAULT_TTS_SPEED[cefr_level]
    return [
        speaker if speaker.speed is not None else speaker.model_copy(update={"speed": default_speed})
        for speaker in speakers
    ]


async def _replace_speakers(
    db: aiosqlite.Connection, project_id: str, speakers: list[SpeakerConfig]
) -> None:
    """Delete and re-insert a project's speakers, preserving submitted order as speaker_index."""
    await db.execute("DELETE FROM speakers WHERE project_id = ?", (project_id,))
    for index, speaker in enumerate(speakers):
        await db.execute(
            "INSERT INTO speakers (id, project_id, speaker_index, name, gender, accent, "
            "tts_engine, voice_id, voice_description, speed, pitch, volume) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                project_id,
                index,
                speaker.name,
                speaker.gender,
                speaker.accent,
                speaker.tts_engine,
                speaker.voice_id,
                speaker.voice_description,
                speaker.speed,
                speaker.pitch,
                speaker.volume,
            ),
        )


def _build_config_snapshot(scalars: dict, language_features: dict, speakers: list[dict]) -> str:
    """Build the config_json blob — a ScriptConfig-shaped snapshot kept in sync on every write."""
    snapshot = {
        **scalars,
        "language_features": language_features,
        "speakers": [
            {
                "name": speaker["name"],
                "gender": speaker["gender"],
                "accent": speaker["accent"],
                "tts_engine": speaker["tts_engine"],
                "voice_id": speaker.get("voice_id"),
                "voice_description": speaker.get("voice_description") or "",
                "speed": speaker["speed"],
                "pitch": speaker["pitch"],
                "volume": speaker["volume"],
            }
            for speaker in speakers
        ],
    }
    return json.dumps(snapshot)


async def _sync_speaker_config(db: aiosqlite.Connection, project_id: str) -> None:
    """Keep the reusable config snapshot in sync with pinned speaker settings."""
    project = await get_project(db, project_id)
    keys = ("name", "topic", "cefr_level", "duration_minutes", "num_speakers", "genre", "accent")
    snapshot = _build_config_snapshot(
        {key: project[key] for key in keys}, project["language_features"], project["speakers"],
    )
    await db.execute("UPDATE projects SET config_json = ?, updated_at = ? WHERE id = ?",
                     (snapshot, _now(), project_id))


async def list_projects(db: aiosqlite.Connection) -> list[dict]:
    """List all projects ordered by most recently updated.

    Args:
        db: Open aiosqlite connection.

    Returns:
        List of project rows as dicts (empty list if none exist yet).
    """
    cursor = await db.execute(
        f"SELECT {_LIST_COLUMNS}, topic, "
        # Phase 26 (Task 26.3): a real picture for the dashboard card -- the selected thumbnail, else none (the
        # first-shot fallback went with the two-person shots, Phase 44 / D123).
        "(SELECT t.id || '|' || t.image_path_16x9 FROM thumbnails t WHERE t.project_id = projects.id "
        " AND t.is_selected = 1 AND t.image_path_16x9 IS NOT NULL LIMIT 1) AS selected_thumb "
        "FROM projects ORDER BY updated_at DESC"
    )
    rows = await cursor.fetchall()
    return [_with_preview(dict(row)) for row in rows]


def _with_preview(project: dict) -> dict:
    thumb = project.pop("selected_thumb")
    project["preview_url"] = None
    if thumb:
        thumbnail_id, path = thumb.split("|", 1)
        image_format = "jpg" if path.lower().endswith((".jpg", ".jpeg")) else "png"
        project["preview_url"] = f"/api/projects/{project['id']}/thumbnails/{thumbnail_id}/16x9.{image_format}"
    return project


async def create_project(
    db: aiosqlite.Connection, config: ScriptConfig, commit: bool = True
) -> dict:
    """Create a new project and its speakers from a script config.

    Args:
        db: Open aiosqlite connection.
        config: Validated Step 1 wizard configuration.
        commit: If False, skip the commit — the caller is responsible for
            committing (or rolling back) as part of a larger transaction.

    Returns:
        The newly created project, including its speakers.
    """
    project_id = str(uuid.uuid4())
    now = _now()
    scalars = {
        "name": config.name,
        "topic": config.topic,
        "cefr_level": config.cefr_level,
        "duration_minutes": config.duration_minutes,
        "num_speakers": config.num_speakers,
        "genre": config.genre,
        "accent": config.accent,
    }
    language_features = config.language_features.model_dump()
    resolved_speakers = _resolve_speaker_speeds(config.speakers, config.cefr_level)
    config_json = _build_config_snapshot(
        scalars, language_features, [speaker.model_dump() for speaker in resolved_speakers]
    )
    await db.execute(
        "INSERT INTO projects (id, name, status, topic, cefr_level, duration_minutes, "
        "num_speakers, genre, accent, language_features, config_json, created_at, updated_at) "
        "VALUES (?, ?, 'draft', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            project_id,
            scalars["name"],
            scalars["topic"],
            scalars["cefr_level"],
            scalars["duration_minutes"],
            scalars["num_speakers"],
            scalars["genre"],
            scalars["accent"],
            json.dumps(language_features),
            config_json,
            now,
            now,
        ),
    )
    await _replace_speakers(db, project_id, resolved_speakers)
    if commit:
        await db.commit()
    return await get_project(db, project_id)


async def get_project(db: aiosqlite.Connection, project_id: str) -> dict:
    """Fetch a single project with its speakers.

    Args:
        db: Open aiosqlite connection.
        project_id: UUID of the project.

    Returns:
        Project dict with a nested `speakers` list.

    Raises:
        NotFoundError: If no project with this id exists.
    """
    cursor = await db.execute(
        f"SELECT {_DETAIL_COLUMNS} FROM projects WHERE id = ?", (project_id,)
    )
    row = await cursor.fetchone()
    if row is None:
        raise NotFoundError(f"Project {project_id} not found")
    project = _row_to_project(row)

    speaker_cursor = await db.execute(
        "SELECT id, speaker_index, name, gender, accent, tts_engine, voice_id, "
        "voice_description, speed, pitch, volume FROM speakers "
        "WHERE project_id = ? ORDER BY speaker_index",
        (project_id,),
    )
    speaker_rows = await speaker_cursor.fetchall()
    # Phase 35 (Task 35.4, D89): no uploaded speaker avatar any more -- a speaker's picture is its cast character's.
    project["speakers"] = [dict(speaker_row) for speaker_row in speaker_rows]
    cast_cursor = await db.execute(
        "SELECT pc.speaker_index, pc.character_id, c.default_voice_id AS profile_voice_id "
        "FROM project_cast pc JOIN characters c ON c.id = pc.character_id WHERE pc.project_id = ?", (project_id,),
    )
    cast = {row["speaker_index"]: dict(row) for row in await cast_cursor.fetchall()}
    for speaker in project["speakers"]:
        speaker["voice_revision"] = voice_revision(speaker)
        speaker["resolved_voice_id"] = speaker.get("voice_id") or resolve_voice_id(speaker)
        member = cast.get(speaker["speaker_index"], {})
        speaker["character_id"] = member.get("character_id")
        speaker["profile_voice_id"] = member.get("profile_voice_id")
    return project


async def update_speaker(
    db: aiosqlite.Connection, project_id: str, speaker_id: str, patch: SpeakerUpdate, commit: bool = True
) -> dict:
    """Update one speaker's TTS voice settings in place (Step 4 Audio Studio).

    Unlike `update_project`'s `speakers` replace-all path (new ids every call — see
    `_replace_speakers`), this updates the existing row by id and never touches any other
    speaker or any script_lines row. Safe to call after a script/audio already exists.

    Raises:
        NotFoundError: If the project or the speaker (within that project) doesn't exist.
    """
    project = await get_project(db, project_id)
    if not any(speaker["id"] == speaker_id for speaker in project["speakers"]):
        raise NotFoundError(f"Speaker {speaker_id} not found on project {project_id}")

    speaker = next(s for s in project["speakers"] if s["id"] == speaker_id)
    if patch.expected_voice_revision and patch.expected_voice_revision != speaker["voice_revision"]:
        raise ConflictError("Speaker voice settings changed. Reload before saving.")
    fields = patch.model_dump(exclude_unset=True, exclude_none=True,
                              exclude={"expected_voice_revision", "apply_profile_voice"})
    if fields:
        set_clause = ", ".join(f"{key} = ?" for key in fields)
        await db.execute(
            f"UPDATE speakers SET {set_clause} WHERE id = ? AND project_id = ?",
            (*fields.values(), speaker_id, project_id),
        )
        await _sync_speaker_config(db, project_id)
        if commit:
            await db.commit()
    return await get_project(db, project_id)


async def rename_speaker(
    db: aiosqlite.Connection, project_id: str, speaker_id: str, new_name: str, commit: bool = True
) -> dict:
    """Phase 40 (D119): a speaker takes its character's name everywhere. The speaker row is renamed and the old name is
    replaced, as a whole word and case-sensitively, in this project's script lines (so "Lina, how would you" becomes
    "Mia, how would you"); when anything changed the project is marked "script changed" (the audio speaks the old name
    and must be redone). Returns {"old_name", "new_name", "lines_changed", "changed"}.
    """
    import re

    new_name = new_name.strip()
    cursor = await db.execute("SELECT name FROM speakers WHERE id = ? AND project_id = ?", (speaker_id, project_id))
    row = await cursor.fetchone()
    if row is None:
        raise NotFoundError(f"Speaker {speaker_id} not found on project {project_id}")
    old_name = (row[0] or "").strip()
    result = {"old_name": old_name, "new_name": new_name, "lines_changed": 0, "changed": False}
    if not new_name or new_name == old_name:
        return result
    await db.execute("UPDATE speakers SET name = ? WHERE id = ? AND project_id = ?", (new_name, speaker_id, project_id))
    cursor = await db.execute("SELECT id, text FROM script_lines WHERE project_id = ?", (project_id,))
    lines = await cursor.fetchall()
    if old_name:
        pattern = re.compile(rf"(?<![\w-]){re.escape(old_name)}(?![\w-])")
        for line_id, text in lines:
            replaced = pattern.sub(new_name, text or "")
            if replaced != text:
                await db.execute(
                    "UPDATE script_lines SET text = ?, audio_cache_path = NULL, duration_seconds = NULL WHERE id = ?",
                    (replaced, line_id),
                )
                result["lines_changed"] += 1
    if lines:  # a script exists: its labels (and maybe its words) changed, so audio and video are stale
        await mark_script_changed(db, project_id, commit=False)
        await mark_media_stale(db, project_id)
    result["changed"] = True
    if commit:
        await db.commit()
    return result


async def has_script(db: aiosqlite.Connection, project_id: str) -> bool:
    cursor = await db.execute("SELECT 1 FROM script_lines WHERE project_id = ? LIMIT 1", (project_id,))
    return await cursor.fetchone() is not None


async def apply_character_voice(db: aiosqlite.Connection, project_id: str, speaker: dict, character: dict) -> bool:
    """Phase 40 follow-up (D119): a speaker also takes its character's voice -- gender, accent, engine, voice id -- so
    swapping Alex for Hoang gives Hoang's Canadian voice, not Alex's. Speed, pitch and volume stay the project's own (set
    for the level, as Step 1 keeps them). Profile fields left empty keep the speaker's value. Returns True when anything
    changed. Does not commit."""
    wanted = {
        "gender": character.get("gender") or speaker.get("gender"),
        "accent": character.get("default_accent") or speaker.get("accent"),
        "tts_engine": character.get("default_tts_engine") or speaker.get("tts_engine"),
        "voice_id": character.get("default_voice_id") or speaker.get("voice_id"),
    }
    changes = {key: value for key, value in wanted.items() if value != speaker.get(key)}
    if not changes:
        return False
    sets = ", ".join(f"{key} = ?" for key in changes)
    await db.execute(f"UPDATE speakers SET {sets} WHERE id = ? AND project_id = ?",
                     (*changes.values(), speaker["id"], project_id))
    await _sync_speaker_config(db, project_id)
    return True


async def update_project(
    db: aiosqlite.Connection, project_id: str, patch: ProjectUpdate, commit: bool = True
) -> dict:
    """Apply a partial update to a project and bump updated_at (used for auto-save).

    `config_json` is recomputed from the merged (current + patched) state on every
    call, so it never drifts from the individual columns. If `status` is included,
    the transition is checked against the forward-only state machine. If either of
    `num_speakers` / `speakers` is present, both must be (enforced by ProjectUpdate)
    and the speakers table is replaced atomically alongside the column update.

    Args:
        db: Open aiosqlite connection.
        project_id: UUID of the project.
        patch: Fields to change; omitted fields are left untouched.
        commit: If False, skip the commit — the caller is responsible for
            committing (or rolling back) as part of a larger transaction.

    Returns:
        The updated project.

    Raises:
        NotFoundError: If no project with this id exists.
        ValidationError: If `status` is not a legal transition from the current status.
    """
    current = await get_project(db, project_id)

    if patch.status is not None:
        _validate_status_transition(current["status"], patch.status)

    patch_fields = patch.model_dump(exclude_unset=True, exclude={"speakers"})

    merged_scalars = {
        key: patch_fields.get(key, current[key])
        for key in ("name", "topic", "cefr_level", "duration_minutes", "num_speakers", "genre", "accent")
    }
    merged_language_features = patch_fields.get("language_features", current["language_features"])
    resolved_patch_speakers = (
        _resolve_speaker_speeds(patch.speakers, merged_scalars["cefr_level"])
        if patch.speakers is not None
        else None
    )
    merged_speakers = (
        [speaker.model_dump() for speaker in resolved_patch_speakers]
        if resolved_patch_speakers is not None
        else current["speakers"]
    )

    set_fields = {key: value for key, value in patch_fields.items() if key != "language_features"}
    if "language_features" in patch_fields:
        set_fields["language_features"] = json.dumps(patch_fields["language_features"])
    set_fields["config_json"] = _build_config_snapshot(
        merged_scalars, merged_language_features, merged_speakers
    )

    set_clause = ", ".join(f"{key} = ?" for key in set_fields)
    values = [*set_fields.values(), _now(), project_id]
    await db.execute(f"UPDATE projects SET {set_clause}, updated_at = ? WHERE id = ?", values)

    if resolved_patch_speakers is not None:
        await _replace_speakers(db, project_id, resolved_patch_speakers)

    if commit:
        await db.commit()
    return await get_project(db, project_id)


async def _downgrade_downstream_to_script_generated(
    db: aiosqlite.Connection, project_id: str, current_status: str
) -> bool:
    """Downgrade stale downstream artifacts without handling early workflow states."""
    if current_status not in _DOWNSTREAM_STATUSES:
        return False
    await db.execute(
        "UPDATE projects SET status = 'script_generated', updated_at = ? WHERE id = ?",
        (_now(), project_id),
    )
    return True


async def mark_script_changed(
    db: aiosqlite.Connection, project_id: str, commit: bool = True
) -> None:
    """Set the lifecycle status that truthfully follows a script change.

    This is a narrow internal transition path for script persistence only. It accepts
    no caller-selected target status: a draft advances to ``script_generated``, that
    status is idempotent, and any later pipeline status is downgraded to
    ``script_generated`` because its downstream artifacts may now be stale. Public
    project updates continue to use :func:`update_project` and its forward-only
    validator.

    Args:
        db: Open aiosqlite connection.
        project_id: UUID of the project whose script changed.
        commit: If False, the caller owns the surrounding transaction.

    Raises:
        NotFoundError: If no project with this id exists.
        ValidationError: If the stored status is unknown.
    """
    cursor = await db.execute("SELECT status FROM projects WHERE id = ?", (project_id,))
    row = await cursor.fetchone()
    if row is None:
        raise NotFoundError(f"Project {project_id} not found")

    current_status = row["status"]
    if current_status not in PROJECT_STATUSES:
        raise ValidationError(f"unknown status: {current_status!r}")
    if current_status == "script_generated":
        return
    if current_status == "draft":
        # Preserve the existing validated forward-transition path. The direct update
        # below is reserved for the three intentional internal downgrades only.
        await update_project(
            db, project_id, ProjectUpdate(status="script_generated"), commit=commit
        )
        return

    await _downgrade_downstream_to_script_generated(db, project_id, current_status)
    if commit:
        await db.commit()


async def mark_media_stale(db: aiosqlite.Connection, project_id: str) -> None:
    """Keep last-good files/metadata, while requiring regeneration for their changed source."""
    message = "Voice or script changed. Generate audio and video again; previous files have been kept."
    for table in ("audio_jobs", "video_jobs"):
        await db.execute(
            f"UPDATE {table} SET status = 'error', error_message = ? WHERE project_id = ?",
            (message, project_id),
        )
    await db.execute("UPDATE short_clips SET status = 'proposed' WHERE project_id = ?", (project_id,))


async def mark_speaker_voice_changed(
    db: aiosqlite.Connection, project_id: str, commit: bool = True, *, speaker_id: str | None = None,
) -> None:
    """Invalidate only the changed speaker's synthesis; preserve every last-good media file."""
    cursor = await db.execute("SELECT status FROM projects WHERE id = ?", (project_id,))
    row = await cursor.fetchone()
    if row is None:
        raise NotFoundError(f"Project {project_id} not found")
    current_status = row["status"]
    if current_status not in PROJECT_STATUSES:
        raise ValidationError(f"unknown status: {current_status!r}")
    where = "project_id = ?" + (" AND speaker_id = ?" if speaker_id else "")
    params = (project_id, speaker_id) if speaker_id else (project_id,)
    await db.execute(f"UPDATE script_lines SET audio_cache_path = NULL, duration_seconds = NULL WHERE {where}", params)
    await mark_media_stale(db, project_id)
    await _downgrade_downstream_to_script_generated(db, project_id, current_status)
    if commit:
        await db.commit()


async def delete_project(db: aiosqlite.Connection, project_id: str, commit: bool = True) -> None:
    """Delete a project and its cascade-linked rows (speakers, script lines, jobs).

    Args:
        db: Open aiosqlite connection.
        project_id: UUID of the project.
        commit: If False, skip the commit — the caller is responsible for
            committing (or rolling back) as part of a larger transaction.

    Raises:
        NotFoundError: If no project with this id exists.
    """
    await get_project(db, project_id)
    await db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    if commit:
        await db.commit()


def _remove_project_directory_sync(category: str, project_id: str) -> None:
    """Best-effort removal of one per-project data directory; never raises for a
    directory that was never created (nothing was ever generated in that category)."""
    directory = settings.DATA_DIR / category / project_id
    try:
        shutil.rmtree(directory)
    except FileNotFoundError:
        pass
    except OSError:
        logger.warning(
            "project_artifact_cleanup_failed category=%s project_id=%s",
            category,
            project_id,
            exc_info=True,
        )


async def cleanup_project_artifacts(project_id: str) -> None:
    """Remove a deleted project's on-disk files (avatars, audio, video, thumbnails, TTS
    cache) — the DB row's ON DELETE CASCADE only ever removed related table rows, never
    these directories, so every deleted project previously leaked its files permanently.

    Best-effort by design: call only *after* the project's DB row is durably committed as
    deleted, never inside the same transaction — a filesystem failure here must not roll
    back (or block) the fact that the project record itself is already gone.
    """
    for category in _PROJECT_ARTIFACT_CATEGORIES:
        await asyncio.to_thread(_remove_project_directory_sync, category, project_id)


async def media_input_revision(
    db: aiosqlite.Connection, project_id: str, *, include_audio: bool = False, include_cache: bool = True,
) -> str:
    """Snapshot relevant media inputs while the caller holds a short read/write transaction."""
    from backend.core.voice import media_revision

    project = await get_project(db, project_id)
    cursor = await db.execute(
        "SELECT id, speaker_id, text, audio_cache_path FROM script_lines WHERE project_id = ? ORDER BY line_index",
        (project_id,),
    )
    lines = [dict(row) for row in await cursor.fetchall()]
    audio = None
    if include_audio:
        cursor = await db.execute(
            "SELECT id, status, mp3_path, wav_path, completed_at FROM audio_jobs WHERE project_id = ?", (project_id,),
        )
        row = await cursor.fetchone()
        audio = dict(row) if row else None
    return media_revision(project, lines, audio, include_cache=include_cache)


async def media_revision_is_current(
    db: aiosqlite.Connection, project_id: str, expected: str, *, include_audio: bool = False, include_cache: bool = True,
) -> bool:
    """A deleted project or edited source invalidates old work without changing newer job state."""
    try:
        return await media_input_revision(
            db, project_id, include_audio=include_audio, include_cache=include_cache,
        ) == expected
    except NotFoundError:
        return False
