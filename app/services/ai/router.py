"""Central AI router: AI_MODE selection, one-retry policy, one Gemini fallback,
and an in-process circuit breaker over the local provider (Phase 13, ADR-001).

Retry/fallback/circuit-breaker policy lives here, never inside a provider -- see
`contracts.Provider`'s docstring for why (no nested retries).
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

from app.core.constants import AI_CIRCUIT_COOLDOWN_SECONDS, AI_CIRCUIT_FAILURE_THRESHOLD
from app.core.exceptions import (
    ProviderError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    SchemaValidationError,
)
from app.services.ai.contracts import AIMode, GenerationRequest, GenerationResult, Provider

logger = logging.getLogger(__name__)

# Infrastructure/transient errors worth one same-provider retry. ProviderAuthError is
# deliberately excluded -- a bad key/config will not fix itself on a second attempt.
_RETRYABLE_ERRORS = (
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderRateLimitError,
    ProviderInvalidResponseError,
    SchemaValidationError,
)


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
        try:
            return await asyncio.wait_for(self._route(request), timeout=request.deadline_seconds)
        except TimeoutError as exc:
            raise ProviderTimeoutError(
                f"AI router deadline of {request.deadline_seconds}s exceeded"
            ) from exc

    async def _route(self, request: GenerationRequest) -> GenerationResult:
        if self._mode is AIMode.GEMINI:
            return await self._attempt_with_one_retry(self._gemini, request)

        if self._mode is AIMode.LOCAL:
            return await self._attempt_with_one_retry(self._local, request)

        # hybrid: local first (unless the circuit is open), one visible Gemini fallback.
        if self._circuit.is_open():
            logger.info(
                "ai_router_circuit_open provider=%s purpose=%s", self._local.name, request.purpose
            )
            result = await self._attempt_with_one_retry(self._gemini, request)
            result.circuit_open = True
            return result

        try:
            return await self._attempt_with_one_retry(self._local, request)
        except ProviderError as exc:
            self._circuit.record_failure()
            logger.warning(
                "ai_router_local_failed provider=%s purpose=%s error=%s -- falling back to gemini",
                self._local.name,
                request.purpose,
                type(exc).__name__,
            )
            result = await self._attempt_with_one_retry(self._gemini, request)
            result.fallback_used = True
            return result

    async def _attempt_with_one_retry(
        self, provider: Provider, request: GenerationRequest
    ) -> GenerationResult:
        """Call `provider` once; retry exactly once more on a retryable error class."""
        try:
            result = await self._call(provider, request, attempt=1)
        except _RETRYABLE_ERRORS as exc:
            logger.warning(
                "ai_router_retry provider=%s purpose=%s error=%s",
                provider.name,
                request.purpose,
                type(exc).__name__,
            )
            result = await self._call(provider, request, attempt=2)
        if provider is self._local:
            self._circuit.record_success()
        return result

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
