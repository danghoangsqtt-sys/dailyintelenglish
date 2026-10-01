"""One-at-a-time image job loop with durable restart and cancellation semantics."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

import aiosqlite

from app.db.transactions import read_transaction, write_transaction
from app.services.visuals import jobs

logger = logging.getLogger(__name__)
JobHandler = Callable[[dict, "ImageJobRunner"], Awaitable[dict | None]]


class JobCancelled(Exception):
    """The user requested cancellation at an image boundary."""


class ImageJobRunner:
    def __init__(self, db_getter: Callable[[], aiosqlite.Connection], poll_seconds: float = 1.0) -> None:
        self._db_getter = db_getter
        self._poll_seconds = poll_seconds
        self._handlers: dict[str, JobHandler] = {}
        self._stop: asyncio.Event | None = None
        self._wake: asyncio.Event | None = None
        self._task: asyncio.Task | None = None

    def register_handler(self, kind: str, handler: JobHandler) -> None:
        self._handlers[kind] = handler
        self.wake()

    def wake(self) -> None:
        """Notify the runner after an API request enqueues a job."""
        if self._wake is not None:
            self._wake.set()

    async def start(self) -> None:
        async with write_transaction(self._db_getter()):
            await jobs.recover_running(self._db_getter())
        self._stop = asyncio.Event()
        self._wake = asyncio.Event()
        self._wake.set()  # drain pending jobs retained across restarts
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stop.set()
        if self._wake is not None:
            self._wake.set()
        try:
            await asyncio.wait_for(self._task, timeout=10)
        except TimeoutError:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        self._wake = None

    async def boundary(self, job_id: str, stage: str, progress: int) -> None:
        """Check cancellation between images, then publish progress."""
        db = self._db_getter()
        async with read_transaction():
            cancelled = await jobs.is_cancel_requested(db, job_id)
        if cancelled:
            raise JobCancelled()
        async with write_transaction(db):
            await jobs.update_progress(db, job_id, stage, progress)

    async def _run(self) -> None:
        assert self._stop is not None
        while not self._stop.is_set():
            try:
                if not self._handlers:
                    await self._wait_for_work()
                    continue
                db = self._db_getter()
                async with write_transaction(db):
                    job = await jobs.claim_next(db, list(self._handlers))
                if job is None:
                    await self._wait_for_work()
                    continue
                try:
                    result = await self._handlers[job["kind"]](job, self)
                except JobCancelled:
                    async with write_transaction(db):
                        await jobs.finish_job(db, job["id"], "cancelled")
                except Exception as exc:  # noqa: BLE001 -- one failed image job must not end the queue
                    logger.exception("image_job_failed job_id=%s", job["id"])
                    async with write_transaction(db):
                        await jobs.finish_job(db, job["id"], "error", error=str(exc)[:500])
                else:
                    async with write_transaction(db):
                        await jobs.finish_job(db, job["id"], "complete", result=result)
            except Exception:  # noqa: BLE001 -- preserve the background loop after DB errors
                logger.exception("image_job_loop_error")
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=1)
                except TimeoutError:
                    pass

    async def _wait_for_work(self) -> None:
        assert self._wake is not None
        assert self._stop is not None
        while not self._wake.is_set() and not self._stop.is_set():
            try:
                await asyncio.wait_for(self._wake.wait(), timeout=self._poll_seconds)
            except TimeoutError:
                pass
        self._wake.clear()

    @property
    def is_alive(self) -> bool:
        return self._task is not None and not self._task.done()
