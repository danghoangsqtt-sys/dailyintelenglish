"""HTTP contract for reusable character profiles."""

from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with TestClient(app) as test_client:
        yield test_client


def data(response):
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["success"] is True
    return payload["data"]


def test_profile_autosave_filter_duplicate_and_archive(client):
    draft = data(client.post("/api/visuals/characters", json={"name": "Maya"}))
    assert draft["status"] == "draft"
    assert draft["readiness"]["profile"]["state"] == "missing"

    saved = data(client.patch(f"/api/visuals/characters/{draft['id']}", json={
        "intro": "A friendly guide",
        "personality": ["patient", "curious"],
        "speaking_style": "friendly",
        "default_voice_id": "en-US-JennyNeural",
        "wizard_step": 4,
    }))
    assert saved["wizard_step"] == 4
    assert saved["readiness"]["profile"]["state"] == "ready"
    assert saved["readiness"]["voice"]["state"] == "ready"
    assert data(client.get("/api/visuals/characters?q=may&readiness=needs_setup"))[0]["id"] == draft["id"]

    assert client.post("/api/visuals/characters", json={"name": " MAYA "}).status_code == 409
    duplicate = data(client.post(f"/api/visuals/characters/{draft['id']}/duplicate"))
    assert duplicate["name"] == "Maya copy"
    assert duplicate["assets"] == []

    archived = data(client.post(f"/api/visuals/characters/{draft['id']}/archive"))
    assert archived["lifecycle"] == "archived"
    assert all(item["id"] != draft["id"] for item in data(client.get("/api/visuals/characters")))
    assert data(client.get("/api/visuals/characters?state=archived"))[0]["id"] == draft["id"]
    restored = data(client.post(f"/api/visuals/characters/{draft['id']}/restore"))
    assert restored["lifecycle"] == "active"


def test_dependency_endpoint_and_safe_delete(client):
    profile = data(client.post("/api/visuals/characters", json={"name": "Maya"}))
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute(
            "INSERT INTO projects (id, name, status, created_at, updated_at) VALUES ('p-profile', 'P', 'draft', 'n', 'n')"
        )
        connection.execute(
            "INSERT INTO project_cast (project_id, speaker_index, character_id, profile_version) VALUES (?, 0, ?, 1)",
            ("p-profile", profile["id"]),
        )
    report = data(client.get(f"/api/visuals/characters/{profile['id']}/dependencies"))
    assert report["projects"] == 1 and report["can_delete"] is False
    assert client.delete(f"/api/visuals/characters/{profile['id']}").status_code == 409
    archived = data(client.post(f"/api/visuals/characters/{profile['id']}/archive"))
    assert archived["lifecycle"] == "archived"


def test_unreferenced_non_seed_profile_can_be_deleted(client):
    profile = data(client.post("/api/visuals/characters", json={"name": "Temporary"}))
    deleted = data(client.delete(f"/api/visuals/characters/{profile['id']}"))
    assert deleted == {"deleted": profile["id"]}
    assert client.get(f"/api/visuals/characters/{profile['id']}").status_code == 404

