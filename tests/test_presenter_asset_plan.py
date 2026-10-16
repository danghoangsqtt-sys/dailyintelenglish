"""Front21 contracts and image persistence; synthetic figure fixtures do not certify actual gesture art."""
import io
import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from backend.core.config import settings
from backend.core.exceptions import ConflictError, NotFoundError, ValidationError
from backend.library import character_profile_service as profiles
from backend.library import presenter_asset_plan as front
from backend.library import sprite_service, sprite_upload
from backend.schemas.visuals import ProfileQuickCreate
from tests.test_character_profiles_api import client, create, data  # noqa: F401


def figure_bytes() -> bytes:
    picture = Image.new("RGBA", (640, 1024))
    pen = ImageDraw.Draw(picture)
    pen.ellipse((260, 70, 380, 210), fill=(200, 160, 140, 255))
    pen.rectangle((235, 210, 405, 600), fill=(30, 60, 100, 255))
    pen.rectangle((230, 600, 300, 900), fill=(40, 40, 40, 255))
    pen.rectangle((340, 600, 410, 900), fill=(40, 40, 40, 255))
    pen.rectangle((215, 900, 300, 940), fill=(230, 50, 30, 255))
    pen.rectangle((340, 900, 425, 940), fill=(230, 50, 30, 255))
    output = io.BytesIO()
    picture.save(output, "PNG")
    return output.getvalue()


def upload(api: TestClient, cid: str, key: str, content: bytes) -> dict:
    return data(api.post(f"/api/visuals/profiles/{cid}/slots/{key}/upload?view=front",
                            files={"file": ("outside-picture.png", content, "image/png")}))


def approve(api: TestClient, cid: str, asset: dict) -> dict:
    return data(api.put(f"/api/visuals/profiles/{cid}/assets/{asset['id']}/review?view=front", json={"decision": "approve"}))


def test_registry21_dag_pairs_screen_directions_and_native29():
    assert len(front.SLOT_KEYS) == len(set(front.SLOT_KEYS)) == 21
    assert len(sprite_service.ALL_NAMES) == 29
    positions = {key: index for index, key in enumerate(front.SLOT_KEYS)}
    for slot in front.SLOTS:
        if slot["parent"]:
            assert positions[slot["parent"]] < positions[slot["key"]]
    assert sum(key.endswith("__open") for key in front.SLOT_KEYS) == 10
    profile = {"name": "Test", "gender": "female", "appearance": "dark hair", "outfit": "blue shirt"}
    assert "LEFT edge of the viewer's screen" in front.slot_prompt(profile, front.SLOTS_BY_KEY["gesture-point-left"])
    assert "RIGHT edge of the viewer's screen" in front.slot_prompt(profile, front.SLOTS_BY_KEY["gesture-point-right"])
    assert "hair-to-soles full body" in front.slot_prompt(profile, front.SLOTS_BY_KEY[front.BASE])
    for slot in front.SLOTS:
        prompt = front.slot_prompt(profile, slot)
        assert f"{slot['key']}.png" in prompt and "1280x1536" in prompt and "EXACT outfit" in prompt
        if slot["parent"]:
            assert f"{slot['parent']}.png" in prompt and "CHECK BEFORE SAVING" in prompt


def test_front_image_preparation_keeps_feet_native_crop_unchanged():
    with Image.open(io.BytesIO(figure_bytes())) as picture:
        front_image, _ = sprite_upload.prepare_front_base(picture)
        native_image, _ = sprite_upload.prepare_base(picture)
    pixels = np.asarray(front_image)
    red = (pixels[..., 0] > 200) & (pixels[..., 1] < 80) & (pixels[..., 3] > 200)
    assert red.sum() > 1000, "front must retain the deliberately red feet"
    old = np.asarray(native_image)
    assert not ((old[..., 0] > 200) & (old[..., 1] < 80) & (old[..., 3] > 200)).any()
    ys, xs = np.where(pixels[..., 3] > 20)
    assert ys.max() < 1536 - 8 and xs.min() >= 20 and xs.max() < 1260
    edited, _ = sprite_upload.prepare_edit(front_image, front_image, front_image, full_body=True)
    edited_pixels = np.asarray(edited)
    assert ((edited_pixels[..., 0] > 200) & (edited_pixels[..., 1] < 80) & (edited_pixels[..., 3] > 200)).sum() > 1000


def test_front_base_refuses_obviously_cropped_source_before_fitting():
    image = Image.new("RGBA", (640, 1024))
    ImageDraw.Draw(image).rectangle((200, 100, 440, 1023), fill=(30, 60, 100, 255))
    with pytest.raises(sprite_upload.UploadError, match="cut off"):
        sprite_upload.prepare_front_base(image)


def test_front_cards_and_prompt_pack_default_native_stays29(client):  # noqa: F811
    cid = create(client)["id"]
    assert len(data(client.get(f"/api/visuals/profiles/{cid}/slots"))["slots"]) == 29
    slots = data(client.get(f"/api/visuals/profiles/{cid}/slots?view=front"))
    assert len(slots["slots"]) == 21 and not slots["readiness"]["ready"] and slots["pack_revision"] is None
    assert "?view=front" in slots["slots"][1]["parent_input_url"]
    pack = client.get(f"/api/visuals/profiles/{cid}/prompt-pack.txt?view=front")
    assert pack.status_code == 200 and "FRONT21" in pack.text and "Screen directions" in pack.text
    assert client.get(f"/api/visuals/profiles/{cid}/slots?view=sideways").status_code == 422
    assert client.post(f"/api/visuals/profiles/{cid}/slots/smile__closed/upload?view=front",
                       files={"file": ("x.png", figure_bytes(), "image/png")}).status_code == 404


def test_front_requires_approved_parent_and_cross_view_review_is_rejected(client):  # noqa: F811
    cid = create(client)["id"]
    response = client.post(f"/api/visuals/profiles/{cid}/slots/calm__open/upload?view=front",
                           files={"file": ("x.png", figure_bytes(), "image/png")})
    assert response.status_code == 422
    base = upload(client, cid, front.BASE, figure_bytes())
    assert client.put(f"/api/visuals/profiles/{cid}/assets/{base['id']}/review", json={"decision": "approve"}).status_code == 422
    approve(client, cid, base)
    state = data(client.get(f"/api/visuals/profiles/{cid}"))["readiness"]
    assert state["front_presenter"]["have"] == 1 and state["full_sprite_pack"]["have"] == 0
    assert not sprite_service.sprite_dir(cid).exists()


async def test_two_uploads_compare_and_swap_and_keep_original_files(db):
    profile = await profiles.create_quick(db, ProfileQuickCreate(name="Presenter", gender="male", accent="american",
                                                                appearance="dark hair", outfit="blue shirt"))
    cid = profile["id"]
    snapshot = await front.upload_snapshot(db, cid, front.BASE)
    first = await front.stage_upload(snapshot, figure_bytes(), "first.png")
    second = await front.stage_upload(snapshot, figure_bytes(), "second.png")
    published = await front.publish_upload(db, snapshot, second)
    with pytest.raises(ConflictError):
        await front.publish_upload(db, snapshot, first)
    assert published["id"] == second["asset_id"]
    assert Path(second["path"]).is_file() and Path(first["path"]).is_file()


def test_full_synthetic_pack_pins_old_revision_after_replacement_and_stales_only_front(client):  # noqa: F811
    cid = create(client)["id"]
    base = upload(client, cid, front.BASE, figure_bytes())
    approve(client, cid, base)
    assets = {front.BASE: base}
    for slot in front.SLOTS[1:]:
        reference = client.get(f"/api/visuals/profiles/{cid}/slots/{slot['parent']}/input.png?view=front")
        assert reference.status_code == 200
        asset = upload(client, cid, slot["key"], reference.content)
        approve(client, cid, asset)
        assets[slot["key"]] = asset
    slots = data(client.get(f"/api/visuals/profiles/{cid}/slots?view=front"))
    assert slots["readiness"] == {"ready": True, "have": 21, "need": 21}
    revision = slots["pack_revision"]
    folder = settings.DATA_DIR / "library/characters" / cid / "v1/front"
    path = folder / "manifests" / (revision + ".json")
    saved = json.loads(path.read_text(encoding="utf-8"))
    old_files = {key: Path(asset["path"]).read_bytes() for key, asset in saved["pictures"].items()}
    assert client.portal.call(front.resolve_manifest, cid, 1, revision)["pack_revision"] == revision
    # Idempotent base approval must not invalidate open-mouth descendants of gestures.
    approve(client, cid, base)
    assert data(client.get(f"/api/visuals/profiles/{cid}/slots?view=front"))["readiness"]["ready"]
    # A changed gesture affects its open mouth only; the pinned old manifest remains valid.
    parent = client.get(f"/api/visuals/profiles/{cid}/slots/{front.BASE}/input.png?view=front")
    gesture = upload(client, cid, "gesture-talk", parent.content)
    approve(client, cid, gesture)
    state = data(client.get(f"/api/visuals/profiles/{cid}/slots?view=front"))
    assert state["readiness"]["have"] == 20
    states = {card["key"]: card["asset"]["review_state"] for card in state["slots"]}
    assert states["gesture-talk__open"] == "stale" and states["blink"] == "approved"
    assert client.portal.call(front.resolve_manifest, cid, 1, revision)["pack_revision"] == revision
    newer = upload(client, cid, front.BASE, figure_bytes())
    approve(client, cid, newer)
    changed = data(client.get(f"/api/visuals/profiles/{cid}/slots?view=front"))
    assert changed["readiness"]["have"] == 1 and not changed["readiness"]["ready"]
    assert all(Path(asset["path"]).read_bytes() == old_files[key] for key, asset in saved["pictures"].items())
    assert path.is_file() and len(data(client.get(f"/api/visuals/profiles/{cid}/slots"))["slots"]) == 29
    assert client.put(f"/api/visuals/profiles/{cid}/assets/{assets['calm__open']['id']}/review?view=front",
                      json={"decision": "approve"}).status_code == 409
    assert data(client.get(f"/api/visuals/profiles/{cid}"))["identity_version"] == 1
    assert client.portal.call(front.resolve_manifest, cid, 1, revision)["pack_revision"] == revision
    Path(saved["pictures"][front.BASE]["path"]).write_bytes(b"corrupt immutable fixture")
    with pytest.raises(NotFoundError):
        client.portal.call(front.resolve_manifest, cid, 1, revision)


def test_front_upload_stages_outside_shared_lock_and_cleans_failed_publication(client, monkeypatch):  # noqa: F811
    from backend.db.transactions import write_lock

    cid = create(client)["id"]
    original = front.stage_upload
    staged_paths = []

    async def observe_stage(snapshot, content, filename):
        assert not write_lock.locked(), "image processing must not stall all shared DB requests"
        staged = await original(snapshot, content, filename)
        staged_paths.append(Path(staged["path"]))
        return staged

    async def fail_publication(db, snapshot, staged):
        assert write_lock.locked(), "publication requires the shared write transaction"
        raise ConflictError("A newer upload won the race")

    monkeypatch.setattr(front, "stage_upload", observe_stage)
    monkeypatch.setattr(front, "publish_upload", fail_publication)
    response = client.post(f"/api/visuals/profiles/{cid}/slots/{front.BASE}/upload?view=front",
                           files={"file": ("x.png", figure_bytes(), "image/png")})
    assert response.status_code == 409
    assert staged_paths and all(not path.exists() for path in staged_paths)
    assert not data(client.get(f"/api/visuals/profiles/{cid}/slots?view=front"))["slots"][0]["asset"]


@pytest.mark.parametrize("identity,revision", [("../elsewhere", "a" * 64), ("valid", "../bad"), ("valid", "a" * 63)])
async def test_manifest_resolution_rejects_traversal(identity, revision):
    with pytest.raises(ValidationError):
        await front.resolve_manifest(identity, 1, revision)


async def test_missing_old_manifest_raises_typed_error(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with pytest.raises(NotFoundError):
        await front.resolve_manifest("valid", 1, "a" * 64)
