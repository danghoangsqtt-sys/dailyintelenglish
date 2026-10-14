"""Phase 40 (D119): no fixed Alex/Lina — a speaker takes its chosen character's name everywhere (script lines too), and a
rename marks the audio to redo."""

from __future__ import annotations

import sqlite3

from backend.core.config import settings
from backend.core.paths import PROJECT_ROOT
from tests.test_visuals_project_api import client, data, locked_character  # noqa: F401


def _project(client, names=("Lina", "Alex")) -> dict:  # noqa: F811
    project = data(client.post("/api/projects", json={
        "name": "Names", "topic": "Meeting the neighbours", "cefr_level": "B1", "duration_minutes": 2, "num_speakers": 2,
        "genre": "small_talk", "accent": "american",
        "speakers": [{"name": names[0], "gender": "female", "accent": "american"},
                     {"name": names[1], "gender": "male", "accent": "american"}],
    }))
    detail = data(client.get(f"/api/projects/{project['id']}"))
    ids = {speaker["speaker_index"]: speaker["id"] for speaker in detail["speakers"]}
    data(client.put(f"/api/projects/{project['id']}/script", json={"lines": [
        {"speaker_id": ids[0], "text": f"Hi {names[1]}! I'm {names[0]}, your new neighbour."},
        {"speaker_id": ids[1], "text": f"Nice to meet you, {names[0]}. {names[0]}'s garden is lovely. Linas and Alexa stay."},
    ]}))
    return {**detail, "ids": ids}


def _lines(project_id: str) -> list[str]:
    with sqlite3.connect(settings.db_path) as connection:
        return [row[0] for row in connection.execute(
            "SELECT text FROM script_lines WHERE project_id = ? ORDER BY line_index", (project_id,))]


def _status(project_id: str) -> str:
    with sqlite3.connect(settings.db_path) as connection:
        return connection.execute("SELECT status FROM projects WHERE id = ?", (project_id,)).fetchone()[0]


def test_choosing_a_character_renames_the_speaker_and_the_script_lines(client):  # noqa: F811
    project = _project(client)
    with sqlite3.connect(settings.db_path) as connection:  # pretend the audio was made: the rename must undo that
        connection.execute("UPDATE projects SET status = 'audio_generated' WHERE id = ?", (project["id"],))
    mia, tom = locked_character("Mia", "yellow"), locked_character("Tom", "navy")
    result = data(client.put(f"/api/projects/{project['id']}/visuals/cast", json=[
        {"speaker_index": 0, "character_id": mia}, {"speaker_index": 1, "character_id": tom}]))
    assert [(item["old_name"], item["new_name"]) for item in result["renamed"]] == [("Lina", "Mia"), ("Alex", "Tom")]
    detail = data(client.get(f"/api/projects/{project['id']}"))
    assert [speaker["name"] for speaker in detail["speakers"]] == ["Mia", "Tom"]
    assert _lines(project["id"]) == ["Hi Tom! I'm Mia, your new neighbour.",
                                     "Nice to meet you, Mia. Mia's garden is lovely. Linas and Alexa stay."]
    assert _status(project["id"]) == "script_generated"  # the voices still say Lina/Alex: audio to redo


def test_a_character_with_the_same_name_changes_nothing(client):  # noqa: F811
    project = _project(client, names=("Mia", "Tom"))
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute("UPDATE projects SET status = 'audio_generated' WHERE id = ?", (project["id"],))
    mia = locked_character("Mia", "yellow")
    result = data(client.put(f"/api/projects/{project['id']}/visuals/cast", json=[{"speaker_index": 0, "character_id": mia}]))
    assert result["renamed"] == [] and _status(project["id"]) == "audio_generated"


def test_the_speaker_rename_route_renames_the_lines_too(client):  # noqa: F811
    project = _project(client)
    updated = data(client.patch(f"/api/projects/{project['id']}/speakers/{project['ids'][0]}", json={"name": "Mia"}))
    assert updated["renamed"]["lines_changed"] == 2
    assert _lines(project["id"])[0] == "Hi Alex! I'm Mia, your new neighbour."
    # a voice-only patch still works and renames nothing
    voice = data(client.patch(f"/api/projects/{project['id']}/speakers/{project['ids'][1]}", json={"speed": 0.9}))
    assert "renamed" not in voice and next(s for s in voice["speakers"] if s["speaker_index"] == 1)["speed"] == 0.9


def test_step1_and_the_channel_plan_no_longer_preselect_alex_and_lina():
    step1 = (PROJECT_ROOT / "frontend" / "static" / "js" / "step1_config.js").read_text(encoding="utf-8")
    channel = (PROJECT_ROOT / "frontend" / "static" / "js" / "channel.js").read_text(encoding="utf-8")
    for source in (step1, channel):
        assert '"Alex"' not in source and '"Lina"' not in source
    assert "preselectDefaults" not in step1 and "Character ${index + 1}" in step1


def test_choosing_a_character_also_gives_the_speaker_its_voice(client):  # noqa: F811
    project = _project(client)
    kim = locked_character("Kim", "white")
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute("UPDATE characters SET default_accent = 'australian', default_voice_id = 'en-AU-NatashaNeural', "
                           "default_speed = 0.9 WHERE id = ?", (kim,))
    data(client.put(f"/api/projects/{project['id']}/visuals/cast", json=[{"speaker_index": 0, "character_id": kim}]))
    speaker = next(s for s in data(client.get(f"/api/projects/{project['id']}"))["speakers"] if s["speaker_index"] == 0)
    assert (speaker["name"], speaker["gender"], speaker["accent"], speaker["voice_id"], speaker["speed"]) \
        == ("Kim", "female", "australian", "en-AU-NatashaNeural", 0.85)  # the level's speed stays


def test_the_edge_voice_comes_from_the_speakers_own_voice_id_when_it_has_one():
    import inspect

    from backend.ai.tts import tts_service
    source = inspect.getsource(tts_service._synthesize_edge_tts)
    assert 'speaker.get("voice_id")' in source
