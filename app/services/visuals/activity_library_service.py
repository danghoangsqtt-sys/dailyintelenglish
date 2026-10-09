"""Review-gated reusable activity illustrations and their safe local storage."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import shutil
import unicodedata
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

import aiosqlite
import aiofiles
from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError

REVIEW_STATES = ("pending", "approved", "rejected")
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
_ASPECT_RATIO = 16 / 9
_ASPECT_TOLERANCE = 0.15
_MIN_WIDTH, _MIN_HEIGHT = 640, 360
_UPLOAD_CHUNK_BYTES = 1024 * 1024
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def activities_dir() -> Path:
    return settings.DATA_DIR / "library" / "activities"


def inbox_dir() -> Path:
    return settings.DATA_DIR / "library" / "activities_inbox"


def _token(value: str) -> str:
    """Return a stable, searchable label without trusting filename punctuation."""
    plain = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    return " ".join(re.findall(r"[a-z0-9]+", plain))


def _labels(values: list[str], field: str) -> list[str]:
    result: list[str] = []
    for value in values:
        normalized = _token(value)
        if not normalized:
            raise ValidationError(f"{field} contains an empty label")
        if normalized not in result:
            result.append(normalized)
    return result


def _metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    activity = _token(str(metadata.get("activity") or ""))
    if not activity:
        raise ValidationError("activity is required")
    return {
        "character_id": metadata.get("character_id") or None,
        "activity": activity,
        "context_tags": _labels(list(metadata.get("context_tags") or []), "context_tags"),
        "aliases": _labels(list(metadata.get("aliases") or []), "aliases"),
        "variant": _token(str(metadata.get("variant") or "")),
    }


async def _character_keys(db: aiosqlite.Connection) -> dict[str, str]:
    cursor = await db.execute("SELECT id, name FROM characters")
    return {_token(row[1]): row[0] for row in await cursor.fetchall()}


async def _row(db: aiosqlite.Connection, activity_id: str) -> dict[str, Any]:
    cursor = await db.execute(
        "SELECT item.*, character.name AS character_name FROM activity_library item "
        "LEFT JOIN characters character ON character.id = item.character_id WHERE item.id = ?",
        (activity_id,),
    )
    found = await cursor.fetchone()
    if found is None:
        raise NotFoundError("Activity image not found")
    return dict(found)


def _view(row: dict[str, Any]) -> dict[str, Any]:
    view = dict(row)
    view["context_tags"] = json.loads(view.pop("context_tags_json"))
    view["aliases"] = json.loads(view.pop("aliases_json"))
    view["content_url"] = f"/api/visuals/library/activities/{view['id']}/content"
    view.pop("path", None)
    view.pop("content_sha", None)
    return view


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_image(path: Path) -> None:
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            width, height = image.size
    except (OSError, UnidentifiedImageError) as exc:
        raise ValidationError("not a readable image") from exc
    if width < _MIN_WIDTH or height < _MIN_HEIGHT:
        raise ValidationError(f"image must be at least {_MIN_WIDTH}x{_MIN_HEIGHT}")
    if abs((width / height) - _ASPECT_RATIO) > _ASPECT_TOLERANCE:
        raise ValidationError("image must use a 16:9 cutaway aspect ratio")


def _verify_image_bytes(content: bytes) -> None:
    try:
        with Image.open(BytesIO(content)) as image:
            image.verify()
        with Image.open(BytesIO(content)) as image:
            width, height = image.size
    except (OSError, UnidentifiedImageError) as exc:
        raise ValidationError("not a readable image") from exc
    if width < _MIN_WIDTH or height < _MIN_HEIGHT:
        raise ValidationError(f"image must be at least {_MIN_WIDTH}x{_MIN_HEIGHT}")
    if abs((width / height) - _ASPECT_RATIO) > _ASPECT_TOLERANCE:
        raise ValidationError("image must use a 16:9 cutaway aspect ratio")


async def read_upload(file: UploadFile) -> bytes:
    """Read and validate one bounded browser upload, then close its temporary handle."""
    content = bytearray()
    try:
        while chunk := await file.read(_UPLOAD_CHUNK_BYTES):
            content.extend(chunk)
            if len(content) > _MAX_UPLOAD_BYTES:
                raise ValidationError("activity images must be 20 MB or smaller")
        if not content:
            raise ValidationError("uploaded activity image is empty")
        value = bytes(content)
        await asyncio.to_thread(_verify_image_bytes, value)
        return value
    finally:
        await file.close()


async def next_variant(db: aiosqlite.Connection, character_id: str | None, activity: str) -> str:
    """Return the next two-digit variant for one character/activity shelf."""
    normalized = _token(activity)
    cursor = await db.execute(
        "SELECT variant FROM activity_library WHERE activity = ? AND character_id IS ?",
        (normalized, character_id),
    )
    numeric = [int(row[0]) for row in await cursor.fetchall() if str(row[0]).isdigit()]
    return f"{(max(numeric, default=0) + 1):02d}"


def _filename(path: Path, character_keys: dict[str, str]) -> dict[str, Any]:
    parts = path.stem.split("__")
    if len(parts) < 2 or len(parts) > 4 or not all(parts[:2]):
        raise ValidationError("filename must be <scope>__<activity>__[context]__[variant]")
    scope, activity = _token(parts[0]), parts[1]
    if scope == "generic":
        character_id = None
    elif scope in character_keys:
        character_id = character_keys[scope]
    else:
        raise ValidationError("filename names an unknown character scope")
    return _metadata({
        "character_id": character_id, "activity": activity,
        "context_tags": [parts[2]] if len(parts) >= 3 and parts[2] else [],
        "variant": parts[3] if len(parts) >= 4 else "",
    })


async def list_activities(
    db: aiosqlite.Connection, review_state: str | None = None, character_id: str | None = None,
    activity: str | None = None,
) -> list[dict[str, Any]]:
    clauses, params = [], []
    if review_state:
        if review_state not in REVIEW_STATES:
            raise ValidationError(f"review_state must be one of {', '.join(REVIEW_STATES)}")
        clauses.append("item.review_state = ?")
        params.append(review_state)
    if character_id:
        clauses.append("item.character_id = ?")
        params.append(character_id)
    if activity:
        clauses.append("item.activity = ?")
        params.append(_token(activity))
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    cursor = await db.execute(
        "SELECT item.*, character.name AS character_name FROM activity_library item "
        f"LEFT JOIN characters character ON character.id = item.character_id {where} "
        "ORDER BY item.created_at DESC, item.id DESC", tuple(params),
    )
    return [_view(dict(row)) for row in await cursor.fetchall()]


async def approved_candidates(db: aiosqlite.Connection) -> list[dict[str, Any]]:
    """Return only reviewed assets usable by deterministic matching; missing files are ignored safely."""
    rows = await list_activities(db, review_state="approved")
    usable = []
    for row in rows:
        try:
            await content_path(db, row["id"])
        except NotFoundError:
            continue
        usable.append(row)
    return usable


async def import_inbox(db: aiosqlite.Connection) -> dict[str, list[dict[str, str]]]:
    """Copy valid inbox files as pending library records; rejected files remain in the inbox."""
    keys, imported, rejected = await _character_keys(db), [], []
    folder = inbox_dir()
    if not folder.is_dir():
        return {"imported": imported, "rejected": rejected}
    for source in sorted(path for path in folder.rglob("*") if path.is_file()):
        try:
            if source.suffix.lower() not in _IMAGE_SUFFIXES:
                raise ValidationError("supported formats are PNG, JPEG and WebP")
            metadata = _filename(source, keys)
            await asyncio.to_thread(_verify_image, source)
            digest = await asyncio.to_thread(_sha, source)
            existing = await db.execute("SELECT id FROM activity_library WHERE content_sha = ?", (digest,))
            if await existing.fetchone() is not None:
                raise ConflictError("identical image already exists in the Activity Library")
            activity_id, now = str(uuid.uuid4()), _now()
            target = activities_dir() / f"{activity_id}{source.suffix.lower()}"
            await asyncio.to_thread(target.parent.mkdir, parents=True, exist_ok=True)
            await asyncio.to_thread(shutil.copyfile, source, target)
            await db.execute(
                "INSERT INTO activity_library (id, character_id, activity, context_tags_json, aliases_json, variant, path, "
                "content_sha, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (activity_id, metadata["character_id"], metadata["activity"], json.dumps(metadata["context_tags"]),
                 json.dumps(metadata["aliases"]), metadata["variant"], str(target), digest, now, now),
            )
            imported.append({"id": activity_id, "file": source.name})
        except (ValidationError, ConflictError) as exc:
            rejected.append({"file": source.name, "reason": str(exc)})
    return {"imported": imported, "rejected": rejected}


async def upload_activity(
    db: aiosqlite.Connection, file: UploadFile, raw_metadata: dict[str, Any],
) -> dict[str, Any]:
    """Validate a browser upload and create one pending Activity Library item."""
    content = await read_upload(file)
    return await upload_activity_bytes(db, file.filename or "activity.png", content, raw_metadata)


async def upload_activity_bytes(
    db: aiosqlite.Connection, filename: str, content: bytes, raw_metadata: dict[str, Any],
) -> dict[str, Any]:
    """Store already-read image bytes as one pending Activity Library item."""
    metadata = _metadata(raw_metadata)
    if metadata["character_id"] and metadata["character_id"] not in (await _character_keys(db)).values():
        raise ValidationError("character_id does not exist")
    suffix = Path(filename).suffix.lower()
    if suffix not in _IMAGE_SUFFIXES:
        raise ValidationError("supported formats are PNG, JPEG and WebP")
    if not content:
        raise ValidationError("uploaded activity image is empty")
    if len(content) > _MAX_UPLOAD_BYTES:
        raise ValidationError("activity images must be 20 MB or smaller")
    await asyncio.to_thread(_verify_image_bytes, content)

    folder = activities_dir()
    await asyncio.to_thread(folder.mkdir, parents=True, exist_ok=True)
    activity_id = str(uuid.uuid4())
    temporary = folder / f".{activity_id}.upload"
    target = folder / f"{activity_id}{suffix}"
    try:
        async with aiofiles.open(temporary, "wb") as destination:
            await destination.write(content)
        digest = await asyncio.to_thread(_sha, temporary)
        existing = await db.execute("SELECT id FROM activity_library WHERE content_sha = ?", (digest,))
        if await existing.fetchone() is not None:
            raise ConflictError("identical image already exists in the Activity Library")
        await asyncio.to_thread(temporary.replace, target)
        now = _now()
        try:
            await db.execute(
                "INSERT INTO activity_library (id, character_id, activity, context_tags_json, aliases_json, variant, path, "
                "content_sha, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (activity_id, metadata["character_id"], metadata["activity"], json.dumps(metadata["context_tags"]),
                 json.dumps(metadata["aliases"]), metadata["variant"], str(target), digest, now, now),
            )
        except Exception:
            await asyncio.to_thread(target.unlink, missing_ok=True)
            raise
        return _view(await _row(db, activity_id))
    except Exception:
        await asyncio.to_thread(temporary.unlink, missing_ok=True)
        raise


async def update_metadata(db: aiosqlite.Connection, activity_id: str, changes: dict[str, Any]) -> dict[str, Any]:
    row = await _row(db, activity_id)
    current = {
        "character_id": row["character_id"], "activity": row["activity"],
        "context_tags": json.loads(row["context_tags_json"]), "aliases": json.loads(row["aliases_json"]),
        "variant": row["variant"],
    }
    current.update(changes)
    metadata = _metadata(current)
    if metadata["character_id"] and metadata["character_id"] not in (await _character_keys(db)).values():
        raise ValidationError("character_id does not exist")
    await db.execute(
        "UPDATE activity_library SET character_id = ?, activity = ?, context_tags_json = ?, aliases_json = ?, variant = ?, "
        "updated_at = ? WHERE id = ?",
        (metadata["character_id"], metadata["activity"], json.dumps(metadata["context_tags"]), json.dumps(metadata["aliases"]),
         metadata["variant"], _now(), activity_id),
    )
    return _view(await _row(db, activity_id))


async def set_review(db: aiosqlite.Connection, activity_id: str, review_state: str) -> dict[str, Any]:
    if review_state not in REVIEW_STATES:
        raise ValidationError(f"review_state must be one of {', '.join(REVIEW_STATES)}")
    await _row(db, activity_id)
    await db.execute("UPDATE activity_library SET review_state = ?, updated_at = ? WHERE id = ?",
                     (review_state, _now(), activity_id))
    return _view(await _row(db, activity_id))


async def content_path(db: aiosqlite.Connection, activity_id: str) -> Path:
    row = await _row(db, activity_id)
    root, candidate = activities_dir().resolve(), Path(row["path"]).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise NotFoundError("Activity image file not found")
    return candidate


async def history(db: aiosqlite.Connection, activity_id: str) -> list[dict[str, Any]]:
    await _row(db, activity_id)
    cursor = await db.execute(
        "SELECT id, project_id, beat_id, render_id, created_at FROM activity_library_usage "
        "WHERE activity_id = ? ORDER BY created_at DESC, id DESC", (activity_id,),
    )
    return [dict(row) for row in await cursor.fetchall()]


async def record_usage(
    db: aiosqlite.Connection, activity_id: str, project_id: str, beat_id: str | None, render_id: str | None,
) -> None:
    """Persist a real selected render use; preview and coverage must never call this function."""
    await _row(db, activity_id)
    now = _now()
    await db.execute(
        "INSERT INTO activity_library_usage (id, activity_id, project_id, beat_id, render_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), activity_id, project_id, beat_id, render_id, now),
    )
    await db.execute("UPDATE activity_library SET use_count = use_count + 1, last_used_at = ?, updated_at = ? WHERE id = ?",
                     (now, now, activity_id))
