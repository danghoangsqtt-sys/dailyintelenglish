"""Music library routes for listing, uploading, previewing, editing details and deleting tracks."""

import asyncio
import os
import time
from pathlib import Path
from uuid import uuid4

import aiofiles
import aiosqlite
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse

from app.core.constants import MAX_MUSIC_UPLOAD_BYTES, MAX_MUSIC_UPLOAD_MB, MUSIC_UPLOAD_CHUNK_BYTES
from app.core.exceptions import MusicUploadTooLargeError, NotFoundError, ValidationError
from app.core.responses import ok
from app.db.database import get_db
from app.db.transactions import write_transaction
from app.models.music import LICENCES, MOODS, PACES, SOURCES, MusicTrackPatch
from app.services import music_library_service as library
from app.services import music_select_service

router = APIRouter(prefix="/api/music", tags=["music"])
project_router = APIRouter(prefix="/api/projects/{project_id}/music", tags=["music"])

AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a"}
UPLOAD_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a"}
AUDIO_MEDIA_TYPES = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".m4a": "audio/mp4",
}
MP3_FRAME_SYNC_BYTES = {0xFB, 0xF3, 0xFA, 0xF2}


_music_dir = library.music_dir


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
        raise ValidationError("Only MP3, WAV, OGG and M4A music files are supported.")
    return cleaned


def _validate_magic_bytes(filename: str, header: bytes) -> None:
    """Reject obvious extension spoofing using lightweight audio signatures."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".wav":
        valid = len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WAVE"
    elif suffix == ".ogg":
        valid = header.startswith(b"OggS")
    elif suffix == ".m4a":
        valid = len(header) >= 12 and header[4:8] == b"ftyp"
    else:
        valid = header.startswith(b"ID3") or (
            len(header) >= 2 and header[0] == 0xFF and header[1] in MP3_FRAME_SYNC_BYTES
        )
    if not valid:
        raise ValidationError(f"The uploaded file does not contain valid {suffix[1:].upper()} header bytes.")


def _place_without_overwrite(temporary_path: Path, requested_name: str) -> Path:
    """Atomically place an upload, adding a numeric suffix instead of overwriting."""
    music_dir = temporary_path.parent
    requested_path = Path(requested_name)
    collision_index = 0
    while True:
        if collision_index == 0:
            candidate_name = requested_name
        else:
            candidate_name = f"{requested_path.stem} ({collision_index}){requested_path.suffix}"
        candidate_path = music_dir / candidate_name
        try:
            os.link(temporary_path, candidate_path)
        except FileExistsError:
            collision_index += 1
            continue
        temporary_path.unlink()
        return candidate_path


_track_payload = library.track_payload


def _unlink_if_exists(path: Path) -> None:
    """Remove a temporary upload if it still exists."""
    try:
        path.unlink()
    except FileNotFoundError:
        pass


_list_music_files = library.list_music_files


def _existing_music_path(filename: str) -> Path:
    """Resolve a safe existing music path or raise a typed 404."""
    safe_name = _validate_filename(filename, AUDIO_EXTENSIONS)
    path = _music_dir() / safe_name
    if not path.is_file():
        raise NotFoundError("Music track not found.")
    return path


_with_details = library.with_details


@router.get("")
async def list_music(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """List background music tracks with their details (Task 22.7)."""
    started_at = time.perf_counter()
    tracks = await asyncio.to_thread(_list_music_files)
    return ok(await _with_details(db, tracks), started_at=started_at)


@router.get("/options")
async def music_options() -> dict:
    """Task 22.7: the choices for a track's mood, source and licence."""
    return ok({
        "moods": [{"id": key, "label": label} for key, label in MOODS.items()],
        "sources": [{"id": key, "label": label} for key, label in SOURCES.items()],
        "licences": [{"id": key, **value} for key, value in LICENCES.items()],
        "paces": [{"id": key, "label": label} for key, label in PACES.items()],
    })


@router.post("/analyse")
async def analyse_music(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Task 22.9: classify every track not analysed yet (pace, ~BPM, energy, mood suggestion)."""
    started_at = time.perf_counter()
    analysed = await library.analyse_missing(db)
    tracks = await library.list_tracks(db)
    return ok({"analysed": analysed, "tracks": tracks}, started_at=started_at)


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

    track = await asyncio.to_thread(_track_payload, stored_path)
    [track] = await _with_details(db, [track])
    return ok(track, started_at=started_at)


@router.get("/{filename}")
async def get_music(filename: str) -> FileResponse:
    """Stream one library track for native browser audio preview."""
    path = await asyncio.to_thread(_existing_music_path, filename)
    return FileResponse(path, media_type=AUDIO_MEDIA_TYPES[path.suffix.lower()])


@router.patch("/{filename}")
async def edit_music(filename: str, body: MusicTrackPatch, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Task 22.7: edit a track's details; only the fields sent change, an empty value clears."""
    started_at = time.perf_counter()
    path = await asyncio.to_thread(_existing_music_path, filename)
    track = await asyncio.to_thread(_track_payload, path)
    await _with_details(db, [track])  # make sure the row exists
    async with write_transaction(db):
        await library.patch_track(db, path.name, body.model_dump(exclude_unset=True))
    [track] = await _with_details(db, [track])
    return ok(track, started_at=started_at)


@router.delete("/{filename}")
async def delete_music(filename: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Delete one library track without allowing paths outside the library."""
    started_at = time.perf_counter()
    path = await asyncio.to_thread(_existing_music_path, filename)
    try:
        await asyncio.to_thread(path.unlink)
    except FileNotFoundError as exc:
        raise NotFoundError("Music track not found.") from exc
    async with write_transaction(db):
        await library.delete_row(db, path.name)
    return ok({"filename": filename}, started_at=started_at)


@project_router.post("/suggest")
async def suggest_music(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Task 22.8 (D51): the library track that best fits this episode's topic and length, with the
    reason (AI choice among the top candidates, else the deterministic score)."""
    started_at = time.perf_counter()
    return ok(await music_select_service.suggest(db, project_id), started_at=started_at)
