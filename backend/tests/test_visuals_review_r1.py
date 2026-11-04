"""PM review r1 fixes F2-F4 (Phase 20): stale shot rows, worker kill, unlock guard."""

import subprocess
import uuid

import pytest
from PIL import Image

from backend.core.config import settings
from backend.core.exceptions import ConflictError
from backend.db.transactions import write_transaction
from backend.schemas.project import ScriptConfig, SpeakerConfig
from backend.schemas.visuals import CharacterInput
from backend.content import project_service
from backend.ai.image import engine as engine_module
from backend.library import library_service, project_visuals_service


@pytest.fixture(autouse=True)
def fake_engine(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr(settings, "IMAGE_ENGINE", "fake")
    monkeypatch.setattr(settings, "AI_VISUALS_ENABLED", True)


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
