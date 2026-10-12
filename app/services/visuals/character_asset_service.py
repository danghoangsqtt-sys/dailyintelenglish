"""Phase 33 (Task 33.3, D84/D86): the picture slots of a character profile, their prompts, uploads and review.

Every profile has the 29 talking-sprite slots of `data/library/sprites_inbox` (7 expressions x closed/open mouth, `blink`,
7 gestures x closed/open mouth). Each slot card shows the picture to attach in the outside AI (its parent), the region to
select, the prompt, and a drop zone. A dropped file is stored under the slot's canonical name whatever it was called, and
waits for the owner's review. The four core pictures (full body and three portraits) are derived from approved sprites, so
the owner only makes the 29 sprite pictures.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite
import numpy as np
from PIL import Image, ImageOps

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.services.visuals import sprite_service, sprite_upload

BASE = "calm__closed"
# Owner feedback 2026-10-12: a short "a warm gentle smile" left the face almost unchanged. Each change now names what must
# visibly differ, and says that the change has to be clearly visible.
EXPRESSION_LOOKS = {
    "calm": "a calm friendly face",
    "smile": ("a clear, warm smile with the lips closed: the corners of the mouth turned well up, the cheeks lifted, small "
              "smile lines at the outer corners of the eyes"),
    "laugh": ("a happy laugh with the lips closed: a big wide closed-mouth grin, the cheeks raised high, the eyes narrowed "
              "into happy curved crescents"),
    "surprised": ("surprised: the eyes opened very wide with white showing above the irises, the eyebrows raised high, the "
                  "forehead lifted, the lips closed and relaxed"),
    "thinking": ("thoughtful: the eyes looking up and to the side, one eyebrow raised higher than the other, the lips pressed "
                 "together and pulled a little to one side"),
    "worried": ("worried: the inner ends of the eyebrows raised and drawn together with a small frown line between them, "
                "the eyes a little wider, the lips closed and slightly tense"),
    "serious": ("serious: the eyebrows level and slightly lowered, a steady focused look, no smile at all, the lips closed "
                "in a straight line"),
}
OPEN_MOUTHS = {
    "calm": ("open the mouth as when saying \"ah\" in the middle of a sentence: the lips parted about a finger's width, the "
             "upper teeth visible, the jaw slightly lowered; natural speech, not a yawn"),
    "smile": "keep the same smile and part the lips while speaking: the upper and lower teeth clearly visible",
    "laugh": "turn the grin into an open laugh: the mouth wide open, the upper teeth fully visible",
    "surprised": 'open the mouth into a small round "oh", the lips rounded and parted',
    "thinking": 'part the lips slightly as if saying "hmm", the teeth just visible',
    "worried": "part the lips as if speaking, the upper teeth just visible, the worried tension kept",
    "serious": "part the lips as if speaking calmly, the upper teeth just visible",
}
# {side}: the partner's side of the image (the way the figure faces); a gesture uses the hand on that side.
GESTURE_POSES = {
    "talk": "the hand on the {side} side raised to chest height with the palm open and turned up, as if explaining something",
    "point": "the hand on the {side} side pointing toward the {side} with the index finger, the elbow bent so the hand stays well inside the picture",
    "think": "one hand resting lightly under the chin with the index finger along the cheek, the other arm folded across the waist",
    "open": "both hands open at waist height with the palms up, close to the body, in a small friendly shrug",
    "heart": "one hand resting flat on the chest over the heart, sincere, as when saying thank you",
    "listen": "both hands lightly clasped together in front of the body at waist height, attentive",
    "wave": "the hand on the {side} side raised beside the shoulder with the palm open toward the camera, waving hello",
}
REGIONS = {
    "face": "the whole face from the eyebrows to the chin (not the hair, ears or neck)",
    "eyes": "only the two eyes",
    "mouth": "only the mouth (both lips and a little skin around them; not the nose, cheeks or chin)",
    "arms": "only the two arms and hands, plus the green area where the hand will go (not the head, neck or chest)",
}
CHANGE_WHAT = {
    "face": "Change only the facial expression.",
    "eyes": "Change only the eyes.",
    "mouth": "Change only the mouth.",
    "arms": "Change only the arms and hands.",
}
KEEP = {
    "face": "the face shape and identity, the hair, the head position and angle",
    "eyes": "the eyebrows, the mouth, the whole face and identity, the hair, the head position and angle",
    "mouth": "the eyes, eyebrows and the rest of the expression, the face and identity, the hair, the head position and angle",
    "arms": "the head, the face and its expression, the hair, the body angle",
}


def _slot(key: str, group: str, tier: int, parent: str | None, region: str | None, change: str) -> dict[str, Any]:
    return {"key": key, "group": group, "tier": tier, "parent": parent, "region": region, "change": change}


def _build_slots() -> list[dict[str, Any]]:
    slots = [_slot(BASE, "base", 1, None, None, EXPRESSION_LOOKS["calm"] + ", lips closed")]
    for expression, look in EXPRESSION_LOOKS.items():
        tier = 1 if expression in ("calm", "smile", "surprised") else 2
        if expression != "calm":
            slots.append(_slot(f"{expression}__closed", "expression", tier, BASE, "face", f"{look}."))
        slots.append(_slot(f"{expression}__open", "mouth", tier, f"{expression}__closed", "mouth",
                           OPEN_MOUTHS[expression] + "."))
    slots.append(_slot("blink", "blink", 1, BASE, "eyes", "both eyes fully closed, as in the middle of a blink, the eyelids relaxed."))
    for gesture, pose in GESTURE_POSES.items():
        slots.append(_slot(f"gesture-{gesture}", "gesture", 3, BASE, "arms", pose + "."))
        slots.append(_slot(f"gesture-{gesture}__open", "mouth", 3, f"gesture-{gesture}", "mouth",
                           "part the lips as if speaking: the upper teeth visible, the jaw slightly lowered."))
    return slots


SLOTS = _build_slots()
SLOT_KEYS = tuple(slot["key"] for slot in SLOTS)
SLOTS_BY_KEY = {slot["key"]: slot for slot in SLOTS}
assert set(SLOT_KEYS) == set(sprite_service.ALL_NAMES), "the slot registry must match the sprite contract"
DERIVED_CORE = {"full_body": BASE, "portrait_calm": BASE, "portrait_smile": "smile__closed",
                "portrait_surprised": "surprised__closed"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def base_prompt(profile: dict) -> str:
    """The prompt of the base picture, written from the Quick create fields (D79) with the facing rule (D82)."""
    side = "right" if profile["sprite_facing"] == "right" else "left"
    who = f"{profile['nationality']} " if profile.get("nationality") else ""
    person = "man" if profile["gender"] == "male" else "woman"
    # The framing and pose of the Alex/Lina packs: head to mid-thigh filling the height, a clear three-quarter turn toward the
    # partner. Owner feedback 2026-10-12: "slightly" was ignored by the image AI (a full-length or straight-to-camera picture).
    # Turning toward the picture's right brings the person's own right shoulder toward the camera, and the other way round.
    shoulder = "right" if side == "right" else "left"
    return (f"A three-quarter length portrait of an adult {who}{person} named {profile['name']}: {profile['appearance']}. "
            f"Wearing {profile['outfit']}. {EXPRESSION_LOOKS['calm'].capitalize()}, lips closed, arms relaxed at the sides. "
            f"Three-quarter view: the whole body and the head are turned about 30 degrees toward the {side} side of the "
            f"image, so the {shoulder} shoulder is nearer the camera. The eyes look toward the {side} edge of the image, as "
            f"if talking to someone standing on the {side}; not looking at the camera. "
            "Framed from the top of the head to mid-thigh: the figure fills the picture height, the head close to the top "
            "edge, the legs cut at mid-thigh by the bottom edge, centred. Portrait format (5:6). Soft even studio lighting. "
            "A flat pure green background (#00B140): no floor, no shadow, no gradient. Photorealistic. No text, no logos, "
            "no props.")


def slot_prompt(profile: dict, slot: dict) -> str:
    """A region edit prompt that stands on its own: what to edit, what the change must look like (clearly visible), and
    everything that must stay the same -- even when the outside AI is used without selecting the region."""
    if slot["key"] == BASE:
        return base_prompt(profile)
    side = "right" if profile["sprite_facing"] == "right" else "left"
    person = "man" if profile["gender"] == "male" else "woman"
    change = slot["change"].format(side=side).rstrip(".")
    return (f"Edit the attached picture of {profile['name']}, the same {person}. {CHANGE_WHAT[slot['region']]} "
            f"New look: {change}. The change must be clearly visible at a glance. "
            f"Keep everything else exactly as it is in the attached picture: {KEEP[slot['region']]}, "
            f"{'the legs' if slot['region'] == 'arms' else 'the body pose, the hands'}, the clothes, the flat green "
            "background, the framing and the image size. Do not redraw the picture.")


def stored_path(path: str) -> Path:
    r"""An asset path as stored: older rows hold `data\library\...` relative to the app folder; read them under the current
    data folder (the packaged app and the tests do not keep their data in ./data)."""
    candidate = Path(path)
    if not candidate.is_absolute() and candidate.parts and candidate.parts[0] == "data":
        return settings.DATA_DIR.joinpath(*candidate.parts[1:])
    return candidate


async def register_legacy_sprites(db: aiosqlite.Connection) -> int:
    """Startup, idempotent: a character with a sprite pack on disk (Phase 32 `sprite_set.json`) but no sprite slot rows yet
    gets one approved row per picture, so its slot cards show the pictures it already has. Returns the rows added."""
    cursor = await db.execute("SELECT id, identity_version FROM characters")
    added, now = 0, _now()
    for character in await cursor.fetchall():
        character_id, version = character[0], character[1]
        existing = await db.execute(
            "SELECT 1 FROM character_assets WHERE character_id = ? AND kind = 'sprite' LIMIT 1", (character_id,))
        if await existing.fetchone() is not None:
            continue
        sprite_set = sprite_service.load_set(character_id)
        if not sprite_set:
            continue
        folder = sprite_service.sprite_dir(character_id)
        for name in sorted(sprite_set.get("pictures", {})):
            picture = folder / f"{name}.png"
            if name not in SLOTS_BY_KEY or not picture.is_file():
                continue
            await db.execute(
                "INSERT INTO character_assets (id, character_id, kind, path, approved, created_at, slot_key, source, "
                "original_filename, review_state, identity_version, is_current, updated_at, facing) "
                "VALUES (?, ?, 'sprite', ?, 1, ?, ?, 'legacy_migration', ?, 'approved', ?, 1, ?, 'native')",
                (str(uuid.uuid4()), character_id, str(picture), now, f"sprite/{name}", picture.name, version, now))
            added += 1
    return added


def _asset_dir(character_id: str, identity_version: int, facing: str) -> Path:
    return settings.DATA_DIR / "library" / "characters" / character_id / f"v{identity_version}" / facing


async def _profile_row(db: aiosqlite.Connection, character_id: str) -> dict:
    cursor = await db.execute("SELECT * FROM characters WHERE id = ?", (character_id,))
    row = await cursor.fetchone()
    if row is None:
        raise NotFoundError("Character profile not found")
    return dict(row)


async def _current(db: aiosqlite.Connection, row: dict, slot_key: str, facing: str = "native") -> dict | None:
    cursor = await db.execute(
        "SELECT * FROM character_assets WHERE character_id = ? AND identity_version = ? AND facing = ? AND slot_key = ? "
        "AND is_current = 1",
        (row["id"], row["identity_version"], facing, f"sprite/{slot_key}"),
    )
    found = await cursor.fetchone()
    return dict(found) if found else None


def _profile_view(row: dict) -> dict:
    return {"name": row["name"], "gender": row["gender"], "nationality": row["ethnicity"], "appearance": row["appearance"],
            "outfit": row["outfit"], "sprite_facing": row["sprite_facing"] or ("right" if row["gender"] == "male" else "left")}


def _asset_view(asset: dict | None) -> dict | None:
    if asset is None:
        return None
    return {"id": asset["id"], "review_state": asset["review_state"], "original_filename": asset["original_filename"],
            "validation": json.loads(asset["validation_json"] or "{}"), "updated_at": asset["updated_at"],
            "url": f"/api/visuals/profiles/{asset['character_id']}/assets/{asset['id']}/content"}


async def list_slots(db: aiosqlite.Connection, character_id: str) -> dict[str, Any]:
    row = await _profile_row(db, character_id)
    profile = _profile_view(row)
    cards = []
    for slot in SLOTS:
        asset = await _current(db, row, slot["key"])
        parent = await _current(db, row, slot["parent"]) if slot["parent"] else None
        cards.append({
            **slot, "file_name": f"{slot['key']}.png", "prompt": slot_prompt(profile, slot),
            "region_text": REGIONS.get(slot["region"] or "", ""),
            "parent_ready": slot["parent"] is None or bool(parent and parent["review_state"] == "approved"),
            "parent_input_url": (f"/api/visuals/profiles/{character_id}/slots/{slot['parent']}/input.png"
                                 if slot["parent"] else None),
            "asset": _asset_view(asset),
        })
    return {"character_id": character_id, "identity_version": row["identity_version"], "slots": cards}


def _validate(slot_key: str, canvas: Image.Image, base: Image.Image | None) -> dict:
    """The sprite checks of `sprite_service` against the approved base (the base itself has nothing to compare with)."""
    if slot_key == BASE or base is None:
        return {"problems": []}
    rgba = np.asarray(canvas.convert("RGBA"))
    result = sprite_service.measure(rgba, sprite_service.Reference(np.asarray(base.convert("RGBA"))),
                                    slot_key.startswith("gesture-"))
    return {"problems": list(result.get("problems", []))}


def _process_sync(slot_key: str, content: bytes, parent_path: str | None, base_path: str | None) -> tuple[Image.Image, dict]:
    picture = sprite_upload.open_upload(content)
    if slot_key == BASE:
        canvas, info = sprite_upload.prepare_base(picture)
        base = None
    else:
        if parent_path is None or base_path is None:
            raise sprite_upload.UploadError(f"approve the {SLOTS_BY_KEY[slot_key]['parent']} picture first: "
                                            "this picture is an edit of it")
        with Image.open(parent_path) as parent, Image.open(base_path) as base_file:
            parent_rgba, base = parent.convert("RGBA"), base_file.convert("RGBA")
        canvas, info = sprite_upload.prepare_edit(picture, parent_rgba, base)
    return canvas, {**info, **_validate(slot_key, canvas, base)}


async def upload(db: aiosqlite.Connection, character_id: str, slot_key: str, content: bytes,
                 original_filename: str | None) -> dict[str, Any]:
    """Store an outside-AI picture in its slot (D84): renamed to `<slot>.png`, aligned, checked, `needs_review`.

    The picture is processed and written to a temporary file before any database change; the previous asset of the slot is
    only retired (is_current = 0) in the same transaction that adds the new row, so a failed upload changes nothing.
    """
    if slot_key not in SLOTS_BY_KEY:
        raise NotFoundError(f"Unknown picture slot {slot_key!r}")
    row = await _profile_row(db, character_id)
    slot = SLOTS_BY_KEY[slot_key]
    parent = await _current(db, row, slot["parent"]) if slot["parent"] else None
    base = await _current(db, row, BASE)
    parent_ok = parent if parent and parent["review_state"] == "approved" else None
    base_ok = base if base and base["review_state"] == "approved" else None
    try:
        canvas, validation = await asyncio.to_thread(
            _process_sync, slot_key, content, str(stored_path(parent_ok["path"])) if parent_ok else None,
            str(stored_path(base_ok["path"])) if base_ok else None)
    except sprite_upload.UploadError as exc:
        raise ValidationError(str(exc)) from exc

    folder = _asset_dir(character_id, row["identity_version"], "native")
    final = folder / f"{slot_key}.png"
    temp = folder / f".{slot_key}.{uuid.uuid4().hex}.tmp.png"
    await asyncio.to_thread(folder.mkdir, parents=True, exist_ok=True)
    await asyncio.to_thread(canvas.save, temp, "PNG")
    previous = await _current(db, row, slot_key)
    asset_id, now = str(uuid.uuid4()), _now()
    try:
        if previous is not None:
            # keep the replaced picture's file under its own ID so an older render or review can still see it
            kept = folder / f"{slot_key}.{previous['id'][:8]}.png"
            if stored_path(previous["path"]).is_file():
                await asyncio.to_thread(stored_path(previous["path"]).replace, kept)
            await db.execute("UPDATE character_assets SET is_current = 0, path = ?, updated_at = ? WHERE id = ?",
                             (str(kept), now, previous["id"]))
        await db.execute(
            "INSERT INTO character_assets (id, character_id, kind, path, approved, created_at, slot_key, source, "
            "original_filename, review_state, validation_json, identity_version, is_current, updated_at, facing) "
            "VALUES (?, ?, 'sprite', ?, 0, ?, ?, 'upload', ?, 'needs_review', ?, ?, 1, ?, 'native')",
            (asset_id, character_id, str(final), now, f"sprite/{slot_key}", (original_filename or "")[:200],
             json.dumps(validation), row["identity_version"], now),
        )
        await asyncio.to_thread(temp.replace, final)
    except Exception:
        await asyncio.to_thread(temp.unlink, missing_ok=True)
        raise
    return _asset_view(await _asset_row(db, asset_id)) | {"slot": slot_key}


async def _asset_row(db: aiosqlite.Connection, asset_id: str) -> dict:
    cursor = await db.execute("SELECT * FROM character_assets WHERE id = ?", (asset_id,))
    found = await cursor.fetchone()
    if found is None:
        raise NotFoundError("Picture not found")
    return dict(found)


async def review(db: aiosqlite.Connection, character_id: str, asset_id: str, decision: str,
                 refresh: bool = True) -> dict[str, Any]:
    """Approve or reject one picture. Approving a new base when another base was approved starts a new identity version:
    the other sprites were edits of the old base, so they must be made again (Phase 33 rule 10)."""
    asset = await _asset_row(db, asset_id)
    if asset["character_id"] != character_id or not asset["is_current"]:
        raise ConflictError("Only the current picture of a slot can be reviewed")
    state = {"approve": "approved", "reject": "rejected"}[decision]
    row = await _profile_row(db, character_id)
    if state == "approved" and asset["slot_key"] == f"sprite/{BASE}":
        cursor = await db.execute(
            "SELECT 1 FROM character_assets WHERE character_id = ? AND slot_key = ? AND review_state = 'approved' "
            "AND id != ? AND identity_version = ?", (character_id, f"sprite/{BASE}", asset_id, row["identity_version"]))
        if await cursor.fetchone() is not None:
            new_version = row["identity_version"] + 1
            await db.execute("UPDATE characters SET identity_version = ?, updated_at = ? WHERE id = ?",
                             (new_version, _now(), character_id))
            await db.execute("UPDATE character_assets SET identity_version = ? WHERE id = ?", (new_version, asset_id))
            await db.execute(
                "UPDATE character_assets SET review_state = 'stale', updated_at = ? WHERE character_id = ? "
                "AND identity_version = ? AND is_current = 1 AND kind = 'sprite' AND id != ?",
                (_now(), character_id, row["identity_version"], asset_id))
    await db.execute("UPDATE character_assets SET review_state = ?, approved = ?, updated_at = ? WHERE id = ?",
                     (state, int(state == "approved"), _now(), asset_id))
    if state == "approved" and refresh:
        await derive_core_pictures(db, character_id)
        await materialize_sprite_set(db, character_id)  # the video uses the approved pictures at once (D83)
    return _asset_view(await _asset_row(db, asset_id)) | {"slot": asset["slot_key"].split("/", 1)[1]}


async def materialize_sprite_set(db: aiosqlite.Connection, character_id: str) -> dict | None:
    """Task 33.6: the renderer's `sprite_set.json` pack, written from the approved current uploaded slot pictures.

    Skipped (None) without an approved base, and for packs whose rows already live in the sprite folder (Lina/Alex's Phase 32
    packs): rewriting the folder from itself would delete it first. Pictures that fail the pack checks are left out of the
    manifest, as the Phase 32 import does.
    """
    row = await _profile_row(db, character_id)
    cursor = await db.execute(
        "SELECT slot_key, path FROM character_assets WHERE character_id = ? AND identity_version = ? AND facing = 'native' "
        "AND is_current = 1 AND review_state = 'approved' AND kind = 'sprite'",
        (character_id, row["identity_version"]))
    files = {item["slot_key"].split("/", 1)[1]: stored_path(item["path"]) for item in await cursor.fetchall()}
    if BASE not in files:
        return None
    folder = sprite_service.sprite_dir(character_id).resolve()
    if any(path.resolve().is_relative_to(folder) for path in files.values()):
        return None

    def write() -> dict:
        accepted, _refused = sprite_service.check_folder(files)
        return sprite_service._write_set(character_id, files, accepted, lambda _path: None)  # silhouette face ellipse

    return await asyncio.to_thread(write)


async def approve_many(db: aiosqlite.Connection, character_id: str, asset_ids: list[str]) -> list[dict[str, Any]]:
    """Approve all (D83/D84): the base first, so the rest are checked against the right version."""
    rows = [await _asset_row(db, asset_id) for asset_id in asset_ids]
    rows.sort(key=lambda asset: asset["slot_key"] != f"sprite/{BASE}")
    results = [await review(db, character_id, asset["id"], "approve", refresh=False) for asset in rows]
    await derive_core_pictures(db, character_id)
    await materialize_sprite_set(db, character_id)
    return results


def _derive_sync(source: str, kind: str, destination: Path, mirror: bool = False) -> None:
    """A derived library picture from an approved sprite: the full figure, a head-and-shoulders portrait (768 px), or the
    512 px face reference the GPU shot pipeline uses (`face`, `face_turned`, D87)."""
    with Image.open(source) as sprite:
        figure = sprite.convert("RGBA")
    background = Image.new("RGBA", figure.size, (236, 238, 241, 255))
    background.alpha_composite(figure)
    picture = background.convert("RGB")
    if kind != "full_body":
        alpha = np.asarray(figure.getchannel("A")) > 20
        ys = np.where(alpha.any(axis=1))[0]
        top, height = int(ys.min()), int(ys.max() - ys.min())
        side = int(height * (0.36 if kind.startswith("portrait") else 0.24))  # face crops: the head only
        centre = int(np.where(alpha[top:top + side // 2])[1].mean())
        left = max(0, min(picture.width - side, centre - side // 2))
        upper = max(0, top - side // 12)
        size = 768 if kind.startswith("portrait") else 512
        picture = picture.crop((left, upper, left + side, upper + side)).resize((size, size), Image.Resampling.LANCZOS)
    if mirror:
        picture = ImageOps.mirror(picture)
    destination.parent.mkdir(parents=True, exist_ok=True)
    picture.save(destination, "PNG")


async def derive_core_pictures(db: aiosqlite.Connection, character_id: str) -> list[str]:
    """Full body, the three portraits and the two face references from the approved sprites. A derived picture replaces the
    previous derived one of its kind (the GPU pipelines take the first `face` row they find, so old ones are removed)."""
    row = await _profile_row(db, character_id)
    looks_left = (row["sprite_facing"] or ("right" if row["gender"] == "male" else "left")) == "left"
    jobs = [(kind, source, False) for kind, source in DERIVED_CORE.items()]
    # D87: the face references of the shot pipeline; `face_turned` must look right (the pipeline mirrors it for left)
    jobs += [("face", BASE, False), ("face_turned", BASE, looks_left)]
    made = []
    for kind, source_slot, mirror in jobs:
        source = await _current(db, row, source_slot)
        if not source or source["review_state"] != "approved":
            continue
        destination = _asset_dir(character_id, row["identity_version"], "native") / f"core_{kind}.png"
        await asyncio.to_thread(_derive_sync, str(stored_path(source["path"])), kind, destination, mirror)
        now = _now()
        await db.execute("DELETE FROM character_assets WHERE character_id = ? AND slot_key = ? AND source = 'derived'",
                         (character_id, kind))
        await db.execute("UPDATE character_assets SET is_current = 0, updated_at = ? WHERE character_id = ? AND slot_key = ? "
                         "AND is_current = 1 AND identity_version = ?", (now, character_id, kind, row["identity_version"]))
        await db.execute(
            "INSERT INTO character_assets (id, character_id, kind, path, approved, created_at, slot_key, source, "
            "review_state, identity_version, is_current, updated_at, facing) "
            "VALUES (?, ?, ?, ?, 1, ?, ?, 'derived', 'approved', ?, 1, ?, 'native')",
            (str(uuid.uuid4()), character_id, kind, str(destination), now, kind, row["identity_version"], now))
        made.append(kind)
    return made


async def asset_content(db: aiosqlite.Connection, character_id: str, asset_id: str) -> Path:
    from app.services.visuals.library_service import resolve_library_content

    asset = await _asset_row(db, asset_id)
    if asset["character_id"] != character_id:
        raise NotFoundError("Picture not found")
    return resolve_library_content(str(stored_path(asset["path"])))


async def parent_input(db: aiosqlite.Connection, character_id: str, slot_key: str) -> bytes:
    """The picture the owner attaches in the outside AI for the slots made from `slot_key` (on green, canvas size)."""
    row = await _profile_row(db, character_id)
    asset = await _current(db, row, slot_key)
    if not asset or asset["review_state"] != "approved":
        raise NotFoundError(f"Approve the {slot_key} picture first")

    def render() -> bytes:
        import io

        with Image.open(stored_path(asset["path"])) as sprite:
            picture = sprite_upload.parent_on_green(sprite.convert("RGBA"))
        buffer = io.BytesIO()
        picture.save(buffer, "PNG")
        return buffer.getvalue()

    return await asyncio.to_thread(render)


async def prompt_pack_text(db: aiosqlite.Connection, character_id: str) -> str:
    """The whole pack as one text file, in the layout of the Phase 32 ChatGPT-web prompt files."""
    data = await list_slots(db, character_id)
    row = await _profile_row(db, character_id)
    lines = [f"{row['name'].upper()} — BỘ ẢNH NHÂN VẬT CHO AI BÊN NGOÀI ({len(SLOTS)} ảnh)", "",
             "Cách làm: mỗi ô có ẢNH TẢI LÊN (tải ở ô cha trong thư viện), VÙNG TÔ và PROMPT. Mở cuộc trò chuyện mới cho mỗi ảnh,",
             "tải ảnh lên, tô đúng vùng, dán prompt, tải ảnh về rồi thả vào đúng ô trong thư viện nhân vật (tên file không quan trọng).",
             ""]
    for card in data["slots"]:
        lines.append(f"Ô: {card['file_name']}  (tier {card['tier']})")
        lines.append(f"Ảnh tải lên: {card['parent'] + '.png' if card['parent'] else 'không (ảnh gốc, tạo mới)'}")
        if card["region_text"]:
            lines.append(f"Vùng tô: {card['region_text']}")
        lines.append(f"Prompt: {card['prompt']}")
        lines.append("")
    return "\n".join(lines)
