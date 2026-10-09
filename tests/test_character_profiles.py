"""Character profile domain, readiness, lifecycle, and deletion rules."""

from __future__ import annotations

import pytest

from app.core.exceptions import ConflictError
from app.models.visuals import CharacterInput, CharacterPatch
from app.services.visuals import character_profile_service as profiles


@pytest.mark.asyncio
async def test_draft_autosave_resume_and_readiness_explanations(db):
    created = await profiles.create_profile(db, CharacterInput(name="Maya"))
    assert created["wizard_step"] == 0
    assert created["readiness"]["profile"]["state"] == "missing"
    assert "personality" in created["readiness"]["profile"]["missing"]
    assert created["readiness"]["voice"]["missing"] == ["voice_id"]
    assert created["readiness"]["visual"]["complete"] == 0

    saved = await profiles.patch_profile(db, created["id"], CharacterPatch(
        intro="A patient conversation guide",
        personality=["patient", "curious"],
        speaking_style="friendly",
        dialogue_behavior="Explains unfamiliar phrases with short examples.",
        default_voice_id="en-US-JennyNeural",
        wizard_step=4,
    ))
    await db.commit()
    resumed = await profiles.profile_view(db, created["id"])

    assert saved["wizard_step"] == resumed["wizard_step"] == 4
    assert resumed["personality"] == ["patient", "curious"]
    assert resumed["readiness"]["profile"]["state"] == "ready"
    assert resumed["readiness"]["voice"]["state"] == "ready"
    assert resumed["readiness"]["visual"]["state"] == "missing"


@pytest.mark.asyncio
async def test_active_name_unique_archive_restore_and_duplicate(db):
    source = await profiles.create_profile(db, CharacterInput(
        name="Maya", personality=["kind"], speaking_style="calm", default_voice_id="voice-a",
    ))
    with pytest.raises(ConflictError, match="already uses"):
        await profiles.create_profile(db, CharacterInput(name="  MAYA  "))

    duplicate = await profiles.duplicate_profile(db, source["id"])
    assert duplicate["id"] != source["id"]
    assert duplicate["name"] == "Maya copy"
    assert duplicate["assets"] == []
    assert duplicate["personality"] == ["kind"]

    archived = await profiles.archive_profile(db, source["id"])
    assert archived["lifecycle"] == "archived"
    replacement = await profiles.create_profile(db, CharacterInput(name="Maya"))
    assert replacement["id"] != source["id"]
    with pytest.raises(ConflictError, match="already uses"):
        await profiles.restore_profile(db, source["id"])


@pytest.mark.asyncio
async def test_dependency_report_blocks_seed_and_project_delete(db):
    profile = await profiles.create_profile(db, CharacterInput(name="Maya"))
    await db.execute(
        "INSERT INTO projects (id, name, status, created_at, updated_at) VALUES ('p-profile', 'P', 'draft', 'n', 'n')"
    )
    await db.execute(
        "INSERT INTO project_cast (project_id, speaker_index, character_id, profile_version) VALUES (?, 0, ?, 1)",
        ("p-profile", profile["id"]),
    )
    report = await profiles.dependencies(db, profile["id"])
    assert report["projects"] == 1
    assert report["can_delete"] is False
    with pytest.raises(ConflictError, match="Archive"):
        await profiles.permanent_delete(db, profile["id"])

    await db.execute("DELETE FROM project_cast WHERE character_id = ?", (profile["id"],))
    await db.execute("UPDATE characters SET is_seed = 1 WHERE id = ?", (profile["id"],))
    report = await profiles.dependencies(db, profile["id"])
    assert report["seed_profile"] is True
    with pytest.raises(ConflictError, match="Archive"):
        await profiles.permanent_delete(db, profile["id"])


@pytest.mark.asyncio
async def test_visual_readiness_uses_approved_current_slots(db):
    profile = await profiles.create_profile(db, CharacterInput(name="Maya"))
    now = "2026-10-10T00:00:00+00:00"
    for slot in profiles.CORE_VISUAL_SLOTS:
        await db.execute(
            "INSERT INTO character_assets (id, character_id, kind, path, approved, created_at, slot_key, "
            "review_state, identity_version, is_current, updated_at) VALUES (?, ?, ?, ?, 1, ?, ?, 'approved', 1, 1, ?)",
            (f"asset-{slot}", profile["id"], slot, f"/copy/{slot}.png", now, slot, now),
        )
    view = await profiles.profile_view(db, profile["id"])
    assert view["readiness"]["visual"] == {"state": "ready", "missing": [], "complete": 5, "total": 5}

