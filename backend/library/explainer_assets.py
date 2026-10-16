"""Immutable per-project illustrations, separate from character sprite packs."""
from __future__ import annotations

import asyncio
import hashlib
import io
import re
import uuid
import warnings
import weakref
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite
from PIL import Image, ImageOps, UnidentifiedImageError

from backend.content import project_service
from backend.core.config import settings
from backend.core.constants import (
    EXPLAINER_IMAGE_CONCURRENCY, EXPLAINER_IMAGE_MAX_BYTES, EXPLAINER_IMAGE_MAX_PIXELS,
    EXPLAINER_IMAGE_MAX_SIDE, EXPLAINER_IMAGE_MIN_SIDE, EXPLAINER_IMAGE_RENDER_MAX_SIDE,
)
from backend.core.exceptions import NotFoundError, ValidationError

_limits: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


def _root(project_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", project_id):
        raise ValidationError("Invalid illustration project identity")
    root = (settings.DATA_DIR / "explainer").resolve()
    target = root / project_id / "assets"
    if not target.resolve().is_relative_to(root):
        raise ValidationError("Illustration path leaves the project data folder")
    return target


def _stage_sync(project_id: str, root: Path, asset_id: str, content: bytes, filename: str) -> dict:
    if not content or len(content) > EXPLAINER_IMAGE_MAX_BYTES:
        raise ValidationError("Choose a non-empty illustration up to 20 MB")
    if not filename or "/" in filename or "\\" in filename or len(filename) > 200:
        raise ValidationError("Choose an illustration with a simple filename up to 200 characters")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as source:
                if source.format not in ("PNG", "JPEG", "WEBP"):
                    raise ValidationError("Illustrations must be PNG, JPEG or WebP")
                width, height = source.size
                if min(width, height) < EXPLAINER_IMAGE_MIN_SIDE or max(width, height) > EXPLAINER_IMAGE_MAX_SIDE or width * height > EXPLAINER_IMAGE_MAX_PIXELS:
                    raise ValidationError(f"Use image sides from {EXPLAINER_IMAGE_MIN_SIDE} to {EXPLAINER_IMAGE_MAX_SIDE} pixels and at most {EXPLAINER_IMAGE_MAX_PIXELS // 1_000_000} megapixels")
                source.verify()
            with Image.open(io.BytesIO(content)) as source:
                picture = ImageOps.exif_transpose(source)
                picture = picture.convert("RGBA" if "A" in picture.getbands() or "transparency" in picture.info else "RGB")
                picture.thumbnail((EXPLAINER_IMAGE_RENDER_MAX_SIDE, EXPLAINER_IMAGE_RENDER_MAX_SIDE), Image.Resampling.LANCZOS)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise ValidationError("The illustration is not a readable supported picture") from exc
    folder = root / asset_id
    folder.mkdir(parents=True, exist_ok=True)
    final = folder / "1.png"
    temporary = folder / ".1.upload.png"
    try:
        picture.save(temporary, "PNG")
        digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
        temporary.replace(final)
    except BaseException:
        temporary.unlink(missing_ok=True)
        final.unlink(missing_ok=True)
        raise
    return {"id": asset_id, "version": 1, "project_id": project_id, "path": str(final), "content_hash": digest,
            "mime_type": "image/png", "width": picture.width, "height": picture.height,
            "original_filename": filename, "created_at": datetime.now(timezone.utc).isoformat()}


async def stage_upload(project_id: str, content: bytes, filename: str) -> dict:
    """Validate/decode/normalize/hash outside DB locks; cancelled processing cleans its unpublished file."""
    root, asset_id = _root(project_id), str(uuid.uuid4())
    loop = asyncio.get_running_loop()
    semaphore = _limits.setdefault(loop, asyncio.Semaphore(EXPLAINER_IMAGE_CONCURRENCY))
    async with semaphore:
        task = asyncio.create_task(asyncio.to_thread(_stage_sync, project_id, root, asset_id, content, filename))
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            try:
                staged = await task
            except Exception:
                pass
            else:
                await discard(staged)
            raise


async def discard(staged: dict) -> None:
    """Remove only this attempt's unpublished file; prior versions stay untouched."""
    path = Path(staged["path"]).resolve()
    if not path.is_relative_to(_root(staged["project_id"]).resolve()):
        raise ValidationError("Invalid staged illustration path")
    await asyncio.to_thread(path.unlink, missing_ok=True)


async def publish(db: aiosqlite.Connection, staged: dict) -> dict:
    """Insert immutable metadata under the caller's transaction after checking the live Solo project."""
    expected = _root(staged["project_id"]) / str(staged["id"]) / "1.png"
    if not re.fullmatch(r"[0-9a-f-]{36}", str(staged["id"])) or staged["version"] != 1 or Path(staged["path"]).resolve() != expected.resolve():
        raise ValidationError("Invalid staged illustration identity or path")
    project = await project_service.get_project(db, staged["project_id"])
    if project.get("presentation_mode") != "solo_explainer":
        raise ValidationError("Illustrations belong to a Solo Explainer project")
    await db.execute("INSERT INTO project_explainer_assets "
                     "(id,version,project_id,content_hash,path,mime_type,width,height,original_filename,created_at) "
                     "VALUES (:id,:version,:project_id,:content_hash,:path,:mime_type,:width,:height,:original_filename,:created_at)", staged)
    return public(staged)


def public(row: dict) -> dict:
    """Safe display metadata and a concrete version reference; filesystem paths remain internal."""
    return {"asset": {"asset_id": row["id"], "version": row["version"], "content_hash": row["content_hash"]},
            "width": row["width"], "height": row["height"], "mime_type": row["mime_type"],
            "filename": row["original_filename"],
            "preview_url": f"/api/projects/{row['project_id']}/explainer/assets/{row['id']}/{row['version']}/content"}


async def get_asset(db: aiosqlite.Connection, project_id: str, asset_id: str, version: int) -> dict:
    """Read one pinned asset only if it belongs to this project and version."""
    cursor = await db.execute("SELECT * FROM project_explainer_assets WHERE project_id=? AND id=? AND version=?",
                              (project_id, asset_id, version))
    row = await cursor.fetchone()
    if row is None:
        raise NotFoundError("Illustration version not found in this project")
    return dict(row)


async def list_assets(db: aiosqlite.Connection, project_id: str) -> list[dict]:
    """List versioned illustration choices without reading or hashing their files."""
    cursor = await db.execute("SELECT * FROM project_explainer_assets WHERE project_id=? ORDER BY created_at,id,version", (project_id,))
    return [public(dict(row)) for row in await cursor.fetchall()]


async def verified_path(row: dict) -> Path:
    """Verify confinement and exact file hash outside DB transactions before serving/rendering a pinned version."""
    root = _root(row["project_id"]).resolve()
    path = Path(row["path"]).resolve()
    if not path.is_relative_to(root):
        raise NotFoundError("Illustration is outside its project data folder")
    def check() -> Path:
        try:
            if hashlib.sha256(path.read_bytes()).hexdigest() != row["content_hash"]:
                raise NotFoundError("Illustration file changed; import and review it again")
        except OSError as exc:
            raise NotFoundError("Illustration file is missing; import it again") from exc
        return path
    return await asyncio.to_thread(check)
