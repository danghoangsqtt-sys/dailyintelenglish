"""Music library routes for listing, uploading, previewing, deleting and generating tracks."""

import asyncio
import random
import time
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

import aiofiles
import aiosqlite
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse

from app.core.constants import MAX_MUSIC_UPLOAD_BYTES, MAX_MUSIC_UPLOAD_MB, MUSIC_UPLOAD_CHUNK_BYTES
from app.core.exceptions import MusicUploadTooLargeError, NotFoundError, ValidationError
from app.core.responses import ok
from app.db.database import get_db
from app.db.transactions import read_transaction, write_transaction
from app.models.music import (
    MAX_BRIEF_CHARS, MAX_DURATION_S, MAX_SEED, MIN_DURATION_S, MUSIC_STYLES, MusicGenerateInput,
)
from app.services.music import tracks
from app.services.music.engine import require_generation, unavailable_reason
from app.services.music.pipelines import JOB_KIND, JOB_KINDS
from app.services.visuals import jobs

router = APIRouter(prefix="/api/music", tags=["music"])

AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a"}
UPLOAD_EXTENSIONS = {".mp3", ".wav"}
AUDIO_MEDIA_TYPES = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".m4a": "audio/mp4",
}
MP3_FRAME_SYNC_BYTES = {0xFB, 0xF3, 0xFA, 0xF2}


def _music_dir() -> Path:
    """Return the configured music-library directory."""
    return tracks.music_dir()


def _validate_filename(filename: str, allowed_extensions: set[str]) -> str:
    """Validate a client-supplied filename without rewriting it."""
    cleaned = filename.strip()
    if (
        not cleaned
        or cleaned != filename
        or cleaned in {".", ".."}
        or "/" in cleaned
        or "\\" in cleaned
        or Path(cleaned).name != cleaned
    ):
        raise ValidationError("Please choose a file with a safe filename.")
    if Path(cleaned).suffix.lower() not in allowed_extensions:
        raise ValidationError("Only MP3 and WAV music files are supported.")
    return cleaned


def _validate_magic_bytes(filename: str, header: bytes) -> None:
    """Reject obvious extension spoofing using lightweight audio signatures."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".wav":
        valid = len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WAVE"
    else:
        valid = header.startswith(b"ID3") or (
            len(header) >= 2 and header[0] == 0xFF and header[1] in MP3_FRAME_SYNC_BYTES
        )
    if not valid:
        raise ValidationError(f"The uploaded file does not contain valid {suffix[1:].upper()} header bytes.")


_place_without_overwrite = tracks.place_without_overwrite


def _track_payload(path: Path) -> dict:
    """Build the public metadata payload for one music track."""
    return {
        "filename": path.name,
        "size_bytes": path.stat().st_size,
        "content_url": f"/api/music/{quote(path.name, safe='')}",
    }


def _unlink_if_exists(path: Path) -> None:
    """Remove a temporary upload if it still exists."""
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _list_music_files() -> list[dict]:
    music_dir = _music_dir()
    music_dir.mkdir(parents=True, exist_ok=True)
    tracks = []
    for path in sorted(music_dir.iterdir(), key=lambda item: item.name.lower()):
        if not path.is_file() or path.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        try:
            tracks.append(_track_payload(path))
        except FileNotFoundError:
            # A concurrent delete between directory iteration and stat simply removes the row.
            continue
    return tracks


def _existing_music_path(filename: str) -> Path:
    """Resolve a safe existing music path or raise a typed 404."""
    safe_name = _validate_filename(filename, AUDIO_EXTENSIONS)
    path = _music_dir() / safe_name
    if not path.is_file():
        raise NotFoundError("Music track not found.")
    return path


@router.get("")
async def list_music(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """List background music tracks with their source (upload | ai) and AI provenance."""
    started_at = time.perf_counter()
    files = await asyncio.to_thread(_list_music_files)
    async with read_transaction():
        rows = await tracks.rows_by_filename(db)
    return ok([tracks.with_provenance(track, rows.get(track["filename"])) for track in files], started_at=started_at)


@router.get("/options")
async def music_options() -> dict:
    """Task 22.2: style families and limits for the "Generate from a brief" form."""
    reason = unavailable_reason()
    return ok({
        "styles": [{"id": key, "label": value["label"]} for key, value in MUSIC_STYLES.items()],
        "min_duration_s": MIN_DURATION_S, "max_duration_s": MAX_DURATION_S,
        "max_brief_chars": MAX_BRIEF_CHARS, "available": reason is None, "unavailable_reason": reason,
    })


@router.post("/generate")
async def generate_music(body: MusicGenerateInput, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Task 22.2: queue one AI track; the seed is fixed now so the provenance can reproduce it."""
    require_generation()
    payload = {**body.model_dump(), "seed": body.seed or random.randint(1, MAX_SEED)}
    async with write_transaction(db):
        job = await jobs.create_job(db, JOB_KIND, str(uuid4()), payload)
    from app.main import image_job_runner  # lifespan singleton; avoid router import cycle

    image_job_runner.wake()
    return ok(job)


async def _music_job(db: aiosqlite.Connection, job_id: str) -> dict:
    job = await jobs.get_job(db, job_id)
    if job["kind"] not in JOB_KINDS:
        raise NotFoundError("Music job not found")
    return job


@router.get("/jobs/{job_id}")
async def get_music_job(job_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with read_transaction():
        job = await _music_job(db, job_id)
    return ok(job)


@router.post("/jobs/{job_id}/cancel")
async def cancel_music_job(job_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        await _music_job(db, job_id)
        job = await jobs.request_cancel(db, job_id)
    return ok(job)


@router.post("")
async def upload_music(file: UploadFile = File(...), db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Upload a validated MP3/WAV track without overwriting an existing file."""
    started_at = time.perf_counter()
    safe_name = _validate_filename(file.filename or "", UPLOAD_EXTENSIONS)
    music_dir = _music_dir()
    await asyncio.to_thread(music_dir.mkdir, parents=True, exist_ok=True)
    temporary_path = music_dir / f".{uuid4().hex}.upload"
    total_bytes = 0
    first_chunk = True

    try:
        async with aiofiles.open(temporary_path, "wb") as destination:
            while chunk := await file.read(MUSIC_UPLOAD_CHUNK_BYTES):
                if first_chunk:
                    _validate_magic_bytes(safe_name, chunk)
                    first_chunk = False
                total_bytes += len(chunk)
                if total_bytes > MAX_MUSIC_UPLOAD_BYTES:
                    raise MusicUploadTooLargeError(
                        f"Music files must be {MAX_MUSIC_UPLOAD_MB} MB or smaller."
                    )
                await destination.write(chunk)

        if total_bytes == 0:
            raise ValidationError("The uploaded music file is empty.")
        stored_path = await asyncio.to_thread(_place_without_overwrite, temporary_path, safe_name)
    except Exception:
        await asyncio.to_thread(_unlink_if_exists, temporary_path)
        raise
    finally:
        await file.close()

    async with write_transaction(db):
        await tracks.record_upload(db, stored_path.name)
    track = await asyncio.to_thread(_track_payload, stored_path)
    return ok(tracks.with_provenance(track, {"source": "upload"}), started_at=started_at)


@router.get("/{filename}")
async def get_music(filename: str) -> FileResponse:
    """Stream one library track for native browser audio preview."""
    path = await asyncio.to_thread(_existing_music_path, filename)
    return FileResponse(path, media_type=AUDIO_MEDIA_TYPES[path.suffix.lower()])


@router.delete("/{filename}")
async def delete_music(filename: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Delete one library track (and its provenance row) without allowing paths outside the library."""
    started_at = time.perf_counter()
    path = await asyncio.to_thread(_existing_music_path, filename)
    try:
        await asyncio.to_thread(path.unlink)
    except FileNotFoundError as exc:
        raise NotFoundError("Music track not found.") from exc
    async with write_transaction(db):
        await tracks.delete_row(db, path.name)
    return ok({"filename": filename}, started_at=started_at)
