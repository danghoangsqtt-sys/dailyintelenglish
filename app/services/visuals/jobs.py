"""Persistent FIFO image jobs. Write methods run inside write_transaction."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from app.core.exceptions import NotFoundError


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row(row: aiosqlite.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


async def get_job(db: aiosqlite.Connection, job_id: str) -> dict[str, Any]:
    cursor = await db.execute("SELECT * FROM image_jobs WHERE id = ?", (job_id,))
    job = _row(await cursor.fetchone())
    if job is None:
        raise NotFoundError("Image job not found")
    return job


async def create_job(
    db: aiosqlite.Connection, kind: str, target_id: str, payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cursor = await db.execute(
        "SELECT * FROM image_jobs WHERE kind = ? AND target_id = ? "
        "AND status IN ('pending', 'running') ORDER BY created_at LIMIT 1",
        (kind, target_id),
    )
    existing = _row(await cursor.fetchone())
    if existing is not None:
        return existing
    job_id, now = str(uuid.uuid4()), _now()
    await db.execute(
        "INSERT INTO image_jobs (id, kind, target_id, status, payload_json, created_at, updated_at) "
        "VALUES (?, ?, ?, 'pending', ?, ?, ?)",
        (job_id, kind, target_id, json.dumps(payload or {}), now, now),
    )
    return await get_job(db, job_id)


async def claim_next(db: aiosqlite.Connection, kinds: list[str] | None = None) -> dict[str, Any] | None:
    if kinds is not None and not kinds:
        return None
    kind_filter = f" AND kind IN ({','.join('?' for _ in kinds)})" if kinds is not None else ""
    cursor = await db.execute(
        "SELECT id FROM image_jobs WHERE status = 'pending'" + kind_filter + " ORDER BY created_at, rowid LIMIT 1",
        kinds or (),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    await db.execute(
        "UPDATE image_jobs SET status = 'running', stage = 'starting', updated_at = ? WHERE id = ?",
        (_now(), row["id"]),
    )
    return await get_job(db, row["id"])


async def update_progress(db: aiosqlite.Connection, job_id: str, stage: str, progress: int) -> dict[str, Any]:
    await db.execute(
        "UPDATE image_jobs SET stage = ?, progress = ?, updated_at = ? WHERE id = ? AND status = 'running'",
        (stage, max(0, min(100, progress)), _now(), job_id),
    )
    return await get_job(db, job_id)


async def request_cancel(db: aiosqlite.Connection, job_id: str) -> dict[str, Any]:
    job = await get_job(db, job_id)
    if job["status"] in ("pending", "running"):
        status = "cancelled" if job["status"] == "pending" else "running"
        await db.execute(
            "UPDATE image_jobs SET cancel_requested = 1, status = ?, updated_at = ? WHERE id = ?",
            (status, _now(), job_id),
        )
    return await get_job(db, job_id)


async def is_cancel_requested(db: aiosqlite.Connection, job_id: str) -> bool:
    return bool((await get_job(db, job_id))["cancel_requested"])


async def finish_job(
    db: aiosqlite.Connection, job_id: str, status: str,
    result: dict[str, Any] | None = None, error: str | None = None,
) -> dict[str, Any]:
    await db.execute(
        "UPDATE image_jobs SET status = ?, stage = ?, progress = ?, result_json = ?, error = ?, "
        "updated_at = ? WHERE id = ?",
        (status, status, 100 if status == "complete" else (await get_job(db, job_id))["progress"],
         json.dumps(result) if result is not None else None, error, _now(), job_id),
    )
    return await get_job(db, job_id)


async def recover_running(db: aiosqlite.Connection) -> int:
    cursor = await db.execute(
        "UPDATE image_jobs SET status = 'error', stage = 'error', error = 'interrupted by app restart', "
        "updated_at = ? WHERE status = 'running'",
        (_now(),),
    )
    return cursor.rowcount


async def queue_counts(db: aiosqlite.Connection) -> dict[str, int]:
    cursor = await db.execute(
        "SELECT status, count(*) AS n FROM image_jobs WHERE status IN ('pending', 'running') GROUP BY status"
    )
    counts = {row["status"]: row["n"] for row in await cursor.fetchall()}
    return {"pending": counts.get("pending", 0), "running": counts.get("running", 0)}
