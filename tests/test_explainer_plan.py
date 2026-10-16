"""Solo draft ownership, source CAS, locked regeneration and durable-job publication races."""
import asyncio
import copy
import json
from types import SimpleNamespace

import pytest

from backend.ai.llm import ai_job_service
from backend.ai.llm.ai_worker import AIWorker
from backend.ai.llm.contracts import GenerationResult
from backend.content import project_service, script_service
from backend.core.config import settings
from backend.core.exceptions import ConflictError, ProviderTimeoutError, ValidationError
from backend.db import transactions
from backend.library import character_profile_service, explainer_service as service
from backend.schemas.explainer import ExplainerApproval, ExplainerPlanPatch, ExplainerProposalRequest, ExplainerSegment
from backend.schemas.project import ScriptConfig
from backend.schemas.visuals import ProfileQuickCreate
from tests.test_explainer_project import solo_config


@pytest.fixture
async def solo(db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    profile = await character_profile_service.create_quick(db, ProfileQuickCreate(
        name="Hoang", gender="male", accent="american", appearance="dark hair", outfit="red jacket",
    ))
    project = await project_service.create_project(db, ScriptConfig(**solo_config()))
    pid, sid = project["id"], project["speakers"][0]["id"]
    await db.execute("INSERT INTO project_cast(project_id,speaker_index,character_id,profile_version) VALUES(?,0,?,1)", (pid, profile["id"]))
    await script_service.save_script(db, pid, [{"speaker_id": sid, "text": "Small actions become daily habits."}, {"speaker_id": sid, "text": "Start with one simple action."}])
    lines = await script_service.get_script(db, pid)
    segments = [ExplainerSegment(id=f"idea-{i}", intent="Explain an everyday idea", line_ids=[line["id"]],
                                start={"line_id": line["id"], "token_index": 0}, end={"line_id": line["id"], "token_index": 5},
                                visual={"kind": "text_card", "title": "Start small"}) for i, line in enumerate(lines)]
    await db.commit()
    return SimpleNamespace(pid=pid, sid=sid, profile=profile, lines=lines, segments=segments)


async def draft(db, solo):
    async with transactions.write_transaction(db):
        return await service.publish_draft(db, solo.pid, solo.segments, ["16:9", "9:16"], 0)


def patch(plan, **changes):
    return ExplainerPlanPatch(expected_revision=plan.revision, expected_source_fingerprint=plan.source_fingerprint,
                              segments=changes.pop("segments", plan.segments), aspects=plan.aspects, **changes)


async def test_draft_reload_history_auto_locks_and_explicit_unlock(db, solo):
    plan = await draft(db, solo)
    assert plan.status == "draft" and any("audio" in item.lower() for item in plan.issues)
    edited = copy.deepcopy(plan.segments)
    edited[0].visual.title = "Owner's chosen explanation"
    edited[0].needs_fact_review = False
    result = await service.save_plan(db, solo.pid, patch(plan, segments=edited))
    saved = result["plan"]
    assert saved["revision"] == 2 and saved["segments"][0]["locks"]["visual"] and saved["segments"][0]["locks"]["content"]
    versions = await service.history(db, solo.pid)
    assert [item["revision"] for item in versions] == [1, 2]
    assert versions[0]["segments"][0]["visual"]["title"] == "Start small"
    current = service.ExplainerPlan.model_validate(saved)
    current.segments[0].locks.visual = False
    current.segments[0].locks.content = False
    locked_again = await service.save_plan(db, solo.pid, patch(current))
    assert locked_again["plan"]["segments"][0]["locks"]["visual"], "clearing a client default cannot accidentally unlock owner edits"
    current = service.ExplainerPlan.model_validate(locked_again["plan"])
    unlocked = await service.save_plan(db, solo.pid, patch(current, unlock_fields={current.segments[0].id: ["visual"]}))
    assert not unlocked["plan"]["segments"][0]["locks"]["visual"]
    assert (await service.history(db, solo.pid))[1] == versions[1], "past revisions are immutable"


async def test_revision_and_source_conflicts_preserve_newer_draft(db, solo):
    plan = await draft(db, solo)
    await service.save_plan(db, solo.pid, patch(plan))
    with pytest.raises(ConflictError):
        await service.save_plan(db, solo.pid, patch(plan))
    current = service.ExplainerPlan.model_validate((await service.get_plan(db, solo.pid))["plan"])
    await db.execute("UPDATE speakers SET speed=1.1 WHERE id=?", (solo.sid,))
    await db.commit()
    assert (await service.get_plan(db, solo.pid))["plan"]["status"] == "stale"
    with pytest.raises(ConflictError, match="changed while editing"):
        await service.save_plan(db, solo.pid, patch(current))
    assert len(await service.history(db, solo.pid)) == 2


async def test_script_anchor_loss_is_reported_and_locked_proposal_refused(db, solo):
    solo.segments[0].locks.content = True
    await draft(db, solo)
    await script_service.save_script(db, solo.pid, [{"speaker_id": solo.sid, "text": "A changed script."}])
    view = await service.get_plan(db, solo.pid)
    assert view["plan"]["status"] == "stale" and any("no longer exists" in issue for issue in view["issues"])
    with pytest.raises(ValidationError, match="locked segment"):
        await service.enqueue_proposal(db, solo.pid, ExplainerProposalRequest(expected_revision=1))


def wire(solo):
    return {"segments": [{key: value for key, value in segment.model_dump().items()
                           if key in service.ProposedExplainerSegment.model_fields} for segment in solo.segments]}


class Router:
    def __init__(self, output, callback=None):
        self.output, self.callback, self.calls = output, callback, 0

    async def generate(self, request):
        # An unrelated status poll may briefly own the global lock. The provider's
        # task must be able to acquire it independently rather than deadlock on its own lock.
        async with asyncio.timeout(1):
            async with transactions.read_transaction():
                pass
        assert request.json_schema["$defs"]["ProposedExplainerSegment"]["additionalProperties"] is False
        assert "token_index" in request.prompt and "Hoang" not in request.purpose
        self.calls += 1
        if self.callback:
            await self.callback()
        if isinstance(self.output, Exception):
            raise self.output
        text = self.output[self.calls - 1] if isinstance(self.output, list) else self.output
        return GenerationResult(text=text, provider="test", model="fixture", latency_ms=1, attempt=1, prompt_hash="a" * 64)


async def run(db, solo, router, expected=0):
    job, _ = await service.enqueue_proposal(db, solo.pid, ExplainerProposalRequest(expected_revision=expected))
    worker = AIWorker(db_getter=lambda: db)
    async with transactions.write_transaction(db):
        claimed = await ai_job_service.claim_job(db, job["id"], worker.worker_id, commit=False)
    await service.make_handler(router)(claimed, worker)
    return await ai_job_service.get_job(db, job["id"], solo.pid)


async def test_proposal_repairs_schema_once_then_publishes_with_checkpoint_atomically(db, solo):
    router = Router(["not JSON", json.dumps(wire(solo))])
    job = await run(db, solo, router)
    assert job["status"] == "complete" and router.calls == 2 and job["repair_count"] == 1
    assert (await service.get_plan(db, solo.pid))["plan"]["revision"] == 1
    checkpoints = await ai_job_service.get_valid_checkpoints(db, job["id"])
    assert len(checkpoints) == 1 and checkpoints[0]["stage"] == "explainer_proposal"
    metrics = json.loads(job["metrics_json"])
    assert "text" not in metrics["calls"][0] and "prompt" not in metrics["calls"][0]


async def test_ai_cannot_change_owner_locks_review_geometry_or_stable_ids(db, solo):
    solo.segments[0].locks.visual = True
    solo.segments[0].locks.content = True
    solo.segments[0].needs_fact_review = False
    await draft(db, solo)
    value = wire(solo)
    value["segments"][0]["visual"]["title"] = "Model wants a different title"
    value["segments"][0]["intent"] = "Model changes locked content"
    job = await run(db, solo, Router(json.dumps(value)), 1)
    saved = (await service.get_plan(db, solo.pid))["plan"]
    assert job["status"] == "complete" and saved["segments"][0]["visual"]["title"] == "Start small"
    assert saved["segments"][0]["intent"] == "Explain an everyday idea" and not saved["segments"][0]["needs_fact_review"]
    assert saved["segments"][1]["needs_fact_review"], "AI cannot claim that facts were reviewed"
    value["segments"][0]["locks"] = {"content": False}
    bad = await run(db, solo, Router(json.dumps(value)), 2)
    assert bad["status"] == "error" and len(await service.history(db, solo.pid)) == 2


@pytest.mark.parametrize("kind", ["source", "draft", "cancel", "delete"])
async def test_inference_races_never_overwrite_current_source_or_plan(db, solo, kind):
    await draft(db, solo)

    async def change():
        async with transactions.write_transaction(db):
            if kind == "source":
                await db.execute("UPDATE speakers SET pitch=1 WHERE id=?", (solo.sid,))
            elif kind == "draft":
                await service.publish_draft(db, solo.pid, solo.segments, ["16:9"], 1)
            elif kind == "cancel":
                active = await ai_job_service.get_active_job(db, solo.pid, "propose_explainer")
                await ai_job_service.request_cancel(db, active["id"], solo.pid, commit=False)
            else:
                await project_service.delete_project(db, solo.pid, commit=False)
    if kind == "delete":
        job, _ = await service.enqueue_proposal(db, solo.pid, ExplainerProposalRequest(expected_revision=1))
        worker = AIWorker(db_getter=lambda: db)
        claimed = await ai_job_service.claim_job(db, job["id"], worker.worker_id)
        await service.make_handler(Router(json.dumps(wire(solo)), change))(claimed, worker)
        assert not await (await db.execute("SELECT 1 FROM project_explainer_plans WHERE project_id=?", (solo.pid,))).fetchone()
    else:
        job = await run(db, solo, Router(json.dumps(wire(solo)), change), 1)
        assert job["status"] == ("cancelled" if kind == "cancel" else "stale")
        assert len(await service.history(db, solo.pid)) == (2 if kind == "draft" else 1)


async def test_provider_failure_retains_old_draft(db, solo):
    await draft(db, solo)
    job = await run(db, solo, Router(ProviderTimeoutError("fixture timeout")), 1)
    assert job["status"] == "error" and job["error_code"] == "provider_timeout"
    assert len(await service.history(db, solo.pid)) == 1


async def test_valid_checkpoint_recovery_skips_the_provider(db, solo):
    job, _ = await service.enqueue_proposal(db, solo.pid, ExplainerProposalRequest(expected_revision=0))
    await ai_job_service.save_checkpoint(db, job["id"], 0, "explainer_proposal", "valid", job["input_hash"], result_json=json.dumps(wire(solo)))
    worker = AIWorker(db_getter=lambda: db)
    claimed = await ai_job_service.claim_job(db, job["id"], worker.worker_id)
    router = Router(AssertionError("recovery must not call AI again"))
    await service.make_handler(router)(claimed, worker)
    assert router.calls == 0 and (await ai_job_service.get_job(db, job["id"], solo.pid))["status"] == "complete"


async def test_interruption_after_checkpoint_resumes_without_losing_owner_plan(db, solo, monkeypatch):
    await draft(db, solo)
    original = service.publish_draft

    async def interrupted(*args, **kwargs):
        raise asyncio.CancelledError("simulated process interruption before publication")

    monkeypatch.setattr(service, "publish_draft", interrupted)
    job, _ = await service.enqueue_proposal(db, solo.pid, ExplainerProposalRequest(expected_revision=1))
    worker = AIWorker(db_getter=lambda: db)
    claimed = await ai_job_service.claim_job(db, job["id"], worker.worker_id)
    router = Router(json.dumps(wire(solo)))
    with pytest.raises(asyncio.CancelledError):
        await service.make_handler(router)(claimed, worker)
    assert not db.in_transaction, "worker cancellation rolls back before releasing the shared connection"
    assert len(await service.history(db, solo.pid)) == 1
    assert len(await ai_job_service.get_valid_checkpoints(db, job["id"])) == 1
    await db.execute("UPDATE ai_generation_jobs SET lease_expires_at='2000-01-01T00:00:00+00:00' WHERE id=?", (job["id"],))
    await db.commit()
    await ai_job_service.recover_abandoned_jobs(db)
    monkeypatch.setattr(service, "publish_draft", original)
    reclaimed = await ai_job_service.claim_job(db, job["id"], worker.worker_id)
    await service.make_handler(router)(reclaimed, worker)
    assert router.calls == 1 and len(await service.history(db, solo.pid)) == 2
    assert (await ai_job_service.get_job(db, job["id"], solo.pid))["status"] == "complete"


async def test_publication_failure_rolls_back_history_and_preserves_old_draft(db, solo, monkeypatch):
    await draft(db, solo)
    original = service.publish_draft

    async def fail_after_insert(*args, **kwargs):
        await original(*args, **kwargs)
        raise ValidationError("simulated publication failure after writing history")

    monkeypatch.setattr(service, "publish_draft", fail_after_insert)
    job = await run(db, solo, Router(json.dumps(wire(solo))), 1)
    assert job["status"] == "error"
    assert len(await service.history(db, solo.pid)) == 1
    assert (await service.get_plan(db, solo.pid))["plan"]["revision"] == 1


async def test_missing_assets_audio_and_factual_review_block_approval(db, solo):
    plan = await draft(db, solo)
    with pytest.raises(ValidationError, match="audio"):
        await service.approve_plan(db, solo.pid, ExplainerApproval(expected_revision=1, source_fingerprint=plan.source_fingerprint))
    assert len(await service.history(db, solo.pid)) == 1


async def test_missing_production_geometry_is_a_refusal_not_a_permissive_placeholder(solo):
    with pytest.raises(ValidationError, match="Layout validation is not available"):
        await service._validate_geometry({}, None)


async def test_valid_locked_anchors_allow_regeneration_of_an_extended_unlocked_span(db, solo):
    solo.segments[0].locks.content = True
    await draft(db, solo)
    await script_service.update_script_line(db, solo.pid, solo.lines[1]["id"], "Start with one simple action and repeat daily.", {})
    value = wire(solo)
    value["segments"][1]["end"]["token_index"] = 8
    job = await run(db, solo, Router(json.dumps(value)), 1)
    assert job["status"] == "complete", job
    assert (await service.get_plan(db, solo.pid))["plan"]["segments"][0]["locks"]["content"]


async def test_unknown_illustration_versions_never_become_a_proposed_plan(db, solo):
    value = wire(solo)
    value["segments"][0]["visual"] = {"kind": "photo", "asset": {"asset_id": "not-in-this-project", "version": 1}}
    job = await run(db, solo, Router(json.dumps(value)))
    assert job["status"] == "error" and not await service.history(db, solo.pid)


def test_proposal_rejects_coerced_boolean_token_boundaries(solo):
    from pydantic import ValidationError as PydanticError
    value = wire(solo)
    value["segments"][0]["start"]["token_index"] = False
    with pytest.raises(PydanticError):
        service.ExplainerProposal.model_validate(value)


async def test_duplicate_proposal_ids_use_bounded_repair_before_publication(db, solo):
    bad = wire(solo)
    bad["segments"][1]["id"] = bad["segments"][0]["id"]
    router = Router([json.dumps(bad), json.dumps(wire(solo))])
    job = await run(db, solo, router)
    assert job["status"] == "complete" and router.calls == 2 and job["repair_count"] == 1
    assert len(await service.history(db, solo.pid)) == 1


async def test_corrupt_checkpoint_is_regenerated_with_bounded_validation(db, solo):
    job, _ = await service.enqueue_proposal(db, solo.pid, ExplainerProposalRequest(expected_revision=0))
    await ai_job_service.save_checkpoint(db, job["id"], 0, "explainer_proposal", "valid", job["input_hash"], result_json="not JSON")
    worker = AIWorker(db_getter=lambda: db)
    claimed = await ai_job_service.claim_job(db, job["id"], worker.worker_id)
    router = Router(json.dumps(wire(solo)))
    await service.make_handler(router)(claimed, worker)
    assert router.calls == 1
    assert (await ai_job_service.get_job(db, job["id"], solo.pid))["status"] == "complete"
    assert len(await service.history(db, solo.pid)) == 1


async def test_lost_worker_lease_cannot_publish_a_late_result(db, solo):
    await draft(db, solo)

    async def take_lease():
        async with transactions.write_transaction(db):
            await db.execute("UPDATE ai_generation_jobs SET lease_owner='replacement-worker' WHERE project_id=? AND operation='propose_explainer'", (solo.pid,))

    router = Router(json.dumps(wire(solo)), take_lease)
    job = await run(db, solo, router, 1)
    assert job["lease_owner"] == "replacement-worker" and job["status"] == "running"
    assert len(await service.history(db, solo.pid)) == 1
    assert not await ai_job_service.get_valid_checkpoints(db, job["id"])
