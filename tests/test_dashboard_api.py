"""Task 36.7 (D106-D108): the channel dashboard -- stats, today's actions, the roadmap, the board and the calendar."""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from backend.core.config import settings
from tests.test_channel_api import PLAN
from tests.test_visuals_project_api import client, data, locked_character  # noqa: F401


def _mark(project_id: str, *steps: str) -> None:
    """Pretend the project went through these steps (rows the step pages would write)."""
    with sqlite3.connect(settings.db_path) as connection:
        if "script" in steps:
            speaker = connection.execute("SELECT id FROM speakers WHERE project_id = ? LIMIT 1", (project_id,)).fetchone()[0]
            connection.execute("INSERT INTO script_lines (id, project_id, line_index, speaker_id, text) VALUES (?, ?, 0, ?, 'Hi')",
                               (f"line-{project_id}", project_id, speaker))
        if "learning" in steps:
            connection.execute("INSERT INTO learning_contents (id, project_id, created_at, updated_at) VALUES (?, ?, 'n', 'n')",
                               (f"learn-{project_id}", project_id))
        if "audio" in steps:
            connection.execute("INSERT INTO audio_jobs (id, project_id, status) VALUES (?, ?, 'complete')",
                               (f"audio-{project_id}", project_id))
        if "video" in steps:
            connection.execute("INSERT INTO video_jobs (id, project_id, status) VALUES (?, ?, 'complete')",
                               (f"video-{project_id}", project_id))
        if "thumbnail" in steps:
            connection.execute("INSERT INTO thumbnails (id, project_id, is_selected) VALUES (?, ?, 1)",
                               (f"thumb-{project_id}", project_id))
        if "youtube" in steps:
            connection.execute("INSERT INTO youtube_packages (id, project_id, created_at, updated_at) VALUES (?, ?, 'n', 'n')",
                               (f"yt-{project_id}", project_id))


def _board(result: dict) -> dict:
    return {column["key"]: [item["number"] for item in column["items"] if item["number"]] for column in result["board"]}


def test_an_empty_channel_starts_the_roadmap_at_identity_or_plan(client):  # noqa: F811
    result = data(client.get("/api/channel/dashboard"))
    assert result["stats"]["topics"] == 0 and result["next_publish"] is None
    stages = result["roadmap"]["stages"]
    assert [stage["key"] for stage in stages] == ["identity", "plan", "first10", "weekly", "grow"]
    current = stages[result["roadmap"]["current"]]
    assert current["key"] in ("identity", "plan") and result["roadmap"]["next"]["link"].startswith("/")
    assert stages[-1]["checks"][-1]["label"].startswith("Shorts")


def test_the_board_today_and_roadmap_follow_the_episodes(client):  # noqa: F811
    alex, lina = locked_character("Alex", "navy"), locked_character("Lina", "white")
    tree = data(client.post("/api/channel/plan/apply", json={"plan": PLAN, "cast": [alex, lina]}))
    series = tree["topics"][0]["series"][0]
    created = data(client.post(f"/api/channel/series/{series['id']}/projects"))["created"]
    first, second, third = (item["project_id"] for item in created)
    _mark(first, "script", "learning", "audio", "video", "thumbnail", "youtube")
    _mark(second, "script", "learning")
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    data(client.post("/api/channel/schedule", json={"start_date": tomorrow, "weekdays": list(range(7))}))

    result = data(client.get("/api/channel/dashboard"))
    board = _board(result)
    assert board["script"] == [3] and board["audio"] == [2] and board["published"] == [1]  # Ep. 1 is ready to publish
    card = next(item for item in result["board"][2]["items"] if item["number"] == 2)
    assert card["link"] == f"/step4?project_id={second}" and card["series"] == "Weekend Trip with Friends"
    assert result["stats"]["episodes"] == {"planned": 2, "created": 3, "published": 0} and result["stats"]["produced"] == 1
    assert result["next_publish"]["publish_date"] == tomorrow
    labels = [action["label"] for action in result["actions"]]
    assert any("Ep. 2" in label and "next step Audio" in label for label in labels)
    assert any("English at Work" not in label and "Choose the characters" not in label for label in labels)
    assert len(result["calendar"]) == 5  # every episode dated within two weeks (daily)
    plan_stage = result["roadmap"]["stages"][1]
    checks = {check["label"]: check["done"] for check in plan_stage["checks"]}
    assert checks["Every topic has a series"] and checks["Publishing dates planned"]
    assert not checks["Three topics (playlists)"] and not checks["Playlist links on the topics"]
    first10 = {check["label"]: check for check in result["roadmap"]["stages"][2]["checks"]}
    assert first10["First episode complete (video + YouTube package)"]["done"]
    assert first10["10 episodes produced"]["progress"] == "1/10"


def test_a_series_without_characters_and_pending_pictures_are_todays_actions(client):  # noqa: F811
    data(client.post("/api/channel/plan/apply", json={"plan": PLAN}))
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute("INSERT INTO activity_library (id, activity, path, content_sha, review_state, created_at, updated_at) "
                           "VALUES ('p1', 'cooking', 'x.png', 'sha-p1', 'pending', 'n', 'n')")
    labels = [action["label"] for action in data(client.get("/api/channel/dashboard"))["actions"]]
    assert "1 illustration waiting for your approval" in labels
    assert any(label.startswith("Choose the characters of 2 series") for label in labels)


def test_a_relative_data_path_is_read_under_the_current_data_folder(client, tmp_path):  # noqa: F811
    """Demo-recording finding: a copied data folder (or the packaged app) keeps `data\library\...` rows from the dev app."""
    from PIL import Image

    from backend.core.exceptions import NotFoundError
    from backend.library import library_service

    plate = settings.DATA_DIR / "library" / "scenes" / "s1" / "preview.png"
    plate.parent.mkdir(parents=True)
    Image.new("RGB", (8, 8)).save(plate)
    assert library_service.resolve_library_content("data/library/scenes/s1/preview.png", "library/scenes") == plate.resolve()
    import pytest

    with pytest.raises(NotFoundError):
        library_service.resolve_library_content("data/../../etc/passwd", "library/scenes")
