"""Solo series, fresh config copies, single-presenter thumbnail and portable export."""
import json
from pathlib import Path

from backend.core.config import settings
from backend.db.database import Database
from backend.media import thumbnail_compose, thumbnail_service
from tests.test_explainer_video_props import approved_fixture
from tests.test_explainer_api import client, data  # noqa: F401
from tests.test_visuals_project_api import locked_character


def test_series_one_presenter_carries_mode_structure_and_keeps_episodes_separate(client):  # noqa: F811
    cid = locked_character("Hoang Series", "green")
    topic = data(client.post("/api/channel/topics", json={"name": "Knowledge"}))
    series = data(client.post(f"/api/channel/topics/{topic['id']}/series", json={"name": "Small habits", "cast": [cid],
        "presentation_mode": "solo_explainer", "explainer_structure": "how"}))
    assert series["presentation_mode"] == "solo_explainer"
    for title in ("Start small", "Keep going"):
        data(client.post(f"/api/channel/series/{series['id']}/episodes", json={"title": title}))
    projects = data(client.post(f"/api/channel/series/{series['id']}/projects"))["created"]
    assert len(projects) == 2 and projects[0]["project_id"] != projects[1]["project_id"]
    for item in projects:
        project = data(client.get(f"/api/projects/{item['project_id']}"))
        assert project["presentation_mode"] == "solo_explainer" and project["explainer_structure"] == "how"
        assert len(project["speakers"]) == 1 and project["speakers"][0]["character_id"] == cid
        assert data(client.get(f"/api/projects/{item['project_id']}/explainer-plan"))["plan"] is None


def test_copy_keeps_voice_and_front_identity_but_inherits_no_approval(client, monkeypatch):  # noqa: F811
    pid, cid, _ = approved_fixture(client, monkeypatch)
    source = data(client.get(f"/api/projects/{pid}"))
    copied = data(client.post(f"/api/projects/{pid}/copy-settings"))
    assert copied["id"] != pid and copied["status"] == "draft"
    assert copied["presentation_mode"] == source["presentation_mode"]
    assert copied["explainer_structure"] == source["explainer_structure"]
    assert copied["speakers"][0]["id"] != source["speakers"][0]["id"]
    for key in ("voice_id", "tts_engine", "speed", "pitch", "volume", "character_id"):
        assert copied["speakers"][0][key] == source["speakers"][0][key]
    assert copied["speakers"][0]["character_id"] == cid
    assert data(client.get(f"/api/projects/{copied['id']}/script")) == []
    assert data(client.get(f"/api/projects/{copied['id']}/explainer-plan"))["plan"] is None


def test_solo_thumbnail_uses_front_image_without_mirroring_and_export_pins_assets(client, monkeypatch, tmp_path):  # noqa: F811
    pid, cid, approved = approved_fixture(client, monkeypatch)
    project = data(client.get(f"/api/projects/{pid}"))
    inputs = client.portal.call(thumbnail_compose.composition_inputs, Database.instance().connection, project)
    assert len(inputs["characters"]) == 1 and not inputs["characters"][0]["mirror"]
    assert inputs["characters"][0]["front_pictures"]
    prompt = thumbnail_service.outside_prompt(project, inputs, [])
    assert len(prompt["pictures"]) == 1 and "/profiles/" in prompt["pictures"][0]["url"]
    assert "two friendly" not in prompt["prompt"]
    view = data(client.put(f"/api/projects/{pid}/export", json={"output_dir": str(tmp_path / "export"), "items": ["script"]}))
    folder = tmp_path / "export"
    exported = json.loads((folder / "explainer/plan.json").read_text(encoding="utf-8"))
    assert exported["revision"] == approved["revision"] and exported["status"] == "approved"
    assert str(settings.DATA_DIR) not in json.dumps(exported)
    assert len(list((folder / "explainer/front").glob("*.png"))) == 21
    assert "explainer/plan.json" in view["sync"]["written"]
    original = (folder / "explainer/plan.json").read_bytes()
    image = next(iter(inputs["characters"][0]["front_pictures"].values()))
    Path(image["path"]).write_bytes(b"changed after approval")
    failed = data(client.post(f"/api/projects/{pid}/export/sync"))
    assert "approved explainer image changed" in failed["error"]
    assert (folder / "explainer/plan.json").read_bytes() == original
