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


def _project(client, style, num=1):  # noqa: F811
    speakers = [{"name": "Huyền", "gender": "female", "accent": "american"}, {"name": "Jack", "gender": "male", "accent": "american"}]
    return data(client.post("/api/projects", json={
        "name": style, "topic": "Kitchen", "cefr_level": "B1", "duration_minutes": 0.75, "num_speakers": num,
        "genre": "small_talk" if num == 2 else "informational", "accent": "american",
        "presentation_mode": "classic" if num == 2 else "solo_explainer", "explainer_style": style, "speakers": speakers[:num]}))


def test_a_slow_podcast_line_edits_its_translation(client):  # noqa: F811
    project = _project(client, "slowpod")
    speaker = project["speakers"][0]["id"]
    lines = data(client.put(f"/api/projects/{project['id']}/script", json={"lines": [
        {"speaker_id": speaker, "text": "I wake up early.", "language_notes": {"translation_vi": "Tôi dậy sớm."}}]}))
    view = data(client.get(f"/api/projects/{project['id']}/beats"))
    assert view["lines"][0]["card"] == {"translation_vi": "Tôi dậy sớm."} and view["props"]["lines"][0]["translation"] == "Tôi dậy sớm."
    data(client.put(f"/api/projects/{project['id']}/beats", json={"lines": [
        {"line_id": lines[0]["id"], "card": {"translation_vi": "Tôi thức dậy sớm."}}]}))
    saved = data(client.get(f"/api/projects/{project['id']}/script"))
    assert saved[0]["language_notes"]["translation_vi"] == "Tôi thức dậy sớm." and saved[0]["text"] == "I wake up early."


def test_a_flashcard_edits_its_word_in_the_lesson(client):  # noqa: F811
    project = _project(client, "flashcards")
    speaker = project["speakers"][0]["id"]
    lines = data(client.put(f"/api/projects/{project['id']}/script", json={"lines": [
        {"speaker_id": speaker, "text": text} for text in ("Vocabulary: kitchen.", "fry. fry.", "Follow us.")]}))
    item = {"word": "fry", "part_of_speech": "verb", "ipa": "/fraɪ/", "definition_en": "cook in oil",
            "definition_vi": "chiên", "example_sentence": "Fry the eggs."}
    from backend.content import learning_service
    from backend.core.config import settings
    import asyncio
    import aiosqlite

    async def seed():
        async with aiosqlite.connect(settings.db_path) as db:
            db.row_factory = aiosqlite.Row
            await learning_service.save_learning_content(db, project["id"], {
                "vocabulary": [item], "idioms": [], "grammar": [], "questions": []})
    asyncio.run(seed())
    view = data(client.get(f"/api/projects/{project['id']}/beats"))
    assert view["lines"][0]["card"] == {} and view["lines"][1]["card"]["definition_vi"] == "chiên"
    assert view["props"]["learning"]["vocab"][0]["definitionVi"] == "chiên"
    data(client.put(f"/api/projects/{project['id']}/beats", json={"lines": [
        {"line_id": lines[1]["id"], "card": {"part_of_speech": "verb", "ipa": "/fraɪ/", "definition_vi": "chiên, rán"}}]}))
    lesson = data(client.get(f"/api/projects/{project['id']}/learning"))
    assert lesson["vocabulary"][0]["definition_vi"] == "chiên, rán" and lesson["vocabulary"][0]["definition_en"] == "cook in oil"
    bad = client.put(f"/api/projects/{project['id']}/beats", json={"lines": [{"line_id": lines[0]["id"], "card": {}}]})
    assert bad.status_code in (400, 422)  # the deck name line has no card


def test_chat_messages_are_edited_as_spoken_lines(client):  # noqa: F811
    project = _project(client, "chat", num=2)
    lina, jack = (speaker["id"] for speaker in project["speakers"])
    lines = data(client.put(f"/api/projects/{project['id']}/script", json={"lines": [
        {"speaker_id": lina, "text": "Free tonight?"}, {"speaker_id": jack, "text": "Yes!"}]}))
    view = data(client.get(f"/api/projects/{project['id']}/beats"))
    assert [line["speaker"] for line in view["lines"]] == ["Huyền", "Jack"]
    assert view["props"]["lines"][1]["speakerId"] == jack
    bad = client.put(f"/api/projects/{project['id']}/beats", json={"lines": [{"line_id": lines[0]["id"], "card": {}}]})
    assert bad.status_code in (400, 422)
    data(client.put(f"/api/projects/{project['id']}/beats/{lines[1]['id']}/text", json={"text": "Yes, sure!"}))
    spoken = data(client.get(f"/api/projects/{project['id']}/beats/lines"))
    assert [line["text"] for line in spoken] == ["Free tonight?", "Yes, sure!"]
