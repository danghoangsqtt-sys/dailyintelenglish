"""HTTP upload validation, deterministic slot naming, batch mapping, and rollback."""

from __future__ import annotations

import io
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.core.config import settings
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with TestClient(app) as test_client:
        yield test_client


def data(response):
    assert response.status_code == 200, response.text
    return response.json()["data"]


def image_bytes(size=(640, 640), image_format="PNG", transparent=False) -> bytes:
    mode = "RGBA" if transparent else "RGB"
    background = (0, 0, 0, 0) if transparent else (220, 230, 220)
    image = Image.new(mode, size, background)
    draw = ImageDraw.Draw(image)
    fill = (180, 90, 70, 255) if transparent else (180, 90, 70)
    draw.rectangle((size[0] // 3, 60, size[0] * 2 // 3, size[1] - 80), fill=fill)
    output = io.BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


def upload(client, character_id, slot, content, filename="picture.png", **form):
    fields = {"expected_identity_version": "1", **{key: str(value).lower() for key, value in form.items()}}
    return client.post(
        f"/api/visuals/characters/{character_id}/assets/{slot}/upload",
        data=fields, files={"picture": (filename, content, "image/png")},
    )


def test_upload_assigns_slot_and_invalid_replacement_preserves_approved_asset(client):
    profile = data(client.post("/api/visuals/characters", json={"name": "Maya"}))
    first = data(upload(client, profile["id"], "face", image_bytes(), "outside-name.jpg"))
    assert first["slot_key"] == "face"
    assert first["original_filename"] == "outside-name.jpg"
    assert first["review_state"] == "needs_review"
    approved = data(client.put(
        f"/api/visuals/characters/{profile['id']}/assets/{first['id']}/review",
        json={"review_state": "approved"},
    ))
    assert approved["approved"] == 1

    bad = upload(client, profile["id"], "face", b"not an image", "bad.png", replace_identity=True)
    assert bad.status_code == 422
    slots = data(client.get(f"/api/visuals/characters/{profile['id']}/asset-slots"))
    face = next(item for item in slots["groups"]["core"] if item["key"] == "face")
    assert face["asset"]["id"] == first["id"]
    assert face["state"] == "approved"


def test_sprite_requires_exact_transparent_canvas(client):
    profile = data(client.post("/api/visuals/characters", json={"name": "Maya"}))
    wrong = upload(client, profile["id"], "calm__closed", image_bytes(), "sprite.png")
    assert wrong.status_code == 422
    valid = upload(
        client, profile["id"], "calm__closed",
        image_bytes((1280, 1536), transparent=True), "sprite.png",
    )
    assert valid.status_code == 200
    assert data(valid)["slot_key"] == "calm__closed"


def test_batch_mapping_imports_each_explicit_slot(client):
    profile = data(client.post("/api/visuals/characters", json={"name": "Maya"}))
    mapping = [
        {"file_index": 0, "slot_key": "portrait_calm"},
        {"file_index": 1, "slot_key": "portrait_smile"},
    ]
    response = client.post(
        f"/api/visuals/characters/{profile['id']}/assets/upload-batch",
        data={"mapping_json": json.dumps(mapping), "expected_identity_version": "1"},
        files=[
            ("pictures", ("one.jpg", image_bytes(image_format="JPEG"), "image/jpeg")),
            ("pictures", ("two.webp", image_bytes(image_format="WEBP"), "image/webp")),
        ],
    )
    results = data(response)
    assert [item["slot_key"] for item in results] == ["portrait_calm", "portrait_smile"]
    assert all(item["success"] and item["asset"]["review_state"] == "needs_review" for item in results)


def test_remove_unpinned_asset_deletes_row_and_file(client):
    profile = data(client.post("/api/visuals/characters", json={"name": "Maya"}))
    asset = data(upload(client, profile["id"], "portrait_calm", image_bytes()))
    with sqlite3.connect(settings.db_path) as connection:
        stored = connection.execute("SELECT path FROM character_assets WHERE id = ?", (asset["id"],)).fetchone()[0]
    removed = data(client.delete(f"/api/visuals/characters/{profile['id']}/assets/{asset['id']}"))
    assert removed == {"removed": asset["id"]}
    assert not __import__("pathlib").Path(stored).exists()

