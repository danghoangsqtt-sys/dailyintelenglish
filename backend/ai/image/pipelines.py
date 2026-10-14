"""Background image jobs. Phase 44 (D123): only Qwen draws -- the scene-library picture (Qwen-Image-2.1-Turbo) and the
generic activity illustrations of a storyboard (ordinary people doing the action, never a cast member's face).
RealVisXL/SDXL, the two-person project shots and the character candidates/sheets are gone; without Qwen a job fails
with a clear message instead of falling back to another model."""

from __future__ import annotations

import asyncio
import logging
import random
from pathlib import Path
from typing import Any

from backend.core.config import settings
from backend.core.exceptions import ConflictError, ValidationError
from backend.db.transactions import read_transaction, write_transaction
from backend.ai.image import recipes
from backend.library import library_service as library
from backend.ai.image.engine import QwenUnavailable, get_image_engine
from backend.ai.image.runner import ImageJobRunner

SIZE = (1344, 768)
logger = logging.getLogger(__name__)
QWEN_MISSING = "The local image model (Qwen-Image-2.1-Turbo) is not installed on this computer"


async def _qwen_pictures(engine, items: list[dict[str, Any]], consumer: str) -> None:
    """Draw `items` with Qwen-Image-2.1-Turbo; raise a clear error when the model is missing or a picture is not made."""
    if not items:
        return
    try:
        await engine.qwen_batch("qwen21", items, consumer)
    except QwenUnavailable as exc:
        logger.warning("qwen_unavailable consumer=%s reason=%s", consumer, exc)
        raise ValidationError(QWEN_MISSING) from exc
    missing = [item["output_path"] for item in items if not Path(item["output_path"]).is_file()]
    if missing:
        raise RuntimeError(f"Qwen did not write {len(missing)} picture(s)")


async def scene_preview(job: dict, runner: ImageJobRunner) -> dict:
    """The scene library's picture of a place (also the plate a still-scene video shows)."""
    db = runner.get_db()
    async with read_transaction():
        scene = await library.get_scene_row(db, job["target_id"])
    path = settings.DATA_DIR / "library" / "scenes" / scene["id"] / "preview.png"
    await runner.boundary(job["id"], "scene preview", 0)
    seed = scene.get("seed") or random.randint(1, 2**31 - 1)
    await _qwen_pictures(get_image_engine(), [{"prompt": recipes.qwen_scene_prompt(scene), "seed": seed,
                                               "width": SIZE[0], "height": SIZE[1], "output_path": str(path)}],
                         "visuals_scene_preview")
    await runner.boundary(job["id"], "scene preview complete", 99)
    async with write_transaction(db):
        await db.execute(
            "UPDATE scenes SET preview_path = ?, updated_at = ? WHERE id = ?",
            (str(path), library._now(), scene["id"]),
        )
    return {"path": str(path), "prompt_truncated": False}


async def activity_illustrations(job: dict, runner: ImageJobRunner) -> dict:
    """Task 33.10 (D102): one local-GPU picture per storyboard insert with no library picture and none pending; each is stored
    as a pending generic Activity Library item (approved in Step 5, then reused by every later video). D123: ordinary
    people doing the action -- never the speaking character."""
    from backend.library import activity_illustrations as illustrations
    from backend.library import activity_library_service as activity_library

    db = runner.get_db()
    project_id = job["target_id"]
    async with read_transaction():
        report = await illustrations.coverage(db, project_id)
    todo = [item for item in report["items"] if item["status"] == "missing" and item["pending"] is None]
    created: list[str] = []
    if not todo:
        return {"created": created}
    folder = settings.DATA_DIR / "visuals" / project_id / "activity_drafts"
    await asyncio.to_thread(folder.mkdir, parents=True, exist_ok=True)
    paths = {item["beat_id"]: folder / f"{item['beat_id']}.png" for item in todo}
    await runner.boundary(job["id"], f"illustrations 0/{len(todo)}", 0)
    await _qwen_pictures(get_image_engine(), [
        {"prompt": recipes.qwen_activity_prompt(item["action"], item["place"]), "seed": random.randint(1, 2**31 - 1),
         "width": SIZE[0], "height": SIZE[1], "output_path": str(paths[item["beat_id"]])} for item in todo
    ], "visuals_activity_illustrations")
    for item in todo:
        path = paths[item["beat_id"]]
        content = await asyncio.to_thread(path.read_bytes)
        metadata = {"activity": item["activity"], "context_tags": [item["place"]] if item["place"] else []}
        try:
            async with write_transaction(db):
                row = await activity_library.upload_activity_bytes(db, path.name, content, metadata)
        except ConflictError:  # the same picture again: nothing new to review
            continue
        finally:
            await asyncio.to_thread(path.unlink, missing_ok=True)
        created.append(row["id"])
    await runner.boundary(job["id"], "illustrations ready for review", 99)
    return {"created": created}
