"""Canonical character asset registry, review, stale versions, and prompt packs."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from app.models.visuals import CharacterInput
from app.services.visuals import character_asset_service as assets
from app.services.visuals import character_profile_service as profiles
from app.services.visuals.image_upload import prepare_image


def picture_bytes(size=(640, 640), mode="RGB", image_format="PNG") -> bytes:
    color = (40, 120, 80, 0) if mode == "RGBA" else (40, 120, 80)
    image = Image.new(mode, size, color)
    if mode == "RGBA":
        opaque = Image.new("RGBA", (600, 1300), (200, 100, 80, 255))
        image.alpha_composite(opaque, (340, 100))
    output = io.BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


@pytest.mark.asyncio
async def test_slot_registry_has_core_and_all_sprite_tiers(db):
    profile = await profiles.create_profile(db, CharacterInput(name="Maya"))
    result = await assets.asset_slots(db, profile["id"])
    assert len(result["groups"]["core"]) == 5
    assert len(result["groups"]["tier_1"]) == 7
    assert sum(len(result["groups"][name]) for name in ("tier_1", "tier_2", "tier_3")) == 29
    assert next(item for item in result["groups"]["tier_1"] if item["key"] == "calm__closed")["state"] == "missing"


@pytest.mark.asyncio
async def test_review_and_identity_replacement_keep_old_version(db, tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    profile = await profiles.create_profile(db, CharacterInput(name="Maya"))
    first = await prepare_image(picture_bytes(), assets.get_contract("face"))
    first_asset = await assets.store_prepared(db, profile["id"], "face", "first.jpg", first, 1)
    reviewed = await assets.review_asset(db, profile["id"], first_asset["id"], "approved")
    assert reviewed["review_state"] == "approved"
    first_path = await (await db.execute(
        "SELECT path FROM character_assets WHERE id = ?", (first_asset["id"],)
    )).fetchone()

    second = await prepare_image(picture_bytes(size=(700, 700)), assets.get_contract("face"))
    replacement = await assets.store_prepared(
        db, profile["id"], "face", "replacement.webp", second, 1, replace_identity=True,
    )
    row = await (await db.execute(
        "SELECT identity_version FROM characters WHERE id = ?", (profile["id"],)
    )).fetchone()
    old = await (await db.execute(
        "SELECT review_state, approved FROM character_assets WHERE id = ?", (first_asset["id"],)
    )).fetchone()

    assert row[0] == replacement["identity_version"] == 2
    assert tuple(old) == ("stale", 0)
    assert first_path[0] != replacement.get("path")
    assert Path(first_path[0]).is_file()
    assert replacement["review_state"] == "needs_review"


@pytest.mark.asyncio
async def test_prompt_pack_contains_contract_and_approved_reference(db, tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    profile = await profiles.create_profile(db, CharacterInput(name="Maya"))
    prepared = await prepare_image(picture_bytes(), assets.get_contract("face"))
    asset = await assets.store_prepared(db, profile["id"], "face", "face.png", prepared, 1)
    await assets.review_asset(db, profile["id"], asset["id"], "approved")
    filename, content = await assets.prompt_pack(db, profile["id"])
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        names = set(archive.namelist())
        assert {"README.md", "slots.json", "references/face.png"} <= names
        assert "Maya" in archive.read("README.md").decode("utf-8")
    assert filename == "maya-prompt-pack.zip"

