"""Front-facing presenter slots and immutable manifests, independent of native29."""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import re
import uuid
from pathlib import Path
from typing import Any

import aiosqlite
import numpy as np
from PIL import Image

from backend.core.config import settings
from backend.core.exceptions import ConflictError, NotFoundError, ValidationError
from backend.library import character_asset_service as native
from backend.library import sprite_service, sprite_upload
from backend.db.transactions import read_transaction

BASE = "calm__closed"
POSES = {
    "talk": "both hands open near waist height, palms up, explaining an idea",
    "point-left": "point to the LEFT edge of the viewer's screen with one index finger; screen-left, not the person's anatomical left",
    "point-right": "point to the RIGHT edge of the viewer's screen with one index finger; screen-right, not the person's anatomical right",
    "emphasize": "one open hand raised near chest height to emphasize an important point",
    "count-1": "hold up exactly ONE finger near the shoulder, clearly visible to the viewer",
    "count-2": "hold up exactly TWO fingers near the shoulder, clearly visible to the viewer",
    "count-3": "hold up exactly THREE fingers near the shoulder, clearly visible to the viewer",
    "think": "one hand lightly under the chin, thoughtful but looking directly at the camera",
    "wave": "one hand raised beside the shoulder with the open palm facing the viewer, a friendly wave",
}


def _slots() -> list[dict[str, Any]]:
    slots = [{"key": BASE, "group": "base", "tier": 1, "parent": None, "region": None}]
    for closed in (BASE, *(f"gesture-{pose}" for pose in POSES)):
        if closed != BASE:
            slots.append({"key": closed, "group": "gesture", "tier": 1, "parent": BASE, "region": "arms"})
        opened = "calm__open" if closed == BASE else closed + "__open"
        slots.append({"key": opened, "group": "mouth", "tier": 1, "parent": closed, "region": "mouth"})
    slots.append({"key": "blink", "group": "blink", "tier": 1, "parent": BASE, "region": "eyes"})
    return slots


SLOTS = _slots()
SLOTS_BY_KEY = {slot["key"]: slot for slot in SLOTS}
SLOT_KEYS = tuple(SLOTS_BY_KEY)
assert len(SLOT_KEYS) == 21


def slot_prompt(profile: dict, slot: dict) -> str:
    """Generate outside-AI instructions keeping identity, clothing and frontal view."""
    if slot["key"] == BASE:
        person = "man" if profile["gender"] == "male" else "woman"
        return (f"Use the attached reference of {profile['name']} to keep the same recognizable face, hair and clothing. "
                f"Photorealistic adult {person}. Nationality: {profile.get('nationality') or 'as in the reference'}. Appearance: {profile['appearance']}. "
                f"Wearing exactly {profile['outfit']}. Standing upright, shoulders and torso square to the viewer, "
                "head facing straight forward, eyes looking directly at the camera. Calm friendly face, lips closed, "
                "arms relaxed. Full body from hair to soles: head, feet and all fingers fully inside the picture with "
                "clear margins. Portrait canvas (5:6). Soft even studio lighting. Flat pure green background #00B140, "
                "no floor, shadow or gradient. Do not add text, props or logos; preserve the clothing markings explicitly "
                "described above. Do not use the reference's three-quarter body angle.")
    if slot["region"] == "arms":
        change = POSES[slot["key"].removeprefix("gesture-")]
    elif slot["region"] == "mouth":
        change = "part only the lips naturally during speech, showing some teeth; keep the same hand gesture"
    else:
        change = "close both eyes for a natural blink, keeping the lips closed"
    return (f"Edit the attached FRONT-facing picture of {profile['name']}. Change only the {slot['region']}: {change}. "
            "Make the change clearly visible, with every finger inside the canvas. Keep face identity, hairstyle, outfit, "
            "camera-facing head/torso, full-body scale and position, background and lighting exactly unchanged. "
            "Look directly at the viewer; never rotate into a three-quarter view. Do not mirror the picture.")


def _root(character_id: str, version: int) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", character_id):
        raise ValidationError("Invalid character identity")
    return settings.DATA_DIR / "library" / "characters" / character_id / f"v{version}" / "front"


async def _current(db: aiosqlite.Connection, row: dict, key: str) -> dict | None:
    return await native._current(db, row, key, "front")


async def list_slots(db: aiosqlite.Connection, character_id: str) -> dict[str, Any]:
    """Expose21 front cards with reference availability and exact asset identity."""
    row = await native._profile_row(db, character_id)
    identity = await native._current(db, row, BASE)
    identity_url = native._asset_view(identity)["url"] if identity and identity["review_state"] == "approved" else None
    cards = []
    for slot in SLOTS:
        asset = await _current(db, row, slot["key"])
        parent = await _current(db, row, slot["parent"]) if slot["parent"] else None
        cards.append({**slot, "file_name": slot["key"] + ".png", "prompt": slot_prompt(native._profile_view(row), slot),
                      "identity_reference_url": identity_url if slot["key"] == BASE else None,
                      "region_text": native.REGIONS.get(slot["region"] or "", ""),
                      "parent_ready": not slot["parent"] or bool(parent and parent["review_state"] == "approved"),
                      "parent_input_url": f"/api/visuals/profiles/{character_id}/slots/{slot['parent']}/input.png?view=front" if slot["parent"] else None,
                      "asset": native._asset_view(asset)})
    ready = sum(bool(card["asset"] and card["asset"]["review_state"] == "approved") for card in cards)
    snapshot = await manifest_snapshot(db, character_id) if ready == 21 else None
    return {"character_id": character_id, "identity_version": row["identity_version"], "view": "front", "slots": cards,
            "pack_revision": snapshot["pack_revision"] if snapshot else None,
            "readiness": {"ready": ready == 21, "have": ready, "need": 21}}


def _prepare(key: str, content: bytes, parent: dict | None, base: dict | None) -> tuple[Image.Image, dict]:
    picture = sprite_upload.open_upload(content)
    if key == BASE:
        canvas, details = sprite_upload.prepare_front_base(picture)
    else:
        if not parent or not base:
            raise ValidationError("Approve the front base and parent picture first")
        with Image.open(native.stored_path(parent["path"])) as reference, Image.open(native.stored_path(base["path"])) as neutral:
            neutral_rgba = neutral.convert("RGBA")
            canvas, details = sprite_upload.prepare_edit(picture, reference.convert("RGBA"), neutral_rgba, full_body=True)
            result = sprite_service.measure(np.asarray(canvas), sprite_service.Reference(np.asarray(neutral_rgba)),
                                            key.startswith("gesture-"))
            if result["problems"]:
                raise ValidationError("; ".join(result["problems"]))
    return canvas, {**details, "problems": [], "front_parent_id": parent["id"] if parent else None,
                    "front_base_id": base["id"] if base else None}


async def upload_snapshot(db: aiosqlite.Connection, character_id: str, slot_key: str) -> dict:
    """Read identity and reference revisions before releasing the shared lock for image processing."""
    if slot_key not in SLOTS_BY_KEY:
        raise NotFoundError("Unknown front picture slot")
    row = await native._profile_row(db, character_id)
    slot = SLOTS_BY_KEY[slot_key]
    parent = await _current(db, row, slot["parent"]) if slot["parent"] else None
    base = await _current(db, row, BASE)
    if slot_key != BASE and (not parent or parent["review_state"] != "approved" or not base or base["review_state"] != "approved"):
        raise ValidationError("Approve the current front base and parent picture first")
    previous = await _current(db, row, slot_key)
    return {"row": row, "slot_key": slot_key, "parent": parent, "base": base,
            "previous_id": previous["id"] if previous else None}


async def stage_upload(snapshot: dict, content: bytes, original_filename: str | None) -> dict:
    """Prepare and hash a unique asset outside every DB transaction; existing files stay immutable."""
    row, slot_key = snapshot["row"], snapshot["slot_key"]
    try:
        canvas, details = await asyncio.to_thread(_prepare, slot_key, content, snapshot["parent"], snapshot["base"])
    except sprite_upload.UploadError as exc:
        raise ValidationError(str(exc)) from exc
    asset_id, now = str(uuid.uuid4()), native._now()
    folder = _root(row["id"], row["identity_version"]) / "assets" / asset_id
    final = folder / (slot_key + ".png")
    await asyncio.to_thread(folder.mkdir, parents=True, exist_ok=True)
    await asyncio.to_thread(canvas.save, final, "PNG")
    details["content_hash"] = await asyncio.to_thread(lambda: hashlib.sha256(final.read_bytes()).hexdigest())
    return {"asset_id": asset_id, "path": str(final), "created_at": now, "details": details,
            "filename": (original_filename or "")[:200]}


async def publish_upload(db: aiosqlite.Connection, snapshot: dict, staged: dict) -> dict:
    """CAS identity/base/parent/current slot under the short publication transaction."""
    row, key = snapshot["row"], snapshot["slot_key"]
    current = await upload_snapshot(db, row["id"], key)
    def signature(value: dict) -> tuple:
        return (value["row"]["identity_version"], value["previous_id"],
                (value["base"] or {}).get("id"), (value["parent"] or {}).get("id"),
                (value["base"] or {}).get("review_state"), (value["parent"] or {}).get("review_state"))
    if signature(snapshot) != signature(current):
        raise ConflictError("The front identity or reference changed during processing; reload and retry")
    await db.execute("UPDATE character_assets SET is_current=0 WHERE character_id=? AND identity_version=? "
                         "AND facing='front' AND slot_key=? AND is_current=1", (row["id"], row["identity_version"], "sprite/" + key))
    await db.execute("INSERT INTO character_assets (id,character_id,kind,path,approved,created_at,slot_key,source,"
                         "original_filename,review_state,validation_json,identity_version,is_current,updated_at,facing) "
                         "VALUES (?,?,'sprite',?,0,?,?,'upload',?,'needs_review',?,?,1,?,'front')",
                         (staged["asset_id"], row["id"], staged["path"], staged["created_at"], "sprite/" + key,
                          staged["filename"], json.dumps(staged["details"]), row["identity_version"], staged["created_at"]))
    return native._asset_view(await native._asset_row(db, staged["asset_id"])) | {"slot": key, "view": "front"}


async def review(db: aiosqlite.Connection, character_id: str, asset_id: str, decision: str,
                 refresh: bool = False) -> dict[str, Any]:
    """Review only current front assets; changed reference invalidates descendants, never native assets."""
    asset = await native._asset_row(db, asset_id)
    row = await native._profile_row(db, character_id)
    if asset["character_id"] != character_id or asset["facing"] != "front" or not asset["is_current"] or asset["identity_version"] != row["identity_version"]:
        raise ConflictError("Only a current front picture of this identity can be reviewed")
    key = asset["slot_key"].split("/", 1)[1]
    if decision == "approve" and key != BASE:
        base = await _current(db, row, BASE)
        parent = await _current(db, row, SLOTS_BY_KEY[key]["parent"])
        details = json.loads(asset["validation_json"])
        if not base or not parent or base["review_state"] != "approved" or parent["review_state"] != "approved" or details.get("front_base_id") != base["id"] or details.get("front_parent_id") != parent["id"]:
            raise ConflictError("The front reference changed; import this picture again from its current approved parent")
    state = {"approve": "approved", "reject": "rejected"}[decision]
    if state == "approved":
        descendants = [slot["key"] for slot in SLOTS if slot["key"] != key and (key == BASE or slot["parent"] == key)]
        reference_key = "front_base_id" if key == BASE else "front_parent_id"
        for child in descendants:
            await db.execute("UPDATE character_assets SET review_state='stale',approved=0,updated_at=? WHERE character_id=? "
                             "AND identity_version=? AND facing='front' AND is_current=1 AND slot_key=? "
                             "AND review_state='approved' AND json_extract(validation_json,?) IS NOT ?",
                             (native._now(), character_id, row["identity_version"], "sprite/" + child, "$." + reference_key, asset_id))
    await db.execute("UPDATE character_assets SET review_state=?,approved=?,updated_at=? WHERE id=?",
                     (state, int(state == "approved"), native._now(), asset_id))
    return native._asset_view(await native._asset_row(db, asset_id)) | {"slot": key, "view": "front"}


async def manifest_snapshot(db: aiosqlite.Connection, character_id: str) -> dict | None:
    """Snapshot all21 approved assets and immutable paths without filesystem I/O."""
    row = await native._profile_row(db, character_id)
    assets = {}
    for key in SLOT_KEYS:
        asset = await _current(db, row, key)
        if not asset or asset["review_state"] != "approved":
            return None
        assets[key] = {"asset_id": asset["id"], "path": asset["path"],
                       "content_hash": json.loads(asset["validation_json"])["content_hash"]}
    payload = {"schema_version": 1, "profile_id": character_id, "identity_version": row["identity_version"], "view": "front", "pictures": assets}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    revision = hashlib.sha256(canonical.encode()).hexdigest()
    payload["pack_revision"] = revision
    return payload


async def manifest(db: aiosqlite.Connection, character_id: str) -> dict | None:
    """Write an immutable revision-addressed manifest outside the DB lock after snapshotting it."""
    async with read_transaction():
        payload = await manifest_snapshot(db, character_id)
    if payload is None:
        return None
    target = _root(character_id, payload["identity_version"]) / "manifests" / (payload["pack_revision"] + ".json")

    def store() -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            temporary = target.with_suffix("." + uuid.uuid4().hex + ".tmp")
            temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            temporary.replace(target)
    await asyncio.to_thread(store)
    return payload


async def parent_input(db: aiosqlite.Connection, character_id: str, slot_key: str) -> bytes:
    """Download an approved front reference on green for editing in an outside AI."""
    if slot_key not in SLOTS_BY_KEY:
        raise NotFoundError("Unknown front picture slot")
    row = await native._profile_row(db, character_id)
    asset = await _current(db, row, slot_key)
    if not asset or asset["review_state"] != "approved":
        raise NotFoundError("Approve this front picture first")

    def render() -> bytes:
        with Image.open(native.stored_path(asset["path"])) as picture:
            image = sprite_upload.parent_on_green(picture.convert("RGBA"))
        output = io.BytesIO()
        image.save(output, "PNG")
        return output.getvalue()
    return await asyncio.to_thread(render)


async def approve_many(db: aiosqlite.Connection, character_id: str, asset_ids: list[str]) -> list[dict]:
    """Approve parent slots before children; preserve each reference validation."""
    order = {key: index for index, key in enumerate(SLOT_KEYS)}
    assets = [await native._asset_row(db, asset_id) for asset_id in asset_ids]
    assets.sort(key=lambda asset: order.get(asset["slot_key"].split("/", 1)[-1], 999))
    results = [await review(db, character_id, asset["id"], "approve", refresh=False) for asset in assets]
    return results


async def resolve_manifest(character_id: str, identity_version: int, revision: str) -> dict:
    """Resolve a pinned old front pack and check every immutable file before production consumes it."""
    if identity_version < 1 or not re.fullmatch(r"[a-f0-9]{64}", revision):
        raise ValidationError("Invalid front pack revision")
    target = _root(character_id, identity_version) / "manifests" / (revision + ".json")
    def resolve() -> dict:
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
            claimed = payload.pop("pack_revision")
            actual = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            if claimed != revision or actual != revision or payload["profile_id"] != character_id or payload["identity_version"] != identity_version or payload["view"] != "front" or set(payload["pictures"]) != set(SLOT_KEYS):
                raise ValueError("manifest identity mismatch")
            for asset in payload["pictures"].values():
                path = native.stored_path(asset["path"]).resolve()
                if not path.is_relative_to(_root(character_id, identity_version).resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != asset["content_hash"]:
                    raise ValueError("immutable front asset changed")
            payload["pack_revision"] = revision
            return payload
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise NotFoundError("The pinned front pack is missing or changed; import/review the required assets") from exc
    return await asyncio.to_thread(resolve)


async def prompt_pack_text(db: aiosqlite.Connection, character_id: str) -> str:
    """Export the front21 recipe, references and explicit viewer-facing direction rules."""
    slots = await list_slots(db, character_id)
    lines = ["FRONT21 — full-body presenter, looking directly at the viewer", "Approve calm__closed first; edit its children using the reference shown. Screen directions refer to the viewer.", ""]
    for slot in slots["slots"]:
        lines.extend(["Slot: " + slot["file_name"], "Reference: " + (slot["parent"] or "existing character identity/outfit reference"), slot["prompt"], ""])
    return "\n".join(lines)
