"""Phase 80 (owner 2026-10-26): "Make videos now" for a Shorts batch.

The night Automation made a batch's videos only before their publishing dates, and "make the projects now" created empty
drafts. This makes every episode of one batch series now, one after another, with the same steps as Automation
(`Producer`: project -> script -> learning -> voice -> visual plan -> video -> thumbnail -> YouTube texts), recording the
progress in the Automation run/item tables (trigger `shorts_batch:<series id>`) so the page can be reloaded and the
Automation page lists it too. The results say where each video is saved (the project's folder under the main save folder).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

import aiosqlite

from backend.automation import automation_service as service
from backend.automation.runner import Producer, StepClient, StepError, get_runner
from backend.content import export_service
from backend.core.exceptions import ConflictError, NotFoundError
from backend.db.transactions import read_transaction, write_transaction

logger = logging.getLogger(__name__)
TRIGGER = "shorts_batch:"

_tasks: dict[str, asyncio.Task] = {}
_stop: set[str] = set()


def running(series_id: str) -> bool:
    task = _tasks.get(series_id)
    return task is not None and not task.done()


def busy() -> bool:
    """A batch is being made (the night Automation waits for it)."""
    return any(running(series_id) for series_id in list(_tasks))


async def _series_episodes(db: aiosqlite.Connection, series_id: str) -> list[dict[str, Any]]:
    items = [item for item in await service.episodes(db) if item["series_id"] == series_id]
    if not items:
        raise NotFoundError("This batch has no episodes")
    return sorted(items, key=lambda item: item["number"])


async def start(app: Any, db_provider: Callable[[], aiosqlite.Connection], series_id: str) -> dict[str, Any]:
    """Start making the batch's unfinished videos (a no-op when it is already being made)."""
    if running(series_id):
        return {"started": False, "running": True}
    runner = get_runner()
    if runner is not None and runner.run_id is not None:
        raise ConflictError("Automation is making videos right now. Wait for it to finish or stop it, then make this batch.")
    if busy():  # one at a time: the GPU, the AI quota and the renderer are shared
        raise ConflictError("Another batch is being made right now. Wait for it to finish.")
    db = db_provider()
    async with write_transaction(db):
        episodes = await _series_episodes(db, series_id)
        run = await service.create_run(db, f"{TRIGGER}{series_id}")
    todo = [episode for episode in episodes if not episode["finished"]]
    _stop.discard(series_id)
    _tasks[series_id] = asyncio.create_task(_make_all(app, db_provider, series_id, run["id"], todo))
    return {"started": True, "running": True, "videos": len(todo)}


def stop(series_id: str) -> bool:
    """Stop after the current step (the next "Make videos now" goes on from there)."""
    if not running(series_id):
        return False
    _stop.add(series_id)
    return True


async def _make_all(app: Any, db_provider: Callable[[], aiosqlite.Connection], series_id: str, run_id: str,
                    episodes: list[dict[str, Any]]) -> None:
    db = db_provider()
    status, message = "complete", ""
    try:
        for episode in episodes:
            if series_id in _stop:
                status, message = "stopped", "Stopped by you."
                break
            await _make_one(app, db, series_id, run_id, episode)
    except Exception as exc:  # noqa: BLE001 -- the run must be closed whatever happens
        logger.exception("shorts_batch_make_failed series_id=%s", series_id)
        status, message = "error", str(exc) or exc.__class__.__name__
    finally:
        async with write_transaction(db):
            await service.finish_run(db, run_id, status, message)
        _stop.discard(series_id)


async def _make_one(app: Any, db: aiosqlite.Connection, series_id: str, run_id: str, episode: dict[str, Any]) -> None:
    async with write_transaction(db):
        item_id = await service.start_item(db, run_id, episode)
    current = {"project_id": episode.get("project_id")}

    async def on_step(step: str, project_id: str | None) -> None:
        if series_id in _stop:
            raise StepError("Stopped by you; it goes on from this step next time.")
        current["project_id"] = project_id
        async with write_transaction(db):
            await service.update_item(db, item_id, step=step, project_id=project_id)

    client = StepClient(app)
    try:
        project_id = await Producer(client).produce(episode, on_step)
        status, message, project = "waiting_review", "Ready: watch it and publish it.", project_id
    except StepError as exc:
        status, message, project = "needs_attention", str(exc), current["project_id"]
    except Exception as exc:  # noqa: BLE001 -- one failed video does not stop the batch
        logger.exception("shorts_batch_item_failed episode_id=%s", episode["id"])
        status, message, project = "error", str(exc) or exc.__class__.__name__, current["project_id"]
    finally:
        await client.close()
    async with write_transaction(db):
        await service.update_item(db, item_id, status=status, message=message[:1000], project_id=project)


async def results(db: aiosqlite.Connection, series_id: str) -> dict[str, Any]:
    """Each Short of the batch: its latest making status and step, its video and where it is saved."""
    async with read_transaction():
        episodes = await _series_episodes(db, series_id)
        cursor = await db.execute(
            "SELECT i.* FROM automation_items i JOIN automation_runs r ON r.id = i.run_id WHERE r.trigger = ? "
            "ORDER BY i.started_at", (f"{TRIGGER}{series_id}",))
        latest = {row["episode_id"]: dict(row) for row in await cursor.fetchall()}
        items = []
        for episode in episodes:
            project_id = episode.get("project_id") or (latest.get(episode["id"]) or {}).get("project_id")
            video = folder = None
            if project_id:
                cursor = await db.execute("SELECT status, mp4_path FROM video_jobs WHERE project_id = ?", (project_id,))
                job = await cursor.fetchone()
                if job and job["status"] == "complete" and job["mp4_path"]:
                    video = f"/api/projects/{project_id}/video/download?format=mp4"
                folder = (await export_service.public(db, project_id))["folder"]
            item = latest.get(episode["id"]) or {}
            items.append({"episode_id": episode["id"], "number": episode["number"], "title": episode["title"],
                          "publish_date": episode["publish_date"], "project_id": project_id,
                          "status": item.get("status") or ("waiting_review" if episode["finished"] else "video_ready" if video else "planned"),
                          "step": item.get("step") or "", "message": item.get("message") or "",
                          "video_url": video, "folder": folder})
    return {"series_id": series_id, "running": running(series_id), "items": items,
            "main_folder": await export_service.main_folder(db)}
