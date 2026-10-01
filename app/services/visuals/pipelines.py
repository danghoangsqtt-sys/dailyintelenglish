"""Background image jobs for the global character and scene library."""

from __future__ import annotations

import json
import random

from app.core.config import settings
from app.core.exceptions import ConflictError
from app.db.transactions import read_transaction, write_transaction
from app.services.visuals import library_service as library, recipes
from app.services.visuals.engine import get_image_engine
from app.services.visuals.runner import ImageJobRunner


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
            "negative_prompt": recipes.NEGATIVE, "seed": random.randint(1, 2**31 - 1),
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
