"""HTTP tests for Learning Content routes (Sprint 1.5B).

learning_service.generate_learning_pack is monkeypatched with a fake — no real
network calls, no real Gemini API key needed. Mirrors tests/test_script_api.py's
approach for the script routes.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.exceptions import LearningGenerationError
from app.main import app
from app.models.learning import LearningPackOut
from app.services import learning_service

PROJECT_PAYLOAD = {
    "name": "Learning API Test Episode",
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

VALID_PACK = LearningPackOut(
    vocabulary=[
        {
            "word": "remote",
            "part_of_speech": "adjective",
            "ipa": "/rɪˈmoʊt/",
            "definition_en": "far away, not in the same place",
            "definition_vi": "từ xa",
            "example_sentence": "I've been working remotely for five years.",
        }
    ],
    idioms=[
        {
            "phrase": "thanks for having me",
            "meaning_en": "a polite way to thank a host for an invitation",
            "meaning_vi": "cảm ơn đã mời tôi",
            "example_sentence": "Thanks for having me.",
        }
    ],
    grammar=[
        {
            "point": "Present Perfect Continuous",
            "structure": "subject + have/has + been + verb-ing",
            "explanation_en": "used for an action that started in the past and continues now",
            "explanation_vi": "diễn tả hành động bắt đầu trong quá khứ và tiếp diễn đến hiện tại",
            "examples": ["I've been working remotely for five years."],
        }
    ],
    questions=[
        {
            "question": "How long has the guest been working remotely?",
            "options": ["1 year", "3 years", "5 years", "10 years"],
            "correct_answer": "5 years",
            "explanation": "The guest says they've been working remotely for five years.",
        }
    ],
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with TestClient(app) as test_client:
        yield test_client


def create_project(client: TestClient) -> dict:
    response = client.post("/api/projects", json=PROJECT_PAYLOAD)
    assert response.status_code == 200
    return response.json()["data"]


def save_script(client: TestClient, project: dict) -> None:
    speaker_ids = [s["id"] for s in project["speakers"]]
    payload = {
        "lines": [
            {"speaker_id": speaker_ids[0], "text": "Welcome to the show!"},
            {"speaker_id": speaker_ids[1], "text": "Thanks for having me."},
        ]
    }
    response = client.put(f"/api/projects/{project['id']}/script", json=payload)
    assert response.status_code == 200


def _envelope_ok(body: dict) -> None:
    assert body["success"] is True
    assert body["error"] is None


def _envelope_error(body: dict) -> None:
    assert body["success"] is False
    assert body["data"] is None
    assert isinstance(body["error"], str) and body["error"]


# --- POST /learning/generate ---


def test_generate_returns_200_and_persists(client, monkeypatch):
    project = create_project(client)
    save_script(client, project)

    async def fake_generate_learning_pack(project_id, config, script_lines):
        assert project_id == project["id"]
        assert len(script_lines) == 2
        return VALID_PACK

    monkeypatch.setattr(learning_service, "generate_learning_pack", fake_generate_learning_pack)

    response = client.post(f"/api/projects/{project['id']}/learning/generate")

    assert response.status_code == 200
    body = response.json()
    _envelope_ok(body)
    assert body["data"]["vocabulary"][0]["word"] == "remote"
    assert body["data"]["idioms"][0]["phrase"] == "thanks for having me"


def test_generate_empty_script_returns_422(client):
    project = create_project(client)

    response = client.post(f"/api/projects/{project['id']}/learning/generate")

    assert response.status_code == 422
    _envelope_error(response.json())


def test_generate_missing_project_returns_404(client):
    response = client.post("/api/projects/does-not-exist/learning/generate")

    assert response.status_code == 404
    _envelope_error(response.json())


def test_generate_gemini_failure_returns_502(client, monkeypatch):
    project = create_project(client)
    save_script(client, project)

    async def failing_generate_learning_pack(project_id, config, script_lines):
        raise LearningGenerationError("Gemini API returned HTTP 429 after 4 attempt(s): rate limited")

    monkeypatch.setattr(learning_service, "generate_learning_pack", failing_generate_learning_pack)

    response = client.post(f"/api/projects/{project['id']}/learning/generate")

    assert response.status_code == 502
    _envelope_error(response.json())


# --- GET /learning ---


def test_get_returns_null_before_generation(client):
    project = create_project(client)

    response = client.get(f"/api/projects/{project['id']}/learning")

    assert response.status_code == 200
    body = response.json()
    _envelope_ok(body)
    assert body["data"] is None


def test_get_returns_pack_after_generate(client, monkeypatch):
    project = create_project(client)
    save_script(client, project)

    async def fake_generate_learning_pack(project_id, config, script_lines):
        return VALID_PACK

    monkeypatch.setattr(learning_service, "generate_learning_pack", fake_generate_learning_pack)
    client.post(f"/api/projects/{project['id']}/learning/generate")

    response = client.get(f"/api/projects/{project['id']}/learning")

    assert response.status_code == 200
    body = response.json()
    _envelope_ok(body)
    assert body["data"]["vocabulary"][0]["word"] == "remote"
    assert body["data"]["grammar"][0]["point"] == "Present Perfect Continuous"


def test_get_missing_project_returns_404(client):
    response = client.get("/api/projects/does-not-exist/learning")

    assert response.status_code == 404
    _envelope_error(response.json())


# --- PUT /learning ---


def test_put_partial_update_returns_200_and_keeps_other_fields(client, monkeypatch):
    project = create_project(client)
    save_script(client, project)

    async def fake_generate_learning_pack(project_id, config, script_lines):
        return VALID_PACK

    monkeypatch.setattr(learning_service, "generate_learning_pack", fake_generate_learning_pack)
    client.post(f"/api/projects/{project['id']}/learning/generate")

    new_vocabulary = [
        {
            "word": "remote",
            "part_of_speech": "adjective",
            "ipa": "/rɪˈmoʊt/",
            "definition_en": "edited definition",
            "definition_vi": "định nghĩa đã sửa",
            "example_sentence": "I've been working remotely for five years.",
        }
    ]

    response = client.put(
        f"/api/projects/{project['id']}/learning", json={"vocabulary": new_vocabulary}
    )

    assert response.status_code == 200
    body = response.json()
    _envelope_ok(body)
    assert body["data"]["vocabulary"][0]["definition_en"] == "edited definition"
    assert body["data"]["idioms"][0]["phrase"] == "thanks for having me"
    assert body["data"]["grammar"][0]["point"] == "Present Perfect Continuous"
    assert body["data"]["questions"][0]["question"] == VALID_PACK.questions[0].question


def test_put_no_existing_content_returns_404(client):
    project = create_project(client)
    save_script(client, project)

    response = client.put(f"/api/projects/{project['id']}/learning", json={"vocabulary": []})

    assert response.status_code == 404
    _envelope_error(response.json())


def test_put_missing_project_returns_404(client):
    response = client.put(
        "/api/projects/does-not-exist/learning", json={"vocabulary": []}
    )

    assert response.status_code == 404
    _envelope_error(response.json())


async def fake_generate_pack(project_id, config, script_lines):
    return VALID_PACK


@pytest.mark.parametrize("section", ["vocabulary", "idioms", "grammar", "questions"])
def test_put_explicit_null_rejected_with_422(client, monkeypatch, section):
    """Explicit null in LearningPackUpdate must be rejected with HTTP 422 (BUG-005)."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-key")
    monkeypatch.setattr(
        learning_service, "generate_learning_pack", fake_generate_pack
    )

    project = create_project(client)
    save_script(client, project)
    client.post(f"/api/projects/{project['id']}/learning/generate")

    response = client.put(
        f"/api/projects/{project['id']}/learning", json={section: None}
    )

    assert response.status_code == 422
    body = response.json()
    assert "explicit null not allowed" in str(body).lower()


def test_put_empty_list_remains_valid(client, monkeypatch):
    """Empty list is valid and empties the section without error (BUG-005)."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-key")
    monkeypatch.setattr(
        learning_service, "generate_learning_pack", fake_generate_pack
    )

    project = create_project(client)
    save_script(client, project)
    client.post(f"/api/projects/{project['id']}/learning/generate")

    response = client.put(
        f"/api/projects/{project['id']}/learning", json={"vocabulary": []}
    )

    assert response.status_code == 200
    body = response.json()
    _envelope_ok(body)
    assert body["data"]["vocabulary"] == []
    # Omitted fields remain untouched
    assert len(body["data"]["idioms"]) > 0


@pytest.mark.asyncio
async def test_service_update_explicit_null_raises_value_error(db):
    """Direct service update with explicit null raises ValueError (BUG-005)."""

    import uuid
    pid = str(uuid.uuid4())
    now = "2026-09-11T00:00:00Z"
    await db.execute(
        "INSERT INTO projects (id, name, topic, cefr_level, num_speakers, genre, accent, created_at, updated_at) "
        "VALUES (?, 'Test', 'Topic', 'B1', 1, 'interview', 'american', ?, ?)",
        (pid, now, now)
    )

    await learning_service.save_learning_content(
        db, pid, VALID_PACK.model_dump(), commit=True
    )

    with pytest.raises(ValueError, match="explicit null not allowed"):
        await learning_service.update_learning_content(
            db, pid, {"vocabulary": None}
        )


def test_step4_route_returns_200(client):
    """GET /step4 serves the TTS Studio placeholder page without 404 (BUG-008)."""
    response = client.get("/step4")
    assert response.status_code == 200
    assert "TTS Audio Studio" in response.text
    assert "Step 4" in response.text
