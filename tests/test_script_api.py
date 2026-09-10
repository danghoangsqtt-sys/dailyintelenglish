"""HTTP tests for script generation/regeneration/save routes (Sprint 1.4C).

script_service's Gemini-calling functions (generate_script, regenerate_line)
are monkeypatched with fakes — no real network calls, no real Gemini API key
needed.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.exceptions import ScriptGenerationError
from app.main import app
from app.services import script_service
from app.services.script_service import LanguageNotesOut, ScriptLineOut

PROJECT_PAYLOAD = {
    "name": "Script API Test Episode",
    "topic": "Remote work culture",
    "cefr_level": "B1",
    "duration_minutes": 8,
    "num_speakers": 2,
    "genre": "interview",
    "accent": "american",
    "speakers": [
        {"name": "Alex", "gender": "male", "accent": "american"},
        {"name": "Sam", "gender": "female", "accent": "american"},
    ],
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with TestClient(app) as test_client:
        yield test_client


def create_project(client: TestClient) -> dict:
    response = client.post("/api/projects", json=PROJECT_PAYLOAD)
    assert response.status_code == 200
    return response.json()["data"]


def _envelope_ok(body: dict) -> None:
    assert body["success"] is True
    assert body["error"] is None


def _envelope_error(body: dict) -> None:
    assert body["success"] is False
    assert body["data"] is None
    assert isinstance(body["error"], str) and body["error"]


# --- POST /script/generate ---


def test_generate_script_returns_200_and_persists(client, monkeypatch):
    project = create_project(client)
    speaker_ids = [s["id"] for s in project["speakers"]]

    async def fake_generate_script(project_id, config):
        return [
            ScriptLineOut(
                id="line_001",
                speaker_id=speaker_ids[0],
                text="Welcome to the show!",
                language_notes=LanguageNotesOut(collocations=["Welcome to"], grammar_point="Present Simple"),
            ),
            ScriptLineOut(id="line_002", speaker_id=speaker_ids[1], text="Thanks for having me."),
        ]

    monkeypatch.setattr(script_service, "generate_script", fake_generate_script)

    response = client.post(f"/api/projects/{project['id']}/script/generate")

    assert response.status_code == 200
    body = response.json()
    _envelope_ok(body)
    assert len(body["data"]) == 2
    assert body["data"][0]["speaker_id"] == speaker_ids[0]
    assert body["data"][0]["text"] == "Welcome to the show!"
    assert body["data"][1]["speaker_id"] == speaker_ids[1]


def test_generate_script_gemini_failure_returns_502(client, monkeypatch):
    project = create_project(client)

    async def failing_generate_script(project_id, config):
        raise ScriptGenerationError("Gemini API returned HTTP 429 after 4 attempt(s): rate limited")

    monkeypatch.setattr(script_service, "generate_script", failing_generate_script)

    response = client.post(f"/api/projects/{project['id']}/script/generate")

    assert response.status_code == 502
    _envelope_error(response.json())


def test_generate_script_missing_project_returns_404(client):
    response = client.post("/api/projects/does-not-exist/script/generate")

    assert response.status_code == 404
    _envelope_error(response.json())


# --- POST /script/regenerate ---


def test_regenerate_line_returns_200_and_updates(client, monkeypatch):
    project = create_project(client)
    speaker_ids = [s["id"] for s in project["speakers"]]

    async def fake_generate_script(project_id, config):
        return [ScriptLineOut(id="line_001", speaker_id=speaker_ids[0], text="Original line.")]

    monkeypatch.setattr(script_service, "generate_script", fake_generate_script)
    generated = client.post(f"/api/projects/{project['id']}/script/generate")
    line_id = generated.json()["data"][0]["id"]

    async def fake_regenerate_line(project_id, config, line_id_arg, current_text, speaker_id):
        assert current_text == "Original line."
        assert speaker_id == speaker_ids[0]
        return ScriptLineOut(id=line_id_arg, speaker_id=speaker_id, text="Rewritten line.")

    monkeypatch.setattr(script_service, "regenerate_line", fake_regenerate_line)

    response = client.post(f"/api/projects/{project['id']}/script/regenerate", json={"line_id": line_id})

    assert response.status_code == 200
    body = response.json()
    _envelope_ok(body)
    assert body["data"]["text"] == "Rewritten line."
    assert body["data"]["speaker_id"] == speaker_ids[0]


def test_regenerate_line_gemini_failure_returns_502(client, monkeypatch):
    project = create_project(client)
    speaker_ids = [s["id"] for s in project["speakers"]]

    async def fake_generate_script(project_id, config):
        return [ScriptLineOut(id="line_001", speaker_id=speaker_ids[0], text="Original line.")]

    monkeypatch.setattr(script_service, "generate_script", fake_generate_script)
    generated = client.post(f"/api/projects/{project['id']}/script/generate")
    line_id = generated.json()["data"][0]["id"]

    async def failing_regenerate_line(project_id, config, line_id_arg, current_text, speaker_id):
        raise ScriptGenerationError("Gemini did not return valid JSON")

    monkeypatch.setattr(script_service, "regenerate_line", failing_regenerate_line)

    response = client.post(f"/api/projects/{project['id']}/script/regenerate", json={"line_id": line_id})

    assert response.status_code == 502
    _envelope_error(response.json())


def test_regenerate_missing_line_returns_404(client):
    project = create_project(client)

    response = client.post(
        f"/api/projects/{project['id']}/script/regenerate", json={"line_id": "does-not-exist"}
    )

    assert response.status_code == 404
    _envelope_error(response.json())


def test_regenerate_missing_project_returns_404(client):
    response = client.post("/api/projects/does-not-exist/script/regenerate", json={"line_id": "line_001"})

    assert response.status_code == 404
    _envelope_error(response.json())


# --- PUT /script ---


def test_save_script_returns_200_and_persists(client):
    project = create_project(client)
    speaker_ids = [s["id"] for s in project["speakers"]]
    payload = {
        "lines": [
            {"speaker_id": speaker_ids[0], "text": "Hello there.", "language_notes": {"grammar_point": "Greeting"}},
            {"speaker_id": speaker_ids[1], "text": "Hi, nice to meet you."},
        ]
    }

    response = client.put(f"/api/projects/{project['id']}/script", json=payload)

    assert response.status_code == 200
    body = response.json()
    _envelope_ok(body)
    assert len(body["data"]) == 2
    assert body["data"][0]["text"] == "Hello there."
    assert body["data"][1]["speaker_id"] == speaker_ids[1]


def test_save_script_unknown_speaker_returns_422(client):
    project = create_project(client)
    payload = {"lines": [{"speaker_id": "99999999-9999-9999-9999-999999999999", "text": "Bad speaker."}]}

    response = client.put(f"/api/projects/{project['id']}/script", json=payload)

    assert response.status_code == 422
    _envelope_error(response.json())


def test_save_script_empty_lines_returns_422(client):
    project = create_project(client)

    response = client.put(f"/api/projects/{project['id']}/script", json={"lines": []})

    assert response.status_code == 422
    _envelope_error(response.json())


def test_save_script_missing_project_returns_404(client):
    response = client.put(
        "/api/projects/does-not-exist/script",
        json={"lines": [{"speaker_id": "11111111-1111-1111-1111-111111111111", "text": "hi"}]},
    )

    assert response.status_code == 404
    _envelope_error(response.json())
