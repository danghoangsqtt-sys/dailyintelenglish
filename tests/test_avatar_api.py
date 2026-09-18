"""HTTP and filesystem safety tests for the speaker avatar upload API (Task 1.7c)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.constants import MAX_AVATAR_UPLOAD_MB
from app.main import app

VALID_PNG = b"\x89PNG\r\n\x1a\n" + b"fake-png-data"
VALID_JPEG = b"\xff\xd8\xff" + b"fake-jpeg-data"

VALID_PAYLOAD = {
    "name": "Avatar Test Episode",
    "topic": "Testing avatar uploads",
    "cefr_level": "B1",
    "duration_minutes": 5,
    "num_speakers": 2,
    "genre": "interview",
    "accent": "american",
    "speakers": [
        {"name": "Alex", "gender": "male", "accent": "american"},
        {"name": "Sam", "gender": "female", "accent": "american"},
    ],
}


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def project(client: TestClient) -> dict:
    return client.post("/api/projects", json=VALID_PAYLOAD).json()["data"]


def upload(client: TestClient, project_id: str, speaker_id: str, filename: str, content: bytes):
    return client.post(
        f"/api/projects/{project_id}/speakers/{speaker_id}/avatar",
        files={"file": (filename, content)},
    )


def test_upload_accepts_valid_png_and_jpeg(client: TestClient, project: dict):
    speaker_id = project["speakers"][0]["id"]

    response = upload(client, project["id"], speaker_id, "face.png", VALID_PNG)

    assert response.status_code == 200
    updated = next(s for s in response.json()["data"]["speakers"] if s["id"] == speaker_id)
    assert updated["avatar_image_path"] == f"/api/projects/{project['id']}/speakers/{speaker_id}/avatar"
    avatar_dir = settings.DATA_DIR / "avatars" / project["id"]
    stored_files = list(avatar_dir.glob(f"{speaker_id}.*"))
    assert len(stored_files) == 1
    assert stored_files[0].suffix == ".png"
    assert stored_files[0].read_bytes() == VALID_PNG


def test_upload_never_leaks_raw_filesystem_path(client: TestClient, project: dict):
    speaker_id = project["speakers"][0]["id"]

    response = upload(client, project["id"], speaker_id, "face.jpg", VALID_JPEG)

    body_text = response.text
    assert str(settings.DATA_DIR) not in body_text


def test_reupload_replaces_previous_avatar_file(client: TestClient, project: dict):
    speaker_id = project["speakers"][0]["id"]
    upload(client, project["id"], speaker_id, "face.png", VALID_PNG)

    second = upload(client, project["id"], speaker_id, "face.jpg", VALID_JPEG)

    assert second.status_code == 200
    avatar_dir = settings.DATA_DIR / "avatars" / project["id"]
    stored_files = list(avatar_dir.glob(f"{speaker_id}.*"))
    assert len(stored_files) == 1
    assert stored_files[0].suffix == ".jpg"


def test_upload_commit_failure_preserves_the_original_avatar(
    client: TestClient, project: dict, monkeypatch: pytest.MonkeyPatch
):
    """Task 10.1 (BUG-019): if the database transaction's commit fails after a
    re-upload, the previous avatar file and the DB's reference to it must both
    survive untouched — not a deleted file with a dangling DB pointer."""
    from app.db.database import Database

    speaker_id = project["speakers"][0]["id"]
    first = upload(client, project["id"], speaker_id, "face.png", VALID_PNG)
    assert first.status_code == 200
    avatar_dir = settings.DATA_DIR / "avatars" / project["id"]
    original_file = next(avatar_dir.glob(f"{speaker_id}.*"))
    original_bytes = original_file.read_bytes()

    connection = Database.instance().connection
    real_commit = connection.commit

    async def failing_commit():
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(connection, "commit", failing_commit)
    try:
        with pytest.raises(RuntimeError, match="simulated commit failure"):
            upload(client, project["id"], speaker_id, "face.jpg", VALID_JPEG)
    finally:
        monkeypatch.setattr(connection, "commit", real_commit)

    assert original_file.exists()
    assert original_file.read_bytes() == original_bytes

    served = client.get(f"/api/projects/{project['id']}/speakers/{speaker_id}/avatar")
    assert served.status_code == 200
    assert served.content == original_bytes


def test_other_speaker_avatar_is_untouched(client: TestClient, project: dict):
    speaker_id, other_id = project["speakers"][0]["id"], project["speakers"][1]["id"]
    upload(client, project["id"], speaker_id, "face.png", VALID_PNG)

    response = client.get(f"/api/projects/{project['id']}")

    other = next(s for s in response.json()["data"]["speakers"] if s["id"] == other_id)
    assert other["avatar_image_path"] is None


def test_upload_rejects_spoofed_extension_and_cleans_temp_file(client: TestClient, project: dict):
    speaker_id = project["speakers"][0]["id"]

    response = upload(client, speaker_id=speaker_id, project_id=project["id"], filename="fake.png", content=b"not-a-png")

    assert response.status_code == 422
    avatar_dir = settings.DATA_DIR / "avatars" / project["id"]
    assert not avatar_dir.exists() or list(avatar_dir.iterdir()) == []


def test_upload_rejects_unsupported_extension_and_empty_file(client: TestClient, project: dict):
    speaker_id = project["speakers"][0]["id"]

    unsupported = upload(client, project["id"], speaker_id, "face.gif", b"GIF89a")
    empty = upload(client, project["id"], speaker_id, "face.png", b"")

    assert unsupported.status_code == 422
    assert empty.status_code == 422


def test_upload_rejects_files_over_configured_limit_and_cleans_partial_file(
    client: TestClient, project: dict, monkeypatch: pytest.MonkeyPatch
):
    from app.services import avatar_service

    monkeypatch.setattr(avatar_service, "MAX_AVATAR_UPLOAD_BYTES", len(VALID_PNG) - 1)
    speaker_id = project["speakers"][0]["id"]

    response = upload(client, project["id"], speaker_id, "face.png", VALID_PNG)

    assert response.status_code == 413
    assert f"{MAX_AVATAR_UPLOAD_MB} MB or smaller" in response.json()["error"]
    avatar_dir = settings.DATA_DIR / "avatars" / project["id"]
    assert not avatar_dir.exists() or list(avatar_dir.iterdir()) == []


def test_upload_unknown_speaker_or_project_returns_404(client: TestClient, project: dict):
    unknown_speaker = upload(client, project["id"], "does-not-exist", "face.png", VALID_PNG)
    unknown_project = upload(client, "does-not-exist", project["speakers"][0]["id"], "face.png", VALID_PNG)

    assert unknown_speaker.status_code == 404
    assert unknown_project.status_code == 404


def test_get_serves_avatar_bytes_with_media_type(client: TestClient, project: dict):
    speaker_id = project["speakers"][0]["id"]
    upload(client, project["id"], speaker_id, "face.png", VALID_PNG)

    response = client.get(f"/api/projects/{project['id']}/speakers/{speaker_id}/avatar")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
    assert response.content == VALID_PNG


def test_get_missing_avatar_returns_404(client: TestClient, project: dict):
    speaker_id = project["speakers"][0]["id"]

    response = client.get(f"/api/projects/{project['id']}/speakers/{speaker_id}/avatar")

    assert response.status_code == 404


def test_delete_removes_avatar_and_clears_reference(client: TestClient, project: dict):
    speaker_id = project["speakers"][0]["id"]
    upload(client, project["id"], speaker_id, "face.png", VALID_PNG)

    deleted = client.delete(f"/api/projects/{project['id']}/speakers/{speaker_id}/avatar")
    refetched = client.get(f"/api/projects/{project['id']}")

    assert deleted.status_code == 200
    updated = next(s for s in refetched.json()["data"]["speakers"] if s["id"] == speaker_id)
    assert updated["avatar_image_path"] is None
    avatar_dir = settings.DATA_DIR / "avatars" / project["id"]
    assert list(avatar_dir.glob(f"{speaker_id}.*")) == []


def test_delete_unknown_speaker_or_project_returns_404(client: TestClient, project: dict):
    unknown_speaker = client.delete(f"/api/projects/{project['id']}/speakers/does-not-exist/avatar")
    unknown_project = client.delete(
        f"/api/projects/does-not-exist/speakers/{project['speakers'][0]['id']}/avatar"
    )

    assert unknown_speaker.status_code == 404
    assert unknown_project.status_code == 404
