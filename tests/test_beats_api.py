"""Phase 90: edit a word-roots or grammar Short on its video -- the beats API."""

import json
import sqlite3

from backend.content.grammar_lesson import GrammarLesson, build_beats
from tests.test_grammar_script import PASSIVE
from tests.test_visuals_project_api import client, data  # noqa: F401


def _grammar_project(client, style="grammar"):  # noqa: F811
    project = data(client.post("/api/projects", json={
        "name": "Câu bị động", "topic": "Câu bị động", "cefr_level": "B1", "duration_minutes": 2.0, "num_speakers": 1,
        "genre": "informational", "accent": "american", "presentation_mode": "solo_explainer", "explainer_style": style,
        "speakers": [{"name": "Huyền", "gender": "female", "accent": "american"}]}))
    speaker = project["speakers"][0]["id"]
    beats = build_beats(GrammarLesson.model_validate(PASSIVE), "vi")[:6]
    lines = data(client.put(f"/api/projects/{project['id']}/script", json={"lines": [
        {"speaker_id": speaker, "text": text, "language_notes": {"grammar": card}} for text, card in beats]}))
    return project, lines


def _db():
    from backend.core.config import settings
    return sqlite3.connect(settings.db_path)


def test_the_beats_come_with_their_cards_and_a_silent_preview(client):  # noqa: F811
    project, lines = _grammar_project(client)
    view = data(client.get(f"/api/projects/{project['id']}/beats"))
    assert view["style"] == "grammar" and view["with_audio"] is False and len(view["lines"]) == 6
    assert view["lines"][1]["card"]["cards"][1]["kind"] == "stamp"
    props = view["props"]
    assert props["shortStyle"] == "grammar" and props["audioPath"] == "" and props["height"] == 1920
    starts = [line["startSec"] for line in props["lines"]]
    assert starts == sorted(starts) and props["lines"][0]["grammar"]["beat"] == "hook"


def test_a_card_edit_is_checked_and_keeps_the_text_and_the_audio(client):  # noqa: F811
    project, lines = _grammar_project(client)
    with _db() as db:  # pretend every line has its audio
        db.execute("UPDATE script_lines SET audio_cache_path = 'x.mp3' WHERE project_id = ?", (project["id"],))
        db.execute("UPDATE projects SET status = 'video_generated' WHERE id = ?", (project["id"],))
    card = json.loads(json.dumps(lines[4]["language_notes"]["grammar"]))
    card["title"] = "Chiếc nhãn dán đứng im!"
    card["cards"][-1]["chips"][0] = {"text": "SUBJECT", "role": "nonsense", "extra": "dropped"}
    card["unknown"] = "dropped"
    data(client.put(f"/api/projects/{project['id']}/beats", json={"lines": [{"line_id": lines[4]["id"], "card": card}]}))
    saved = data(client.get(f"/api/projects/{project['id']}/script"))
    stored = saved[4]["language_notes"]["grammar"]
    assert stored["title"] == "Chiếc nhãn dán đứng im!" and "unknown" not in stored
    assert stored["cards"][-1]["chips"][0] == {"text": "SUBJECT", "role": "plain"}
    assert saved[4]["text"] == lines[4]["text"]
    with _db() as db:
        caches = [row[0] for row in db.execute(
            "SELECT audio_cache_path FROM script_lines WHERE project_id = ? ORDER BY line_index", (project["id"],))]
        status = db.execute("SELECT status FROM projects WHERE id = ?", (project["id"],)).fetchone()[0]
    assert caches == ["x.mp3"] * 6 and status == "audio_generated"  # the audio stays, the video is out of date
    bad = client.put(f"/api/projects/{project['id']}/beats", json={"lines": [
        {"line_id": lines[4]["id"], "card": {**card, "cards": [{"kind": "video"}]}}]})
    assert bad.status_code in (400, 422)


def test_a_text_edit_keeps_the_card_and_clears_only_that_lines_audio(client):  # noqa: F811
    project, lines = _grammar_project(client)
    with _db() as db:
        db.execute("UPDATE script_lines SET audio_cache_path = 'x.mp3' WHERE project_id = ?", (project["id"],))
    data(client.put(f"/api/projects/{project['id']}/beats/{lines[3]['id']}/text", json={"text": "Nhìn hai câu sau nhé."}))
    saved = data(client.get(f"/api/projects/{project['id']}/script"))
    assert saved[3]["text"] == "Nhìn hai câu sau nhé." and saved[3]["language_notes"]["grammar"]["beat"] == "scene"
    assert [line["id"] for line in saved] == [line["id"] for line in lines]  # the lines keep their identity
    with _db() as db:
        caches = [row[0] for row in db.execute(
            "SELECT audio_cache_path FROM script_lines WHERE project_id = ? ORDER BY line_index", (project["id"],))]
    assert caches == ["x.mp3"] * 3 + [None] + ["x.mp3"] * 2


def test_only_word_roots_and_grammar_shorts_are_edited_here(client):  # noqa: F811
    project = data(client.post("/api/projects", json={
        "name": "News", "topic": "News", "cefr_level": "B1", "duration_minutes": 0.9, "num_speakers": 1,
        "genre": "informational", "accent": "american", "presentation_mode": "solo_explainer", "explainer_style": "news",
        "speakers": [{"name": "Huyền", "gender": "female", "accent": "american"}]}))
    assert client.get(f"/api/projects/{project['id']}/beats").status_code in (400, 422)
    assert client.get(f"/api/projects/{project['id']}/beats/pictures/..%2Fapp.db").status_code == 404


def test_a_word_roots_card_is_saved_with_its_parts(client):  # noqa: F811
    project = data(client.post("/api/projects", json={
        "name": "Gốc PRESS", "topic": "Gốc PRESS", "cefr_level": "B1", "duration_minutes": 2.0, "num_speakers": 1,
        "genre": "informational", "accent": "american", "presentation_mode": "solo_explainer", "explainer_style": "roots",
        "speakers": [{"name": "Huyền", "gender": "female", "accent": "american"}]}))
    speaker = project["speakers"][0]["id"]
    card = {"beat": "whole", "word": "compress", "meaning": "nén lại", "kind": "root",
            "parts": [{"text": "com", "role": "prefix", "meaning": "cùng nhau"}, {"text": "press", "role": "root", "meaning": "ép"}]}
    lines = data(client.put(f"/api/projects/{project['id']}/script", json={"lines": [
        {"speaker_id": speaker, "text": "Compress, nén lại.", "language_notes": {"roots": card}}]}))
    edited = {**card, "meaning": "nén, ép lại", "picture": "a zipped folder on a screen"}
    data(client.put(f"/api/projects/{project['id']}/beats", json={"lines": [{"line_id": lines[0]["id"], "card": edited}]}))
    view = data(client.get(f"/api/projects/{project['id']}/beats"))
    assert view["key"] == "roots" and view["lines"][0]["card"]["meaning"] == "nén, ép lại"
    assert view["lines"][0]["card"]["parts"][1] == {"text": "press", "role": "root", "meaning": "ép"}
    assert view["props"]["lines"][0]["roots"]["picture"] == "a zipped folder on a screen"


def test_after_a_text_edit_only_that_line_needs_its_voice(client, monkeypatch):  # noqa: F811
    """Phase 90.3: the editor makes the voice of the lines whose audio no longer matches, and only those."""
    from backend.ai.tts import tts_service

    monkeypatch.setattr(tts_service, "cache_matches", lambda project, line, **_: bool(line.get("audio_cache_path")))
    project, lines = _grammar_project(client)
    with _db() as db:
        db.execute("UPDATE script_lines SET audio_cache_path = 'x.mp3' WHERE project_id = ?", (project["id"],))
    assert all(line["audio_ok"] for line in data(client.get(f"/api/projects/{project['id']}/beats"))["lines"])
    data(client.put(f"/api/projects/{project['id']}/beats/{lines[2]['id']}/text", json={"text": "Một phút là đủ!"}))
    view = data(client.get(f"/api/projects/{project['id']}/beats"))
    assert [line["audio_ok"] for line in view["lines"]] == [True, True, False, True, True, True]
