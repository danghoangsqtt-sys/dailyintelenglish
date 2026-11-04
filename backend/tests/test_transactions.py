"""Real shared-connection isolation across failures and coroutine cancellation."""

import asyncio

import aiosqlite
import pytest

from backend.db import transactions


@pytest.fixture
async def connection():
    async with aiosqlite.connect(":memory:") as db:
        await db.execute("CREATE TABLE items (label TEXT)")
        await db.commit()
        yield db


async def labels(db: aiosqlite.Connection) -> list[str]:
    """Read persisted/visible rows through the same lock used by API readers."""
    async with transactions.read_transaction():
        return [row[0] for row in await (await db.execute("SELECT label FROM items ORDER BY rowid")).fetchall()]


@pytest.mark.parametrize("during_commit", [False, True])
async def test_cancelled_write_never_leaks_into_next_request(connection, monkeypatch, during_commit):
    entered = asyncio.Event()

    async def stalled_commit():
        entered.set()
        await asyncio.Event().wait()

    if during_commit:
        monkeypatch.setattr(connection, "commit", stalled_commit)

    async def abandoned_write():
        async with transactions.write_transaction(connection):
            await connection.execute("INSERT INTO items VALUES ('abandoned')")
            if not during_commit:
                entered.set()
                await asyncio.Event().wait()

    task = asyncio.create_task(abandoned_write())
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    monkeypatch.undo()
    assert not connection.in_transaction
    assert await labels(connection) == []
    async with transactions.write_transaction(connection):
        await connection.execute("INSERT INTO items VALUES ('next request')")
    await connection.rollback()
    assert await labels(connection) == ["next request"]


@pytest.mark.parametrize("initial_failure", ["cancel", "error"])
async def test_repeated_cancel_waits_for_rollback_before_unlock(connection, monkeypatch, initial_failure):
    wrote, rolling_back, allow_rollback, reader_started = (asyncio.Event() for _ in range(4))
    original_rollback = connection.rollback

    async def delayed_rollback():
        rolling_back.set()
        await allow_rollback.wait()
        await original_rollback()

    monkeypatch.setattr(connection, "rollback", delayed_rollback)

    async def abandoned_write():
        async with transactions.write_transaction(connection):
            await connection.execute("INSERT INTO items VALUES ('abandoned')")
            wrote.set()
            if initial_failure == "error":
                raise ValueError("fixture failure before cleanup")
            await asyncio.Event().wait()

    task = asyncio.create_task(abandoned_write())
    await wrote.wait()
    if initial_failure == "cancel":
        task.cancel()
    await asyncio.wait_for(rolling_back.wait(), timeout=2)

    async def next_reader():
        reader_started.set()
        return await labels(connection)

    reader = asyncio.create_task(next_reader())
    await reader_started.wait()
    try:
        for _ in range(2):
            task.cancel()
            await asyncio.sleep(0)
            assert transactions.write_lock.locked(), "cleanup must finish before another request can enter"
            assert not reader.done()
        allow_rollback.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert await reader == []
        assert not connection.in_transaction
    finally:
        allow_rollback.set()
        await asyncio.gather(task, reader, return_exceptions=True)


@pytest.mark.parametrize("during_commit", [False, True])
async def test_ordinary_failure_rolls_back_and_preserves_exception(connection, monkeypatch, during_commit):
    original = RuntimeError("fixture commit/body failure")

    async def failed_commit():
        raise original

    if during_commit:
        monkeypatch.setattr(connection, "commit", failed_commit)
    with pytest.raises(RuntimeError) as caught:
        async with transactions.write_transaction(connection):
            await connection.execute("INSERT INTO items VALUES ('failed')")
            if not during_commit:
                raise original
    assert caught.value is original
    assert not connection.in_transaction and not transactions.write_lock.locked()
    assert await labels(connection) == []


async def test_successful_transaction_commits(connection):
    async with transactions.write_transaction(connection):
        await connection.execute("INSERT INTO items VALUES ('saved')")
    assert not connection.in_transaction
    await connection.rollback()
    assert await labels(connection) == ["saved"]


async def test_cancelled_rollback_itself_is_propagated(connection, monkeypatch):
    async def unavailable_rollback():
        raise asyncio.CancelledError("fixture cleanup task cancelled independently")

    monkeypatch.setattr(connection, "rollback", unavailable_rollback)
    with pytest.raises(asyncio.CancelledError):
        async with transactions.write_transaction(connection):
            raise ValueError("fixture failure")
    assert not transactions.write_lock.locked()
