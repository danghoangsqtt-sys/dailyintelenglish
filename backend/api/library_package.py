"""Phase 70 (ENH-052): the library package routes -- what would be exported, export, download and import."""

import shutil
import time
from pathlib import Path

import aiosqlite
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse

from backend.core.exceptions import NotFoundError, ValidationError
from backend.core.responses import ok
from backend.db.database import get_db
from backend.db.transactions import read_transaction, write_transaction
from backend.library import library_package as package

router = APIRouter(prefix="/api/library-package", tags=["library-package"])


@router.get("")
async def get_summary(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    started_at = time.perf_counter()
    async with read_transaction():
        result = await package.summary(db)
    result["exports"] = sorted((path.name for path in package.exports_dir().glob("library-*.zip")), reverse=True)[:5]
    return ok(result, started_at=started_at)


@router.post("/export", status_code=201)
async def export(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    started_at = time.perf_counter()
    async with read_transaction():
        rows = await package.collect_rows(db)
    result = await package.write_package(rows)
    return ok({**result, "folder": str(package.exports_dir())}, started_at=started_at)


@router.get("/download/{name}")
async def download(name: str) -> FileResponse:
    if not name.startswith("library-") or not name.endswith(".zip") or "/" in name or "\\" in name or ".." in name:
        raise ValidationError("Unknown package name.")
    path = package.exports_dir() / name
    if not path.is_file():
        raise NotFoundError("That package is not here any more.")
    return FileResponse(path, filename=name, media_type="application/zip")


@router.post("/import")
async def import_upload(file: UploadFile = File(...), db: aiosqlite.Connection = Depends(get_db)) -> dict:
    started_at = time.perf_counter()
    incoming = package.exports_dir() / "incoming" / f"upload-{int(time.time() * 1000)}.zip"
    incoming.parent.mkdir(parents=True, exist_ok=True)
    try:
        with incoming.open("wb") as output:
            shutil.copyfileobj(file.file, output, 1024 * 1024)
        result = await _import(db, incoming)
    finally:
        incoming.unlink(missing_ok=True)
    return ok(result, started_at=started_at)


async def _import(db: aiosqlite.Connection, path: Path) -> dict:
    try:
        async with write_transaction(db):
            result = await package.merge_rows(db, path)
        result["files"] = await package.extract_files(path)
    except package.PackageError as error:
        raise ValidationError(str(error)) from error
    return result
