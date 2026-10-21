"""Verified Solo media bridge shared by embedded preview and production staging."""
from __future__ import annotations

import asyncio
import json
import uuid
import hashlib
from pathlib import Path

import aiosqlite

from backend.core.exceptions import ConflictError, ValidationError
from backend.db.transactions import read_transaction
from backend.library import explainer_service as plans, explainer_assets, explainer_stage, presenter_asset_plan
from backend.library.explainer_layout_service import validate_plan, RULES
from backend.library.explainer_timing import ScriptIndex, resolve_timeline
from backend.schemas.explainer import ExplainerPlan


async def build_payload(db: aiosqlite.Connection, project_id: str, aspect: str = "16:9", *, approved: bool = False) -> dict:
    """Capture source, verify immutable files out of lock, then recheck revision before returning."""
    if aspect not in RULES["aspects"]:
        raise ValidationError("Choose16:9 or9:16")
    async with read_transaction():
        row = await plans._row(db, project_id)
        if not row:
            raise ValidationError("Propose and review an explainer plan first")
        plan = ExplainerPlan.model_validate_json(row["plan_json"])
        snapshot = await plans.source_snapshot(db, project_id, plan.segments)
        if not snapshot["audio"] or snapshot["audio"]["status"] != "complete":
            raise ValidationError("Generate the actual audio mix before opening the synchronized preview")
        if not plan.presenter.front_pack_revision:
            raise ValidationError("Import and approve the full front21 pack before preview/render")
        if snapshot["fingerprint"] != plan.source_fingerprint:
            raise ConflictError("The explainer source changed; save/review a fresh plan")
        if aspect not in plan.aspects:
            raise ValidationError("Review this output aspect in the explainer plan first")
        if approved and (row["status"] != "approved" or row["approved_revision"] != plan.revision or not row["approved_snapshot_json"]):
            raise ValidationError("Approve the current explainer plan before rendering")
        if approved and plans.source_issues(snapshot, plan.segments):
            raise ValidationError("Resolve all source, factual review and asset issues before rendering")
        assets = [await explainer_assets.get_asset(db, project_id, item["id"], item["version"])
                  for item in snapshot["source"]["illustrations"] if not item.get("missing")]
        pinned = json.loads(row["approved_snapshot_json"]) if approved else None
    audio_files = await asyncio.to_thread(plans._audio_files, snapshot)
    stage = await asyncio.to_thread(explainer_stage.pinned_files, snapshot["source"])
    await presenter_asset_plan.manifest(db, plan.presenter.profile_id)
    front = await presenter_asset_plan.resolve_manifest(plan.presenter.profile_id, plan.presenter.identity_version, plan.presenter.front_pack_revision)
    for asset in assets:
        await explainer_assets.verified_path(asset)
    geometry = await validate_plan(snapshot, plan)
    timeline = resolve_timeline(ScriptIndex(snapshot["lines"]), snapshot["audio"]).segments(plan.segments)
    if pinned and (pinned["audio_files"] != audio_files or pinned["front"] != front or pinned["geometry"] != geometry):
        raise ConflictError("An approved media file or geometry proof changed; review and approve again")
    if pinned:
        explainer_stage.verify_unchanged(pinned, stage)
    async with read_transaction():
        fresh = await plans._row(db, project_id)
        current = await plans.source_snapshot(db, project_id, plan.segments)
        if not fresh or fresh["revision"] != plan.revision or current["fingerprint"] != plan.source_fingerprint:
            raise ConflictError("The source or plan changed while preparing the preview/render")
    speaker, audio = snapshot["project"]["speakers"][0], snapshot["audio"]
    word_map = {entry["line_id"]: entry["words"] for entry in audio["word_timestamps"]}
    lines = [{"startSec": entry["start_sec"], "endSec": entry["end_sec"], "speaker": speaker["name"],
              "speakerId": speaker["id"], "text": line["text"], "words": [
                  {"text": word["text"], "startSec": word["start_sec"], "endSec": word["end_sec"]}
                  for word in word_map[line["id"]]]}
             for line, entry in zip(snapshot["lines"], audio["timestamps"], strict=True)]
    spec = RULES["aspects"][aspect]
    props = {"episodeId": project_id, "lines": lines,
             "speakers": [{"id": speaker["id"], "name": speaker["name"], "gender": speaker["gender"]}],
             "audioPath": f"/api/projects/{project_id}/audio/download?format=mp3", "fps": 30,
             "width": spec["width"], "height": spec["height"], "title": snapshot["project"]["name"],
             "topic": snapshot["project"]["topic"], "cefrLevel": snapshot["project"]["cefr_level"], "chapters": [],
             "introSec": 0, "outroSec": 0, "outroText": "", "captionStyle": "outline", "visualMode": "podcast_black",
             "layout": "vertical" if aspect == "9:16" else "horizontal", "presentationMode": "solo_explainer",
             "durationSeconds": timeline[-1]["end_sec"],
             "solo": {"plan": plan.model_dump(), "geometry": geometry, "timeline": timeline,
                      "pictures": {key: f"/api/visuals/profiles/{plan.presenter.profile_id}/assets/{value['asset_id']}/content" for key, value in front["pictures"].items()},
                      "photos": {f"{item['id']}:{item['version']}": explainer_assets.public(item)["preview_url"] for item in assets},
                      "scenes": {item["id"]: f"/api/visuals/scenes/{item['id']}/preview" for item in stage["scenes"]},
                      "activities": {item["id"]: f"/api/visuals/library/activities/{item['id']}/content" for item in stage["activities"]}}}
    if snapshot.get("learning"):
        learning = snapshot["learning"]
        props["learning"] = {
            "vocab": [{"word": item["word"], "partOfSpeech": item["part_of_speech"], "ipa": item["ipa"],
                       "definitionEn": item["definition_en"], "definitionVi": item["definition_vi"],
                       "exampleSentence": item["example_sentence"]} for item in learning["vocabulary"]],
            "idioms": [{"phrase": item["phrase"], "meaningEn": item["meaning_en"], "meaningVi": item["meaning_vi"],
                        "exampleSentence": item["example_sentence"]} for item in learning["idioms"]],
        }
    return {"props": props, "source_fingerprint": plan.source_fingerprint, "revision": plan.revision,
            "front": front, "illustrations": assets, "audio_files": audio_files, "stage": stage}


async def preview(db: aiosqlite.Connection, project_id: str, aspect: str) -> dict:
    """Expose only safe browser props; internal filesystem paths never reach the UI."""
    result = await build_payload(db, project_id, aspect)
    return {key: result[key] for key in ("props", "source_fingerprint", "revision")}


async def production_props(db: aiosqlite.Connection, project_id: str, aspect: str = "16:9") -> dict:
    """Pin verified images into an isolated public directory for this render attempt."""
    from backend.media.video_renderer_remotion import REMOTION_VISUALS_DIR, _copy_visual_source

    payload = await build_payload(db, project_id, aspect, approved=True)
    props = payload["props"]
    key = f"{project_id}-{uuid.uuid4().hex}"
    root = REMOTION_VISUALS_DIR / key
    pictures, photos = {}, {}
    def copy_pinned(source: Path, target: Path, digest: str) -> None:
        _copy_visual_source(source, target)
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            target.unlink(missing_ok=True)
            raise ConflictError("A pinned image changed while staging; review and approve again")
    for slot, image in payload["front"]["pictures"].items():
        target = root / f"{slot}.png"
        await asyncio.to_thread(copy_pinned, Path(image["path"]), target, image["content_hash"])
        pictures[slot] = f"remotion-render/visuals/{key}/{target.name}"
    for image in payload["illustrations"]:
        source = await explainer_assets.verified_path(image)
        target = root / f"photo-{image['id']}-{image['version']}.png"
        await asyncio.to_thread(copy_pinned, source, target, image["content_hash"])
        photos[f"{image['id']}:{image['version']}"] = f"remotion-render/visuals/{key}/{target.name}"
    scenes, activities = {}, {}
    for kind, staged in (("scene", scenes), ("activity", activities)):
        for image in payload["stage"]["scenes" if kind == "scene" else "activities"]:
            source = Path(image["path"])
            target = root / f"{kind}-{image['id']}{source.suffix.lower() or '.png'}"
            await asyncio.to_thread(copy_pinned, source, target, image["content_hash"])
            staged[image["id"]] = f"remotion-render/visuals/{key}/{target.name}"
    props["solo"].update(pictures=pictures, photos=photos, scenes=scenes, activities=activities)
    # Private: the video API records each rendered activity picture's use (never written into the Remotion props).
    props["_activityUses"] = [{"activity_id": segment["visual"]["activity_id"], "beat_id": segment["id"]}
                              for segment in props["solo"]["plan"]["segments"] if segment["visual"]["kind"] == "activity"]
    return props
