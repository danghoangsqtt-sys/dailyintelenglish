"""Audio mixing routes (Task 1.6, Sub-task 1.6b).

`GET /status` is a plain polling GET, not real Server-Sent Events despite
ARCHITECTURE.md's "(SSE)" label on that route — a deliberate, documented deviation (see
task-1.6.md Implementation Notes): mixing a short podcast takes a few seconds of local CPU
work, and every other `*/generate` route in this codebase (script/learning/thumbnail/
youtube) is a synchronous await-then-return call with no SSE anywhere in the actual
implementation.
"""

import asyncio
import time
import uuid

import aiosqlite
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from backend.db.transactions import read_transaction, write_transaction
from backend.core.exceptions import ConflictError, NotFoundError, ValidationError
from backend.core.voice import line_fingerprint
from backend.core.responses import ok
from backend.db.database import get_db
from backend.schemas.audio import GenerateAudioRequest
from backend.schemas.project import ProjectUpdate
from backend.media import audio_service
from backend.content import project_service
from backend.ai.tts import tts_service
from backend.content import export_service

router = APIRouter(prefix="/api/projects/{project_id}/audio", tags=["audio"])

_DOWNLOAD_FORMATS = {"mp3": "audio/mpeg", "wav": "audio/wav"}


@router.post("/generate")
async def generate_audio(
    project_id: str, payload: GenerateAudioRequest, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Mix all of a project's synthesized lines into one podcast track."""
    started_at = time.perf_counter()
    async with read_transaction():
        project = await project_service.get_project(db, project_id)
        lines = await audio_service.get_lines_for_mixing(db, project_id)
        original = await project_service.media_input_revision(db, project_id, include_audio=True, include_cache=False)
    if not lines:
        raise ValidationError("Cannot generate audio: script is empty")
    project = {**project, "_attempt_id": uuid.uuid4().hex}

    try:
        await _resynthesize_lines_without_word_timings(db, project, lines)
        async with read_transaction():
            if not await project_service.media_revision_is_current(
                db, project_id, original, include_audio=True, include_cache=False,
            ):
                raise ConflictError("Voice, script or audio changed. Generate the audio again.")
            current_lines = await audio_service.get_lines_for_mixing(db, project_id)
            if [(item["id"], item.get("audio_cache_path")) for item in current_lines] != [
                (item["id"], item.get("audio_cache_path")) for item in lines
            ]:
                raise ConflictError("Speech cache changed during preparation. Generate the audio again.")
            expected = await project_service.media_input_revision(db, project_id, include_audio=True)
        result = await audio_service.mix_project(project, lines, payload.background_music)
    except Exception as exc:
        async with write_transaction(db):
            if await project_service.media_revision_is_current(
                db, project_id, original, include_audio=True, include_cache=False,
            ):
                await audio_service.mark_audio_job_failed(db, project_id, str(exc), commit=False)
        raise

    async with write_transaction(db):
        if not await project_service.media_revision_is_current(db, project_id, expected, include_audio=True):
            raise ConflictError("Voice, script or audio changed during mixing. The previous audio has been kept.")
        job = await audio_service.save_audio_job(
            db,
            project_id,
            status="complete",
            mp3_path=result["mp3_path"],
            wav_path=result["wav_path"],
            timestamps=result["timestamps"],
            word_timestamps=result["word_timestamps"],
            background_music=payload.background_music,
            duration_seconds=result["duration_seconds"],
            loudness_lufs=result["loudness_lufs"],
            commit=False,
        )
        if project["status"] == "script_generated":
            await project_service.update_project(
                db, project_id, ProjectUpdate(status="audio_generated"), commit=False
            )
    job = {**job, "lines_without_words": sum(1 for entry in result["word_timestamps"] if not entry["words"])}
    await export_service.sync_quietly(db, project_id)
    return ok(job, started_at=started_at)


async def _resynthesize_lines_without_word_timings(db: aiosqlite.Connection, project: dict, lines: list[dict]) -> None:
    """Task 32.8c (BUG-030, D77): a cached line without its word-timing sidecar counts as a cache miss.

    Lines cached before Task 19.2 (no `.words.json`) are re-synthesized with word boundaries before the mix, so the
    finished episode keeps karaoke captions. The Edge TTS call runs outside the write lock (see `backend/api/tts.py`).
    Mismatched voice fingerprints count as misses too. Lines without audio still require Generate All first.
    """
    for line in lines:
        if not line.get("audio_cache_path"):
            continue
        if await asyncio.to_thread(tts_service.cache_matches, project, line):
            continue
        expected = line_fingerprint(project, line)
        synthesized = await tts_service.synthesize_line_audio(project, line)
        async with write_transaction(db):
            await tts_service.save_line_audio_cache(
                db, project["id"], line["id"], synthesized["audio_path"], commit=False, expected_fingerprint=expected,
            )
        line["audio_cache_path"] = synthesized["audio_path"]


@router.get("/status")
async def get_audio_status(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Return the current audio job for a project (404 if audio was never generated)."""
    started_at = time.perf_counter()
    async with read_transaction():
        await project_service.get_project(db, project_id)
        job = await audio_service.get_audio_job(db, project_id)
    if job is None:
        raise NotFoundError(f"No audio job for project {project_id}")
    return ok(job, started_at=started_at)


@router.get("/download")
async def download_audio(
    project_id: str, format: str = "mp3", db: aiosqlite.Connection = Depends(get_db)
) -> FileResponse:
    """Download the mixed audio as MP3 (default) or WAV."""
    media_type = _DOWNLOAD_FORMATS.get(format)
    if media_type is None:
        raise ValidationError(f"Unsupported format {format!r}: expected 'mp3' or 'wav'")
    async with read_transaction():
        await project_service.get_project(db, project_id)
        job = await audio_service.get_audio_job(db, project_id)
    if job is None or job["status"] not in ("complete", "error"):
        raise NotFoundError(f"No completed audio mix for project {project_id}")
    path = job["mp3_path"] if format == "mp3" else job["wav_path"]
    if path is None:
        raise NotFoundError(f"No completed {format!r} audio mix for project {project_id}")
    return FileResponse(path, media_type=media_type, filename=f"{project_id}.{format}")
