"""Task 29.4 / 29.5 (ENH-020): the shot library of ready-made pictures of the cast, and the matcher that reuses them.

A library shot is described by tags (scene, framing, the ordered characters, action, expression) so a match is a lookup,
not a guess. Only `approved`, non-stale shots are reused; a shot is tied to each character's face reference through a
signature, so a regenerated character makes its shots stale instead of silently reused.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import shutil
import uuid
from pathlib import Path
from typing import Any

import aiosqlite
from PIL import Image, ImageOps

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.services.visuals import library_service as library

REVIEW_STATES = ("pending", "approved", "rejected")
LIBRARY_KINDS = ("single", "duo_close", "duo_wide")
# An expression is reused for the same expression, and calm and smile stand in for each other (both are a relaxed talk).
_RELAXED = {"calm", "smile"}


def shots_dir() -> Path:
    return settings.DATA_DIR / "library" / "shots"


def _expression_fits(wanted: str, have: str) -> bool:
    return wanted == have or (wanted in _RELAXED and have in _RELAXED)


def _action_fits(wanted: str, have: str) -> bool:
    """The same action, or every word of the library action is in the wanted one ("walking" serves "walking along the
    path"); an empty library action only serves an empty one."""
    wanted, have = (wanted or "").strip().lower(), (have or "").strip().lower()
    if wanted == have:
        return True
    if not have:
        return False
    return set(re.findall(r"[a-z]+", have)) <= set(re.findall(r"[a-z]+", wanted))


def _gaze_fits(have: str) -> bool:
    """A shot drawn with the gaze fix is never offered to a setup that turned the fix off, and the other way round."""
    return (have == "off") if settings.VISUALS_GAZE == "off" else (have != "off")


async def face_signature(db: aiosqlite.Connection, character_ids: list[str]) -> str:
    """One string for the face references of these characters, in order: asset id and size of each `face`."""
    parts = []
    for character_id in character_ids:
        assets = await library.list_assets(db, character_id)
        face = next((asset for asset in assets if asset["kind"] == "face"), None)
        if face is None:
            parts.append("none")
            continue
        try:
            size = Path(face["path"]).stat().st_size
        except OSError:
            size = 0
        parts.append(f"{face['id']}:{size}")
    return "|".join(parts)


async def cast_character_ids(db: aiosqlite.Connection, project_id: str, speaker_indexes: list[int]) -> list[str] | None:
    """The characters of these speakers in order, or None when a speaker is not cast."""
    cursor = await db.execute("SELECT speaker_index, character_id FROM project_cast WHERE project_id = ?", (project_id,))
    cast = {row[0]: row[1] for row in await cursor.fetchall()}
    if not speaker_indexes or any(index not in cast for index in speaker_indexes):
        return None
    return [cast[index] for index in speaker_indexes]


def _view(row: dict) -> dict:
    view = dict(row)
    view["character_ids"] = json.loads(view.pop("character_ids_json"))
    view["stale"] = bool(view["stale"])
    view["content_url"] = f"/api/visuals/library/shots/{view['id']}/content"
    view.pop("path", None)
    view.pop("face_signature", None)
    return view


async def _get_row(db: aiosqlite.Connection, shot_id: str) -> dict:
    cursor = await db.execute("SELECT * FROM shot_library WHERE id = ?", (shot_id,))
    row = await cursor.fetchone()
    if row is None:
        raise NotFoundError("Library shot not found")
    return dict(row)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def add_from_project_shot(db: aiosqlite.Connection, project_id: str, shot_id: str) -> dict:
    """Copy a finished project shot into the library as `pending` (the owner approves it once). The same picture is
    never added twice. Caller holds the write transaction."""
    from app.services.visuals import project_visuals_service as project_visuals

    shot = await project_visuals.get_shot_row(db, project_id, shot_id)
    if shot["kind"] not in LIBRARY_KINDS:
        raise ValidationError("Only a single or a duo shot of the cast can go to the library")
    if shot["status"] != "complete" or not shot["final_path"]:
        raise ConflictError("The shot has no finished picture yet")
    character_ids = await cast_character_ids(db, project_id, json.loads(shot["speaker_indexes"]))
    if character_ids is None:
        raise ValidationError("The shot's speakers are not cast characters")
    source = await asyncio.to_thread(project_visuals.resolve_shot_content, project_id, shot["final_path"])
    digest = await asyncio.to_thread(_sha, source)
    cursor = await db.execute("SELECT * FROM shot_library WHERE content_sha = ?", (digest,))
    existing = await cursor.fetchone()
    if existing is not None:
        return _view(dict(existing))
    library_id = str(uuid.uuid4())
    target = shots_dir() / f"{library_id}.png"
    await asyncio.to_thread(target.parent.mkdir, parents=True, exist_ok=True)
    await asyncio.to_thread(shutil.copyfile, source, target)
    now = library._now()
    await db.execute(
        "INSERT INTO shot_library (id, kind, scene_id, character_ids_json, action, expression, gaze, face_signature, "
        "path, content_sha, review_state, source_project_id, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)",
        (library_id, shot["kind"], shot["scene_id"], json.dumps(character_ids), shot.get("action") or "",
         shot.get("expression") or "calm", settings.VISUALS_GAZE, await face_signature(db, character_ids),
         str(target), digest, project_id, now, now),
    )
    return _view(await _get_row(db, library_id))


async def refresh_stale(db: aiosqlite.Connection) -> int:
    """Mark a shot stale when the face reference of any of its characters changed since it was drawn."""
    cursor = await db.execute("SELECT id, character_ids_json, face_signature FROM shot_library WHERE stale = 0")
    rows = await cursor.fetchall()
    marked, cache = 0, {}
    for row in rows:
        ids = json.loads(row["character_ids_json"])
        key = tuple(ids)
        if key not in cache:
            try:
                cache[key] = await face_signature(db, ids)
            except NotFoundError:
                cache[key] = "gone"
        if cache[key] != row["face_signature"]:
            await db.execute("UPDATE shot_library SET stale = 1, updated_at = ? WHERE id = ?", (library._now(), row["id"]))
            marked += 1
    return marked


async def list_shots(db: aiosqlite.Connection, scene_id: str | None = None, kind: str | None = None,
                     review_state: str | None = None, character_id: str | None = None) -> list[dict]:
    clauses, params = [], []
    for column, value in (("scene_id", scene_id), ("kind", kind), ("review_state", review_state)):
        if value:
            clauses.append(f"{column} = ?")
            params.append(value)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    cursor = await db.execute(f"SELECT * FROM shot_library {where} ORDER BY created_at DESC, rowid DESC", tuple(params))
    views = [_view(dict(row)) for row in await cursor.fetchall()]
    if character_id:
        views = [view for view in views if character_id in view["character_ids"]]
    return views


async def set_review(db: aiosqlite.Connection, shot_id: str, review_state: str) -> dict:
    if review_state not in REVIEW_STATES:
        raise ValidationError(f"review_state must be one of {', '.join(REVIEW_STATES)}")
    await _get_row(db, shot_id)
    await db.execute("UPDATE shot_library SET review_state = ?, updated_at = ? WHERE id = ?",
                     (review_state, library._now(), shot_id))
    return _view(await _get_row(db, shot_id))


async def delete_shot(db: aiosqlite.Connection, shot_id: str) -> None:
    row = await _get_row(db, shot_id)
    await db.execute("DELETE FROM shot_library WHERE id = ?", (shot_id,))
    await asyncio.to_thread(Path(row["path"]).unlink, True)


async def content_path(db: aiosqlite.Connection, shot_id: str) -> Path:
    row = await _get_row(db, shot_id)
    root = shots_dir().resolve()
    candidate = Path(row["path"]).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise NotFoundError("Library shot image not found")
    return candidate


async def find_match(db: aiosqlite.Connection, *, scene_id: str, kind: str, character_ids: list[str], action: str,
                     expression: str, exclude: set[str] | None = None) -> dict | None:
    """The best approved, non-stale library shot for a shot spec, or None. The scene, framing and characters must be the
    same; for two people the picture may also have them the other way round (the returned row then has `mirror` True and
    the picture must be flipped when it is used); the action fits (same, or every word of the library action is in the
    wanted one; an empty library action only serves an empty one); the expression is the same (calm and smile stand in
    for each other). Ranked by: not mirrored, not used lately, fewest uses. A shot in `exclude` (already used in this
    episode) is skipped, so a picture is not repeated inside one video."""
    if kind not in LIBRARY_KINDS or not scene_id or not character_ids:
        return None
    orders = [list(character_ids)]
    if kind != "single" and len(character_ids) == 2:
        orders.append(list(character_ids)[::-1])
    marks = ",".join("?" * len(orders))
    cursor = await db.execute(
        f"SELECT * FROM shot_library WHERE scene_id = ? AND kind = ? AND character_ids_json IN ({marks}) "
        "AND review_state = 'approved' AND stale = 0",
        (scene_id, kind, *(json.dumps(order) for order in orders)),
    )
    candidates = [dict(row) for row in await cursor.fetchall()]
    usable = []
    signatures: dict[str, str] = {}
    for row in candidates:
        ids = json.loads(row["character_ids_json"])
        key = row["character_ids_json"]
        if key not in signatures:
            signatures[key] = await face_signature(db, ids)
        if row["face_signature"] != signatures[key]:
            await db.execute("UPDATE shot_library SET stale = 1, updated_at = ? WHERE id = ?", (library._now(), row["id"]))
            continue
        if (row["id"] in (exclude or set()) or not _action_fits(action, row["action"])
                or not _expression_fits(expression or "calm", row["expression"]) or not _gaze_fits(row["gaze"])
                or not Path(row["path"]).is_file()):
            continue
        row["mirror"] = ids != list(character_ids)
        usable.append(row)
    if not usable:
        return None
    usable.sort(key=lambda row: (row["mirror"], row["use_count"], row["last_used_at"] or ""))
    return usable[0]


async def delete_for_character(db: aiosqlite.Connection, character_id: str) -> int:
    """Remove every library shot that shows this character (a deleted character leaves no orphan pictures).
    Caller holds the write transaction; returns how many were removed."""
    cursor = await db.execute("SELECT id, path, character_ids_json FROM shot_library")
    doomed = [row for row in await cursor.fetchall() if character_id in json.loads(row["character_ids_json"])]
    for row in doomed:
        await db.execute("DELETE FROM shot_library WHERE id = ?", (row["id"],))
        await asyncio.to_thread(Path(row["path"]).unlink, True)
    return len(doomed)


# ---- importing the owner's own pictures (Phase 31) ------------------------------------------------------------------------

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
EXPRESSIONS = ("calm", "smile", "laugh", "surprised", "thinking", "worried", "serious")
TARGET_ASPECT = 16 / 9
ASPECT_TOLERANCE = 0.06  # a picture within 6% of 16:9 is kept as it is
CROP_TOP_ANCHOR = 0.15  # a taller picture loses most of its bottom (the heads are at the top)


def inbox_dir() -> Path:
    return settings.DATA_DIR / "library" / "shots_inbox"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def parse_inbox_name(stem: str) -> dict[str, Any]:
    """`scene__framing[__action words][__expression]`: framing is `duo-wide`, `duo-close` (the woman on the left, the man
    on the right), `duo-wide-rev` / `duo-close-rev` (the other way round), `duo-wide-<left>-<right>` (the two names, left to
    right: needed when the library has more than two characters) or `single-<character name>`. Raises ValueError."""
    parts = [part for part in stem.split("__") if part]
    if len(parts) < 2:
        raise ValueError("the name must be scene__framing, for example cafe__duo-wide")
    scene, framing, rest = parts[0], _slug(parts[1]), parts[2:]
    match = re.fullmatch(r"(duo-wide|duo-close)(?:-(?!rev)([a-z0-9]+)-([a-z0-9]+))?(-rev)?|single-([a-z0-9-]+)", framing)
    if match is None:
        raise ValueError(f"framing '{parts[1]}' is not duo-wide, duo-close, duo-wide-rev, duo-close-rev, "
                         "duo-wide-<left>-<right> or single-<name>")
    expression, action = "calm", ""
    for part in rest:
        if part.isdigit():  # a variant number (cafe__duo-wide__2): the same tags, another picture
            continue
        if _slug(part) in EXPRESSIONS:
            expression = _slug(part)
        else:
            action = " ".join(re.sub(r"[^A-Za-z]+", " ", part).split()).lower()
    kind = "single" if match.group(5) else match.group(1).replace("-", "_")
    return {"scene": scene, "kind": kind, "reverse": bool(match.group(4)), "single": match.group(5),
            "pair": (match.group(2), match.group(3)) if match.group(2) else None, "action": action, "expression": expression}


async def _resolve_scene(db: aiosqlite.Connection, token: str) -> str | None:
    wanted = _slug(token)
    cursor = await db.execute("SELECT id, name FROM scenes")
    for row in await cursor.fetchall():
        if wanted in (_slug(row["id"]), _slug(row["id"]).removeprefix("builtin-"), _slug(row["name"])):
            return row["id"]
    return None


async def _resolve_characters(db: aiosqlite.Connection, parsed: dict[str, Any]) -> list[str]:
    cursor = await db.execute("SELECT id, name, gender FROM characters WHERE status = 'locked' ORDER BY created_at, rowid")
    people = [dict(row) for row in await cursor.fetchall()]
    if parsed["single"]:
        match = [p for p in people if _slug(p["name"]) == parsed["single"]]
        if not match:
            raise ValueError(f"no locked character named '{parsed['single']}'")
        return [match[0]["id"]]
    if parsed.get("pair"):
        by_name = {_slug(p["name"]): p["id"] for p in people}
        missing = [name for name in parsed["pair"] if name not in by_name]
        if missing:
            raise ValueError(f"no locked character named '{missing[0]}'")
        return [by_name[name] for name in parsed["pair"]]
    if len(people) != 2:
        raise ValueError("a duo picture needs exactly two locked characters in the library, or the names: "
                         "duo-wide-<left>-<right>")
    people.sort(key=lambda p: 0 if p["gender"] == "female" else 1)  # the woman on the left, the man on the right
    ordered = [people[0]["id"], people[1]["id"]]
    return ordered[::-1] if parsed["reverse"] else ordered


def _fit_16_9(path: Path, target: Path) -> bool:
    """Save the picture as a PNG; a picture that is not about 16:9 is cropped to it (the top is kept). True if cropped."""
    with Image.open(path) as source:
        image = source.convert("RGB")
    width, height = image.size
    cropped = False
    if abs(width / height - TARGET_ASPECT) / TARGET_ASPECT > ASPECT_TOLERANCE:
        cropped = True
        if width / height < TARGET_ASPECT:  # too tall: cut height
            new_height = round(width / TARGET_ASPECT)
            top = round((height - new_height) * CROP_TOP_ANCHOR)
            image = image.crop((0, top, width, top + new_height))
        else:  # too wide: cut width, centred
            new_width = round(height * TARGET_ASPECT)
            left = (width - new_width) // 2
            image = image.crop((left, 0, left + new_width, height))
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, format="PNG")
    return cropped


async def import_picture(db: aiosqlite.Connection, source: Path, scene_id: str, kind: str, character_ids: list[str],
                         action: str = "", expression: str = "calm") -> tuple[dict, bool]:
    """Add the owner's own picture to the library as `pending`. Returns (the library shot, whether it was cropped).
    Caller holds the write transaction. A picture already in the library (same content) raises ConflictError."""
    library_id = str(uuid.uuid4())
    target = shots_dir() / f"{library_id}.png"
    cropped = await asyncio.to_thread(_fit_16_9, source, target)
    digest = await asyncio.to_thread(_sha, target)
    cursor = await db.execute("SELECT 1 FROM shot_library WHERE content_sha = ?", (digest,))
    if await cursor.fetchone() is not None:
        await asyncio.to_thread(target.unlink, True)
        raise ConflictError("this picture is already in the library")
    now = library._now()
    await db.execute(
        "INSERT INTO shot_library (id, kind, scene_id, character_ids_json, action, expression, gaze, face_signature, "
        "path, content_sha, review_state, source_project_id, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 'imported', ?, ?, ?, 'pending', NULL, ?, ?)",
        (library_id, kind, scene_id, json.dumps(character_ids), action, expression,
         await face_signature(db, character_ids), str(target), digest, now, now),
    )
    return _view(await _get_row(db, library_id)), cropped


def list_inbox() -> list[str]:
    folder = inbox_dir()
    if not folder.is_dir():
        return []
    return sorted(p.name for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)


async def import_inbox(db: aiosqlite.Connection) -> dict[str, list]:
    """Import every picture of the inbox folder (named by the convention above). Imported files move to `imported/`;
    a file that cannot be imported stays, with the reason. Caller holds the write transaction."""
    folder = inbox_dir()
    imported, skipped = [], []
    for name in list_inbox():
        path = folder / name
        try:
            parsed = parse_inbox_name(path.stem)
            scene_id = await _resolve_scene(db, parsed["scene"])
            if scene_id is None:
                raise ValueError(f"unknown scene '{parsed['scene']}' (use a scene id or name from the list)")
            characters = await _resolve_characters(db, parsed)
            shot, cropped = await import_picture(db, path, scene_id, parsed["kind"], characters, parsed["action"],
                                                 parsed["expression"])
        except (ValueError, ConflictError) as error:
            skipped.append({"file": name, "reason": str(error)})
            continue
        done = folder / "imported"
        await asyncio.to_thread(done.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(shutil.move, str(path), str(done / name))
        imported.append({"file": name, "id": shot["id"], "scene_id": scene_id, "kind": parsed["kind"], "cropped": cropped})
    return {"imported": imported, "skipped": skipped}


# ---- the owner's own scene backgrounds (Phase 31) --------------------------------------------------------------------

def backgrounds_dir() -> Path:
    return settings.DATA_DIR / "assets_background"


def backgrounds_status() -> dict[str, Any]:
    folder = backgrounds_dir()
    images = sorted(p.name for p in (folder / "assets").iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS) \
        if (folder / "assets").is_dir() else []
    return {"folder": str(folder), "images": len(images)}


async def import_backgrounds(db: aiosqlite.Connection) -> dict[str, list]:
    """Make the pictures of `assets_background/assets` (named by scene key: cafe.png, city-street.png...) the plates of
    their scenes, and keep the prompt of `assets_background/prompts/<key>.txt` next to the plate. A picture that is not
    16:9 is cropped to it. Importing again is safe: an unchanged picture is reported as unchanged. Caller holds the write
    transaction."""
    folder = backgrounds_dir()
    assets = folder / "assets"
    imported, unchanged, skipped = [], [], []
    if not assets.is_dir():
        return {"imported": imported, "unchanged": unchanged, "skipped": skipped}
    for image in sorted(p for p in assets.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS):
        scene_id = await _resolve_scene(db, image.stem)
        if scene_id is None:
            skipped.append({"file": image.name, "reason": f"unknown scene '{image.stem}' (use a scene key)"})
            continue
        target = settings.DATA_DIR / "library" / "scenes" / scene_id / "preview.png"
        staged = target.with_suffix(".new.png")
        try:
            cropped = await asyncio.to_thread(_fit_16_9, image, staged)
        except OSError as error:
            skipped.append({"file": image.name, "reason": f"not a readable picture ({error})"})
            continue
        same = target.is_file() and await asyncio.to_thread(_sha, staged) == await asyncio.to_thread(_sha, target)
        if same:
            await asyncio.to_thread(staged.unlink, True)
            unchanged.append(image.name)
        else:
            await asyncio.to_thread(staged.replace, target)
            await db.execute("UPDATE scenes SET preview_path = ?, updated_at = ? WHERE id = ?",
                             (str(target.resolve()), library._now(), scene_id))
            imported.append({"file": image.name, "scene_id": scene_id, "cropped": cropped})
        prompt = folder / "prompts" / f"{image.stem}.txt"
        if prompt.is_file():
            text = await asyncio.to_thread(prompt.read_text, "utf-8-sig")
            await asyncio.to_thread((target.parent / "prompt.txt").write_text, text, "utf-8")
    return {"imported": imported, "unchanged": unchanged, "skipped": skipped}


async def mark_used(db: aiosqlite.Connection, shot_id: str) -> None:
    await db.execute("UPDATE shot_library SET use_count = use_count + 1, last_used_at = ? WHERE id = ?",
                     (library._now(), shot_id))


async def coverage(db: aiosqlite.Connection, project_id: str) -> dict[str, Any]:
    """What the library already covers for this project's shots (the approved storyboard's specs, else the shots that
    exist): per shot whether an approved picture would be reused, and the totals."""
    from app.services.visuals import project_visuals_service as project_visuals
    from app.services.visuals import storyboard_service

    cast = await project_visuals.cast_rows(db, project_id)
    beats = await storyboard_service.approved_beats(db, project_id)
    if beats is not None and cast:
        specs = project_visuals.storyboard_shot_specs(beats, cast)
    else:
        specs = [{**row, "speakers": json.loads(row["speaker_indexes"])} for row in await project_visuals.shot_rows(db, project_id)]
    used: set[str] = set()
    items = []
    for spec in specs:
        if spec["kind"] == "insert":
            items.append({"kind": "insert", "covered": False, "reusable": False})
            continue
        ids = await cast_character_ids(db, project_id, list(spec["speakers"]))
        match = (await find_match(db, scene_id=spec["scene_id"], kind=spec["kind"], character_ids=ids or [],
                                  action=spec.get("action") or "", expression=spec.get("expression") or "calm",
                                  exclude=used) if ids else None)
        if match:
            used.add(match["id"])
        items.append({"kind": spec["kind"], "scene_id": spec["scene_id"], "action": spec.get("action") or "",
                      "expression": spec.get("expression") or "calm", "covered": match is not None, "reusable": True,
                      "library_shot_id": match["id"] if match else None})
    reusable = [item for item in items if item["reusable"]]
    return {"items": items, "total": len(reusable), "covered": sum(1 for item in reusable if item["covered"]),
            "missing": sum(1 for item in reusable if not item["covered"])}


def _save_mirrored(source: Path, target: Path) -> None:
    with Image.open(source) as picture:
        ImageOps.mirror(picture.convert("RGB")).save(target, format="PNG")


async def reuse_for_rows(db: aiosqlite.Connection, project_id: str, rows: list[dict]) -> tuple[list[dict], list[str]]:
    """Task 29.5: copy an approved library shot into each pending non-insert row that has a match (no GPU) and return
    (the rows still to generate, the ids of the rows served from the library). Caller holds the write transaction."""
    if not settings.VISUALS_USE_LIBRARY:
        return rows, []
    remaining, served, used = [], [], set()
    for row in rows:
        if row["kind"] not in LIBRARY_KINDS:
            remaining.append(row)
            continue
        ids = await cast_character_ids(db, project_id, json.loads(row["speaker_indexes"]))
        match = (await find_match(db, scene_id=row["scene_id"], kind=row["kind"], character_ids=ids,
                                  action=row.get("action") or "", expression=row.get("expression") or "calm",
                                  exclude=used) if ids else None)
        if match is None:
            remaining.append(row)
            continue
        folder = settings.DATA_DIR / "visuals" / project_id / "shots" / row["id"]
        final_path = folder / "final.png"
        await asyncio.to_thread(folder.mkdir, parents=True, exist_ok=True)
        if match.get("mirror"):  # the picture has the two people the other way round: flip it
            await asyncio.to_thread(_save_mirrored, Path(match["path"]), final_path)
        else:
            await asyncio.to_thread(shutil.copyfile, match["path"], final_path)
        await db.execute(
            "UPDATE project_shots SET final_path = ?, status = 'complete', review_note = NULL, source = 'library', "
            "library_shot_id = ?, error = NULL, updated_at = ? WHERE id = ?",
            (str(final_path), match["id"], library._now(), row["id"]),
        )
        await mark_used(db, match["id"])
        used.add(match["id"])
        served.append(row["id"])
    return remaining, served
