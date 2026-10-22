"""Phase 70 (ENH-052): the library package -- move the characters and the data libraries between machines.

A package is one `.zip`: `manifest.json`, one `db/<table>.json` per library table, and the library files under `files/`
(paths relative to the data folder). It never holds `app_settings` (the API keys), the automation settings, or any project
and its media.

Import merges, it never deletes: a row missing here is added, a row already here is replaced only when the package copy has
a newer `updated_at`, and a file is copied when it is missing here or the package copy is newer. Paths stored in the rows are
written in the package relative to the data folder and rewritten for this machine on import. The database is backed up first.
"""

from __future__ import annotations

import asyncio
import json
import os
import platform
import sqlite3
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import aiosqlite

from backend.core.config import settings
from backend.core.paths import get_project_root

FORMAT = "dbe-library-package"
FORMAT_VERSION = 1
# parents first, so the foreign keys hold while the rows go in
TABLES = ("characters", "character_assets", "activity_library", "scenes", "music_tracks",
          "channel_topics", "channel_series", "channel_episodes", "news_feeds")
PATH_COLUMNS = {"character_assets": ("path",), "activity_library": ("path",), "scenes": ("preview_path",)}
FOLDERS = ("library/characters", "library/sprites", "library/activities", "library/scenes", "assets_background/assets",
           "music_library", "brand_voice")
JOB_TABLES = ("ai_generation_jobs", "audio_jobs", "image_jobs", "video_jobs")
ACTIVE = ("pending", "queued", "running", "processing")
DATA_TAG = "@data/"


class PackageError(ValueError):
    """The package cannot be read, or this machine cannot take it now."""


def exports_dir() -> Path:
    return settings.DATA_DIR / "exports"


# ---------------------------------------------------------------- paths

def _to_package_path(value: str | None) -> str | None:
    """A stored path as `@data/<relative posix path>` when it lies in the data folder; other values stay as they are."""
    if not value:
        return value
    path = Path(value)
    absolute = path if path.is_absolute() else get_project_root() / path
    try:
        relative = absolute.resolve().relative_to(settings.DATA_DIR.resolve())
    except ValueError:
        return value
    return DATA_TAG + relative.as_posix()


def _from_package_path(value: str | None) -> str | None:
    """`@data/...` back into this machine's form: relative to the workspace when the data folder is `<workspace>/data`."""
    if not value or not value.startswith(DATA_TAG):
        return value
    relative = _safe_relative(value[len(DATA_TAG):])
    target = settings.DATA_DIR.resolve() / Path(*relative.parts)
    try:
        return str(target.relative_to(get_project_root().resolve()))
    except ValueError:
        return str(target)


def _safe_relative(name: str) -> PurePosixPath:
    path = PurePosixPath(name.replace("\\", "/"))
    if not name or path.is_absolute() or ".." in path.parts or ":" in path.parts[0]:
        raise PackageError(f"Unsafe path in the package: {name}")
    return path


# ---------------------------------------------------------------- summary

async def _columns(db: aiosqlite.Connection, table: str) -> list[dict]:
    cursor = await db.execute(f'PRAGMA table_info("{table}")')
    return [{"name": row[1], "pk": row[5]} for row in await cursor.fetchall()]


async def summary(db: aiosqlite.Connection) -> dict:
    counts = {}
    for table in TABLES:
        cursor = await db.execute(f'SELECT COUNT(*) FROM "{table}"')
        counts[table] = (await cursor.fetchone())[0]
    files, size = await asyncio.to_thread(_folder_totals)
    return {"counts": counts, "files": files, "bytes": size}


def _iter_files():
    root = settings.DATA_DIR
    for folder in FOLDERS:
        base = root / folder
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.is_file():
                yield path, path.relative_to(root).as_posix()


def _folder_totals() -> tuple[int, int]:
    files = size = 0
    for path, _name in _iter_files():
        files += 1
        size += path.stat().st_size
    return files, size


# ---------------------------------------------------------------- export

async def collect_rows(db: aiosqlite.Connection) -> dict[str, list[dict]]:
    """The library rows, paths in package form. Quick: the caller may hold a read transaction."""
    tables: dict[str, list[dict]] = {}
    for table in TABLES:
        cursor = await db.execute(f'SELECT * FROM "{table}"')
        names = [column[0] for column in cursor.description]
        rows = [dict(zip(names, row)) for row in await cursor.fetchall()]
        for row in rows:
            for column in PATH_COLUMNS.get(table, ()):
                row[column] = _to_package_path(row.get(column))
        tables[table] = rows
    return tables


async def write_package(tables: dict[str, list[dict]], destination: Path | None = None) -> dict:
    """Write the package (slow: the files) and return its path and counts. Needs no database."""
    from backend.core.build_info import get_build_info

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    destination = destination or exports_dir() / f"library-{stamp}.zip"
    manifest = {"format": FORMAT, "format_version": FORMAT_VERSION, "app_version": get_build_info().get("version"),
                "created_at": datetime.now(timezone.utc).isoformat(), "machine": platform.node(),
                "counts": {table: len(rows) for table, rows in tables.items()}}
    files = await asyncio.to_thread(_write_zip, destination, manifest, tables)
    manifest["files"] = files
    return {"path": str(destination), "name": destination.name, "bytes": destination.stat().st_size, "manifest": manifest}


def _write_zip(destination: Path, manifest: dict, tables: dict) -> int:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(".partial")
    count = 0
    # pictures and audio are already compressed: store them, which is fast for a package of a gigabyte or more
    with zipfile.ZipFile(partial, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        for path, name in _iter_files():
            archive.write(path, f"files/{name}")
            count += 1
        for table, rows in tables.items():
            archive.writestr(f"db/{table}.json", json.dumps(rows, ensure_ascii=False), compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("manifest.json", json.dumps({**manifest, "files": count}, ensure_ascii=False, indent=2))
    os.replace(partial, destination)
    return count


# ---------------------------------------------------------------- import

def read_manifest(package: Path) -> dict:
    try:
        with zipfile.ZipFile(package) as archive:
            manifest = json.loads(archive.read("manifest.json"))
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError, OSError) as error:
        raise PackageError("This is not a library package.") from error
    if manifest.get("format") != FORMAT:
        raise PackageError("This is not a library package.")
    if int(manifest.get("format_version", 0)) > FORMAT_VERSION:
        raise PackageError("The package comes from a newer version of the app — update this app first.")
    return manifest


async def _active_jobs(db: aiosqlite.Connection) -> int:
    total = 0
    marks = ",".join("?" * len(ACTIVE))
    for table in JOB_TABLES:
        cursor = await db.execute(f'SELECT COUNT(*) FROM "{table}" WHERE status IN ({marks})', ACTIVE)
        total += (await cursor.fetchone())[0]
    return total


def backup_database() -> Path:
    """A consistent copy of the database (the sqlite backup API keeps what sits in the WAL)."""
    target = settings.DATA_DIR / "backups" / f"app-before-library-import-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
    target.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(settings.db_path)
    try:
        copy = sqlite3.connect(target)
        with copy:
            source.backup(copy)
        copy.close()
    finally:
        source.close()
    return target


def _newer(incoming: dict, existing: dict) -> bool:
    return str(incoming.get("updated_at") or "") > str(existing.get("updated_at") or "")


async def merge_rows(db: aiosqlite.Connection, package: Path) -> dict:
    """Back up the database and merge the package rows. The caller holds the write transaction; copy the files after
    with `extract_files`, outside it."""
    manifest = read_manifest(package)
    if await _active_jobs(db):
        raise PackageError("A job is running — wait for it to finish, then import.")
    with zipfile.ZipFile(package) as archive:
        tables = {table: json.loads(archive.read(f"db/{table}.json")) for table in TABLES
                  if f"db/{table}.json" in archive.namelist()}
    backup = await asyncio.to_thread(backup_database)
    cursor = await db.execute("SELECT id FROM projects")
    projects = {row[0] for row in await cursor.fetchall()}
    report = {}
    for table in TABLES:
        report[table] = await _merge_table(db, table, tables.get(table, []), projects)
    return {"backup": str(backup), "tables": report, "source": manifest.get("machine"), "created_at": manifest.get("created_at")}


async def _merge_table(db: aiosqlite.Connection, table: str, rows: list[dict], projects: set[str]) -> dict:
    columns = await _columns(db, table)
    names = [column["name"] for column in columns]
    keys = [column["name"] for column in sorted(columns, key=lambda column: column["pk"]) if column["pk"]] or ["rowid"]
    added = updated = kept = 0
    for incoming in rows:
        row = {name: incoming[name] for name in names if name in incoming}
        if not all(key in row for key in keys):
            continue
        for column in PATH_COLUMNS.get(table, ()):
            if column in row:
                row[column] = _from_package_path(row[column])
        where = " AND ".join(f'"{key}" = ?' for key in keys)
        cursor = await db.execute(f'SELECT * FROM "{table}" WHERE {where}', [row[key] for key in keys])
        found = await cursor.fetchone()
        existing = dict(zip([column[0] for column in cursor.description], found)) if found else None
        if table == "channel_episodes":
            _keep_project_link(row, existing, projects)
        marks = ",".join("?" * len(row))
        quoted = ",".join(f'"{name}"' for name in row)
        if existing is None:
            cursor = await db.execute(f'INSERT OR IGNORE INTO "{table}" ({quoted}) VALUES ({marks})', list(row.values()))
            added += cursor.rowcount > 0
            kept += cursor.rowcount <= 0
        elif "updated_at" in row and _newer(row, existing):
            sets = ",".join(f'"{name}" = ?' for name in row if name not in keys)
            await db.execute(f'UPDATE "{table}" SET {sets} WHERE {where}',
                             [value for name, value in row.items() if name not in keys] + [row[key] for key in keys])
            updated += 1
        else:
            kept += 1
    return {"added": added, "updated": updated, "kept": kept}


def _keep_project_link(row: dict, existing: dict | None, projects: set[str]) -> None:
    """An episode keeps this machine's project; a project that only exists on the other machine is not linked."""
    if row.get("project_id") in projects:
        return
    row["project_id"] = existing.get("project_id") if existing else None
    if row.get("status") != "published":
        row["status"] = existing.get("status") if existing else "planned"


async def extract_files(package: Path) -> dict:
    return await asyncio.to_thread(_extract_files, package)


def _extract_files(package: Path) -> dict:
    root = settings.DATA_DIR.resolve()
    added = updated = kept = 0
    with zipfile.ZipFile(package) as archive:
        for info in archive.infolist():
            if info.is_dir() or not info.filename.startswith("files/"):
                continue
            relative = _safe_relative(info.filename[len("files/"):])
            if not any(relative.as_posix().startswith(folder + "/") for folder in FOLDERS):
                raise PackageError(f"Unexpected file in the package: {relative}")
            target = root / Path(*relative.parts)
            stamp = time.mktime(info.date_time + (0, 0, -1))
            if target.is_file():
                # zip times have a 2-second step: only a clearly newer package copy replaces the file here
                if target.stat().st_mtime >= stamp - 2:
                    kept += 1
                    continue
                updated += 1
            else:
                added += 1
            target.parent.mkdir(parents=True, exist_ok=True)
            partial = target.with_name(target.name + ".partial")
            with archive.open(info) as source, partial.open("wb") as output:
                while block := source.read(1024 * 1024):
                    output.write(block)
            os.replace(partial, target)
            os.utime(target, (stamp, stamp))
    return {"added": added, "updated": updated, "kept": kept}
