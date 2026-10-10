"""Profile-backed sprite tiers and deterministic renderer fallbacks."""

import pytest

from app.models.visuals import CharacterInput
from app.services.visuals import character_asset_service as assets
from app.services.visuals import character_profile_service as profiles
from app.services.visuals import sprite_plan, sprite_service
from app.services.visuals.image_upload import prepare_image
from tests.test_character_asset_slots import picture_bytes


async def add_approved(db, character_id: str, names: tuple[str, ...]) -> None:
    for name in names:
        prepared = await prepare_image(
            picture_bytes((1280, 1536), mode="RGBA"), assets.get_contract(name),
        )
        item = await assets.store_prepared(db, character_id, name, f"outside-{name}.png", prepared, 1)
        await assets.review_asset(db, character_id, item["id"], "approved")


@pytest.mark.asyncio
async def test_seven_approved_profile_sprites_enable_talking_starter(db, tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    profile = await profiles.create_profile(db, CharacterInput(name="Tier Hero"))
    await add_approved(db, profile["id"], sprite_service.TIER_1)
    sprite_set = await sprite_service.load_profile_set(db, profile["id"], 1)
    assert sprite_set is not None
    assert sprite_set["tier"] == 1
    assert set(sprite_set["names"]) == set(sprite_service.TIER_1)
    assert sprite_service.usable(sprite_set)
    assert all(sprite_service.picture_path(sprite_set, name).is_file() for name in sprite_set["names"])


@pytest.mark.asyncio
async def test_tier_two_and_three_upgrade_without_changing_starter(db, tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    profile = await profiles.create_profile(db, CharacterInput(name="Tier Upgrade"))
    await add_approved(db, profile["id"], sprite_service.TIER_2)
    tier_two = await sprite_service.load_profile_set(db, profile["id"], 1)
    assert tier_two["tier"] == 2
    assert set(sprite_service.TIER_1) <= set(tier_two["names"])

    remaining = tuple(name for name in sprite_service.ALL_NAMES if name not in sprite_service.TIER_2)
    await add_approved(db, profile["id"], remaining)
    tier_three = await sprite_service.load_profile_set(db, profile["id"], 1)
    assert tier_three["tier"] == 3
    assert tuple(name for name in sprite_service.ALL_NAMES if name not in tier_three["names"]) == ()


@pytest.mark.asyncio
async def test_pinned_old_identity_version_keeps_its_stale_approved_tier(db, tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    profile = await profiles.create_profile(db, CharacterInput(name="Pinned Hero"))
    await add_approved(db, profile["id"], sprite_service.TIER_1)
    replacement = await prepare_image(
        picture_bytes((1280, 1536), mode="RGBA"), assets.get_contract("calm__closed"),
    )
    await assets.store_prepared(
        db, profile["id"], "calm__closed", "new-base.png", replacement, 1, replace_identity=True,
    )
    pinned = await sprite_service.load_profile_set(db, profile["id"], 1)
    current = await sprite_service.load_profile_set(db, profile["id"], 2)
    assert pinned is not None and pinned["tier"] == 1
    assert current is None


def test_tier_one_plan_falls_back_without_requesting_optional_assets():
    names = set(sprite_service.TIER_1)
    lines = [{"startSec": 0.0, "endSec": 5.0, "text": "I think we should point over there.", "words": []}]
    plan = sprite_plan.build_plan(lines, [0], ["thinking"], {0: names, 1: names}, None, 30)
    assert plan[0]["expression"] == "calm"
    assert plan[0]["listenerExpression"] in {"calm", "smile"}
    assert plan[0]["gesture"] is None
    assert plan[0]["listenerGesture"] is None


def test_legacy_full_manifest_keeps_all_canonical_names(tmp_path, monkeypatch):
    from app.core.config import settings
    from tests.test_sprite_service import _figure

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    source = tmp_path / "source"
    files = {}
    for name in sprite_service.ALL_NAMES:
        _figure(source / f"{name}.png")
        files[name] = source / f"{name}.png"
    accepted, refused = sprite_service.check_folder(files)
    assert not refused
    sprite_service._write_set("legacy", files, accepted, lambda _path: [0.5, 0.22, 0.08, 0.07])
    loaded = sprite_service.load_set("legacy")
    assert loaded is not None
    assert set(loaded["names"]) == set(sprite_service.ALL_NAMES)
