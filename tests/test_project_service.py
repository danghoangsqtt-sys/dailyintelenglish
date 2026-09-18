"""CRUD tests for ProjectService (ROADMAP Task 1.2)."""

import json

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.exceptions import ValidationError as AppValidationError
from app.models.project import ProjectUpdate, ScriptConfig, SpeakerConfig
from app.services import project_service


def make_config(**overrides) -> ScriptConfig:
    defaults = dict(
        name="Test Episode",
        topic="AI in daily life",
        cefr_level="B1",
        duration_minutes=8.0,
        num_speakers=2,
        genre="small_talk",
        accent="american",
        speakers=[
            SpeakerConfig(name="Alex", gender="male", accent="american"),
            SpeakerConfig(name="Sam", gender="female", accent="british"),
        ],
    )
    defaults.update(overrides)
    return ScriptConfig(**defaults)


async def test_create_project_persists_config_and_speakers(db):
    project = await project_service.create_project(db, make_config())

    assert project["name"] == "Test Episode"
    assert project["status"] == "draft"
    assert project["cefr_level"] == "B1"
    assert len(project["speakers"]) == 2
    assert project["speakers"][0]["name"] == "Alex"


async def test_list_projects_orders_by_most_recently_updated(db):
    first = await project_service.create_project(db, make_config(name="First"))
    second = await project_service.create_project(db, make_config(name="Second"))

    projects = await project_service.list_projects(db)

    assert [p["id"] for p in projects] == [second["id"], first["id"]]


async def test_get_project_missing_raises_not_found(db):
    with pytest.raises(NotFoundError):
        await project_service.get_project(db, "does-not-exist")


async def test_update_project_applies_partial_patch(db):
    project = await project_service.create_project(db, make_config())

    updated = await project_service.update_project(
        db, project["id"], ProjectUpdate(name="Renamed Episode", status="script_generated")
    )

    assert updated["name"] == "Renamed Episode"
    assert updated["status"] == "script_generated"
    assert updated["topic"] == project["topic"]
    assert updated["updated_at"] >= project["updated_at"]


async def test_update_project_missing_raises_not_found(db):
    with pytest.raises(NotFoundError):
        await project_service.update_project(db, "does-not-exist", ProjectUpdate(name="X"))


async def test_delete_project_removes_it_and_cascades_speakers(db):
    project = await project_service.create_project(db, make_config())

    await project_service.delete_project(db, project["id"])

    with pytest.raises(NotFoundError):
        await project_service.get_project(db, project["id"])

    cursor = await db.execute("SELECT COUNT(*) AS n FROM speakers WHERE project_id = ?", (project["id"],))
    row = await cursor.fetchone()
    assert row["n"] == 0


async def test_delete_project_missing_raises_not_found(db):
    with pytest.raises(NotFoundError):
        await project_service.delete_project(db, "does-not-exist")


async def test_cleanup_project_artifacts_removes_every_category_directory(monkeypatch, tmp_path):
    """Real bug found by PM audit 2026-09-14: delete_project only ever removed DB rows
    (cascade), never any of the 5 per-project data directories -- every deleted project
    permanently leaked its avatars/audio/video/thumbnails/tts_cache files."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    project_id = "proj-cleanup-1"
    for category in ("avatars", "audio", "video", "thumbnails", "tts_cache"):
        directory = tmp_path / category / project_id
        directory.mkdir(parents=True)
        (directory / "file.bin").write_bytes(b"data")

    await project_service.cleanup_project_artifacts(project_id)

    for category in ("avatars", "audio", "video", "thumbnails", "tts_cache"):
        assert not (tmp_path / category / project_id).exists()


async def test_cleanup_project_artifacts_is_a_noop_when_nothing_was_ever_generated(monkeypatch, tmp_path):
    """A project deleted before any avatar/audio/video/thumbnail/TTS work ever happened
    has no directories to remove -- must not raise."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)

    await project_service.cleanup_project_artifacts("never-generated-anything")


async def test_update_project_syncs_config_json_even_for_unrelated_field(db):
    project = await project_service.create_project(db, make_config())

    updated = await project_service.update_project(db, project["id"], ProjectUpdate(topic="New topic"))

    snapshot = json.loads(updated["config_json"])
    assert snapshot["topic"] == "New topic"
    assert snapshot["name"] == updated["name"]
    assert snapshot["num_speakers"] == 2
    assert len(snapshot["speakers"]) == 2
    assert snapshot["speakers"][0]["name"] == "Alex"


async def test_update_project_explicit_null_is_rejected(db):
    with pytest.raises(PydanticValidationError):
        ProjectUpdate(name=None)


async def test_update_project_num_speakers_alone_is_rejected(db):
    with pytest.raises(PydanticValidationError):
        ProjectUpdate(num_speakers=3)


async def test_update_project_num_speakers_and_speakers_mismatch_is_rejected(db):
    with pytest.raises(PydanticValidationError):
        ProjectUpdate(num_speakers=3, speakers=[SpeakerConfig(name="Only One")])


async def test_update_project_num_speakers_and_speakers_atomic_succeeds(db):
    project = await project_service.create_project(db, make_config())

    updated = await project_service.update_project(
        db,
        project["id"],
        ProjectUpdate(
            num_speakers=3,
            speakers=[
                SpeakerConfig(name="Alex", gender="male", accent="american"),
                SpeakerConfig(name="Sam", gender="female", accent="british"),
                SpeakerConfig(name="Jo", gender="neutral", accent="canadian"),
            ],
        ),
    )

    assert updated["num_speakers"] == 3
    assert [s["name"] for s in updated["speakers"]] == ["Alex", "Sam", "Jo"]
    snapshot = json.loads(updated["config_json"])
    assert snapshot["num_speakers"] == 3
    assert len(snapshot["speakers"]) == 3


async def test_status_transition_forward_one_step_succeeds(db):
    project = await project_service.create_project(db, make_config())

    updated = await project_service.update_project(
        db, project["id"], ProjectUpdate(status="script_generated")
    )

    assert updated["status"] == "script_generated"


async def test_status_transition_skip_is_rejected(db):
    project = await project_service.create_project(db, make_config())

    with pytest.raises(AppValidationError):
        await project_service.update_project(db, project["id"], ProjectUpdate(status="audio_generated"))


async def test_status_transition_backward_is_rejected(db):
    project = await project_service.create_project(db, make_config())
    await project_service.update_project(db, project["id"], ProjectUpdate(status="script_generated"))

    with pytest.raises(AppValidationError):
        await project_service.update_project(db, project["id"], ProjectUpdate(status="draft"))


async def test_status_transition_same_status_is_idempotent(db):
    project = await project_service.create_project(db, make_config())

    updated = await project_service.update_project(db, project["id"], ProjectUpdate(status="draft"))

    assert updated["status"] == "draft"


async def test_mark_script_changed_advances_draft_and_is_idempotent(db):
    project = await project_service.create_project(db, make_config())

    await project_service.mark_script_changed(db, project["id"])
    advanced = await project_service.get_project(db, project["id"])
    assert advanced["status"] == "script_generated"

    await project_service.mark_script_changed(db, project["id"])
    unchanged = await project_service.get_project(db, project["id"])
    assert unchanged["status"] == "script_generated"
    assert unchanged["updated_at"] == advanced["updated_at"]


@pytest.mark.parametrize("status", ["audio_generated", "video_generated", "complete"])
async def test_mark_script_changed_downgrades_later_statuses(db, status):
    project = await project_service.create_project(db, make_config())
    await db.execute("UPDATE projects SET status = ? WHERE id = ?", (status, project["id"]))
    await db.commit()

    await project_service.mark_script_changed(db, project["id"])

    updated = await project_service.get_project(db, project["id"])
    assert updated["status"] == "script_generated"


async def test_mark_script_changed_preserves_downstream_jobs_and_files(db, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    project = await project_service.create_project(db, make_config())
    audio_path = tmp_path / "audio" / project["id"] / "final.mp3"
    video_path = tmp_path / "video" / project["id"] / "final.mp4"
    audio_path.parent.mkdir(parents=True)
    video_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"existing-audio")
    video_path.write_bytes(b"existing-video")

    await db.execute("UPDATE projects SET status = 'complete' WHERE id = ?", (project["id"],))
    await db.execute(
        "INSERT INTO audio_jobs (id, project_id, status, mp3_path, duration_seconds) "
        "VALUES (?, ?, 'complete', ?, ?)",
        ("audio-job", project["id"], str(audio_path), 12.5),
    )
    await db.execute(
        "INSERT INTO video_jobs (id, project_id, status, mp4_path, background_image) "
        "VALUES (?, ?, 'complete', ?, ?)",
        ("video-job", project["id"], str(video_path), "midnight"),
    )
    await db.commit()

    audio_cursor = await db.execute(
        "SELECT * FROM audio_jobs WHERE project_id = ?", (project["id"],)
    )
    video_cursor = await db.execute(
        "SELECT * FROM video_jobs WHERE project_id = ?", (project["id"],)
    )
    audio_before = dict(await audio_cursor.fetchone())
    video_before = dict(await video_cursor.fetchone())

    await project_service.mark_script_changed(db, project["id"])

    audio_cursor = await db.execute(
        "SELECT * FROM audio_jobs WHERE project_id = ?", (project["id"],)
    )
    video_cursor = await db.execute(
        "SELECT * FROM video_jobs WHERE project_id = ?", (project["id"],)
    )
    audio_after = dict(await audio_cursor.fetchone())
    video_after = dict(await video_cursor.fetchone())
    assert (await project_service.get_project(db, project["id"]))["status"] == "script_generated"
    assert audio_after == audio_before
    assert video_after == video_before
    assert audio_path.read_bytes() == b"existing-audio"
    assert video_path.read_bytes() == b"existing-video"



def test_script_config_rejects_blank_strings():
    with pytest.raises(PydanticValidationError):
        make_config(name="   ")

    with pytest.raises(PydanticValidationError):
        make_config(topic="   ")

    with pytest.raises(PydanticValidationError):
        make_config(speakers=[SpeakerConfig(name="   ", gender="male", accent="american")])


def test_project_update_rejects_blank_strings():
    with pytest.raises(PydanticValidationError):
        ProjectUpdate(name="   ")

    with pytest.raises(PydanticValidationError):
        ProjectUpdate(topic="   ")


async def test_service_create_strips_whitespace(db):
    config = make_config(
        name="  Service Episode  ",
        topic="  Service Topic  ",
        speakers=[
            SpeakerConfig(name="  Alex  ", gender="male", accent="american"),
            SpeakerConfig(name="  Sam  ", gender="female", accent="british"),
        ],
    )
    project = await project_service.create_project(db, config)
    assert project["name"] == "Service Episode"
    assert project["topic"] == "Service Topic"
    assert project["speakers"][0]["name"] == "Alex"
    assert project["speakers"][1]["name"] == "Sam"
