"""Pydantic models for the durable AI generation job API (Phase 13, Task 13.3)."""

import json
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.core.constants import AI_JOB_OPERATIONS


class CreateAIJobRequest(BaseModel):
    """Body for `POST /api/projects/{project_id}/ai-jobs`."""

    operation: str = Field(pattern="^(" + "|".join(AI_JOB_OPERATIONS) + ")$")
    idempotency_key: str | None = None


class AIJobOut(BaseModel):
    """Safe, client-facing view of one `ai_generation_jobs` row.

    Deliberately excludes `input_snapshot_json`, `remote_interaction_id`, and
    `lease_owner`/`lease_expires_at`/`heartbeat_at` (internal worker bookkeeping,
    never useful to a client and not meant to be relied on externally) — declaring
    only the fields below means `AIJobOut.model_validate(row)` drops everything
    else automatically, since Pydantic ignores undeclared fields by default.
    """

    id: str
    project_id: str
    operation: str
    status: str
    stage: str
    progress: int
    requested_provider: str | None = None
    actual_provider: str | None = None
    model: str | None = None
    fallback_used: bool
    fallback_reason: str | None = None
    cancel_requested: bool
    attempt: int
    repair_count: int
    fallback_count: int
    recovery_count: int
    error_code: str | None = None
    error_message: str | None = None
    metrics: dict = Field(default_factory=dict)
    created_at: str
    started_at: str | None = None
    updated_at: str
    finished_at: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _derive_metrics_from_metrics_json(cls, data: Any) -> Any:
        """Task 14.2: the job row stores `metrics_json` (a TEXT column), never a
        `metrics` key -- every route does `AIJobOut.model_validate(job)` on the raw
        row dict, so this is where `metrics_json` becomes the safe `metrics` field
        (`{}` on any parse failure) instead of every call site re-parsing it."""
        if isinstance(data, dict) and "metrics" not in data:
            raw = data.get("metrics_json")
            if raw:
                try:
                    parsed = json.loads(raw)
                except (TypeError, ValueError):
                    parsed = {}
                data = {**data, "metrics": parsed if isinstance(parsed, dict) else {}}
        return data
