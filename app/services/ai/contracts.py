"""Typed request/result contracts and the provider interface for the AI gateway."""

from __future__ import annotations

from enum import Enum
from typing import Protocol

from pydantic import BaseModel, Field


class AIMode(str, Enum):
    """The `DIE_AI_MODE` kill switch (see ADR-001)."""

    GEMINI = "gemini"
    LOCAL = "local"
    HYBRID = "hybrid"


class GenerationRequest(BaseModel):
    """One structured-generation request, provider-agnostic.

    Attributes:
        prompt: Full rendered prompt text. Never logged in full anywhere in this
            package -- only its sha256 (via `prompt_hash` on the result) is recorded.
        json_schema: Optional JSON Schema (e.g. `SomeModel.model_json_schema()`)
            asking the provider for structured output.
        temperature: Optional sampling temperature; `None` uses the provider default.
        deadline_seconds: Wall-clock budget for the whole `AIRouter.generate()` call,
            including any retry/fallback -- independent of each provider's own
            per-request HTTP timeout.
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
    """

    text: str
    provider: str
    model: str
    tokens_used: int | None = None
    latency_ms: float = Field(ge=0)
    attempt: int = Field(ge=1)
    prompt_hash: str
    fallback_used: bool = False
    circuit_open: bool = False
    attempts: int = Field(default=1, ge=1)
    backoff_seconds: float = Field(default=0.0, ge=0)
    transient_errors: list[str] = Field(default_factory=list)


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
