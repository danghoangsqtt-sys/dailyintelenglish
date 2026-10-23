"""Phase 73: archives preserve history while new selections use active scenes."""

import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from backend.core.config import settings
from backend.core.exceptions import ValidationError
from backend.library import explainer_stage, library_service as library
from backend.media.video_renderer_remotion import _resolve_still_plate
from backend.schemas.visuals import SceneInput


async def _project(db, project_id):
    await db.execute(
        "INSERT INTO projects (id, name, created_at, updated_at) VALUES (?, ?, 'now', 'now')",
        (project_id, project_id),
    )


async def _scene(db, name):
    return await library.create_scene(db, SceneInput(name=name, place="a quiet library", staging="standing"))


async def _reference(db, project_id, scene_id, source):
    plan = json.dumps({"segments": [{"scene": {"scene_id": scene_id}}]})
    if source == "shortlist":
        await db.execute("INSERT INTO project_scenes VALUES (?, 0, ?)", (project_id, scene_id))
    elif source == "beat":
        await db.execute(
            "INSERT INTO project_beats (id, project_id, position, line_from, line_to, kind, scene_id, created_at, updated_at) "
            "VALUES (?, ?, 0, 0, 0, 'scene', ?, 'now', 'now')", (f"beat-{project_id}", project_id, scene_id),
        )
    elif source == "version":
        await db.execute(
            "INSERT INTO project_explainer_plan_versions VALUES (?, 1, ?, ?, 'now')", (project_id, "a" * 64, plan),
        )
    else:
        snapshot = None
        if source == "snapshot":
            snapshot = json.dumps({"plan": json.loads(plan)})
        elif source == "stage":
            snapshot = json.dumps({"stage": {"scenes": [{"id": scene_id}]}})
        await db.execute(
            "INSERT INTO project_explainer_plans "
            "(project_id, revision, status, source_fingerprint, plan_json, approved_snapshot_json, updated_at) "
            "VALUES (?, 1, 'draft', ?, ?, ?, 'now')",
            (project_id, "a" * 64, plan if source == "plan" else '{"segments": []}', snapshot),
        )


def test_migration_preserves_existing_scene_plate_and_references():
    migrations = Path(__file__).resolve().parents[1] / "backend/db/migrations"
    with sqlite3.connect(":memory:") as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        for path in sorted(migrations.glob("*.sql")):
            if path.name < "037_scene_archive.sql":
                connection.executescript(path.read_text(encoding="utf-8"))
        connection.executescript("""
            INSERT INTO projects (id, name, created_at, updated_at) VALUES ('p', 'Old', 'then', 'then');
            INSERT INTO scenes (id, name, place, staging, preview_path, created_at, updated_at)
                VALUES ('s', 'Old scene', 'a quiet room', 'standing', 'plate.png', 'then', 'then');
            INSERT INTO project_scenes VALUES ('p', 0, 's');
            INSERT INTO project_beats
                (id, project_id, position, line_from, line_to, kind, scene_id, created_at, updated_at)
                VALUES ('b', 'p', 0, 0, 1, 'scene', 's', 'then', 'then');
        """)
        connection.executescript((migrations / "037_scene_archive.sql").read_text(encoding="utf-8"))
        assert connection.execute("SELECT archived_at, preview_path, updated_at FROM scenes").fetchone() == (
            None, "plate.png", "then")
        assert connection.execute("SELECT scene_id FROM project_scenes").fetchone() == ("s",)
        assert connection.execute("SELECT scene_id FROM project_beats").fetchone() == ("s",)
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


@pytest.mark.parametrize("source", ["shortlist", "beat", "plan", "version", "snapshot", "stage"])
async def test_historical_visibility_and_usage_across_reference_sources(db, source):
    await _project(db, "owner")
    await _project(db, "other")
    active = await _scene(db, "Active")
    archived = await _scene(db, "Archived")
    unrelated = await _scene(db, "Unrelated")
    await _reference(db, "owner", archived["id"], source)
    await library.archive_scene(db, archived["id"])
    await library.archive_scene(db, unrelated["id"])
    assert [scene["id"] for scene in await library.list_scenes(db)] == [active["id"]]
    historical = {scene["id"]: scene for scene in await library.list_scenes(db, project_id="owner")}
    assert set(historical) == {active["id"], archived["id"]}
    assert historical[archived["id"]]["used_count"] == 1
    assert await library.project_scene_ids(db, "owner") == {archived["id"]}
    assert [scene["id"] for scene in await library.list_scenes(db, project_id="other")] == [active["id"]]
    all_scenes = await library.list_scenes(db, include_archived=True, project_id="other")
    assert {scene["id"] for scene in all_scenes} == {active["id"], archived["id"], unrelated["id"]}


async def test_used_count_deduplicates_projects_and_tracks_project_deletion(db):
    scene = await _scene(db, "Shared")
    for project_id in ("one", "two"):
        await _project(db, project_id)
    for source in ("shortlist", "beat", "plan", "version"):
        await _reference(db, "one", scene["id"], source)
    await _reference(db, "two", scene["id"], "beat")
    assert (await library.list_scenes(db))[0]["used_count"] == 2
    await db.execute("DELETE FROM projects WHERE id = 'one'")
    assert (await library.list_scenes(db))[0]["used_count"] == 1


async def test_explainer_choices_hide_archive_but_references_and_versions_stay_stable(db):
    scene = await _scene(db, "Stage")
    await db.execute("UPDATE scenes SET preview_path = 'plate.png' WHERE id = ?", (scene["id"],))
    segment = SimpleNamespace(scene=SimpleNamespace(scene_id=scene["id"]), visual=SimpleNamespace(kind="none"))
    before = await explainer_stage.references(db, [segment], "presenter")
    assert [item["id"] for item in (await explainer_stage.choices(db, "presenter"))["scenes"]] == [scene["id"]]
    await library.archive_scene(db, scene["id"])
    assert (await explainer_stage.choices(db, "presenter"))["scenes"] == []
    assert await explainer_stage.references(db, [segment], "presenter") == before
    await library.restore_scene(db, scene["id"])
    assert await explainer_stage.references(db, [segment], "presenter") == before
    assert len((await explainer_stage.choices(db, "presenter"))["scenes"]) == 1


async def test_still_render_preserves_archived_project_shortlist_and_filters_global_fallback(db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    await _project(db, "old-project")
    await _project(db, "new-project")
    archived = await _scene(db, "Archived plate")
    active = await _scene(db, "Active plate")
    paths = {}
    for scene in (archived, active):
        path = tmp_path / "library/scenes" / f"{scene['id']}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (8, 8), "blue").save(path)
        await db.execute("UPDATE scenes SET preview_path = ? WHERE id = ?", (str(path), scene["id"]))
        paths[scene["id"]] = path.resolve()
    await _reference(db, "old-project", archived["id"], "shortlist")
    await library.archive_scene(db, archived["id"])
    assert await _resolve_still_plate(db, "old-project", None) == paths[archived["id"]]
    assert await _resolve_still_plate(db, "new-project", None) == paths[active["id"]]
    assert await _resolve_still_plate(db, "old-project", archived["id"]) == paths[archived["id"]]
    await library.archive_scene(db, active["id"])
    with pytest.raises(ValidationError, match="Activity Library → Scenes"):
        await _resolve_still_plate(db, "new-project", None)
    assert await _resolve_still_plate(db, "old-project", None) == paths[archived["id"]]
