"""Per-speaker avatar image upload/serve/delete (Task 1.7c — Video Studio groundwork).

Deliberately scoped to storing and safely serving one portrait image per speaker. No
LivePortrait/lip-sync inference happens here or anywhere yet — see the task card for why.
"""

import asyncio
from pathlib import Path
from uuid import uuid4

import aiofiles
import aiosqlite
from fastapi import UploadFile

from app.core.config import settings
from app.core.constants import (
    AVATAR_UPLOAD_CHUNK_BYTES,
    AVATAR_UPLOAD_EXTENSIONS,
    MAX_AVATAR_UPLOAD_BYTES,
    MAX_AVATAR_UPLOAD_MB,
)
from app.core.exceptions import AvatarUploadTooLargeError, NotFoundError, ValidationError
from app.services import project_service

AVATAR_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def _avatar_dir(project_id: str) -> Path:
    """Return the configured avatar-storage directory for one project."""
    return settings.DATA_DIR / "avatars" / project_id


def _validate_extension(filename: str) -> str:
    """Validate a client-supplied filename's extension without trusting the rest of it."""
    suffix = Path(filename).suffix.lower()
    if suffix not in AVATAR_UPLOAD_EXTENSIONS:
        raise ValidationError("Only PNG and JPEG avatar images are supported.")
    return suffix


def _validate_magic_bytes(suffix: str, header: bytes) -> None:
    """Reject obvious extension spoofing using lightweight image signatures."""
    if suffix == ".png":
        valid = header.startswith(b"\x89PNG\r\n\x1a\n")
    else:
        valid = header[:3] == b"\xff\xd8\xff"
    if not valid:
        raise ValidationError("The uploaded file does not contain valid image header bytes.")


def _existing_avatar_files(project_id: str, speaker_id: str) -> list[Path]:
    """Find any previously stored avatar file(s) for one speaker, regardless of extension."""
    avatar_dir = _avatar_dir(project_id)
    if not avatar_dir.is_dir():
        return []
    return [path for path in avatar_dir.glob(f"{speaker_id}.*") if path.is_file()]


def _remove_existing_avatar_files(project_id: str, speaker_id: str) -> None:
    for path in _existing_avatar_files(project_id, speaker_id):
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def _unlink_if_exists(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _finalize_avatar_file(project_id: str, speaker_id: str, suffix: str, temporary_path: Path) -> Path:
    """Replace any previous avatar file for this speaker with the newly uploaded one."""
    _remove_existing_avatar_files(project_id, speaker_id)
    final_path = _avatar_dir(project_id) / f"{speaker_id}{suffix}"
    temporary_path.replace(final_path)
    return final_path


async def _require_speaker(db: aiosqlite.Connection, project_id: str, speaker_id: str) -> dict:
    project = await project_service.get_project(db, project_id)
    if not any(speaker["id"] == speaker_id for speaker in project["speakers"]):
        raise NotFoundError(f"Speaker {speaker_id} not found on project {project_id}")
    return project


async def upload_avatar(
    db: aiosqlite.Connection, project_id: str, speaker_id: str, file: UploadFile, commit: bool = True
) -> dict:
    """Validate and store one speaker's avatar image, replacing any previous one."""
    await _require_speaker(db, project_id, speaker_id)
    suffix = _validate_extension(file.filename or "")

    avatar_dir = _avatar_dir(project_id)
    await asyncio.to_thread(avatar_dir.mkdir, parents=True, exist_ok=True)
    temporary_path = avatar_dir / f".{uuid4().hex}.upload"
    total_bytes = 0
    first_chunk = True

    try:
        async with aiofiles.open(temporary_path, "wb") as destination:
            while chunk := await file.read(AVATAR_UPLOAD_CHUNK_BYTES):
                if first_chunk:
                    _validate_magic_bytes(suffix, chunk)
                    first_chunk = False
                total_bytes += len(chunk)
                if total_bytes > MAX_AVATAR_UPLOAD_BYTES:
                    raise AvatarUploadTooLargeError(
                        f"Avatar images must be {MAX_AVATAR_UPLOAD_MB} MB or smaller."
                    )
                await destination.write(chunk)

        if total_bytes == 0:
            raise ValidationError("The uploaded avatar image is empty.")

        final_path = await asyncio.to_thread(
            _finalize_avatar_file, project_id, speaker_id, suffix, temporary_path
        )
    except Exception:
        await asyncio.to_thread(_unlink_if_exists, temporary_path)
        raise
    finally:
        await file.close()

    await db.execute(
        "UPDATE speakers SET avatar_image_path = ? WHERE id = ? AND project_id = ?",
        (str(final_path), speaker_id, project_id),
    )
    if commit:
        await db.commit()
    return await project_service.get_project(db, project_id)


def _resolve_avatar_sync(project_id: str, stored_path: str) -> Path:
    candidate = Path(stored_path).resolve()
    project_root = _avatar_dir(project_id).resolve()
    if project_root not in candidate.parents or not candidate.is_file():
        raise NotFoundError("Speaker avatar not found.")
    return candidate


async def resolve_avatar_path(db: aiosqlite.Connection, project_id: str, speaker_id: str) -> Path:
    """Resolve one validated, existing avatar file path owned by this project/speaker."""
    cursor = await db.execute(
        "SELECT avatar_image_path FROM speakers WHERE id = ? AND project_id = ?",
        (speaker_id, project_id),
    )
    row = await cursor.fetchone()
    if row is None or not row["avatar_image_path"]:
        raise NotFoundError("Speaker avatar not found.")
    return await asyncio.to_thread(_resolve_avatar_sync, project_id, row["avatar_image_path"])


async def delete_avatar(
    db: aiosqlite.Connection, project_id: str, speaker_id: str, commit: bool = True
) -> dict:
    """Remove a speaker's stored avatar file (if any) and clear the DB column."""
    await _require_speaker(db, project_id, speaker_id)
    await asyncio.to_thread(_remove_existing_avatar_files, project_id, speaker_id)
    await db.execute(
        "UPDATE speakers SET avatar_image_path = NULL WHERE id = ? AND project_id = ?",
        (speaker_id, project_id),
    )
    if commit:
        await db.commit()
    return await project_service.get_project(db, project_id)
