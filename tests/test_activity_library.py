"""Phase 32.6a contract tests for review-gated activity cutaway assets."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import aiosqlite
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from starlette.datastructures import UploadFile

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.main import app
from app.services.visuals import activity_library_service as activities

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "app" / "db" / "migrations"


def image_bytes(color: tuple[int, int, int]) -> bytes:
    content = BytesIO()
    Image.new("RGB", (1280, 720), color).save(content, format="PNG")
    return content.getvalue()


def image_upload(filename: str, color: tuple[int, int, int]) -> UploadFile:
    return UploadFile(BytesIO(image_bytes(color)), filename=filename)


async def seed_character(db: aiosqlite.Connection, character_id: str = "character-alex", name: str = "Alex") -> None:
    await db.execute(
        "INSERT INTO characters (id, name, gender, age_group, role, hair, eyes, top_color, top_item, "
        "bottom_color, bottom_item, status, base_seed, created_at, updated_at) "
        "VALUES (?, ?, 'male', 'adult', 'host', 'black', 'brown', 'navy', 'suit', "
        "'navy', 'trousers', 'locked', 1, 'now', 'now')",
        (character_id, name),
    )


async def seed_project(db: aiosqlite.Connection, project_id: str = "project-activity") -> None:
    await db.execute(
        "INSERT INTO projects (id, name, created_at, updated_at) VALUES (?, 'Activity test', 'now', 'now')",
        (project_id,),
    )


@pytest.mark.asyncio
async def test_generic_inbox_import_starts_pending_and_keeps_metadata(db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    inbox = activities.inbox_dir()
    inbox.mkdir(parents=True)
    Image.new("RGB", (1280, 720), (20, 40, 60)).save(inbox / "generic__cooking__kitchen__01.png")

    result = await activities.import_inbox(db)
    assert result["rejected"] == [] and len(result["imported"]) == 1
    rows = await activities.list_activities(db)
    assert rows[0]["review_state"] == "pending"
    assert rows[0]["character_id"] is None
    assert rows[0]["activity"] == "cooking"
    assert rows[0]["context_tags"] == ["kitchen"]
    assert await activities.list_activities(db, review_state="approved") == []
    assert (await activities.content_path(db, rows[0]["id"])).is_file()


@pytest.mark.asyncio
async def test_import_inbox_recursively_accepts_scope_folders(db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    picture = activities.inbox_dir() / "generic" / "generic__doing-laundry__laundry-room__01.png"
    picture.parent.mkdir(parents=True)
    Image.new("RGB", (1280, 720), (80, 90, 100)).save(picture)

    result = await activities.import_inbox(db)

    assert result["rejected"] == [] and result["imported"][0]["file"] == picture.name
    rows = await activities.list_activities(db)
    assert rows[0]["activity"] == "doing laundry"
    assert rows[0]["context_tags"] == ["laundry room"]


@pytest.mark.asyncio
async def test_direct_upload_uses_form_metadata_and_starts_pending(db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)

    created = await activities.upload_activity(
        db,
        image_upload("friendly-name.png", (30, 70, 110)),
        {
            "character_id": None,
            "activity": "Chopping Vegetables",
            "context_tags": ["Kitchen", "Cooking"],
            "aliases": ["chop", "dice"],
            "variant": "01",
        },
    )

    assert created["review_state"] == "pending"
    assert created["activity"] == "chopping vegetables"
    assert created["context_tags"] == ["kitchen", "cooking"]
    assert created["aliases"] == ["chop", "dice"]
    assert created["character_id"] is None
    assert (await activities.content_path(db, created["id"])).is_file()


@pytest.mark.asyncio
async def test_invalid_or_duplicate_inbox_file_is_not_imported_twice(db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    inbox = activities.inbox_dir()
    inbox.mkdir(parents=True)
    picture = inbox / "generic__reading.png"
    Image.new("RGB", (1280, 720), (1, 2, 3)).save(picture)
    assert len((await activities.import_inbox(db))["imported"]) == 1
    second = await activities.import_inbox(db)
    assert second["imported"] == []
    assert "identical image" in second["rejected"][0]["reason"]
    (inbox / "generic__broken.png").write_text("not an image", encoding="utf-8")
    rejected = await activities.import_inbox(db)
    assert any("not a readable image" in item["reason"] for item in rejected["rejected"])


@pytest.mark.asyncio
async def test_character_scope_import_and_unknown_scope_remains_recoverable(db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    await seed_character(db)
    inbox = activities.inbox_dir()
    inbox.mkdir(parents=True)
    accepted = inbox / "alex__turning-left__city-street__01.png"
    unknown = inbox / "sam__turning-right__city-street__01.png"
    Image.new("RGB", (1280, 720), (10, 20, 30)).save(accepted)
    Image.new("RGB", (1280, 720), (40, 50, 60)).save(unknown)

    result = await activities.import_inbox(db)

    assert [item["file"] for item in result["imported"]] == [accepted.name]
    assert result["rejected"] == [{"file": unknown.name, "reason": "filename names an unknown character scope"}]
    assert unknown.is_file()
    row = (await activities.list_activities(db))[0]
    assert row["character_id"] == "character-alex"
    assert row["character_name"] == "Alex"
    assert row["activity"] == "turning left"
    assert row["context_tags"] == ["city street"]


@pytest.mark.asyncio
async def test_metadata_review_matching_and_safe_content_contract(db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    await seed_character(db)
    created = await activities.upload_activity(
        db,
        image_upload("alex-turning.png", (70, 80, 90)),
        {"character_id": "character-alex", "activity": "Turn Left", "context_tags": ["City Street"]},
    )

    assert await activities.approved_candidates(db) == []
    with pytest.raises(ValidationError, match="character_id does not exist"):
        await activities.update_metadata(db, created["id"], {"character_id": "missing"})
    with pytest.raises(ValidationError, match="activity is required"):
        await activities.update_metadata(db, created["id"], {"activity": "---"})
    with pytest.raises(ValidationError, match="review_state"):
        await activities.set_review(db, created["id"], "published")

    edited = await activities.update_metadata(
        db, created["id"], {"activity": "Turning Left", "aliases": ["Turn left", "Make a left"]},
    )
    assert edited["activity"] == "turning left"
    assert edited["aliases"] == ["turn left", "make a left"]
    approved = await activities.set_review(db, created["id"], "approved")
    assert approved["review_state"] == "approved"
    assert [row["id"] for row in await activities.approved_candidates(db)] == [created["id"]]
    assert await activities.set_review(db, created["id"], "rejected")
    assert await activities.approved_candidates(db) == []

    outside = tmp_path.parent / "outside-activity.png"
    Image.new("RGB", (1280, 720), (100, 110, 120)).save(outside)
    await db.execute("UPDATE activity_library SET path = ? WHERE id = ?", (str(outside), created["id"]))
    with pytest.raises(NotFoundError, match="file not found"):
        await activities.content_path(db, created["id"])


@pytest.mark.asyncio
async def test_usage_requires_approval_and_updates_history_and_counters(db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    await seed_project(db)
    created = await activities.upload_activity(
        db, image_upload("crossing.png", (130, 140, 150)),
        {"activity": "crossing the street", "context_tags": ["city"]},
    )
    with pytest.raises(ConflictError, match="approved"):
        await activities.record_usage(db, created["id"], "project-activity", "beat-1", "render-1")

    await activities.set_review(db, created["id"], "approved")
    await activities.record_usage(db, created["id"], "project-activity", "beat-1", "render-1")
    await activities.record_usage(db, created["id"], "project-activity", "beat-2", "render-2")

    row = (await activities.list_activities(db))[0]
    history = await activities.history(db, created["id"])
    assert row["use_count"] == 2 and row["last_used_at"]
    assert {(item["beat_id"], item["render_id"]) for item in history} == {
        ("beat-1", "render-1"), ("beat-2", "render-2"),
    }


@pytest.mark.asyncio
async def test_metadata_review_and_usage_survive_database_reopen(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    database_path = tmp_path / "reopen.db"
    db = await aiosqlite.connect(database_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
        await db.executescript(migration.read_text(encoding="utf-8"))
    await seed_project(db)
    created = await activities.upload_activity(
        db, image_upload("packing.png", (160, 170, 180)),
        {"activity": "Pack a Suitcase", "context_tags": ["Travel"], "aliases": ["Pack luggage"]},
    )
    await activities.set_review(db, created["id"], "approved")
    await activities.record_usage(db, created["id"], "project-activity", "beat-pack", "render-pack")
    await db.commit()
    await db.close()

    reopened = await aiosqlite.connect(database_path)
    reopened.row_factory = aiosqlite.Row
    rows = await activities.list_activities(reopened)
    history = await activities.history(reopened, created["id"])
    await reopened.close()

    assert rows[0]["review_state"] == "approved"
    assert rows[0]["activity"] == "pack a suitcase"
    assert rows[0]["context_tags"] == ["travel"]
    assert rows[0]["aliases"] == ["pack luggage"]
    assert rows[0]["use_count"] == 1
    assert history[0]["beat_id"] == "beat-pack" and history[0]["render_id"] == "render-pack"


def test_activity_library_api_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with TestClient(app) as client:
        response = client.post(
            "/api/visuals/library/activities/upload",
            files={"file": ("directions.png", image_bytes((190, 200, 210)), "image/png")},
            data={"activity": "Go Straight", "context_tags": "City, Street", "aliases": "Continue straight"},
        )
        assert response.status_code == 201, response.text
        created = response.json()["data"]
        activity_id = created["id"]
        assert created["review_state"] == "pending"

        listed = client.get("/api/visuals/library/activities", params={"review_state": "pending"})
        assert listed.status_code == 200 and listed.json()["data"][0]["id"] == activity_id
        edited = client.patch(
            f"/api/visuals/library/activities/{activity_id}",
            json={"activity": "Walking Straight", "aliases": ["go straight", "continue straight"]},
        )
        assert edited.status_code == 200 and edited.json()["data"]["activity"] == "walking straight"
        approved = client.patch(
            f"/api/visuals/library/activities/{activity_id}/review", json={"review_state": "approved"},
        )
        assert approved.status_code == 200 and approved.json()["data"]["review_state"] == "approved"
        assert client.get(f"/api/visuals/library/activities/{activity_id}/content").status_code == 200
        history = client.get(f"/api/visuals/library/activities/{activity_id}/history")
        assert history.status_code == 200 and history.json()["data"] == []


def test_batch_upload_uses_separate_owner_names_and_stays_pending(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with TestClient(app) as client:
        response = client.post(
            "/api/visuals/library/activities/upload-batch",
            files=[
                ("files", ("east.png", image_bytes((180, 30, 30)), "image/png")),
                ("files", ("west.png", image_bytes((30, 30, 180)), "image/png")),
            ],
            data={"metadata_json": '[{"activity":"Go East","context_tags":["city"],'
                                   '"aliases":["head east"]},{"activity":"Go West",'
                                   '"context_tags":["waterfront"],"aliases":["head west"]}]'},
        )
        assert response.status_code == 201, response.text
        rows = response.json()["data"]["items"]
        assert response.json()["data"]["rejected"] == []
        assert [(row["activity"], row["aliases"], row["review_state"]) for row in rows] == [
            ("go east", ["head east"], "pending"),
            ("go west", ["head west"], "pending"),
        ]
        assert client.post("/api/visuals/library/activities/smart-upload").status_code == 405


def test_batch_upload_rejects_missing_or_misaligned_names_without_saving(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with TestClient(app) as client:
        files = [("files", ("east.png", image_bytes((60, 90, 120)), "image/png"))]
        for metadata_json in ('[]', '[{"activity":"   "}]', 'not json'):
            response = client.post(
                "/api/visuals/library/activities/upload-batch",
                files=files,
                data={"metadata_json": metadata_json},
            )
            assert response.status_code == 422, response.text
        assert client.get("/api/visuals/library/activities").json()["data"] == []


def test_batch_approval_is_explicit_pending_only_and_atomic(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with TestClient(app) as client:
        created = client.post(
            "/api/visuals/library/activities/upload-batch",
            files=[
                ("files", ("east.png", image_bytes((30, 60, 90)), "image/png")),
                ("files", ("west.png", image_bytes((90, 60, 30)), "image/png")),
                ("files", ("left.png", image_bytes((60, 90, 30)), "image/png")),
            ],
            data={"metadata_json": '[{"activity":"go east"},{"activity":"go west"},{"activity":"turn left"}]'},
        )
        assert created.status_code == 201, created.text
        east, west, left = [row["id"] for row in created.json()["data"]["items"]]
        rejected = client.patch(
            f"/api/visuals/library/activities/{left}/review", json={"review_state": "rejected"},
        )
        assert rejected.status_code == 200
        endpoint = "/api/visuals/library/activities/approve-batch"
        assert client.post(endpoint, json={"ids": [east, east]}).status_code == 422
        assert client.post(endpoint, json={"ids": [east, left]}).status_code == 409
        pending = client.get("/api/visuals/library/activities", params={"review_state": "pending"})
        assert {row["id"] for row in pending.json()["data"]} == {east, west}
        response = client.post(endpoint, json={"ids": [east, west]})
        assert response.status_code == 200, response.text
        assert response.json()["data"] == {"approved": 2}
        assert client.post(endpoint, json={"ids": [east]}).status_code == 409
        approved = client.get("/api/visuals/library/activities", params={"review_state": "approved"})
        assert {row["id"] for row in approved.json()["data"]} == {east, west}


def test_delete_activity_removes_record_and_file(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with TestClient(app) as client:
        response = client.post(
            "/api/visuals/library/activities/upload",
            files={"file": ("east.png", image_bytes((20, 80, 140)), "image/png")},
            data={"activity": "go east"},
        )
        assert response.status_code == 201, response.text
        activity_id = response.json()["data"]["id"]
        stored = activities.activities_dir() / f"{activity_id}.png"
        assert stored.is_file()
        assert client.patch(
            f"/api/visuals/library/activities/{activity_id}/review", json={"review_state": "approved"},
        ).status_code == 200
        deleted = client.delete(f"/api/visuals/library/activities/{activity_id}")
        assert deleted.status_code == 200, deleted.text
        assert deleted.json()["data"] == {"deleted": activity_id, "file_removed": True}
        assert not stored.exists()
        assert client.get(f"/api/visuals/library/activities/{activity_id}/content").status_code == 404
        assert client.delete(f"/api/visuals/library/activities/{activity_id}").status_code == 404
        assert client.get("/api/visuals/library/activities").json()["data"] == []


def test_delete_activity_reports_a_file_cleanup_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with TestClient(app) as client:
        response = client.post(
            "/api/visuals/library/activities/upload",
            files={"file": ("locked.png", image_bytes((140, 80, 20)), "image/png")},
            data={"activity": "turn right"},
        )
        activity_id = response.json()["data"]["id"]
        stored = activities.activities_dir() / f"{activity_id}.png"
        original_unlink = Path.unlink

        def fail_stored_unlink(path: Path, missing_ok: bool = False) -> None:
            if path == stored:
                raise PermissionError("file in use")
            original_unlink(path, missing_ok=missing_ok)

        with monkeypatch.context() as patch:
            patch.setattr(Path, "unlink", fail_stored_unlink)
            deleted = client.delete(f"/api/visuals/library/activities/{activity_id}")
        assert deleted.status_code == 200
        assert deleted.json()["data"] == {"deleted": activity_id, "file_removed": False}
        assert stored.is_file()
        assert client.get("/api/visuals/library/activities").json()["data"] == []


@pytest.mark.asyncio
async def test_delete_activity_refuses_a_path_outside_the_library(db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    created = await activities.upload_activity(
        db, image_upload("inside.png", (100, 80, 60)), {"activity": "walk"},
    )
    outside = tmp_path / "outside.png"
    outside.write_bytes(image_bytes((60, 80, 100)))
    await db.execute("UPDATE activity_library SET path = ? WHERE id = ?", (str(outside), created["id"]))
    with pytest.raises(ValidationError, match="outside the library"):
        await activities.delete_activity(db, created["id"])
    assert outside.is_file()
    assert len(await activities.list_activities(db)) == 1


@pytest.mark.asyncio
async def test_delete_used_activity_cascades_only_its_history(db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    await seed_project(db)
    used = await activities.upload_activity(
        db, image_upload("used.png", (20, 50, 80)), {"activity": "go east"},
    )
    kept = await activities.upload_activity(
        db, image_upload("kept.png", (80, 50, 20)), {"activity": "go west"},
    )
    await activities.set_review(db, used["id"], "approved")
    await activities.record_usage(db, used["id"], "project-activity", "beat-east", "render-1")
    assert len(await activities.history(db, used["id"])) == 1
    await activities.delete_activity(db, used["id"])
    await db.commit()
    cursor = await db.execute("SELECT COUNT(*) FROM activity_library_usage WHERE activity_id = ?", (used["id"],))
    assert (await cursor.fetchone())[0] == 0
    assert (await activities.content_path(db, kept["id"])).is_file()
