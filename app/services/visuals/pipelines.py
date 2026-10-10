"""Background image jobs for the global character and scene library."""

from __future__ import annotations

import json
import random
import asyncio
import shutil
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

from app.core.config import settings
from app.core.exceptions import ConflictError
from app.db.transactions import read_transaction, write_transaction
from app.services.visuals import character_asset_service as character_assets
from app.services.visuals import colour_check, geometry, shot_checks, library_service as library, project_visuals_service as project_visuals, recipes, shot_library_service as shot_library
from app.services.visuals.engine import get_image_engine
from app.services.visuals.image_upload import prepare_image
from app.services.visuals.runner import ImageJobRunner, JobCancelled


async def character_candidates(job: dict, runner: ImageJobRunner) -> dict:
    db = runner.get_db()
    async with read_transaction():
        character = await library.get_character_row(db, job["target_id"])
    if character["status"] == "locked":
        raise ConflictError("Unlock the character before generating candidates")
    character_id = character["id"]
    output_dir = settings.DATA_DIR / "library" / "characters" / character_id / "candidates"
    prompt = recipes.candidate_prompt(character)
    engine = get_image_engine()
    async with write_transaction(db):
        await db.execute("DELETE FROM character_assets WHERE character_id = ?", (character_id,))
        await db.execute(
            "UPDATE characters SET reference_asset_id = NULL, status = 'draft' WHERE id = ?", (character_id,)
        )
    asset_ids = []
    async with engine.session("text2img", ip="none", consumer="visuals_candidates") as session:
        for index in range(4):
            await runner.boundary(job["id"], f"candidate {index + 1}/4", index * 25)
            seed = character["base_seed"] + index
            path = output_dir / f"candidate_{index}.png"
            response = await session.request({
                "command": "generate", "prompt": prompt, "negative_prompt": recipes.NEGATIVE,
                "seed": seed, "width": 1024, "height": 1024, "steps": 30,
                "guidance_scale": 6.0, "output_path": str(path),
            })
            async with write_transaction(db):
                asset = await library.add_asset(db, character_id, "candidate", path, seed, response)
            asset_ids.append(asset["id"])
    await runner.boundary(job["id"], "candidates complete", 99)
    async with write_transaction(db):
        await db.execute(
            "UPDATE characters SET status = 'candidates', updated_at = ? WHERE id = ?",
            (library._now(), character_id),
        )
    return {"asset_ids": asset_ids}


async def character_sheet(job: dict, runner: ImageJobRunner) -> dict:
    db = runner.get_db()
    character_id = job["target_id"]
    async with read_transaction():
        character = await library.get_character_row(db, character_id)
        assets = await library.list_assets(db, character_id)
    if character["status"] == "locked":
        raise ConflictError("Unlock the character before generating a sheet")
    face = next((asset for asset in assets if asset["kind"] == "face"), None)
    if face is None:
        raise ConflictError("Pick a candidate before generating a sheet")
    requested = json.loads(job["payload_json"]).get("kind")
    kinds = (requested,) if requested else recipes.SHEET_KINDS
    engine = get_image_engine()
    asset_ids = []
    async with engine.session("text2img", ip="with_encoder", consumer="visuals_sheet") as session:
        for index, kind in enumerate(kinds):
            await runner.boundary(job["id"], f"sheet {kind}", round(index * 100 / len(kinds)))
            path = settings.DATA_DIR / "library" / "characters" / character_id / "sheet" / f"{kind}.png"
            seed = random.randint(1, 2**31 - 1) if requested else character["base_seed"] + 100 + index
            width, height = (832, 1216) if kind == "full_body" else (1024, 1024)
            response = await session.request({
                "command": "generate", "prompt": recipes.sheet_prompt(character, kind),
                "negative_prompt": recipes.NEGATIVE, "seed": seed, "width": width, "height": height,
                "steps": 30, "guidance_scale": 6.0, "output_path": str(path),
                "ip_adapter_image": face["path"], "ip_adapter_scale": 0.45,
            })
            async with write_transaction(db):
                await db.execute(
                    "DELETE FROM character_assets WHERE character_id = ? AND kind = ?", (character_id, kind)
                )
                asset = await library.add_asset(db, character_id, kind, path, seed, response)
            asset_ids.append(asset["id"])
    await runner.boundary(job["id"], "sheet complete", 99)
    async with write_transaction(db):
        await db.execute(
            "UPDATE characters SET status = 'sheet', updated_at = ? WHERE id = ?",
            (library._now(), character_id),
        )
    return {"asset_ids": asset_ids}


async def character_asset(job: dict, runner: ImageJobRunner) -> dict:
    """Generate one core profile slot and store it under the same review contract as uploads."""
    db = runner.get_db()
    payload = json.loads(job["payload_json"])
    slot_key = payload["slot_key"]
    contract = character_assets.get_contract(slot_key)
    if contract["group"] == "sprite":
        raise ConflictError("Local sprite generation is not supported")
    async with read_transaction():
        character = await library.get_character_row(db, job["target_id"])
    if character["identity_version"] != payload["identity_version"]:
        raise ConflictError("Character identity changed; start generation again")
    await runner.boundary(job["id"], f"generating {contract['title']}", 5)
    width, height = contract["minimum_size"]
    width, height = max(1024, width), max(1024, height)
    output = settings.DATA_DIR / "library" / "characters" / character["id"] / "jobs" / f"{job['id']}.png"
    identity = ", ".join(filter(None, (
        character["name"], character["role"], character["age_group"], character["ethnicity"],
        character["hair"], character["eyes"], character["extra"],
        f"{character['top_color']} {character['top_item']}",
        f"{character['bottom_color']} {character['bottom_item']}",
    )))
    engine = get_image_engine()
    try:
        async with engine.session("text2img", ip="none", consumer="character_asset") as session:
            await session.request({
                "command": "generate", "prompt": f"{contract['prompt']}. {identity}. editorial character photo",
                "negative_prompt": recipes.NEGATIVE, "seed": random.randint(1, 2**31 - 1),
                "width": width, "height": height, "steps": 30, "guidance_scale": 6.0,
                "output_path": str(output),
            })
        await runner.boundary(job["id"], "validating generated image", 85)
        prepared = await prepare_image(await asyncio.to_thread(output.read_bytes), contract)
        async with write_transaction(db):
            asset = await character_assets.store_prepared(
                db, character["id"], slot_key, f"local-{slot_key}.png", prepared,
                payload["identity_version"], replace_identity=payload.get("replace_identity", False),
                source="local_generation",
            )
        return {"asset_id": asset["id"], "slot_key": slot_key}
    finally:
        await asyncio.to_thread(output.unlink, missing_ok=True)


async def scene_preview(job: dict, runner: ImageJobRunner) -> dict:
    db = runner.get_db()
    async with read_transaction():
        scene = await library.get_scene_row(db, job["target_id"])
    path = settings.DATA_DIR / "library" / "scenes" / scene["id"] / "preview.png"
    await runner.boundary(job["id"], "scene preview", 0)
    engine = get_image_engine()
    async with engine.session("text2img", ip="none", consumer="visuals_scene_preview") as session:
        response = await session.request({
            "command": "generate", "prompt": recipes.scene_preview_prompt(scene),
            "negative_prompt": recipes.PLATE_NEGATIVE,
            "seed": scene.get("seed") or random.randint(1, 2**31 - 1),
            "width": 1344, "height": 768, "steps": 30, "guidance_scale": 6.0,
            "output_path": str(path),
        })
    await runner.boundary(job["id"], "scene preview complete", 99)
    async with write_transaction(db):
        await db.execute(
            "UPDATE scenes SET preview_path = ?, updated_at = ? WHERE id = ?",
            (str(path), library._now(), scene["id"]),
        )
    return {"path": str(path), "prompt_truncated": response.get("prompt_truncated", False)}


SIZE = (1344, 768)


def _save(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG")


def _crop_and_mask(source: Path, hand: dict, crop_path: Path, mask_path: Path) -> None:
    side = hand["box"][2] - hand["box"][0]
    with Image.open(source) as image:
        crop = image.convert("RGB").crop(hand["box"]).resize((768, 768), Image.Resampling.LANCZOS)
    _save(crop, crop_path)
    scale = 768 / side
    mask = geometry.hand_mask(
        768, (round(hand["center"][0] * scale), round(hand["center"][1] * scale)),
        round(hand["radius"] * scale),
    )
    _save(mask, mask_path)


def _paste_repaired(source: Path, fixed: Path, hand: dict, destination: Path) -> None:
    side = hand["box"][2] - hand["box"][0]
    with Image.open(source) as image, Image.open(fixed) as patch:
        output = geometry.paste_hand(
            image, patch, hand["box"], geometry.hand_mask(side, hand["center"], hand["radius"]),
        )
    _save(output, destination)


def _composite_refine(source: Path, rendered: Path, mask: Image.Image, destination: Path) -> None:
    with Image.open(source) as scene, Image.open(rendered) as fixed:
        output = Image.composite(fixed.convert("RGB").resize(scene.size), scene.convert("RGB"), mask)
    _save(output, destination)


COLOUR_RETRY_STRENGTH = 0.8
INSERT_FACE_SCALE = 0.5  # Task 29.2: the face reference of an insert that shows a character (sheet recipe: 0.45)
EXTRA_PERSON_SEED_STEP = 7919


def gaze_reference(face: str, turned: str | None, side: str, folder: Path) -> str:
    """Task 29.1: the IP-Adapter face reference of a person who looks toward `side`. The turned face (a library asset)
    looks right; for "left" a mirrored copy is made once next to it. A character without one keeps its front face."""
    if not turned:
        return face
    if side == "right":
        return turned
    flipped = Path(folder) / "face_turned_flipped.png"
    if not flipped.is_file() or flipped.stat().st_mtime < Path(turned).stat().st_mtime:
        with Image.open(turned) as source:
            ImageOps.mirror(source.convert("RGB")).save(flipped, format="PNG")
    return str(flipped)


def gaze_sides(kind: str, indexes: list[int]) -> list[str]:
    """Where each person of a shot looks: a duo looks at each other (left person right, right person left); a single
    speaker looks to the side of the partner (speaker 0 right, speaker 1 left: the classic shot / reverse shot)."""
    if kind == "single":
        return ["right" if indexes[0] == 0 else "left"]
    return ["right", "left"]


async def _count_faces(session, image_path: Path, expected: int) -> int:
    """Task 28.5: the faces a picture shows (the fake engine answers `expected_faces`)."""
    response = await session.request({"command": "count_faces", "input_path": str(image_path),
                                      "expected_faces": expected})
    return int(response["faces"])


def face_note(faces: int, people: int) -> str | None:
    """The review note for a shot that shows more faces than people, or None."""
    if not shot_checks.extra_faces(faces, people):
        return None
    return f"{faces} {'face' if faces == 1 else 'faces'} found for {people} {'person' if people == 1 else 'people'}"


def colour_notes(character: dict, result: dict) -> list[str]:
    """Review notes for the garments of one person that still miss their locked colour."""
    notes = []
    for part in ("top", "bottom"):
        entry = result.get(part)
        if entry and not entry.get("ok", True):
            notes.append(f"{character['name']}'s {part} may not be {entry['expected']}")
    return notes


async def _extra_person_pass(session, runner: ImageJobRunner, job: dict, context: dict, payload: dict,
                             progress: int) -> None:
    """Task 28.5 (was the anime cut-out of Task 20.11): a raw that shows more faces than the people of the shot is
    re-rendered with a new seed, at most VISUALS_EXTRA_PERSON_RETRIES times; the render with the fewest extra faces
    is kept (the earliest on a tie). Singles are checked too."""
    folder, raw_path = context["folder"], context["raw"]
    people = len(context["people"])
    seed = context["row"]["seed"]
    tries = [{"seed": seed, "path": raw_path, "faces": await _count_faces(session, raw_path, people)}]

    def extra(item: dict) -> int:
        return shot_checks.extra_faces(item["faces"], people)

    while extra(tries[-1]) and len(tries) <= settings.VISUALS_EXTRA_PERSON_RETRIES:
        attempt = len(tries)
        await runner.boundary(job["id"], f"extra person retry ({attempt})", progress)
        path = folder / f"raw_retry_{attempt}.png"
        retry_seed = seed + EXTRA_PERSON_SEED_STEP * attempt
        await session.request({**payload, "seed": retry_seed, "output_path": str(path)})
        tries.append({"seed": retry_seed, "path": path, "faces": await _count_faces(session, path, people)})
    best = min(tries, key=extra)
    if best["path"] != raw_path:
        await asyncio.to_thread(shutil.copyfile, best["path"], raw_path)
        context["row"] = {**context["row"], "seed": best["seed"]}
    report = {"people": people, "chosen_seed": best["seed"],
              "tries": [{"seed": item["seed"], "faces": item["faces"]} for item in tries]}
    await asyncio.to_thread((folder / "extra_person_check.json").write_text, json.dumps(report, indent=1), "utf-8")


def _colour_result(path: Path, person: dict, character: dict, check_bottom: bool) -> dict:
    with Image.open(path) as image:
        return colour_check.check_person(image, person, character, check_bottom)


async def _colour_pass(session, runner: ImageJobRunner, job: dict, context: dict, current: Path,
                       progress: int) -> Path:
    """Task 20.11: measure each person's garments; repaint a failing person's region with a
    garment-first prompt and a new seed, at most VISUALS_COLOUR_RETRIES times."""
    folder, row = context["folder"], context["row"]
    check_bottom = context["scene"]["staging"] == "standing"
    full = Image.new("L", SIZE, 255)
    report = []
    for index, person in enumerate(context["people"]):
        character = context["characters"][index]
        half = context["halves"][index] if "halves" in context else full
        result = await asyncio.to_thread(_colour_result, current, person, character, check_bottom)
        attempts = 0
        while not result["ok"] and attempts < settings.VISUALS_COLOUR_RETRIES:
            attempts += 1
            await runner.boundary(job["id"], f"colour retry person {index + 1} ({attempts})", progress)
            mask = await asyncio.to_thread(geometry.refine_mask, person, SIZE, half)
            mask_path = folder / f"colour_mask_{index}.png"
            rendered = folder / f"colour_render_{index}_{attempts}.png"
            destination = folder / f"colour_fixed_{index}_{attempts}.png"
            await asyncio.to_thread(_save, mask, mask_path)
            await session.request({
                "command": "generate", "prompt": recipes.garment_refine_prompt(character, context["scene"],
                                                                         gaze=context["sides"][index]),
                "negative_prompt": recipes.negative_for(character), "seed": row["seed"] + 300 + 10 * attempts + index,
                "width": SIZE[0], "height": SIZE[1], "steps": 30, "guidance_scale": 6.0,
                "output_path": str(rendered), "init_image": str(current), "mask_image": str(mask_path),
                "strength": COLOUR_RETRY_STRENGTH, "ip_adapter_image": context["faces"][index],
                "ip_adapter_scale": 0.5,
            })
            await asyncio.to_thread(_composite_refine, current, rendered, mask, destination)
            current = destination
            result = await asyncio.to_thread(_colour_result, current, person, character, check_bottom)
        report.append({"person": index, "attempts": attempts, **result})
        if not result["ok"]:  # still wrong after the retries: the user is told (Task 28.5)
            context.setdefault("review", []).extend(colour_notes(character, result))
    await asyncio.to_thread(
        (folder / "colour_check.json").write_text, json.dumps(report, indent=1), "utf-8",
    )
    return current


async def _contexts(db, project_id: str, rows: list[dict]) -> list[dict[str, Any]]:
    async with read_transaction():
        cast = {member["speaker_index"]: member for member in await project_visuals.cast_rows(db, project_id)}
        # Task 24.5a: storyboard shots may use any library scene, not only the project's chosen ones.
        scenes = {scene_id: await library.get_scene_row(db, scene_id)
                  for scene_id in {row["scene_id"] for row in rows if row["scene_id"]}}
        characters = {index: await library.get_character_row(db, member["character_id"])
                      for index, member in cast.items()}
        faces, turned_faces = {}, {}
        for index, member in cast.items():
            assets = await library.list_assets(db, member["character_id"])
            faces[index] = next(asset["path"] for asset in assets if asset["kind"] == "face")
            turned_faces[index] = next((asset["path"] for asset in assets if asset["kind"] == "face_turned"), None)
    contexts = []
    for row in rows:
        indexes = json.loads(row["speaker_indexes"])
        folder = settings.DATA_DIR / "visuals" / project_id / "shots" / row["id"]
        kind = row["kind"]
        if kind == "insert":
            person = next((index for index in indexes if index in characters), None)
            subject = row.get("subject") or row.get("action") or ""
            if person is not None:  # Task 29.2: a cast speaker does the thing: drawn with the character's face
                contexts.append({"row": row, "insert": True, "folder": folder, "people": [],
                                 "characters": [characters[person]], "faces": [faces[person]],
                                 "prompt": recipes.insert_person_prompt(characters[person], row.get("action") or subject),
                                 "negative": recipes.negative_for(characters[person])})
                continue
            contexts.append({"row": row, "insert": True, "folder": folder, "people": [], "faces": [],
                             "prompt": recipes.insert_prompt(subject or "an illustration"),
                             "negative": recipes.PLATE_NEGATIVE if not indexes else recipes.NEGATIVE})
            continue
        people = [characters[index] for index in indexes]
        scene = scenes[row["scene_id"]]
        action, expression = row.get("action") or "", row.get("expression") or "calm"
        gaze_on = settings.VISUALS_GAZE != "off"
        sides = gaze_sides(kind, indexes)
        single_gaze = sides[0] if gaze_on else None
        if action or expression != "calm":  # Task 24.3/24.5a: a storyboard beat's action and mood
            prompt = (recipes.beat_single_prompt(people[0], scene, action, expression, gaze=single_gaze)
                      if kind == "single"
                      else recipes.beat_duo_prompt(people[0], people[1], scene, kind, action, expression,
                                                   gaze=gaze_on))
            poses = geometry.beat_people(kind, scene["staging"], SIZE,
                                         [geometry.action_category(action)] * len(indexes))
        else:  # legacy shot sets keep their exact prompts and poses
            prompt = (recipes.single_prompt(people[0], scene, gaze=single_gaze) if kind == "single"
                      else recipes.duo_prompt(people[0], people[1], scene, kind, gaze=gaze_on))
            poses = geometry.shot_people(kind, scene["staging"], SIZE)
        if gaze_on and kind == "single":  # a duo skeleton already turns its heads inward
            poses = [geometry.turn_head(pose, side) for pose, side in zip(poses, sides, strict=True)]
        shot_faces = [faces[index] for index in indexes]
        if settings.VISUALS_GAZE == "turned":
            shot_faces = [gaze_reference(faces[index], turned_faces[index], side,
                                         Path(faces[index]).parent)
                          for index, side in zip(indexes, sides, strict=True)]
        contexts.append({"row": row, "indexes": indexes, "characters": people,
                         "faces": shot_faces, "scene": scene, "sides": sides if gaze_on else [None] * len(indexes),
                         "prompt": prompt, "folder": folder, "people": poses})
    return contexts


async def _render_inserts(db, engine, runner: ImageJobRunner, job: dict, inserts: list[dict]) -> None:
    """Task 24.5a: insert shots are text2img illustrations (no plate, no pose); their raw image is final. Task 29.2:
    an insert that names a cast speaker is drawn with that character's face reference (IP-Adapter, the character
    sheet's recipe); the others stay plain illustrations in the first session."""
    plain = [context for context in inserts if not context["faces"]]
    with_person = [context for context in inserts if context["faces"]]
    done = 0
    for contexts, session_args in ((plain, {"ip": "none", "consumer": "visuals_shots_inserts"}),
                                   (with_person, {"ip": "with_encoder", "consumer": "visuals_shots_inserts_person"})):
        if not contexts:
            continue
        async with engine.session("text2img", **session_args) as session:
            for context in contexts:
                done += 1
                await runner.boundary(job["id"], f"insert {done}/{len(inserts)}", 0)
                row, folder = context["row"], context["folder"]
                raw_path, final_path = folder / "raw.png", folder / "final.png"
                payload = {
                    "command": "generate", "prompt": context["prompt"], "negative_prompt": context["negative"],
                    "seed": row["seed"], "width": SIZE[0], "height": SIZE[1], "steps": 30, "guidance_scale": 6.0,
                    "output_path": str(raw_path),
                }
                if context["faces"]:
                    payload.update({"ip_adapter_image": context["faces"][0], "ip_adapter_scale": INSERT_FACE_SCALE})
                response = await session.request(payload)
                await asyncio.to_thread(shutil.copyfile, raw_path, final_path)
                async with write_transaction(db):
                    await db.execute(
                        "UPDATE project_shots SET raw_path = ?, final_path = ?, prompt_tokens = ?, prompt_truncated = ?, "
                        "status = 'complete', updated_at = ? WHERE id = ?",
                        (str(raw_path), str(final_path), response.get("prompt_tokens"),
                         int(bool(response.get("prompt_truncated"))), library._now(), row["id"]),
                    )


async def recover_pending_shots(db) -> int:
    """Review r1 F2: shot rows become `pending` only inside a running job, so any row still
    pending at startup belongs to a job the restart interrupted."""
    async with write_transaction(db):
        cursor = await db.execute(
            "UPDATE project_shots SET status = 'error', error = 'interrupted by app restart', updated_at = ? "
            "WHERE status = 'pending'",
            (library._now(),),
        )
    return cursor.rowcount


async def _mark_error(db, rows: list[dict], message: str) -> None:
    async with write_transaction(db):
        for row in rows:
            await db.execute(
                "UPDATE project_shots SET status = 'error', error = ?, updated_at = ? "
                "WHERE id = ? AND status = 'pending'",
                (message[:500], library._now(), row["id"]),
            )


def _plate_path(scene: dict) -> Path:
    return settings.DATA_DIR / "library" / "scenes" / scene["id"] / "preview.png"


async def _ensure_plates(db, engine, runner: ImageJobRunner, job: dict, contexts: list[dict]) -> None:
    """Task 23.2 L0: a project scene without a plate gets one (text2img, no IP, the scene's own
    seed), stored as its preview, before the shots use it as the scene reference."""
    missing: dict[str, dict] = {}
    for context in contexts:
        scene = context["scene"]
        if not (scene.get("preview_path") and Path(scene["preview_path"]).is_file()):
            missing[scene["id"]] = scene
    if missing:
        async with engine.session("text2img", ip="none", consumer="visuals_scene_plates") as session:
            for index, scene in enumerate(missing.values()):
                await runner.boundary(job["id"], f"scene plate {index + 1}/{len(missing)}", 0)
                path = _plate_path(scene)
                await session.request({
                    "command": "generate", "prompt": recipes.scene_preview_prompt(scene),
                    "negative_prompt": recipes.PLATE_NEGATIVE,
                    "seed": scene.get("seed") or random.randint(1, 2**31 - 1),
                    "width": SIZE[0], "height": SIZE[1], "steps": 30, "guidance_scale": 6.0,
                    "output_path": str(path),
                })
                async with write_transaction(db):
                    await db.execute("UPDATE scenes SET preview_path = ?, updated_at = ? WHERE id = ?",
                                     (str(path), library._now(), scene["id"]))
                scene["preview_path"] = str(path)  # contexts share each scene's dict


async def _generate_set(job: dict, runner: ImageJobRunner, project_id: str, rows: list[dict]) -> dict:
    db = runner.get_db()
    contexts = await _contexts(db, project_id, rows)
    engine = get_image_engine()
    inserts = [context for context in contexts if context.get("insert")]
    contexts = [context for context in contexts if not context.get("insert")]
    if inserts:
        await _render_inserts(db, engine, runner, job, inserts)
    if not contexts:
        await runner.boundary(job["id"], "shots complete", 99)
        return {"shot_ids": [context["row"]["id"] for context in inserts]}
    use_scene = settings.VISUALS_SCENE_REFERENCE_SCALE > 0
    if use_scene:
        await _ensure_plates(db, engine, runner, job, contexts)
    counts = [len(geometry.hand_boxes(person["points"], SIZE, person["head_h"]))
              for context in contexts for person in context["people"]]
    total = len(contexts) * 2 + sum(counts)
    if settings.VISUALS_DUO_REFINE:
        total += sum(2 for context in contexts if context["row"]["kind"] != "single")
    completed = 0

    def progress() -> int:
        return min(99, round(completed * 100 / max(1, total)))

    # L1: text encoder + IP encoder. One embed file per shot permits each shot to carry
    # its own one- or two-face reference while all prompts share one worker lifetime.
    async with engine.session("text2img", ip="with_encoder", consumer="visuals_shots_encode",
                              scene=use_scene) as session:
        for context in contexts:
            await runner.boundary(job["id"], f"encode {completed + 1}/{total}", progress())
            folder = context["folder"]
            context["embeds"] = folder / "embeds.pt"
            payload = {"command": "encode", "output_path": str(context["embeds"]),
                       "items": [{"prompt": context["prompt"],
                                  "negative_prompt": recipes.negative_for(*context["characters"])}],
                       "guidance_scale": 6.0}
            if len(context["faces"]) == 1:
                payload["ip_adapter_image"] = context["faces"][0]
            else:
                payload["ip_adapter_images"] = context["faces"]
            if use_scene:
                payload["ip_adapter_scene_image"] = context["scene"]["preview_path"]
            response = await session.request(payload)
            context["tokens"] = response["item_tokens"][0]
            completed += 1

    # L2: pose-controlled one-pass scenes with only IP layers in GPU memory.
    async with engine.session("controlnet", encoders=False, ip="layers_only",
                              consumer="visuals_shots_render", scene=use_scene) as session:
        for context in contexts:
            await runner.boundary(job["id"], f"render {completed + 1}/{total}", progress())
            folder, row = context["folder"], context["row"]
            pose_path, raw_path = folder / "pose.png", folder / "raw.png"
            pose = await asyncio.to_thread(geometry.draw_people, context["people"], SIZE)
            await asyncio.to_thread(_save, pose, pose_path)
            payload = {"command": "generate", "embeds_path": str(context["embeds"]), "embeds_index": 0,
                       "seed": row["seed"], "width": SIZE[0], "height": SIZE[1], "steps": 30,
                       "guidance_scale": 6.0, "output_path": str(raw_path), "control_image": str(pose_path),
                       "controlnet_conditioning_scale": 1.0, "ip_adapter_scale": 0.45}
            if row["kind"] != "single":
                left, right = await asyncio.to_thread(geometry.half_masks, SIZE)
                masks = [folder / "half_left.png", folder / "half_right.png"]
                await asyncio.to_thread(_save, left, masks[0])
                await asyncio.to_thread(_save, right, masks[1])
                payload["ip_adapter_masks"] = [str(path) for path in masks]
                context["halves"] = (left, right)
            if use_scene:
                background = await asyncio.to_thread(geometry.background_mask, context["people"], SIZE)
                background_path = folder / "scene_mask.png"
                await asyncio.to_thread(_save, background, background_path)
                payload["ip_adapter_scene_mask"] = str(background_path)
                payload["ip_adapter_scene_scale"] = settings.VISUALS_SCENE_REFERENCE_SCALE
            response = await session.request(payload)
            context["raw"] = raw_path
            if settings.VISUALS_EXTRA_PERSON_RETRIES > 0:
                await _extra_person_pass(session, runner, job, context, payload, progress())
            async with write_transaction(db):
                await db.execute(
                    "UPDATE project_shots SET raw_path = ?, seed = ?, prompt_tokens = ?, prompt_truncated = ?, "
                    "updated_at = ? WHERE id = ?",
                    (str(raw_path), context["row"]["seed"],
                     response.get("prompt_tokens", context["tokens"].get("prompt_tokens")),
                     int(bool(response.get("prompt_truncated", context["tokens"].get("prompt_truncated")))),
                     library._now(), row["id"]),
                )
            completed += 1

    # L3: refine each duo person inside their own silhouette/half, then repair each
    # in-frame hand crop at 768 square. The raw scene is preserved separately.
    async with engine.session("inpaint", ip="with_encoder", consumer="visuals_shots_repair") as session:
        for context in contexts:
            folder, row = context["folder"], context["row"]
            current = context["raw"]
            if row["kind"] != "single" and settings.VISUALS_DUO_REFINE:
                for index, person in enumerate(context["people"]):
                    await runner.boundary(job["id"], f"refine person {index + 1}", progress())
                    mask = await asyncio.to_thread(geometry.refine_mask, person, SIZE, context["halves"][index])
                    mask_path = folder / f"refine_mask_{index}.png"
                    rendered = folder / f"refine_render_{index}.png"
                    destination = folder / f"refined_{index}.png"
                    await asyncio.to_thread(_save, mask, mask_path)
                    await session.request({
                        "command": "generate", "prompt": recipes.refine_prompt(context["characters"][index],
                                                                                   context["scene"],
                                                                                   gaze=context["sides"][index]),
                        "negative_prompt": recipes.negative_for(context["characters"][index]),
                        "seed": row["seed"] + 100 + index,
                        "width": SIZE[0], "height": SIZE[1], "steps": 30, "guidance_scale": 6.0,
                        "output_path": str(rendered), "init_image": str(current), "mask_image": str(mask_path),
                        "strength": 0.55, "ip_adapter_image": context["faces"][index], "ip_adapter_scale": 0.5,
                    })
                    await asyncio.to_thread(_composite_refine, current, rendered, mask, destination)
                    current = destination
                    completed += 1
            if settings.VISUALS_COLOUR_RETRIES > 0:
                current = await _colour_pass(session, runner, job, context, current, progress())
            hand_number = 0
            for person_index, person in enumerate(context["people"]):
                hands = geometry.hand_boxes(person["points"], SIZE, person["head_h"])
                for hand in hands:
                    await runner.boundary(job["id"], f"repair hand {hand_number + 1}", progress())
                    crop = folder / f"hand_{hand_number}_crop.png"
                    mask = folder / f"hand_{hand_number}_mask.png"
                    fixed = folder / f"hand_{hand_number}_fixed.png"
                    pasted = folder / f"hand_{hand_number}_pasted.png"
                    await asyncio.to_thread(_crop_and_mask, current, hand, crop, mask)
                    await session.request({
                        "command": "generate", "prompt": recipes.hand_prompt(),
                        "negative_prompt": recipes.HAND_NEGATIVE, "seed": row["seed"] + 200 + hand_number,
                        "width": 768, "height": 768, "steps": 30, "guidance_scale": 6.0,
                        "output_path": str(fixed), "init_image": str(crop), "mask_image": str(mask),
                        "strength": 0.5, "ip_adapter_image": context["faces"][person_index],
                        "ip_adapter_scale": 0.0,
                    })
                    await asyncio.to_thread(_paste_repaired, current, fixed, hand, pasted)
                    current = pasted
                    hand_number += 1
                    completed += 1
            final_path = folder / "final.png"
            await asyncio.to_thread(shutil.copyfile, current, final_path)
            notes = list(context.get("review", []))
            faces_note = face_note(await _count_faces(session, final_path, len(context["people"])),
                                   len(context["people"]))
            if faces_note:
                notes.append(faces_note)
            async with write_transaction(db):
                await db.execute(
                    "UPDATE project_shots SET final_path = ?, status = 'complete', review_note = ?, updated_at = ? "
                    "WHERE id = ?",
                    (str(final_path), "; ".join(notes) or None, library._now(), row["id"]),
                )
    await runner.boundary(job["id"], "shots complete", 99)
    if settings.VISUALS_LIBRARY_AUTO_ADD:  # Task 29.4: a shot that passed its checks goes to the library as pending
        for context in contexts:
            try:
                finished = await project_visuals.get_shot_row(db, project_id, context["row"]["id"])
                if finished["status"] == "complete" and not finished["review_note"]:
                    async with write_transaction(db):
                        await shot_library.add_from_project_shot(db, project_id, finished["id"])
            except Exception:  # noqa: BLE001  (a library hiccup never fails the shot job)
                pass
    return {"shot_ids": [context["row"]["id"] for context in inserts + contexts]}


async def project_shots(job: dict, runner: ImageJobRunner) -> dict:
    db = runner.get_db()
    project_id = job["target_id"]
    async with write_transaction(db):
        # Task 24.5a: an approved storyboard decides the shots; else the per-scene shot set.
        rows = (await project_visuals.prepare_storyboard_shots(db, project_id)
                or await project_visuals.prepare_shots(db, project_id))
    directory = settings.DATA_DIR / "visuals" / project_id / "shots"
    await asyncio.to_thread(shutil.rmtree, directory, ignore_errors=True)
    try:
        # Task 29.5: approved library shots serve every spec they match; only the rest is drawn.
        async with write_transaction(db):
            rows, served = await shot_library.reuse_for_rows(db, project_id, rows)
        result = await _generate_set(job, runner, project_id, rows) if rows else {"shot_ids": []}
        return {**result, "from_library": served}
    except JobCancelled:
        await _mark_error(db, rows, "cancelled")
        raise
    except Exception as exc:
        await _mark_error(db, rows, str(exc))
        raise


async def shot_regenerate(job: dict, runner: ImageJobRunner) -> dict:
    db = runner.get_db()
    project_id = json.loads(job["payload_json"])["project_id"]
    async with write_transaction(db):
        row = await project_visuals.prepare_regenerate(db, project_id, job["target_id"])
    directory = settings.DATA_DIR / "visuals" / project_id / "shots" / row["id"]
    await asyncio.to_thread(shutil.rmtree, directory, ignore_errors=True)
    try:
        return await _generate_set(job, runner, project_id, [row])
    except JobCancelled:
        await _mark_error(db, [row], "cancelled")
        raise
    except Exception as exc:
        await _mark_error(db, [row], str(exc))
        raise
