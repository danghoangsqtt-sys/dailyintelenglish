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
DOODLE_GROUP = 20  # Phase 98 (D166): each group loads the model once (about 85 s) and is saved, so a late failure keeps the rest
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


def explainer_photo_slots(plan: dict | None) -> list[dict]:
    """Phase 85: the photo slots of a Solo / VOX plan that still have no picture (a locked owner visual is left alone)."""
    return [segment for segment in (plan or {}).get("segments", [])
            if (segment.get("visual") or {}).get("kind") == "photo" and not segment["visual"].get("asset")
            and not (segment.get("locks") or {}).get("visual")]


async def explainer_illustrations(job: dict, runner: ImageJobRunner) -> dict:
    """Phase 85 (owner 2026-10-28): Qwen draws every photo slot of a Solo / VOX plan that has no picture, from the slot's
    own description; each picture becomes the project's illustration, is set on its segment, and is kept in the Activity
    Library as an approved generic picture tagged "qwen" (the owner chose: used right away, kept for later videos)."""
    from backend.content import project_service
    from backend.library import explainer_service

    db = runner.get_db()
    project_id = job["target_id"]
    view = await explainer_service.get_plan(db, project_id)
    todo = explainer_photo_slots(view.get("plan"))
    async with read_transaction():
        project = await project_service.get_project(db, project_id)
    style = project.get("explainer_style")
    prompt_of = recipes.qwen_collage_prompt if style == "vox" else recipes.qwen_illustration_prompt  # Phase 86
    if not todo:
        return {"drawn": []}
    doodle = style == "doodle"
    if doodle:
        hero = ""
        has_recurring_hero = project.get("explainer_subject") in ("myth", "story")
        if has_recurring_hero:
            async with read_transaction():
                hero = (await explainer_service.doodle_notes(db, project_id)).get("hero") or ""
        prompt_of = lambda description: recipes.qwen_doodle_prompt(description, hero, allow_labels=not has_recurring_hero)  # noqa: E731
    group = DOODLE_GROUP if doodle else len(todo)
    drawn: list[str] = []
    for start in range(0, len(todo), group):
        drawn += await _draw_explainer_group(job, runner, db, project_id, todo[start:start + group], prompt_of, not doodle,
                                             len(drawn), len(todo))
    await runner.boundary(job["id"], "illustrations ready", 99)
    return {"drawn": sorted(drawn)}


async def _draw_explainer_group(job: dict, runner: ImageJobRunner, db, project_id: str, todo: list[dict], prompt_of, keep_in_library: bool,
                                done: int, total: int) -> list[str]:
    """One group of photo slots: drawn, imported, and set on their segments. Phase 98: a Doodle story's pictures stay out of the
    Activity Library, which other videos draw from."""
    from backend.library import activity_library_service as activity_library
    from backend.library import explainer_service
    from backend.schemas.explainer import ExplainerPlanPatch

    folder = settings.DATA_DIR / "visuals" / project_id / "explainer_drafts"
    await asyncio.to_thread(folder.mkdir, parents=True, exist_ok=True)
    paths = {segment["id"]: folder / f"{segment['id']}.png" for segment in todo}
    await runner.boundary(job["id"], f"illustrations {done}/{total}", round(99 * done / total))
    await _qwen_pictures(get_image_engine(), [
        {"prompt": prompt_of(segment["visual"].get("prompt") or segment["visual"].get("caption") or segment.get("intent") or ""),
         "seed": random.randint(1, 2**31 - 1), "width": SIZE[0], "height": SIZE[1], "output_path": str(paths[segment["id"]])}
        for segment in todo
    ], "explainer_illustrations")
    assets: dict[str, dict] = {}
    for segment in todo:
        path = paths[segment["id"]]
        content = await asyncio.to_thread(path.read_bytes)
        try:
            assets[segment["id"]] = (await explainer_service.import_illustration(db, project_id, content, path.name))["asset"]
            if keep_in_library:
                label = " ".join((segment["visual"].get("prompt") or segment.get("intent") or "illustration").split()[:6])
                try:
                    async with write_transaction(db):
                        row = await activity_library.upload_activity_bytes(db, path.name, content,
                                                                           {"activity": label, "context_tags": ["qwen"]})
                        await activity_library.set_review(db, row["id"], "approved")
                except (ConflictError, ValidationError) as exc:  # the library copy is a convenience; the video has its picture
                    logger.info("explainer_illustration_library_skipped segment=%s reason=%s", segment["id"], exc)
        finally:
            await asyncio.to_thread(path.unlink, missing_ok=True)
    view = await explainer_service.get_plan(db, project_id)
    plan = view["plan"]
    segments = [{**segment, "visual": {**segment["visual"], "asset": assets[segment["id"]]}} if segment["id"] in assets
                else segment for segment in plan["segments"]]
    await explainer_service.save_plan(db, project_id, ExplainerPlanPatch.model_validate({
        "expected_revision": plan["revision"], "expected_source_fingerprint": view["current_source_fingerprint"],
        "segments": segments, "aspects": plan["aspects"]}))
    return list(assets)


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
