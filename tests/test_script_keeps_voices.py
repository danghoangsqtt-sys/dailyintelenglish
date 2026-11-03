"""Phase 91.1 (D133): saving the script in Step 2 keeps the voice of every unchanged line."""

import sqlite3

from tests.test_visuals_project_api import client, data  # noqa: F401


def _caches(project_id: str) -> list:
    from backend.core.config import settings

    with sqlite3.connect(settings.db_path) as db:
        return db.execute("SELECT id, audio_cache_path FROM script_lines WHERE project_id = ? ORDER BY line_index",
                          (project_id,)).fetchall()


def test_an_edit_in_step_2_keeps_the_voice_of_the_unchanged_lines(client):  # noqa: F811
    from backend.core.config import settings

    project = data(client.post("/api/projects", json={
        "name": "Talk", "topic": "Coffee", "cefr_level": "B1", "duration_minutes": 5, "num_speakers": 2,
        "genre": "small_talk", "accent": "american",
        "speakers": [{"name": "Ann", "gender": "female", "accent": "american"},
                     {"name": "Ben", "gender": "male", "accent": "american"}]}))
    ann, ben = (speaker["id"] for speaker in project["speakers"])
    texts = [(ann, "Do you like coffee?"), (ben, "I love it."), (ann, "Me too."), (ben, "Let's go.")]
    lines = data(client.put(f"/api/projects/{project['id']}/script", json={"lines": [
        {"speaker_id": speaker, "text": text} for speaker, text in texts]}))
    with sqlite3.connect(settings.db_path) as db:
        db.execute("UPDATE script_lines SET audio_cache_path = 'voice-' || line_index WHERE project_id = ?", (project["id"],))
    edited = [(ann, "Do you like coffee?"), (ben, "I really love it."), (ann, "Me too."), (ann, "Let's go.")]
    data(client.put(f"/api/projects/{project['id']}/script", json={"lines": [
        {"speaker_id": speaker, "text": text} for speaker, text in edited]}))
    after = _caches(project["id"])
    assert [cache for _, cache in after] == ["voice-0", None, "voice-2", None]  # text changed / speaker changed
    assert after[0][0] == lines[0]["id"] and after[1][0] != lines[1]["id"]
    data(client.put(f"/api/projects/{project['id']}/script", json={"lines": [
        {"speaker_id": speaker, "text": text} for speaker, text in edited[:2]]}))
    assert [cache for _, cache in _caches(project["id"])] == ["voice-0", None]  # a shorter script keeps the rest
