"""Central AI router: AI_MODE selection, bounded per-provider retry with
exponential backoff for transient errors, one Gemini fallback, and an
in-process circuit breaker over the local provider (Phase 13/14, ADR-001).

Retry/fallback/circuit-breaker policy lives here, never inside a provider -- see
`contracts.Provider`'s docstring for why (no nested retries).
"""

from __future__ import annotations

import asyncio
import logging
import time
from asyncio import sleep
from dataclasses import dataclass

from app.core.constants import (
    AI_BACKOFF_MIN_REMAINING_SECONDS,
    AI_CIRCUIT_COOLDOWN_SECONDS,
    AI_CIRCUIT_FAILURE_THRESHOLD,
    AI_TRANSIENT_BACKOFF_BASE_SECONDS,
    AI_TRANSIENT_BACKOFF_MAX_SECONDS,
    AI_TRANSIENT_MAX_ATTEMPTS,
    GEMINI_MODEL,
)
from app.core.exceptions import (
    ProviderError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    SchemaValidationError,
)
from app.services.ai.contracts import AIMode, GenerationRequest, GenerationResult, Provider
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)


def build_ai_router_from_settings() -> "AIRouter":
    """Construct the Task 13.2 provider gateway from current app settings.

    The one shared factory for every Gemini consumer (Phase 13, Task 13.7) --
    previously duplicated per-service (`script_service._build_ai_router`). A fresh
    instance per call is fine: there is no shared-lifespan client the way a
    lifespan-managed worker would want, matching each provider's own per-call
    `httpx.AsyncClient` lifetime.
    """
    from app.core.config import settings  # local import: avoids a config<->ai import cycle

    local = OllamaProvider(
        base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL, num_ctx=settings.OLLAMA_NUM_CTX
    )
    gemini = GeminiProvider(api_key=settings.GEMINI_API_KEY, model=GEMINI_MODEL)
    return AIRouter(local=local, gemini=gemini, mode=AIMode(settings.AI_MODE))

# Infrastructure/transient errors: ordinary overload/rate-limit/timeout conditions
# that resolve themselves given a moment -- worth up to AI_TRANSIENT_MAX_ATTEMPTS
# same-provider attempts with exponential backoff between them (Task 14.1).
_TRANSIENT_ERRORS = (
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderRateLimitError,
)
# Content-shaped errors: the provider responded, but the response itself was
# malformed/unparseable -- not an infrastructure condition, so no backoff. Kept at
# the pre-14.1 policy of exactly one immediate retry (the semantic-repair budget
# in script_pipeline.py is what actually recovers from persistent content issues).
_CONTENT_RETRY_ERRORS = (
    ProviderInvalidResponseError,
    SchemaValidationError,
)
# ProviderAuthError (and any other ProviderError not listed above) is deliberately
# excluded from both tuples -- a bad key/config will not fix itself on a retry.


@dataclass
class _CircuitBreaker:
    """Tracks consecutive local-provider failures; opens for a cooldown window."""

    failure_threshold: int
    cooldown_seconds: float
    consecutive_failures: int = 0
    opened_until: float = 0.0

    def is_open(self) -> bool:
        """True while a prior failure streak's cooldown window has not elapsed."""
        return time.monotonic() < self.opened_until

    def record_success(self) -> None:
        """Reset the failure streak and close the circuit."""
        self.consecutive_failures = 0
        self.opened_until = 0.0

    def record_failure(self) -> None:
        """Count one failure; open the circuit once the threshold is reached."""
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.failure_threshold:
            self.opened_until = time.monotonic() + self.cooldown_seconds


class AIRouter:
    """Routes one `GenerationRequest` to the local/Gemini providers per `AI_MODE`.

    Circuit-breaker state is in-process only, not persisted -- Task 13.3's durable
    job layer is the real persistence/recovery boundary, not this router.
    """

    def __init__(
        self,
        local: Provider,
        gemini: Provider,
        mode: AIMode,
        failure_threshold: int = AI_CIRCUIT_FAILURE_THRESHOLD,
        cooldown_seconds: float = AI_CIRCUIT_COOLDOWN_SECONDS,
    ) -> None:
        self._local = local
        self._gemini = gemini
        self._mode = mode
        self._circuit = _CircuitBreaker(failure_threshold, cooldown_seconds)

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Route one request, bounded by `request.deadline_seconds` overall.

        Raises:
            ProviderError (or a subclass): If every attempt this mode allows fails,
                or the deadline elapses first.
        """
        deadline_at = time.monotonic() + request.deadline_seconds
        try:
            return await asyncio.wait_for(
                self._route(request, deadline_at), timeout=request.deadline_seconds
            )
        except TimeoutError as exc:
            raise ProviderTimeoutError(
                f"AI router deadline of {request.deadline_seconds}s exceeded"
            ) from exc

    async def _route(self, request: GenerationRequest, deadline_at: float) -> GenerationResult:
        if self._mode is AIMode.GEMINI:
            return await self._attempt(self._gemini, request, deadline_at)

        if self._mode is AIMode.LOCAL:
            return await self._attempt(self._local, request, deadline_at)

        # hybrid: local first (unless the circuit is open), one visible Gemini fallback.
        if self._circuit.is_open():
            logger.info(
                "ai_router_circuit_open provider=%s purpose=%s", self._local.name, request.purpose
            )
            result = await self._attempt(self._gemini, request, deadline_at)
            result.circuit_open = True
            return result

        try:
            return await self._attempt(self._local, request, deadline_at)
        except ProviderError as exc:
            self._circuit.record_failure()
            logger.warning(
                "ai_router_local_failed provider=%s purpose=%s error=%s -- falling back to gemini",
                self._local.name,
                request.purpose,
                type(exc).__name__,
            )
            result = await self._attempt(self._gemini, request, deadline_at)
            result.fallback_used = True
            return result

    async def _attempt(
        self, provider: Provider, request: GenerationRequest, deadline_at: float
    ) -> GenerationResult:
        """Call `provider`, absorbing transient errors with capped exponential
        backoff (up to `AI_TRANSIENT_MAX_ATTEMPTS` attempts total, never sleeping
        past `deadline_at`) and content errors with exactly one immediate retry."""
        attempt = 1
        backoff_seconds = 0.0
        transient_errors: list[str] = []
        while True:
            try:
                result = await self._call(provider, request, attempt=attempt)
            except _TRANSIENT_ERRORS as exc:
                transient_errors.append(type(exc).__name__)
                if attempt >= AI_TRANSIENT_MAX_ATTEMPTS:
                    self._log_exhausted(provider, request, attempt, backoff_seconds)
                    raise
                delay = min(
                    AI_TRANSIENT_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)),
                    AI_TRANSIENT_BACKOFF_MAX_SECONDS,
                )
                remaining = deadline_at - time.monotonic()
                if remaining < delay + AI_BACKOFF_MIN_REMAINING_SECONDS:
                    self._log_exhausted(provider, request, attempt, backoff_seconds)
                    raise
                logger.warning(
                    "ai_router_backoff provider=%s purpose=%s attempt=%d delay_seconds=%.1f error=%s",
                    provider.name,
                    request.purpose,
                    attempt,
                    delay,
                    type(exc).__name__,
                )
                await sleep(delay)
                backoff_seconds += delay
                attempt += 1
            except _CONTENT_RETRY_ERRORS as exc:
                if attempt >= 2:
                    raise
                logger.warning(
                    "ai_router_retry provider=%s purpose=%s error=%s",
                    provider.name,
                    request.purpose,
                    type(exc).__name__,
                )
                attempt += 1
            else:
                result.attempts = attempt
                result.backoff_seconds = backoff_seconds
                result.transient_errors = transient_errors
                if provider is self._local:
                    self._circuit.record_success()
                return result

    def _log_exhausted(
        self, provider: Provider, request: GenerationRequest, attempts: int, backoff_seconds: float
    ) -> None:
        logger.warning(
            "ai_router_exhausted provider=%s purpose=%s attempts=%d backoff_seconds=%.1f",
            provider.name,
            request.purpose,
            attempts,
            backoff_seconds,
        )

    async def _call(
        self, provider: Provider, request: GenerationRequest, attempt: int
    ) -> GenerationResult:
        """Call the provider once and log safe metadata only (never prompt/response text)."""
        result = await provider.generate(request)
        result.attempt = attempt
        logger.info(
            "ai_router_call provider=%s model=%s purpose=%s prompt_hash=%s latency_ms=%.1f "
            "tokens_used=%s attempt=%d",
            result.provider,
            result.model,
            request.purpose,
            result.prompt_hash,
            result.latency_ms,
            result.tokens_used,
            attempt,
        )
        return result
