"""Durable AI generation job routes, and the AI runtime health check (Phase 13, Task 13.3)."""

import time
from datetime import datetime, timezone

import aiosqlite
import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.responses import ok
from app.db.database import get_db
from app.db.transactions import read_transaction, write_transaction
from app.models.ai_job import AIJobOut, CreateAIJobRequest
from app.services import ai_job_service, project_service
from app.services.ai.ollama_provider import validate_loopback_url

router = APIRouter(prefix="/api/projects/{project_id}/ai-jobs", tags=["ai-jobs"])
health_router = APIRouter(prefix="/api/ai", tags=["ai-jobs"])


@router.post("")
async def create_ai_job(
    project_id: str, body: CreateAIJobRequest, db: aiosqlite.Connection = Depends(get_db)
) -> JSONResponse:
    """Create a durable AI job, or return the project's existing active one for
    this operation (matches the app's established idempotent-create pattern).

    HTTP 202 for a genuinely new job, HTTP 200 when an existing active/idempotent
    job was returned instead -- both are explicitly allowed by the API contract.
    """
    started_at = time.perf_counter()
    async with read_transaction():
        project = await project_service.get_project(db, project_id)
    async with write_transaction(db):
        job, created = await ai_job_service.create_job(
            db,
            project_id=project_id,
            operation=body.operation,
            input_snapshot={"project": project, "operation": body.operation},
            idempotency_key=body.idempotency_key,
            requested_provider=settings.AI_MODE,
            commit=False,
        )
    payload = ok(AIJobOut.model_validate(job).model_dump(), started_at=started_at)
    return JSONResponse(status_code=202 if created else 200, content=payload)


@router.get("/active")
async def get_active_ai_job(
    project_id: str, operation: str, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Return the project's active job for `operation`, or `null` if none.

    Matches this app's established "empty means null/empty payload, not a 404"
    style for a "nothing yet" state (e.g. `GET .../script` before generation).
    """
    started_at = time.perf_counter()
    async with read_transaction():
        await project_service.get_project(db, project_id)
        job = await ai_job_service.get_active_job(db, project_id, operation)
    data = AIJobOut.model_validate(job).model_dump() if job else None
    return ok(data, started_at=started_at)


@router.get("/{job_id}")
async def get_ai_job(
    project_id: str, job_id: str, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Fetch one job's safe status view. 404s if it doesn't belong to `project_id`."""
    started_at = time.perf_counter()
    async with read_transaction():
        job = await ai_job_service.get_job(db, job_id, project_id)
    return ok(AIJobOut.model_validate(job).model_dump(), started_at=started_at)


@router.post("/{job_id}/cancel")
async def cancel_ai_job(
    project_id: str, job_id: str, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Idempotently request cancellation. A terminal job is returned unchanged."""
    started_at = time.perf_counter()
    async with write_transaction(db):
        job = await ai_job_service.request_cancel(db, job_id, project_id, commit=False)
    return ok(AIJobOut.model_validate(job).model_dump(), started_at=started_at)


@health_router.get("/health")
async def ai_health(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Report AI runtime health. Never exposes the Gemini key; a failed local probe
    degrades this payload, it never fails or delays app startup."""
    started_at = time.perf_counter()
    ollama_reachable = False
    model_present = False
    model_digest: str | None = None
    try:
        base_url = validate_loopback_url(settings.OLLAMA_BASE_URL)
        async with httpx.AsyncClient(base_url=base_url, timeout=2.0) as client:
            version_response = await client.get("/api/version")
            ollama_reachable = version_response.status_code == 200
            if ollama_reachable:
                tags_response = await client.get("/api/tags")
                if tags_response.status_code == 200:
                    for model in tags_response.json().get("models", []):
                        if settings.OLLAMA_MODEL in (model.get("name"), model.get("model")):
                            model_present = True
                            model_digest = model.get("digest")
                            break
    except (httpx.HTTPError, ValueError):
        ollama_reachable = False

    # Deferred import (Task 16.1, BUG-022): app.main constructs the real AIWorker
    # singleton after importing this module to build its router, so a top-level
    # import here would be circular. _ai_circuits (Task 18.3/18.8) is imported the
    # same way, for the same reason.
    from app.main import _ai_circuits, ai_worker
    from app.services.ai.contracts import AIMode
    from app.services.ai.router import _configured_chain_entry_names, compute_effective_mode

    entry_names = _configured_chain_entry_names(settings)
    effective_mode = compute_effective_mode(AIMode(settings.AI_MODE), settings.AI_ALLOW_CLOUD, bool(entry_names))

    async with read_transaction():
        fallback_rate = await ai_job_service.get_fallback_rate_stats(db)

    # Task 18.8 (D28) Q4 ruling: circuit_open/circuit_open_until (18.6) are
    # re-derived from a per-provider breakdown, not "any circuit" -- true only
    # when EVERY configured provider is currently paused (the app is genuinely
    # running local-only right now), with the EARLIEST reopen time among them.
    # An entry never yet dispatched to has no breaker in _ai_circuits at all --
    # treated as not open (nothing has ever failed for it).
    providers: dict[str, dict] = {}
    provider_epochs: dict[str, float | None] = {}
    for entry_name in entry_names:
        circuit = _ai_circuits.get(entry_name)
        open_epoch = circuit.opened_until_epoch_seconds() if circuit is not None else None
        provider_epochs[entry_name] = open_epoch
        providers[entry_name] = {
            "configured": True,
            "circuit_open": circuit.is_open() if circuit is not None else False,
            "circuit_open_until": (
                datetime.fromtimestamp(open_epoch, tz=timezone.utc).isoformat() if open_epoch is not None else None
            ),
        }
    all_paused = bool(providers) and all(p["circuit_open"] for p in providers.values())
    known_epochs = [epoch for epoch in provider_epochs.values() if epoch is not None]
    circuit_open_until = (
        datetime.fromtimestamp(min(known_epochs), tz=timezone.utc).isoformat()
        if all_paused and known_epochs
        else None
    )

    return ok(
        {
            "mode": settings.AI_MODE,
            "ollama_reachable": ollama_reachable,
            "model": settings.OLLAMA_MODEL,
            "model_present": model_present,
            "model_digest": model_digest,
            "cloud_enabled": settings.AI_ALLOW_CLOUD,
            "worker_alive": ai_worker.is_alive,
            "cloud_configured": bool(settings.OPENAI_COMPAT_API_KEY and settings.OPENAI_COMPAT_MODEL),
            "cloud_model": settings.OPENAI_COMPAT_MODEL,
            "effective_mode": effective_mode.value,
            "circuit_open": all_paused,
            "circuit_open_until": circuit_open_until,
            "providers": providers,
            "fallback_rate": fallback_rate,
        },
        started_at=started_at,
    )
