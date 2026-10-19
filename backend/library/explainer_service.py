"""Versioned Solo plans: source snapshots, owner locks and atomic draft publication."""
from __future__ import annotations

import asyncio
import hashlib
import json
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import aiosqlite

from backend.content import project_service, script_service
from pydantic import TypeAdapter, ValidationError as SchemaError

from backend.core.config import settings
from backend.core.constants import (
    AI_JOB_HEARTBEAT_SECONDS, EXPLAINER_LAYOUT_RULES_VERSION, EXPLAINER_PLAN_MAX_ISSUES,
    EXPLAINER_PROPOSAL_REPAIR_ATTEMPTS, EXPLAINER_PROPOSAL_TEMPERATURE,
)
from backend.core.exceptions import ConflictError, NotFoundError, ProviderError, SchemaValidationError, ValidationError
from backend.ai.llm import ai_job_service
from backend.ai.llm.contracts import GenerationRequest
from backend.ai.llm.prompt_loader import render_explainer_prompt
from backend.ai.llm.validation import parse_and_validate
from backend.db.transactions import read_transaction, write_transaction as _write_transaction
from backend.library import explainer_assets, presenter_asset_plan
from backend.library.explainer_timing import ScriptIndex, resolve_timeline
from backend.media import audio_service
from backend.schemas.explainer import (
    ExplainerApproval, ExplainerPlan, ExplainerPlanPatch, ExplainerProposal, ExplainerProposalRequest,
    ExplainerSegment, PresenterReference, ProposedExplainerSegment,
)

if TYPE_CHECKING:
    from backend.ai.llm.ai_worker import AIWorker, JobHandler
    from backend.ai.llm.router import AIRouter

_PROPOSAL = TypeAdapter(ExplainerProposal)


def fingerprint(value: dict) -> str:
    """Hash canonical plain data; source changes never depend on presentation labels or update times."""
    try:
        canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except ValueError as exc:
        raise ValidationError("The current source contains invalid numeric data; regenerate its audio before review") from exc
    return hashlib.sha256(canonical.encode()).hexdigest()


async def _row(db: aiosqlite.Connection, project_id: str) -> dict | None:
    row = await (await db.execute("SELECT * FROM project_explainer_plans WHERE project_id=?", (project_id,))).fetchone()
    return dict(row) if row else None


async def source_snapshot(db: aiosqlite.Connection, project_id: str, segments: list[ExplainerSegment]) -> dict:
    """Capture source metadata under the caller's short transaction, without filesystem/network work."""
    project = await project_service.get_project(db, project_id)
    if project.get("presentation_mode") != "solo_explainer" or len(project["speakers"]) != 1:
        raise ValidationError("Explainer plans require a Solo project with one presenter")
    lines = await script_service.get_script(db, project_id)
    ScriptIndex(lines)
    speaker = project["speakers"][0]
    cast = await (await db.execute("SELECT pc.*,c.identity_version AS current_identity_version FROM project_cast pc "
                                  "JOIN characters c ON c.id=pc.character_id WHERE pc.project_id=? ORDER BY speaker_index",
                                  (project_id,))).fetchall()
    if len(cast) != 1 or cast[0]["speaker_index"] != speaker["speaker_index"]:
        raise ValidationError("Select one character profile for this Solo presenter")
    member = dict(cast[0])
    front = await presenter_asset_plan.manifest_snapshot(db, member["character_id"])
    presenter = PresenterReference(speaker_id=speaker["id"], profile_id=member["character_id"],
                                   identity_version=member["profile_version"],
                                   front_pack_revision=front["pack_revision"] if front else None,
                                   asset_ids=[item["asset_id"] for item in front["pictures"].values()] if front else [])
    audio = await audio_service.get_audio_job(db, project_id)
    from backend.content import learning_service
    learning = await learning_service.get_learning_content(db, project_id)
    assets = {}
    for segment in segments:
        if segment.visual.kind == "photo" and segment.visual.asset:
            ref = segment.visual.asset
            try:
                asset = await explainer_assets.get_asset(db, project_id, ref.asset_id, ref.version)
                assets[(ref.asset_id, ref.version)] = {key: asset[key] for key in ("id", "version", "content_hash", "width", "height", "path")}
            except NotFoundError:
                assets[(ref.asset_id, ref.version)] = {"id": ref.asset_id, "version": ref.version, "missing": True}
    source = {
        "project": {key: project.get(key) for key in ("id", "presentation_mode", "explainer_structure", "topic", "cefr_level", "language_features")},
        "speaker": {key: speaker.get(key) for key in ("id", "speaker_index", "tts_engine", "voice_id", "accent", "gender", "voice_description", "speed", "pitch", "volume")},
        "lines": [{key: line.get(key) for key in ("id", "speaker_id", "text", "audio_cache_path")} for line in lines],
        "cast": member, "presenter": presenter.model_dump(),
        "audio": {key: audio.get(key) for key in ("id", "status", "mp3_path", "wav_path", "completed_at", "duration_seconds", "timestamps", "word_timestamps")} if audio else None,
        "illustrations": sorted(assets.values(), key=lambda item: (item["id"], item["version"])),
        "layout_rules_version": EXPLAINER_LAYOUT_RULES_VERSION,
        "learning": {key: learning.get(key, []) for key in ("vocabulary", "idioms")} if learning else None,
    }
    return {"source": source, "fingerprint": fingerprint(source), "project": project, "lines": lines,
            "presenter": presenter.model_dump(), "front": front, "audio": audio, "learning": learning}


def source_issues(snapshot: dict, segments: list[ExplainerSegment]) -> list[str]:
    """Report actionable blockers while keeping an incomplete plan editable as a draft."""
    issues = []
    try:
        ScriptIndex(snapshot["lines"]).validate_coverage(segments)
        resolve_timeline(ScriptIndex(snapshot["lines"]), snapshot["audio"]).segments(segments)
    except ValidationError as exc:
        issues.append(str(exc))
    if not snapshot["front"]:
        issues.append("Import and approve the presenter's complete front21 pack before approval")
    if snapshot["source"]["cast"]["profile_version"] != snapshot["source"]["cast"]["current_identity_version"]:
        issues.append("The cast's pinned identity is older than its current profile; review and reselect the presenter")
    for segment in segments:
        if segment.needs_fact_review:
            issues.append(f"Segment {segment.id}: review its knowledge claims and illustration text")
        if segment.visual.kind == "photo" and not segment.visual.asset:
            issues.append(f"Segment {segment.id}: import or select its illustration")
    issues.extend(f"Illustration {asset['id']} is missing from this project" for asset in snapshot["source"]["illustrations"] if asset.get("missing"))
    return list(dict.fromkeys(issues))[:EXPLAINER_PLAN_MAX_ISSUES]


def merge_proposal(previous: list[ExplainerSegment], proposed: list[ExplainerSegment]) -> list[ExplainerSegment]:
    """Preserve stable segment IDs and every owner-locked group, regardless of model output."""
    old = {segment.id: segment for segment in previous}
    if previous and [segment.id for segment in proposed] != [segment.id for segment in previous]:
        raise ValidationError("Regeneration must preserve existing segment IDs and order; unlock/edit segmentation explicitly")
    result = []
    for segment in proposed:
        value = segment.model_dump()
        value["needs_fact_review"] = True
        value["locks"] = old[segment.id].locks.model_dump() if segment.id in old else {}
        if segment.id in old:
            original = old[segment.id].model_dump()
            locks = old[segment.id].locks
            if locks.content:
                for key in ("intent", "line_ids", "start", "end", "source_notes", "needs_fact_review"):
                    value[key] = original[key]
            if locks.visual:
                value["visual"] = original["visual"]
            value["needs_fact_review"] = original["needs_fact_review"] if locks.content and locks.visual else True
            if locks.gestures:
                value["gestures"] = original["gestures"]
            # Model proposals never get to author geometry or clear a reviewed layout.
            value["layouts"] = {aspect: layout for aspect, layout in original["layouts"].items()
                                if (aspect == "16:9" and locks.layout_16_9) or (aspect == "9:16" and locks.layout_9_16)}
        else:
            value["layouts"] = {}
        result.append(ExplainerSegment.model_validate(value))
    return result


async def publish_draft(db: aiosqlite.Connection, project_id: str, segments: list[ExplainerSegment],
                        aspects: list[str], expected_revision: int) -> ExplainerPlan:
    """CAS-publish current and immutable history together under the caller's write transaction."""
    old = await _row(db, project_id)
    if (old["revision"] if old else 0) != expected_revision:
        raise ConflictError("The explainer plan changed; reload before saving or regenerating")
    snapshot = await source_snapshot(db, project_id, segments)
    ScriptIndex(snapshot["lines"]).validate_coverage(segments)
    plan = ExplainerPlan(project_id=project_id, revision=expected_revision + 1,
                         source_fingerprint=snapshot["fingerprint"], presenter=snapshot["presenter"], segments=segments,
                         aspects=aspects, issues=source_issues(snapshot, segments))
    now = datetime.now(timezone.utc).isoformat()
    await db.execute("INSERT INTO project_explainer_plan_versions(project_id,revision,source_fingerprint,plan_json,created_at) VALUES(?,?,?,?,?)",
                     (project_id, plan.revision, plan.source_fingerprint, plan.model_dump_json(), now))
    await db.execute("INSERT INTO project_explainer_plans(project_id,revision,status,source_fingerprint,plan_json,updated_at) VALUES(?,?,'draft',?,?,?) "
                     "ON CONFLICT(project_id) DO UPDATE SET revision=excluded.revision,status='draft',source_fingerprint=excluded.source_fingerprint,"
                     "plan_json=excluded.plan_json,updated_at=excluded.updated_at",
                     (project_id, plan.revision, plan.source_fingerprint, plan.model_dump_json(), now))
    return plan


async def get_plan(db: aiosqlite.Connection, project_id: str) -> dict:
    """Return the saved plan plus live staleness/issues without rewriting immutable history."""
    async with read_transaction():
        project = await project_service.get_project(db, project_id)
        if project.get("presentation_mode") != "solo_explainer":
            raise ValidationError("Explainer plans belong to Solo projects")
        row = await _row(db, project_id)
        if not row:
            return {"plan": None, "current_source_fingerprint": None, "issues": [], "approved_revision": None}
        plan = ExplainerPlan.model_validate_json(row["plan_json"])
        try:
            snapshot = await source_snapshot(db, project_id, plan.segments)
            current = snapshot["fingerprint"]
            issues = source_issues(snapshot, plan.segments)
        except (NotFoundError, ValidationError) as exc:
            current, issues = None, [str(exc)]
    value = plan.model_dump()
    if current != plan.source_fingerprint:
        value["status"] = "stale"
        issues.insert(0, "Script, audio, presenter or illustrations changed; review a new plan revision")
    value["issues"] = list(dict.fromkeys(issues))[:EXPLAINER_PLAN_MAX_ISSUES]
    return {"plan": value, "current_source_fingerprint": current, "issues": value["issues"], "approved_revision": row["approved_revision"]}


async def save_plan(db: aiosqlite.Connection, project_id: str, body: ExplainerPlanPatch) -> dict:
    """Save an owner revision atomically; only the owner may mark factual review complete."""
    async with _write_transaction(db):
        row = await _row(db, project_id)
        if not row or row["revision"] != body.expected_revision:
            raise ConflictError("The explainer plan changed; reload before saving")
        old = ExplainerPlan.model_validate_json(row["plan_json"])
        source = await source_snapshot(db, project_id, old.segments)
        if source["fingerprint"] != body.expected_source_fingerprint:
            raise ConflictError("The script, audio or presenter changed while editing; reload before saving")
        previous = {segment.id: segment.model_dump() for segment in old.segments}
        changed = []
        for segment in body.segments:
            value = segment.model_dump()
            before = previous.get(segment.id)
            if before:
                value["locks"] = {key: value["locks"][key] or before["locks"][key] for key in before["locks"]}
            groups = {
                "content": ("intent", "line_ids", "start", "end", "source_notes", "needs_fact_review"),
                "visual": ("visual",), "gestures": ("gestures",),
            }
            for group, keys in groups.items():
                if before is None or any(value[key] != before[key] for key in keys):
                    value["locks"][group] = True
            for aspect, group in (("16:9", "layout_16_9"), ("9:16", "layout_9_16")):
                if before is None or value["layouts"].get(aspect) != before["layouts"].get(aspect):
                    value["locks"][group] = True
            # Explicit unlocks let the owner opt a previously edited field back into regeneration.
            for group in body.unlock_fields.get(segment.id, []):
                value["locks"][group] = False
            changed.append(ExplainerSegment.model_validate(value))
        await publish_draft(db, project_id, changed, body.aspects, body.expected_revision)
    return await get_plan(db, project_id)


async def history(db: aiosqlite.Connection, project_id: str) -> list[dict]:
    """Read immutable past revisions, scoped to this project."""
    async with read_transaction():
        await project_service.get_project(db, project_id)
        rows = await (await db.execute("SELECT plan_json FROM project_explainer_plan_versions WHERE project_id=? ORDER BY revision", (project_id,))).fetchall()
    return [ExplainerPlan.model_validate_json(row[0]).model_dump() for row in rows]


async def enqueue_proposal(db: aiosqlite.Connection, project_id: str, body: ExplainerProposalRequest) -> tuple[dict, bool]:
    """Capture source, current locks/revision and available image references in one short transaction."""
    async with _write_transaction(db):
        row = await _row(db, project_id)
        revision = row["revision"] if row else 0
        if revision != body.expected_revision:
            # A retry of the exact request may return its prior completed job.
            if body.idempotency_key:
                prior = await (await db.execute("SELECT * FROM ai_generation_jobs WHERE project_id=? AND operation='propose_explainer' AND idempotency_key=?",
                                                (project_id, body.idempotency_key))).fetchone()
                if prior:
                    return dict(prior), False
            raise ConflictError("The explainer plan changed; reload before proposing")
        previous = ExplainerPlan.model_validate_json(row["plan_json"]) if row else None
        source = await source_snapshot(db, project_id, previous.segments if previous else [])
        if previous:
            index = ScriptIndex(source["lines"])
            for segment in previous.segments:
                if not any(segment.locks.model_dump().values()):
                    continue
                try:
                    start, end = index.boundary(segment.start), index.boundary(segment.end)
                    if end <= start or segment.line_ids != index.line_ids(segment.start, segment.end):
                        raise ValidationError("The segment no longer covers its original ordered lines")
                    if segment.locks.gestures:
                        for cue in segment.gestures:
                            if not start <= index.boundary(cue.at) < end:
                                raise ValidationError("A locked gesture no longer belongs to its segment")
                except ValidationError as exc:
                    raise ValidationError(f"A locked segment lost its script anchors ({segment.id}); edit/unlock it first: {exc}") from exc
        available = await explainer_assets.list_assets(db, project_id)
        snapshot = {"expected_revision": revision, "source_fingerprint": source["fingerprint"],
                    "source": source["source"], "previous": previous.model_dump() if previous else None,
                    "available_assets": available}
        return await ai_job_service.create_job(db, project_id, "propose_explainer", snapshot,
                                               idempotency_key=body.idempotency_key, requested_provider=settings.AI_MODE, commit=False)


async def _validate_geometry(snapshot: dict, plan: ExplainerPlan) -> dict:
    from backend.library.explainer_layout_service import validate_plan

    return await validate_plan(snapshot, plan)


def _audio_files(snapshot: dict) -> list[dict]:
    root = (settings.DATA_DIR / "audio" / snapshot["project"]["id"]).resolve()
    result = []
    for kind in ("wav_path", "mp3_path"):
        value = snapshot["audio"].get(kind)
        if not value:
            raise ValidationError("Current audio files are missing; regenerate audio")
        path = Path(value).resolve()
        if not path.is_relative_to(root):
            raise ValidationError("Current audio is outside its project folder; regenerate audio")
        try:
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
        except OSError as exc:
            raise ValidationError("Current audio file is missing; regenerate audio") from exc
        result.append({"kind": kind, "path": str(path), "content_hash": digest})
    return result


async def approve_plan(db: aiosqlite.Connection, project_id: str, body: ExplainerApproval) -> dict:
    """Verify actual assets/timing/geometry outside the DB lock, then CAS-pin a new immutable revision."""
    async with read_transaction():
        row = await _row(db, project_id)
        if not row or row["revision"] != body.expected_revision:
            raise ConflictError("The explainer plan changed; reload before approval")
        plan = ExplainerPlan.model_validate_json(row["plan_json"])
        snapshot = await source_snapshot(db, project_id, plan.segments)
        if body.source_fingerprint != plan.source_fingerprint or snapshot["fingerprint"] != body.source_fingerprint:
            raise ConflictError("The plan source changed; save and review a new revision before approval")
        issues = source_issues(snapshot, plan.segments)
        if issues:
            raise ValidationError("; ".join(issues))
        images = []
        for segment in plan.segments:
            if segment.visual.kind == "photo":
                ref = segment.visual.asset
                asset = await explainer_assets.get_asset(db, project_id, ref.asset_id, ref.version)
                if ref.content_hash and ref.content_hash != asset["content_hash"]:
                    raise ValidationError("An illustration reference does not match its immutable content hash")
                images.append(asset)
    audio = await asyncio.to_thread(_audio_files, snapshot)
    # Ensure this revision's immutable manifest exists, then resolve/hash every pinned front picture.
    await presenter_asset_plan.manifest(db, plan.presenter.profile_id)
    front = await presenter_asset_plan.resolve_manifest(plan.presenter.profile_id, plan.presenter.identity_version, plan.presenter.front_pack_revision)
    for image in images:
        await explainer_assets.verified_path(image)
    geometry = await _validate_geometry(snapshot, plan)
    if not isinstance(geometry, dict) or geometry.get("rules_version") != EXPLAINER_LAYOUT_RULES_VERSION or set(geometry.get("aspects", {})) != set(plan.aspects):
        raise ValidationError("Layout validation did not produce a complete proof for the selected aspects")
    timeline = resolve_timeline(ScriptIndex(snapshot["lines"]), snapshot["audio"]).segments(plan.segments)
    async with _write_transaction(db):
        fresh = await _row(db, project_id)
        current = await source_snapshot(db, project_id, plan.segments)
        if not fresh or fresh["revision"] != body.expected_revision or current["fingerprint"] != body.source_fingerprint:
            raise ConflictError("The plan or source changed during approval; reload and review again")
        approved = plan.model_copy(update={"revision": plan.revision + 1, "status": "approved", "issues": []})
        pinned = {"schema_version": 1, "plan": approved.model_dump(), "source": current["source"], "audio_files": audio,
                  "front": front, "illustrations": images, "timing": timeline, "geometry": geometry}
        now = datetime.now(timezone.utc).isoformat()
        await db.execute("INSERT INTO project_explainer_plan_versions(project_id,revision,source_fingerprint,plan_json,created_at) VALUES(?,?,?,?,?)",
                         (project_id, approved.revision, approved.source_fingerprint, approved.model_dump_json(), now))
        await db.execute("UPDATE project_explainer_plans SET revision=?,status='approved',plan_json=?,approved_revision=?,approved_snapshot_json=?,updated_at=? WHERE project_id=?",
                         (approved.revision, approved.model_dump_json(), approved.revision, json.dumps(pinned), now, project_id))
    return await get_plan(db, project_id)


async def arrange_plan(db: aiosqlite.Connection, project_id: str, body: ExplainerApproval) -> dict:
    """Return checked layout suggestions; owner PATCH remains the explicit save/lock action."""
    from backend.library.explainer_layout_service import arrange

    async with read_transaction():
        row = await _row(db, project_id)
        if not row or row["revision"] != body.expected_revision:
            raise ConflictError("The plan changed; reload before arranging layouts")
        plan = ExplainerPlan.model_validate_json(row["plan_json"])
        snapshot = await source_snapshot(db, project_id, plan.segments)
        if snapshot["fingerprint"] != body.source_fingerprint:
            raise ConflictError("The source changed; reload and save a reviewed revision before arranging")
    await presenter_asset_plan.manifest(db, plan.presenter.profile_id)
    segments, geometry = await arrange(snapshot, plan)
    async with read_transaction():
        fresh = await _row(db, project_id)
        current = await source_snapshot(db, project_id, plan.segments)
        if not fresh or fresh["revision"] != body.expected_revision or current["fingerprint"] != body.source_fingerprint:
            raise ConflictError("The source or plan changed during layout validation; reload before applying")
    return {"segments": [segment.model_dump() for segment in segments], "geometry": geometry,
            "expected_revision": body.expected_revision, "source_fingerprint": body.source_fingerprint}


async def import_illustration(db: aiosqlite.Connection, project_id: str, content: bytes, filename: str) -> dict:
    """Decode out of lock and publish only while the live project is still eligible."""
    async with read_transaction():
        project = await project_service.get_project(db, project_id)
        if project.get("presentation_mode") != "solo_explainer":
            raise ValidationError("Illustrations belong to a Solo project")
    staged = await explainer_assets.stage_upload(project_id, content, filename)
    try:
        async with _write_transaction(db):
            result = await explainer_assets.publish(db, staged)
    except BaseException:
        await explainer_assets.discard(staged)
        raise
    return result


async def illustration_content(db: aiosqlite.Connection, project_id: str, asset_id: str, version: int) -> Path:
    """Resolve one immutable project-owned file without holding a DB lock during hashing."""
    async with read_transaction():
        row = await explainer_assets.get_asset(db, project_id, asset_id, version)
    return await explainer_assets.verified_path(row)


async def list_illustrations(db: aiosqlite.Connection, project_id: str) -> list[dict]:
    """List project-owned choices for the editor, scoped to an existing Solo project."""
    async with read_transaction():
        project = await project_service.get_project(db, project_id)
        if project.get("presentation_mode") != "solo_explainer":
            raise ValidationError("Illustrations belong to a Solo project")
        return await explainer_assets.list_assets(db, project_id)


def _proposed_segments(text: str, previous: list[ExplainerSegment], snapshot: dict, lines: list[dict]) -> list[ExplainerSegment]:
    wire = parse_and_validate(text, _PROPOSAL)
    segments = merge_proposal(previous, [ExplainerSegment.model_validate(item.model_dump()) for item in wire.segments])
    ScriptIndex(lines).validate_coverage(segments)
    choices = {(item["asset"]["asset_id"], item["asset"]["version"]): item["asset"]["content_hash"] for item in snapshot["available_assets"]}
    for segment in segments:
        if segment.visual.kind == "photo" and segment.visual.asset:
            ref = segment.visual.asset
            actual = choices.get((ref.asset_id, ref.version))
            if actual is None or (ref.content_hash is not None and ref.content_hash != actual):
                raise ValidationError("Use only the illustration versions listed in the proposal input")
    return segments


async def _job_guard(db: aiosqlite.Connection, job: dict, captured: dict) -> bool:
    """Caller holds a write transaction: cancellation/source/revision/lease are checked at publication too."""
    try:
        current_job = await ai_job_service.get_job(db, job["id"], job["project_id"])
    except NotFoundError:
        return False  # Project deletion cascades its job; no late result may recreate it.
    if current_job["status"] not in ("running", "validating") or current_job["lease_owner"] != job["lease_owner"]:
        return False
    if current_job["cancel_requested"]:
        await ai_job_service.transition_status(db, job["id"], "cancelled", commit=False)
        return False
    row = await _row(db, job["project_id"])
    previous = ExplainerPlan.model_validate(captured["previous"]) if captured["previous"] else None
    try:
        source = await source_snapshot(db, job["project_id"], previous.segments if previous else [])
        matches = (row["revision"] if row else 0) == captured["expected_revision"] and source["fingerprint"] == captured["source_fingerprint"]
    except (NotFoundError, ValidationError):
        matches = False
    if not matches:
        await ai_job_service.mark_stale(db, job["id"], commit=False)
        return False
    return True


async def _heartbeat(worker: "AIWorker", job_id: str) -> None:
    while True:
        await asyncio.sleep(AI_JOB_HEARTBEAT_SECONDS)
        await worker.heartbeat(job_id)


def make_handler(router: "AIRouter") -> "JobHandler":
    """Build the durable proposal handler using the app's current provider policy."""
    async def handler(job: dict, worker: "AIWorker") -> None:
        heartbeat = asyncio.create_task(_heartbeat(worker, job["id"]))
        try:
            await _run_proposal(job, worker, router)
        finally:
            heartbeat.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat
    return handler


async def _run_proposal(job: dict, worker: "AIWorker", router: "AIRouter") -> None:
    db = worker.get_db()
    captured = json.loads(job["input_snapshot_json"])
    # Never resume a malformed project-only snapshot supplied through another job entry point.
    required = {"source", "source_fingerprint", "expected_revision", "previous", "available_assets"}
    if not isinstance(captured, dict) or not required <= captured.keys():
        raise ValidationError("The explainer proposal job has no valid source snapshot; create a fresh proposal")
    async with _write_transaction(db):
        if not await _job_guard(db, job, captured):
            return
        source = await source_snapshot(db, job["project_id"], [])
        checkpoints = await ai_job_service.get_valid_checkpoints(db, job["id"])
    previous = ExplainerPlan.model_validate(captured["previous"]) if captured["previous"] else None
    old_segments = previous.segments if previous else []
    checkpoint = next((item for item in checkpoints if item["stage"] == "explainer_proposal" and item["input_hash"] == job["input_hash"]), None)
    segments = None
    if checkpoint:
        try:
            segments = _proposed_segments(checkpoint["result_json"], old_segments, captured, source["lines"])
        except (SchemaValidationError, SchemaError, ValidationError):
            # A corrupt/incompatible checkpoint is never treated as trusted content.
            segments = None
    error = ""
    last_output = ""
    try:
        for attempt in range(EXPLAINER_PROPOSAL_REPAIR_ATTEMPTS + 1):
            if segments is not None:
                break
            async with _write_transaction(db):
                if not await _job_guard(db, job, captured):
                    return
                await ai_job_service.update_progress(db, job["id"], "repair" if attempt else "proposal", 40 if attempt else 15, commit=False)
            index = ScriptIndex(source["lines"])
            prompt = await render_explainer_prompt(
                topic=source["project"]["topic"], cefr_level=source["project"]["cefr_level"],
                structure=source["project"]["explainer_structure"],
                lines=[{"line_id": line["id"], "text": line["text"], "tokens": [token.text for token in index.tokens if token.line_id == line["id"]]} for line in source["lines"]],
                previous=captured["previous"], assets=captured["available_assets"], previous_error=error,
                previous_output=last_output,
            )
            request = GenerationRequest(prompt=prompt, json_schema=_PROPOSAL.json_schema(), temperature=EXPLAINER_PROPOSAL_TEMPERATURE,
                                        deadline_seconds=settings.AI_REQUEST_DEADLINE_SECONDS, purpose="explainer_proposal_repair" if attempt else "explainer_proposal")
            try:
                response = await router.generate(request)
            except ProviderError as exc:
                async with _write_transaction(db):
                    if await _job_guard(db, job, captured):
                        await ai_job_service.record_generation_call(db, job["id"], {"purpose": request.purpose, "outcome": "error", "error_type": type(exc).__name__, "is_repair": bool(attempt)}, commit=False)
                        await ai_job_service.transition_status(db, job["id"], "error", error_code=ai_job_service.provider_error_code(exc), error_message=type(exc).__name__, commit=False)
                return
            async with _write_transaction(db):
                if not await _job_guard(db, job, captured):
                    return
                await ai_job_service.record_generation_call(db, job["id"], {
                    **response.model_dump(exclude={"text"}), "purpose": request.purpose, "section_index": None,
                    "outcome": "ok", "is_repair": bool(attempt), "at": datetime.now(timezone.utc).isoformat(),
                }, commit=False)
            last_output = response.text
            try:
                segments = _proposed_segments(response.text, old_segments, captured, source["lines"])
            except (SchemaValidationError, SchemaError, ValidationError) as exc:
                error = str(exc)[:500]
        if segments is None:
            async with _write_transaction(db):
                if await _job_guard(db, job, captured):
                    await ai_job_service.transition_status(db, job["id"], "error", error_code="explainer_invalid_proposal", error_message=error[:200], commit=False)
            return
        # Store only provider wire content: locks/review are reapplied from the captured owner draft on recovery.
        wire = {"segments": [{key: value for key, value in segment.model_dump().items() if key in ProposedExplainerSegment.model_fields} for segment in segments]}
        async with _write_transaction(db):
            if not await _job_guard(db, job, captured):
                return
            await ai_job_service.save_checkpoint(db, job["id"], 0, "explainer_proposal", "valid", job["input_hash"], result_json=json.dumps(wire), commit=False)
        # A separate durable checkpoint allows a process interruption here to resume without another model call.
        async with _write_transaction(db):
            if not await _job_guard(db, job, captured):
                return
            fresh = await ai_job_service.get_job(db, job["id"], job["project_id"])
            if fresh["status"] == "running":
                await ai_job_service.transition_status(db, job["id"], "validating", commit=False)
            await publish_draft(db, job["project_id"], segments, previous.aspects if previous else ["16:9", "9:16"], captured["expected_revision"])
            await ai_job_service.transition_status(db, job["id"], "complete", commit=False)
    except (NotFoundError, ValidationError, ConflictError) as exc:
        async with _write_transaction(db):
            if await _job_guard(db, job, captured):
                await ai_job_service.transition_status(db, job["id"], "error", error_code="explainer_validation_failed", error_message=str(exc)[:200], commit=False)
