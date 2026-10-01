"""PM review r1 fixes F2-F4 (Phase 20): stale shot rows, worker kill, unlock guard."""

import json
import subprocess
import uuid

import pytest
from PIL import Image

from app.core.config import settings
from app.core.exceptions import ConflictError
from app.db.transactions import write_transaction
from app.models.project import ScriptConfig, SpeakerConfig
from app.models.visuals import CharacterInput
from app.services import project_service
from app.services.visuals import engine as engine_module
from app.services.visuals import jobs, library_service, pipelines, project_visuals_service
from app.services.visuals.runner import JobCancelled


@pytest.fixture(autouse=True)
def fake_engine(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr(settings, "IMAGE_ENGINE", "fake")
    monkeypatch.setattr(settings, "AI_VISUALS_ENABLED", True)
    monkeypatch.setattr(settings, "VISUALS_DUO_REFINE", True)


async def _locked_character(db, name: str, color: str) -> str:
    character_id = str(uuid.uuid4())
    face = settings.DATA_DIR / "library" / "characters" / character_id / "face.png"
    face.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (512, 512), color).save(face)
    await db.execute(
        "INSERT INTO characters (id, name, gender, age_group, role, hair, eyes, top_color, top_item, "
        "bottom_color, bottom_item, status, base_seed, created_at, updated_at) VALUES "
        "(?, ?, 'female', 'young', 'English teacher', 'long black hair', 'brown eyes', ?, 'shirt', "
        "'navy blue', 'jeans', 'locked', 100, 'now', 'now')",
        (character_id, name, color),
    )
    await db.execute(
        "INSERT INTO character_assets (id, character_id, kind, path, created_at) VALUES (?, ?, 'face', ?, 'now')",
        (str(uuid.uuid4()), character_id, str(face)),
    )
    return character_id


async def _project_with_cast(db) -> dict:
    config = ScriptConfig(
        name="Review r1", topic="t", cefr_level="B1", duration_minutes=5.0, num_speakers=2,
        genre="interview", accent="american",
        speakers=[SpeakerConfig(name="Nova", gender="female", accent="american"),
                  SpeakerConfig(name="Mira", gender="female", accent="american")],
    )
    async with write_transaction(db):
        project = await project_service.create_project(db, config)
        await db.execute(
            "INSERT OR IGNORE INTO scenes (id, name, place, staging, is_builtin, created_at, updated_at) "
            "VALUES ('builtin-cafe', 'Cafe', 'a cozy Vietnamese street cafe', 'seated', 1, 'now', 'now')"
        )
        first = await _locked_character(db, "Nova", "yellow")
        second = await _locked_character(db, "Mira", "green")
        await project_visuals_service.set_cast(db, project["id"], [
            {"speaker_index": 0, "character_id": first}, {"speaker_index": 1, "character_id": second},
        ])
        await project_visuals_service.set_scenes(db, project["id"], ["builtin-cafe"])
    return project


class _CancelAfterFirstShot:
    """Stub runner: requests cancellation at the first image boundary after one shot completed."""

    def __init__(self, db) -> None:
        self.db = db

    def get_db(self):
        return self.db

    async def boundary(self, job_id: str, stage: str, progress: int) -> None:
        cursor = await self.db.execute("SELECT count(*) AS n FROM project_shots WHERE status = 'complete'")
        if (await cursor.fetchone())["n"] >= 1:
            raise JobCancelled()


@pytest.mark.asyncio
async def test_cancel_marks_unfinished_shots_and_keeps_completed(db):
    project = await _project_with_cast(db)
    async with write_transaction(db):
        job = await jobs.create_job(db, "project_shots", project["id"])
    with pytest.raises(JobCancelled):
        await pipelines.project_shots(job, _CancelAfterFirstShot(db))
    shots = await project_visuals_service.shot_rows(db, project["id"])
    statuses = sorted((shot["status"], shot["error"]) for shot in shots)
    assert len(shots) == 4  # 2 singles + duo_close + duo_wide in one scene
    assert statuses[0] == ("complete", None)
    assert all(status == ("error", "cancelled") for status in statuses[1:])


@pytest.mark.asyncio
async def test_startup_recovery_marks_stale_pending_shots(db):
    project = await _project_with_cast(db)
    async with write_transaction(db):
        await db.execute(
            "INSERT INTO project_shots (id, project_id, scene_id, kind, speaker_indexes, seed, status, "
            "created_at, updated_at) VALUES ('stale', ?, 'builtin-cafe', 'single', ?, 7, 'pending', 'now', 'now')",
            (project["id"], json.dumps([0])),
        )
        await db.execute(
            "INSERT INTO project_shots (id, project_id, scene_id, kind, speaker_indexes, seed, status, "
            "final_path, created_at, updated_at) VALUES "
            "('done', ?, 'builtin-cafe', 'single', ?, 8, 'complete', 'x.png', 'now', 'now')",
            (project["id"], json.dumps([1])),
        )
    assert await pipelines.recover_pending_shots(db) == 1
    rows = {row["id"]: row for row in await project_visuals_service.shot_rows(db, project["id"])}
    assert (rows["stale"]["status"], rows["stale"]["error"]) == ("error", "interrupted by app restart")
    assert rows["done"]["status"] == "complete"


class _StubStdout:
    def __init__(self, line: str) -> None:
        self.line = line

    def readline(self) -> str:
        return self.line


class _StubPopen:
    handshake = '{"status": "ready"}\n'
    instances: list["_StubPopen"] = []

    def __init__(self, *args, **kwargs) -> None:
        self.stdin = open(settings.DATA_DIR / "stub_stdin.txt", "w", encoding="utf-8")  # noqa: SIM115
        self.stdout = _StubStdout(self.handshake)
        self.killed = False
        self.waits = 0
        _StubPopen.instances.append(self)

    def kill(self) -> None:
        self.killed = True

    def wait(self, timeout=None) -> int:
        self.waits += 1
        if not self.killed:
            raise subprocess.TimeoutExpired("image_worker", timeout)
        return -9


def test_hung_worker_is_killed_on_close(monkeypatch):
    monkeypatch.setattr(engine_module.subprocess, "Popen", _StubPopen)
    worker = engine_module._WorkerProcess()
    process = _StubPopen.instances[-1]
    worker.close()
    assert process.killed is True
    assert worker.stderr_file.closed


def test_failed_handshake_kills_worker(monkeypatch):
    monkeypatch.setattr(engine_module.subprocess, "Popen", _StubPopen)
    monkeypatch.setattr(_StubPopen, "handshake", '{"status": "error", "reason": "no_nvidia_gpu"}\n')
    with pytest.raises(RuntimeError, match="no_nvidia_gpu"):
        engine_module._WorkerProcess()
    assert _StubPopen.instances[-1].killed is True


@pytest.mark.asyncio
async def test_unlock_requires_locked_character(db):
    body = CharacterInput(
        name="Nova", gender="female", age_group="young", role="university student",
        hair="long black hair", eyes="brown eyes", top_color="yellow", top_item="sweater",
        bottom_color="light blue", bottom_item="jeans",
    )
    async with write_transaction(db):
        character = await library_service.create_character(db, body)
        with pytest.raises(ConflictError, match="not locked"):
            await library_service.unlock_character(db, character["id"])
        assert (await library_service.get_character_row(db, character["id"]))["status"] == "draft"
