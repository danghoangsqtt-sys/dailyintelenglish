from __future__ import annotations

import sqlite3
from pathlib import Path

from backend.content import export_service
from backend.core.config import settings
from tests.test_phase40_character_names import _project
from tests.test_phase41_export import _episode
from tests.test_visuals_project_api import client, data  # noqa: F401


def test_new_hierarchy_uses_channel_topic_series_and_episode_title(client, tmp_path):  # noqa: F811
    project = _project(client)
    _episode(project["id"], 2, "Shopping at the Market")
    root = tmp_path / "Videos"

    view = data(client.put(f"/api/projects/{project['id']}/export", json={
        "output_dir": str(root), "items": ["script"], "layout_mode": "topic_hierarchy",
    }))

    expected = root / "Food" / "The Dinner Party Challenge" / "Ep 02 - Shopping at the Market"
    assert view["settings"]["layout_mode"] == "topic_hierarchy"
    assert view["folder"] == str(expected)
    assert view["sync"]["folder"] == str(expected)
    assert (expected / "script.txt").is_file()


def test_standalone_topics_share_a_suggested_root_but_use_project_name_for_video(client, tmp_path):  # noqa: F811
    first = _project(client)
    root = tmp_path / "Videos"
    data(client.put(f"/api/projects/{first['id']}/export", json={
        "output_dir": str(root), "items": ["script"], "layout_mode": "topic_hierarchy",
    }))

    second = _project(client)
    suggested = data(client.get(f"/api/projects/{second['id']}/export"))
    assert suggested["suggested_dir"] == str(root)
    assert suggested["layout_mode"] == "topic_hierarchy"
    saved = data(client.put(f"/api/projects/{second['id']}/export", json={
        "output_dir": suggested["suggested_dir"], "items": ["script"], "layout_mode": suggested["layout_mode"],
    }))
    assert saved["folder"].startswith(str(root / "Meeting the neighbours" / "Names - "))
    assert (tmp_path / "Videos" / "Meeting the neighbours").is_dir()


def test_preview_returns_hierarchy_without_creating_the_destination(client, tmp_path):  # noqa: F811
    project = _project(client)
    root = tmp_path / "Preview only"
    view = data(client.post(f"/api/projects/{project['id']}/export/preview", json={
        "output_dir": str(root), "items": [], "layout_mode": "topic_hierarchy",
    }))
    assert view["folder"] == str(root / "Meeting the neighbours" / "Names")
    assert not root.exists()


def test_existing_export_defaults_to_legacy_and_opt_in_leaves_old_files(client, tmp_path):  # noqa: F811
    project = _project(client)
    old_folder = tmp_path / "Old export"
    legacy = data(client.put(f"/api/projects/{project['id']}/export", json={
        "output_dir": str(old_folder), "items": ["script"],
    }))
    assert legacy["settings"]["layout_mode"] == "legacy"
    assert legacy["folder"] == str(old_folder)
    old_script = old_folder / "script.txt"
    assert old_script.is_file()

    new_root = tmp_path / "New root"
    hierarchical = data(client.put(f"/api/projects/{project['id']}/export", json={
        "output_dir": str(new_root), "items": ["script"], "layout_mode": "topic_hierarchy",
    }))
    assert hierarchical["folder"] == str(new_root / "Meeting the neighbours" / "Names")
    assert old_script.is_file()
    assert (new_root / "Meeting the neighbours" / "Names" / "script.txt").is_file()


def test_duplicate_series_labels_get_stable_distinct_folders(client, tmp_path):  # noqa: F811
    first, second = _project(client), _project(client)
    now = "2026-10-14T00:00:00+00:00"
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute("INSERT OR IGNORE INTO channel_topics (id, name, created_at, updated_at) VALUES ('t1', 'Food', ?, ?)",
                           (now, now))
        for series_id in ("same-a", "same-b"):
            connection.execute("INSERT INTO channel_series (id, topic_id, name, created_at, updated_at) "
                               "VALUES (?, 't1', 'The Dinner Party Challenge', ?, ?)", (series_id, now, now))
        connection.execute("INSERT INTO channel_episodes (id, series_id, number, title, project_id, created_at, updated_at) "
                           "VALUES ('episode-a', 'same-a', 1, 'Same video', ?, ?, ?)", (first["id"], now, now))
        connection.execute("INSERT INTO channel_episodes (id, series_id, number, title, project_id, created_at, updated_at) "
                           "VALUES ('episode-b', 'same-b', 1, 'Same video', ?, ?, ?)", (second["id"], now, now))
    root = tmp_path / "Videos"

    first_view = data(client.put(f"/api/projects/{first['id']}/export", json={
        "output_dir": str(root), "items": ["script"], "layout_mode": "topic_hierarchy",
    }))
    second_view = data(client.put(f"/api/projects/{second['id']}/export", json={
        "output_dir": str(root), "items": ["script"], "layout_mode": "topic_hierarchy",
    }))

    assert first_view["folder"] != second_view["folder"]
    assert data(client.get(f"/api/projects/{first['id']}/export"))["folder"] == first_view["folder"]
    assert (tmp_path / "Videos" / "Food").is_dir()


def test_safe_components_handle_windows_reserved_names_and_invalid_characters():
    assert export_service._safe_component('A/B: C?*.', "fallback") == "A B C"
    assert export_service._safe_component("CON", "fallback").startswith("_")
    assert len(export_service._safe_component("x" * 200, "fallback")) == 80


def test_migration_adds_legacy_mode_without_changing_existing_export_rows():
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        "CREATE TABLE project_exports (project_id TEXT PRIMARY KEY, output_dir TEXT NOT NULL, "
        "items_json TEXT NOT NULL DEFAULT '[]', last_sync_at TEXT, last_error TEXT, updated_at TEXT NOT NULL); "
        "INSERT INTO project_exports (project_id, output_dir, items_json, updated_at) "
        "VALUES ('old-project', 'C:/old', '[\"script\"]', 'old-time');"
    )
    migration = Path(__file__).resolve().parents[1] / "backend" / "db" / "migrations" / "039_topic_export_roots.sql"
    connection.executescript(migration.read_text(encoding="utf-8"))
    row = connection.execute("SELECT output_dir, items_json, updated_at, layout_mode, relative_dir "
                             "FROM project_exports WHERE project_id = 'old-project'").fetchone()
    assert row == ("C:/old", '["script"]', "old-time", "legacy", "")
    connection.close()
