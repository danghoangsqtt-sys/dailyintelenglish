"""Project CRUD and state-machine logic."""

import json
import uuid
from datetime import datetime, timezone

import aiosqlite

from app.core.constants import PROJECT_STATUSES
from app.core.exceptions import NotFoundError, ValidationError
from app.models.project import ProjectUpdate, ScriptConfig, SpeakerConfig, SpeakerUpdate

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


async def _replace_speakers(
    db: aiosqlite.Connection, project_id: str, speakers: list[SpeakerConfig]
) -> None:
    """Delete and re-insert a project's speakers, preserving submitted order as speaker_index."""
    await db.execute("DELETE FROM speakers WHERE project_id = ?", (project_id,))
    for index, speaker in enumerate(speakers):
        await db.execute(
            "INSERT INTO speakers (id, project_id, speaker_index, name, gender, accent, "
            "tts_engine, voice_description, speed, pitch, volume) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                project_id,
                index,
                speaker.name,
                speaker.gender,
                speaker.accent,
                speaker.tts_engine,
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
                "voice_description": speaker.get("voice_description") or "",
                "speed": speaker["speed"],
                "pitch": speaker["pitch"],
                "volume": speaker["volume"],
            }
            for speaker in speakers
        ],
    }
    return json.dumps(snapshot)


async def list_projects(db: aiosqlite.Connection) -> list[dict]:
    """List all projects ordered by most recently updated.

    Args:
        db: Open aiosqlite connection.

    Returns:
        List of project rows as dicts (empty list if none exist yet).
    """
    cursor = await db.execute(f"SELECT {_LIST_COLUMNS} FROM projects ORDER BY updated_at DESC")
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


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
    config_json = _build_config_snapshot(
        scalars, language_features, [speaker.model_dump() for speaker in config.speakers]
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
    await _replace_speakers(db, project_id, config.speakers)
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
        "voice_description, speed, pitch, volume, avatar_image_path FROM speakers "
        "WHERE project_id = ? ORDER BY speaker_index",
        (project_id,),
    )
    speaker_rows = await speaker_cursor.fetchall()
    project["speakers"] = [dict(speaker_row) for speaker_row in speaker_rows]
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

    fields = patch.model_dump(exclude_unset=True)
    if fields:
        set_clause = ", ".join(f"{key} = ?" for key in fields)
        await db.execute(
            f"UPDATE speakers SET {set_clause} WHERE id = ? AND project_id = ?",
            (*fields.values(), speaker_id, project_id),
        )
        if commit:
            await db.commit()
    return await get_project(db, project_id)


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
    merged_speakers = (
        [speaker.model_dump() for speaker in patch.speakers]
        if patch.speakers is not None
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

    if patch.speakers is not None:
        await _replace_speakers(db, project_id, patch.speakers)

    if commit:
        await db.commit()
    return await get_project(db, project_id)


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
