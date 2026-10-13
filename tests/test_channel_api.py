"""Task 36.5 (D103-D105): the channel plan -- topics -> series -> episodes, the AI map, projects and the calendar."""

from __future__ import annotations

import json
from datetime import date

import pytest

from backend.channel import channel_service
from backend.ai.llm.contracts import AIMode, GenerationResult
from backend.ai.llm.fake_provider import FakeProvider
from backend.ai.llm.router import AIRouter
from tests.test_visuals_project_api import client, data, locked_character  # noqa: F401

PLAN = {"topics": [
    {"name": "Travel English", "description": "Trips, airports and hotels.", "series": [
        {"name": "Weekend Trip with Friends", "description": "Three friends plan a trip.", "genre": "small_talk",
         "cefr_level": "B1", "episodes": [{"title": "Planning the Trip", "brief": "They choose a place."},
                                          {"title": "Booking a Cabin", "brief": "Prices and dates."},
                                          {"title": "Packing Day", "brief": "What to bring."}]}]},
    {"name": "English at Work", "description": "Meetings and emails.", "series": [
        {"name": "First Week at the Office", "description": "A new job.", "genre": "interview", "cefr_level": "B2",
         "episodes": [{"title": "Meeting the Team", "brief": "Introductions."},
                      {"title": "The First Meeting", "brief": "Agendas."}]}]},
]}


def failed(response, status=422):
    assert response.status_code == status, response.text
    return response.json()["error"]


def test_a_plan_is_applied_as_a_tree_and_merges_an_existing_topic(client):  # noqa: F811
    tree = data(client.post("/api/channel/plan/apply", json={"plan": PLAN}))
    assert [topic["name"] for topic in tree["topics"]] == ["Travel English", "English at Work"]
    series = tree["topics"][0]["series"][0]
    assert [episode["number"] for episode in series["episodes"]] == [1, 2, 3]
    assert tree["counts"] == {"planned": 5, "created": 0, "published": 0} and tree["episodes"] == 5
    again = {"topics": [{**PLAN["topics"][0], "name": "travel english", "series": [
        {**PLAN["topics"][0]["series"][0], "name": "At the Airport"}]}]}
    tree = data(client.post("/api/channel/plan/apply", json={"plan": again}))
    assert len(tree["topics"]) == 2 and [s["name"] for s in tree["topics"][0]["series"]] == [
        "Weekend Trip with Friends", "At the Airport"]


def test_topics_series_and_episodes_are_edited_and_episodes_stay_numbered(client):  # noqa: F811
    topic = data(client.post("/api/channel/topics", json={"name": "Daily Life"}))
    data(client.patch(f"/api/channel/topics/{topic['id']}", json={"playlist_url": "https://youtube.com/playlist?list=A"}))
    failed(client.patch(f"/api/channel/topics/{topic['id']}", json={"playlist_url": "not a link"}))
    series = data(client.post(f"/api/channel/topics/{topic['id']}/series",
                              json={"name": "Morning Routines", "genre": "Small Talk", "cefr_level": "a2"}))
    assert (series["genre"], series["cefr_level"]) == ("small_talk", "A2")
    ids = [data(client.post(f"/api/channel/series/{series['id']}/episodes", json={"title": f"Ep {n}"}))["id"]
           for n in range(1, 5)]
    data(client.delete(f"/api/channel/episodes/{ids[1]}"))
    episodes = data(client.get("/api/channel"))["topics"][0]["series"][0]["episodes"]
    assert [(episode["number"], episode["title"]) for episode in episodes] == [(1, "Ep 1"), (2, "Ep 3"), (3, "Ep 4")]
    assert "project first" in failed(client.patch(f"/api/channel/episodes/{ids[0]}", json={"status": "created"}))
    failed(client.post(f"/api/channel/topics/{topic['id']}/series", json={"name": "X", "cast": ["missing"]}), 404)


def test_a_series_makes_its_numbered_projects_with_its_cast(client):  # noqa: F811
    alex, lina = locked_character("Alex", "navy"), locked_character("Lina", "white")
    tree = data(client.post("/api/channel/plan/apply", json={"plan": PLAN, "cast": [alex, lina]}))
    series = tree["topics"][0]["series"][0]
    assert series["cast"] == [alex, lina]
    created = data(client.post(f"/api/channel/series/{series['id']}/projects"))["created"]
    assert [item["number"] for item in created] == [1, 2, 3]
    project = data(client.get(f"/api/projects/{created[1]['project_id']}"))
    assert project["name"] == "Weekend Trip with Friends · Ep. 2: Booking a Cabin"
    assert project["cefr_level"] == "B1" and project["genre"] == "small_talk" and "Prices and dates" in project["topic"]
    assert [speaker["name"] for speaker in project["speakers"]] == ["Alex", "Lina"]
    cast = data(client.get(f"/api/projects/{created[1]['project_id']}/visuals"))["cast"]
    assert [member["character_id"] for member in cast] == [alex, lina]
    assert data(client.post(f"/api/channel/series/{series['id']}/projects"))["created"] == []  # never twice
    lonely = tree["topics"][1]["series"][0]
    data(client.patch(f"/api/channel/series/{lonely['id']}", json={"cast": [alex]}))
    assert "two characters" in failed(client.post(f"/api/channel/series/{lonely['id']}/projects"))


def test_the_calendar_rotates_topics_over_the_publishing_weekdays(client):  # noqa: F811
    data(client.post("/api/channel/plan/apply", json={"plan": PLAN}))
    tree = data(client.post("/api/channel/schedule", json={"start_date": "2026-10-19", "weekdays": [0, 2, 4]}))
    dated = sorted((episode["publish_date"], topic["name"], episode["title"])
                   for topic in tree["topics"] for series in topic["series"] for episode in series["episodes"])
    assert [item[1] for item in dated] == ["Travel English", "English at Work", "Travel English", "English at Work",
                                           "Travel English"]
    assert [date.fromisoformat(item[0]).weekday() for item in dated] == [0, 2, 4, 0, 2]
    assert [item[2] for item in dated if item[1] == "Travel English"] == ["Planning the Trip", "Booking a Cabin", "Packing Day"]


def test_rotation_never_repeats_a_topic_while_others_wait():
    queues = [[{"t": "A", "n": n} for n in range(3)], [{"t": "B", "n": 0}], [{"t": "C", "n": n} for n in range(2)]]
    assert [item["t"] for item in channel_service.rotate(queues)] == ["A", "B", "C", "A", "C", "A"]


def test_a_project_knows_its_series_episode_and_neighbours(client):  # noqa: F811
    alex, lina = locked_character("Alex", "navy"), locked_character("Lina", "white")
    tree = data(client.post("/api/channel/plan/apply", json={"plan": PLAN, "cast": [alex, lina]}))
    series, topic = tree["topics"][0]["series"][0], tree["topics"][0]
    created = data(client.post(f"/api/channel/series/{series['id']}/projects"))["created"]
    data(client.patch(f"/api/channel/topics/{topic['id']}", json={"playlist_url": "https://youtube.com/playlist?list=T"}))
    first = series["episodes"][0]["id"]
    assert "video link" in failed(client.patch(f"/api/channel/episodes/{first}", json={"status": "published"}))
    data(client.patch(f"/api/channel/episodes/{first}", json={"status": "published", "video_url": "https://youtu.be/one"}))
    context = data(client.get(f"/api/channel/projects/{created[1]['project_id']}"))
    assert (context["series"], context["number"], context["total"]) == ("Weekend Trip with Friends", 2, 3)
    assert context["playlist_url"] == "https://youtube.com/playlist?list=T"
    assert context["previous"] == {"number": 1, "title": "Planning the Trip", "url": "https://youtu.be/one"}
    assert context["next"]["title"] == "Packing Day" and context["next"]["url"] == ""
    assert data(client.get("/api/channel/projects/not-in-the-plan")) is None


@pytest.mark.asyncio
async def test_the_ai_map_tolerates_renamed_fields_and_is_never_saved(client, monkeypatch):  # noqa: F811
    renamed = {"playlists": [{"title": "Food and Cooking", "description": "Kitchens.", "series": [
        {"title": "Cooking with Friends", "cefr": "a2", "genre": "Storytelling",
         "episode_list": ["Market Day", {"name": "Making Pho", "brief": "Steps."}, "Dinner Party"]}]}]}
    provider = FakeProvider("fake-local", [GenerationResult(text=json.dumps(renamed), provider="fake", model="fake",
                                                            latency_ms=1.0, attempt=1, prompt_hash="x")])
    monkeypatch.setattr(channel_service, "build_ai_router_from_settings",
                        lambda: AIRouter(primary=None, fallback=provider, mode=AIMode.LOCAL))
    data(client.post("/api/channel/topics", json={"name": "Travel English"}))
    plan = data(client.post("/api/channel/plan/propose", json={"topics": 1, "series_per_topic": 1, "episodes_per_series": 3,
                                                               "cefr_levels": ["A2", "b1"], "focus": "food"}))
    series = plan["topics"][0]["series"][0]
    assert (series["name"], series["cefr_level"], series["genre"]) == ("Cooking with Friends", "A2", "storytelling")
    assert [episode["title"] for episode in series["episodes"]] == ["Market Day", "Making Pho", "Dinner Party"]
    prompt = provider.calls[0].prompt
    assert "Travel English" in prompt and "food" in prompt and "A2, B1" in prompt  # existing topics are not repeated
    assert [topic["name"] for topic in data(client.get("/api/channel"))["topics"]] == ["Travel English"]


def test_the_thumbnail_shows_the_episode_number_of_the_series(client, monkeypatch):  # noqa: F811
    """Task 36.5: a project made from a series carries its episode number into the thumbnail's composition."""
    from backend.core.config import settings
    from backend.schemas.thumbnail import ThumbnailSuggestionPack
    from backend.media import thumbnail_service
    from tests.test_thumbnail_service import suggestion_json

    async def fake(project, template, variant_count, router=None):
        return ThumbnailSuggestionPack.model_validate_json(suggestion_json(variant_count))

    monkeypatch.setattr(thumbnail_service, "generate_suggestions", fake)
    alex, lina = locked_character("Alex", "navy"), locked_character("Lina", "white")
    series = data(client.post("/api/channel/plan/apply", json={"plan": PLAN, "cast": [alex, lina]}))["topics"][0]["series"][0]
    project_id = data(client.post(f"/api/channel/series/{series['id']}/projects"))["created"][2]["project_id"]
    row = data(client.post(f"/api/projects/{project_id}/thumbnails/generate",
                           json={"template_name": "composed", "variant_count": 3}))[0]
    sidecar = json.loads((settings.DATA_DIR / "thumbnails" / project_id / row["revision"] / "render.json")
                         .read_text(encoding="utf-8"))
    assert sidecar["composition"]["episode"] == 3
