"""Regression tests for the FIX2B/FIX2C gates: a single connection-wide lock must
serialize ALL access to the shared connection — writes *and* reads, not just
same-project script writes — so one request's rollback can never touch another
request's uncommitted work, and a read can never see a write's data before it
commits (a dirty read) or after it rolls back (a phantom read). See
app/api/projects.py::_write_transaction / _read_transaction / _write_lock.

Calls `app.api.projects` internals directly (not through TestClient) against the
`db` fixture (raw aiosqlite connection, migrations applied — see conftest.py) so
the test can deterministically control exactly when each transaction is paused,
using asyncio.Event for synchronization rather than sleep-based timing.
"""

import asyncio

import pytest

from app.api import projects as projects_api
from app.models.project import ScriptConfig, SpeakerConfig
from app.services import project_service, script_service


def make_config(name: str) -> ScriptConfig:
    return ScriptConfig(
        name=name,
        topic="Concurrency testing",
        cefr_level="B1",
        duration_minutes=5.0,
        num_speakers=1,
        genre="interview",
        accent="american",
        speakers=[SpeakerConfig(name="Alex", gender="male", accent="american")],
    )


async def test_write_lock_prevents_cross_project_transaction_interleaving(db, monkeypatch):
    """Deterministic scenario: two DIFFERENT projects (A, B) write concurrently.
    B writes its script (uncommitted) then fails before its own commit. A must
    never be interleaved into B's transaction, and B's rollback must not touch
    A's data — proven by (1) the lock being provably held while A is paused
    mid-transaction (asyncio.Lock.locked(), no sleep needed), and (2) after both
    finish, A is saved intact and B has no script at all.

    All ordering is forced with asyncio.Event, not sleep-based timing: A pauses
    mid-transaction until the test releases it; B is only ever scheduled after
    that pause is confirmed, so it can only proceed once A's lock is released —
    whether B's task actually starts running before or after `release_a.set()`
    doesn't matter, since asyncio.Lock itself enforces the ordering either way.
    """
    project_a = await project_service.create_project(db, make_config("Project A"))
    project_b = await project_service.create_project(db, make_config("Project B"))
    speaker_a = project_a["speakers"][0]["id"]
    speaker_b = project_b["speakers"][0]["id"]

    a_paused = asyncio.Event()  # set once A has written (uncommitted) and is paused mid-transaction
    release_a = asyncio.Event()  # test sets this once it has confirmed A holds the lock

    real_update_project = project_service.update_project

    async def patched_update_project(db_arg, project_id, patch, commit=True):
        if project_id == project_a["id"]:
            # A has already saved its script lines (uncommitted) by this point —
            # see _save_script_and_advance, which calls save_script before this.
            a_paused.set()
            await release_a.wait()
        elif project_id == project_b["id"]:
            raise RuntimeError("simulated B failure before commit")
        return await real_update_project(db_arg, project_id, patch, commit=commit)

    monkeypatch.setattr(project_service, "update_project", patched_update_project)

    lines_a = [{"speaker_id": speaker_a, "text": f"A-{i}"} for i in range(5)]
    lines_b = [{"speaker_id": speaker_b, "text": f"B-{i}"} for i in range(5)]

    task_a = asyncio.create_task(
        projects_api._save_script_and_advance(db, project_a["id"], project_a, lines_a)
    )
    await asyncio.wait_for(a_paused.wait(), timeout=2)
    assert projects_api._write_lock.locked()  # A is holding the connection-wide lock, uncommitted

    # B is created only now, while A provably still holds the lock — B cannot possibly
    # acquire it (and therefore cannot write) before A releases, regardless of exactly
    # when B's task gets its first turn on the event loop.
    task_b = asyncio.create_task(
        projects_api._save_script_and_advance(db, project_b["id"], project_b, lines_b)
    )

    release_a.set()
    await task_a  # A completes: commits its script + status advance

    with pytest.raises(RuntimeError, match="simulated B failure"):
        await task_b  # B's script write happened, then its status-advance step raised -> rollback

    final_a_lines = await script_service.get_script(db, project_a["id"])
    assert [line["text"] for line in final_a_lines] == [f"A-{i}" for i in range(5)]

    final_b_lines = await script_service.get_script(db, project_b["id"])
    assert final_b_lines == []

    project_a_after = await project_service.get_project(db, project_a["id"])
    assert project_a_after["status"] == "script_generated"

    project_b_after = await project_service.get_project(db, project_b["id"])
    assert project_b_after["status"] == "draft"


async def test_read_transaction_waits_for_write_and_sees_no_phantom_rows(db, monkeypatch):
    """FIX2C #1/#2: a GET-style read must serialize behind an in-flight write on the
    same connection-wide lock, and once that write rolls back, the read must see
    only the pre-write state — never the rolled-back write's rows (a phantom read).

    Ordering is forced with asyncio.Event (no sleep): the read task is only ever
    created after the write is confirmed paused and holding the lock, and
    asyncio.Lock's own FIFO waiter queue guarantees the read cannot acquire it
    until the write's `_write_transaction` block fully exits (here, via rollback).
    """
    project = await project_service.create_project(db, make_config("Read Lock Project"))
    speaker_id = project["speakers"][0]["id"]

    write_paused = asyncio.Event()
    release_write = asyncio.Event()

    async def patched_update_project(db_arg, project_id, patch, commit=True):
        write_paused.set()
        await release_write.wait()
        raise RuntimeError("simulated write failure before commit")

    monkeypatch.setattr(project_service, "update_project", patched_update_project)

    lines = [{"speaker_id": speaker_id, "text": f"L-{i}"} for i in range(3)]

    write_task = asyncio.create_task(
        projects_api._save_script_and_advance(db, project["id"], project, lines)
    )
    await asyncio.wait_for(write_paused.wait(), timeout=2)
    assert projects_api._write_lock.locked()  # write holds the lock, script rows uncommitted

    async def do_read() -> list[dict]:
        async with projects_api._read_transaction():
            return await script_service.get_script(db, project["id"])

    read_task = asyncio.create_task(do_read())

    release_write.set()
    with pytest.raises(RuntimeError, match="simulated write failure"):
        await write_task  # rolls back — its script rows never really persisted

    read_lines = await read_task
    assert read_lines == []  # no phantom rows from the rolled-back write leaked into the read


async def test_write_transaction_rolls_back_on_commit_failure(db, monkeypatch):
    """FIX2B #3: the commit itself must run inside the try — a failure raised by
    db.commit() (not just by the wrapped writes) must still trigger a rollback.
    """
    project = await project_service.create_project(db, make_config("Commit Failure Project"))
    speaker_id = project["speakers"][0]["id"]
    lines = [{"speaker_id": speaker_id, "text": "Should not survive a failed commit."}]

    real_commit = db.commit

    async def failing_commit():
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(db, "commit", failing_commit)

    with pytest.raises(RuntimeError, match="simulated commit failure"):
        await projects_api._save_script_and_advance(db, project["id"], project, lines)

    monkeypatch.setattr(db, "commit", real_commit)  # restore before touching db again

    saved_lines = await script_service.get_script(db, project["id"])
    assert saved_lines == []

    project_after = await project_service.get_project(db, project["id"])
    assert project_after["status"] == "draft"
