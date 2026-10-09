"""Phase 32.6a contract tests for review-gated activity cutaway assets."""

from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image
from starlette.datastructures import UploadFile

from app.core.config import settings
from app.services.visuals import activity_analysis_service as analysis
from app.services.visuals import activity_library_service as activities


def image_upload(filename: str, color: tuple[int, int, int]) -> UploadFile:
    content = BytesIO()
    Image.new("RGB", (1280, 720), color).save(content, format="PNG")
    content.seek(0)
    return UploadFile(content, filename=filename)


@pytest.mark.asyncio
async def test_activity_analysis_uses_filename_fallback_when_vision_is_disabled(monkeypatch):
    monkeypatch.setattr(settings, "ACTIVITY_VISION_PROVIDER", "filename")
    result = await analysis.analyze_activity_image(b"not sent or decoded", "washing-dishes.png")
    assert result == {
        "activity": "washing dishes",
        "context_tags": [],
        "aliases": [],
        "confidence": 0.0,
        "source": "filename",
    }


@pytest.mark.asyncio
async def test_generic_inbox_import_starts_pending_and_keeps_metadata(db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    inbox = activities.inbox_dir()
    inbox.mkdir(parents=True)
    Image.new("RGB", (1280, 720), (20, 40, 60)).save(inbox / "generic__cooking__kitchen__01.png")

    result = await activities.import_inbox(db)
    assert result["rejected"] == [] and len(result["imported"]) == 1
    rows = await activities.list_activities(db)
    assert rows[0]["review_state"] == "pending"
    assert rows[0]["character_id"] is None
    assert rows[0]["activity"] == "cooking"
    assert rows[0]["context_tags"] == ["kitchen"]
    assert await activities.list_activities(db, review_state="approved") == []
    assert (await activities.content_path(db, rows[0]["id"])).is_file()


@pytest.mark.asyncio
async def test_import_inbox_recursively_accepts_scope_folders(db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    picture = activities.inbox_dir() / "generic" / "generic__doing-laundry__laundry-room__01.png"
    picture.parent.mkdir(parents=True)
    Image.new("RGB", (1280, 720), (80, 90, 100)).save(picture)

    result = await activities.import_inbox(db)

    assert result["rejected"] == [] and result["imported"][0]["file"] == picture.name
    rows = await activities.list_activities(db)
    assert rows[0]["activity"] == "doing laundry"
    assert rows[0]["context_tags"] == ["laundry room"]


@pytest.mark.asyncio
async def test_direct_upload_uses_form_metadata_and_starts_pending(db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)

    created = await activities.upload_activity(
        db,
        image_upload("friendly-name.png", (30, 70, 110)),
        {
            "character_id": None,
            "activity": "Chopping Vegetables",
            "context_tags": ["Kitchen", "Cooking"],
            "aliases": ["chop", "dice"],
            "variant": "01",
        },
    )

    assert created["review_state"] == "pending"
    assert created["activity"] == "chopping vegetables"
    assert created["context_tags"] == ["kitchen", "cooking"]
    assert created["aliases"] == ["chop", "dice"]
    assert created["character_id"] is None
    assert (await activities.content_path(db, created["id"])).is_file()


@pytest.mark.asyncio
async def test_invalid_or_duplicate_inbox_file_is_not_imported_twice(db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    inbox = activities.inbox_dir()
    inbox.mkdir(parents=True)
    picture = inbox / "generic__reading.png"
    Image.new("RGB", (1280, 720), (1, 2, 3)).save(picture)
    assert len((await activities.import_inbox(db))["imported"]) == 1
    second = await activities.import_inbox(db)
    assert second["imported"] == []
    assert "identical image" in second["rejected"][0]["reason"]
    (inbox / "generic__broken.png").write_text("not an image", encoding="utf-8")
    rejected = await activities.import_inbox(db)
    assert any("not a readable image" in item["reason"] for item in rejected["rejected"])
