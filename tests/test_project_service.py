"""CRUD tests for ProjectService (ROADMAP Task 1.2)."""

import json

import pytest
from pydantic import ValidationError as PydanticValidationError

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
