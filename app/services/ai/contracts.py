"""Typed request/result contracts and the provider interface for the AI gateway."""

from __future__ import annotations

from enum import Enum
from typing import Protocol

from pydantic import BaseModel, Field


class AIMode(str, Enum):
    """The `DIE_AI_MODE` kill switch (see ADR-001; Phase 18/D21 made cloud the
    default primary, local the automatic fallback -- `CLOUD`/`CLOUD_FIRST`
    replace the old `GEMINI`/`HYBRID` names, which named a specific provider
    instead of a role)."""

    LOCAL = "local"
    CLOUD = "cloud"
    CLOUD_FIRST = "cloud_first"


class GenerationRequest(BaseModel):
    """One structured-generation request, provider-agnostic.

    Attributes:
        prompt: Full rendered prompt text. Never logged in full anywhere in this
            package -- only its sha256 (via `prompt_hash` on the result) is recorded.
        json_schema: Optional JSON Schema (e.g. `SomeModel.model_json_schema()`)
            asking the provider for structured output.
        temperature: Optional sampling temperature; `None` uses the provider default.
        deadline_seconds: Wall-clock budget for one phase of `AIRouter.generate()`
            (Phase 18): the sole budget in `local` mode, and the fallback's own
            budget in `cloud_first` mode -- the primary/cloud phase gets its own,
            separate `AI_CLOUD_DEADLINE_SECONDS` budget instead, never sharing
            this one. Independent of each provider's own per-request HTTP timeout.
        purpose: Short label for logging/metrics only (e.g. "script_outline"),
            never raw project/user content.
    """

    prompt: str = Field(min_length=1)
    json_schema: dict | None = None
    temperature: float | None = None
    deadline_seconds: float = Field(gt=0)
    purpose: str = Field(min_length=1)


class GenerationResult(BaseModel):
    """One successful generation, with enough metadata to log/audit safely.

    `text` and any parsed content are the only fields carrying prompt-derived
    content -- callers are responsible for not logging them; this package's own
    logging only ever uses the other fields.

    Attributes:
        attempts: Total calls made on the winning provider (Task 14.1), including
            backoff retries -- distinct from `attempt`, which is the winning call's
            own 1-based position.
        backoff_seconds: Total time slept before the winning call (Task 14.1).
        transient_errors: Exception *class names* of transient errors absorbed
            before the winning call (Task 14.1) -- never the exception message, so
            this field stays as safe to log as every other field here.
        fallback_reason: The primary's exception *class name* (Phase 18), set only
            when `fallback_used` is true -- never the exception message, same
            policy as `transient_errors`, so a key an upstream echoed back can
            never ride along into a persisted job-metrics record via this field.
        providers_tried: Task 18.8 -- every cloud provider *name* attempted for
            this call, in order, including the eventual winner (empty when
            nothing was tried, e.g. `AIMode.LOCAL`). Names only, matching
            `fallback_reason`'s never-the-message policy.
    """

    text: str
    provider: str
    model: str
    tokens_used: int | None = None
    latency_ms: float = Field(ge=0)
    attempt: int = Field(ge=1)
    prompt_hash: str
    fallback_used: bool = False
    fallback_reason: str | None = None
    circuit_open: bool = False
    attempts: int = Field(default=1, ge=1)
    backoff_seconds: float = Field(default=0.0, ge=0)
    transient_errors: list[str] = Field(default_factory=list)
    providers_tried: list[str] = Field(default_factory=list)


class Provider(Protocol):
    """Structural interface every AI provider adapter implements.

    A provider makes exactly one attempt per `generate()` call -- retry, fallback,
    and circuit-breaker policy all live in `AIRouter`, never inside a provider, so
    the router's own retry budget can't multiply with a provider-internal one.
    """

    name: str

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Make one real (or, for a fake provider, simulated) generation attempt.

        Raises:
            ProviderError (or a subclass): On any failure. Never returns a partial
                or fabricated success.
        """
        ...
