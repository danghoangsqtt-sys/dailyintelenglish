"""Central AI router: AI_MODE selection, bounded per-provider retry with
exponential backoff for transient errors, one visible cloud-to-local fallback,
and an in-process circuit breaker over the primary provider (Phase 13/14,
ADR-001; Phase 18/D21 made cloud the default primary, local the fallback).

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
    AI_CLOUD_DEADLINE_SECONDS,
    AI_TRANSIENT_BACKOFF_BASE_SECONDS,
    AI_TRANSIENT_BACKOFF_MAX_SECONDS,
    AI_TRANSIENT_MAX_ATTEMPTS,
)
from app.core.exceptions import (
    ProviderAuthError,
    ProviderDailyQuotaError,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    SchemaValidationError,
)
from app.services.ai.contracts import AIMode, GenerationRequest, GenerationResult, Provider
from app.services.ai.ollama_provider import OllamaProvider
from app.services.ai.openai_compat_provider import OpenAICompatProvider, parse_fallback_models

logger = logging.getLogger(__name__)


def compute_effective_mode(configured_mode: AIMode, allow_cloud: bool, api_key: str, model: str) -> AIMode:
    """Phase 18, invariant 32/D24: cloud is only ever effective when the kill
    switch is on and both a key and a model are configured -- otherwise the
    app behaves exactly like today's local-only mode, regardless of what
    `configured_mode` (the stored/env setting) says."""
    if configured_mode is AIMode.LOCAL:
        return AIMode.LOCAL
    if not allow_cloud or not api_key or not model:
        return AIMode.LOCAL
    return configured_mode


def build_ai_router_from_settings(circuit: "CircuitBreaker | None" = None) -> "AIRouter":
    """Construct the Task 13.2 provider gateway from current app settings.

    The one shared factory for every cloud-AI consumer -- previously duplicated
    per-service (`script_service._build_ai_router`). A fresh instance per call is
    fine: there is no shared-lifespan client the way a lifespan-managed worker
    would want, matching each provider's own per-call `httpx.AsyncClient`
    lifetime. `circuit` is `None` by default (a fresh breaker per call, matching
    today's per-call-fresh router semantics) -- a caller that needs
    circuit-breaker state to persist across calls (the durable job worker,
    `app/main.py`) constructs its own `CircuitBreaker` once, for the app's
    whole lifetime, and passes it here on every call instead.
    """
    from app.core.config import settings  # local import: avoids a config<->ai import cycle

    fallback = OllamaProvider(
        base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL, num_ctx=settings.OLLAMA_NUM_CTX
    )
    effective_mode = compute_effective_mode(
        AIMode(settings.AI_MODE), settings.AI_ALLOW_CLOUD, settings.OPENAI_COMPAT_API_KEY, settings.OPENAI_COMPAT_MODEL
    )
    primary: Provider = fallback  # placeholder; never called when effective_mode is LOCAL
    if effective_mode is not AIMode.LOCAL:
        try:
            primary = OpenAICompatProvider(
                base_url=settings.OPENAI_COMPAT_BASE_URL,
                api_key=settings.OPENAI_COMPAT_API_KEY,
                model=settings.OPENAI_COMPAT_MODEL,
                timeout=settings.AI_CLOUD_DEADLINE_SECONDS,
                fallback_models=parse_fallback_models(settings.OPENAI_COMPAT_FALLBACK_MODELS),
            )
        except ValueError:
            logger.warning("ai_router_invalid_cloud_base_url -- falling back to local")
            effective_mode = AIMode.LOCAL
    return AIRouter(
        primary=primary, fallback=fallback, mode=effective_mode,
        cloud_deadline_seconds=settings.AI_CLOUD_DEADLINE_SECONDS, circuit=circuit,
    )


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

# Task 18.6 (D27), PM review C3: caps CircuitBreaker.open_until's computed open
# duration against a garbled or far-future X-RateLimit-Reset. 26h (not 24h) covers
# a reset that's correctly the next UTC midnight but read shortly after the
# *previous* one, plus slack for clock skew/latency.
_MAX_OPEN_UNTIL_SECONDS = 26 * 3600.0


@dataclass
class CircuitBreaker:
    """Tracks consecutive primary-provider failures; opens for a cooldown window.

    Public (Phase 18, renamed from `_CircuitBreaker`) so `app/main.py` can hold
    one instance for the app's whole lifetime and thread it through every
    freshly-built per-job `AIRouter` -- otherwise rebuilding the router per job
    dispatch (needed so a Settings change reaches the next job without a
    restart) would also reset breaker state on every job, which the plan does
    not ask for and would make the breaker far less useful in practice.
    """

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

    def open_immediately(self) -> None:
        """A config error (bad key/model) can't self-resolve on retry -- skip
        the consecutive-failure threshold and open the cooldown window at once."""
        self.consecutive_failures = self.failure_threshold
        self.opened_until = time.monotonic() + self.cooldown_seconds

    def open_until(self, reset_at_epoch_seconds: float) -> None:
        """Task 18.6 (D27): open the circuit until a wall-clock deadline
        (OpenRouter's `X-RateLimit-Reset`, a daily-quota reset) instead of a
        fixed cooldown -- the *same* `opened_until` field `is_open()` already
        checks, not a parallel circuit; this is a third way to set it,
        alongside `record_failure()`'s threshold path and `open_immediately()`'s
        fixed-cooldown path. Converts the wall-clock deadline to a
        monotonic-clock offset once, here, since `opened_until`/`is_open()`
        compare against `time.monotonic()` everywhere else in this class.

        PM review C3: the computed open duration is capped at 26 hours,
        guarding against a garbled or far-future `X-RateLimit-Reset` opening
        the circuit for months. A reset already in the past (clock skew, a
        stale header) opens for `max(0.0, ...)` = 0 seconds -- effectively an
        immediate close on the next check, never negative/stuck-open.
        """
        self.consecutive_failures = self.failure_threshold
        remaining = max(0.0, reset_at_epoch_seconds - time.time())
        remaining = min(remaining, _MAX_OPEN_UNTIL_SECONDS)
        self.opened_until = time.monotonic() + remaining

    def opened_until_epoch_seconds(self) -> float | None:
        """Wall-clock equivalent of `opened_until` (for external reporting
        only -- health payload -- never used by `is_open()` itself). `None`
        when the circuit isn't currently open. Both clocks are read "now"
        together at call time, so the delta between them is accurate then."""
        if not self.is_open():
            return None
        return time.time() + (self.opened_until - time.monotonic())


class AIRouter:
    """Routes one `GenerationRequest` to the primary/fallback providers per `AI_MODE`.

    Circuit-breaker state is in-process only, not persisted -- Task 13.3's durable
    job layer is the real persistence/recovery boundary, not this router.
    """

    def __init__(
        self,
        primary: Provider,
        fallback: Provider,
        mode: AIMode,
        cloud_deadline_seconds: float = AI_CLOUD_DEADLINE_SECONDS,
        failure_threshold: int = AI_CIRCUIT_FAILURE_THRESHOLD,
        cooldown_seconds: float = AI_CIRCUIT_COOLDOWN_SECONDS,
        circuit: CircuitBreaker | None = None,
    ) -> None:
        """`failure_threshold`/`cooldown_seconds` are ignored when `circuit` is
        given (it's already configured) -- they exist only to build this
        router's own default breaker when the caller doesn't hold a
        longer-lived one itself. `cloud_deadline_seconds` is read once, here, at
        construction -- consistent with `primary`/`fallback`/`mode` also being
        frozen at construction, not re-read from `settings` on every call."""
        self._primary = primary
        self._fallback = fallback
        self._mode = mode
        self._cloud_deadline_seconds = cloud_deadline_seconds
        self._circuit = circuit if circuit is not None else CircuitBreaker(failure_threshold, cooldown_seconds)

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Route one request. `local` mode and the fallback phase of `cloud_first`
        are bounded by `request.deadline_seconds`; the primary phase (`cloud` and
        `cloud_first`'s first attempt) gets its own, separate
        `AI_CLOUD_DEADLINE_SECONDS` budget -- the two never share one deadline
        (Phase 18: a shared deadline is exactly how a slow primary starved the
        fallback of any time at all).

        Raises:
            ProviderError (or a subclass): If every attempt this mode allows fails,
                or the relevant budget elapses first.
        """
        if self._mode is AIMode.LOCAL:
            return await self._run_with_budget(self._fallback, request, request.deadline_seconds)

        if self._mode is AIMode.CLOUD:
            return await self._run_with_budget(self._primary, request, self._cloud_deadline_seconds)

        # cloud_first: primary first (unless the circuit is open), one visible fallback.
        if self._circuit.is_open():
            logger.info(
                "ai_router_circuit_open provider=%s purpose=%s", self._primary.name, request.purpose
            )
            result = await self._run_with_budget(self._fallback, request, request.deadline_seconds)
            result.circuit_open = True
            return result

        try:
            return await self._run_with_budget(self._primary, request, self._cloud_deadline_seconds)
        except ProviderError as exc:
            if isinstance(exc, ProviderDailyQuotaError):
                self._circuit.open_until(exc.reset_at_epoch_seconds)
            elif isinstance(exc, ProviderAuthError):
                self._circuit.open_immediately()
            else:
                self._circuit.record_failure()
            logger.warning(
                "ai_router_primary_failed provider=%s purpose=%s error=%s -- falling back to %s",
                self._primary.name,
                request.purpose,
                type(exc).__name__,
                self._fallback.name,
            )
            result = await self._run_with_budget(self._fallback, request, request.deadline_seconds)
            result.fallback_used = True
            result.fallback_reason = type(exc).__name__
            return result

    def is_primary_result(self, result: GenerationResult) -> bool:
        """Task 18.6 C2: True only when `result` was genuinely served by a
        distinct primary provider (cloud), not a hardcoded provider-name
        comparison -- lets a caller (a pipeline's `_call_router`) ask "was
        this cloud-served" without hardcoding a name, and survives a future
        provider rename. Excludes `AIMode.LOCAL`, where
        `build_ai_router_from_settings` sets `primary` to the same object as
        `fallback` as a placeholder ("never called when effective_mode is
        LOCAL") -- a bare name comparison would otherwise wrongly return
        `True` for an ordinary local-mode result."""
        return self._mode is not AIMode.LOCAL and result.provider == self._primary.name

    async def generate_on_fallback(self, request: GenerationRequest) -> GenerationResult:
        """Task 18.6 item 4: force exactly one call on the local fallback,
        bypassing the primary/circuit entirely -- used by a pipeline's call
        wrapper for the one-shot local retry after a cloud-served result fails
        JSON parse/validation, before the pipeline's own normal repair path.
        Reuses `_run_with_budget`/`_attempt` unchanged, so it gets the same
        per-call retry/backoff policy any other fallback-phase call gets.
        Deliberately never touches `self._circuit`: a malformed-JSON content
        failure says nothing about the primary provider's health (it
        answered, on time, just with unparseable content), so it must never
        count toward the circuit's failure threshold the way an infra error
        does."""
        return await self._run_with_budget(self._fallback, request, request.deadline_seconds)

    async def _run_with_budget(
        self, provider: Provider, request: GenerationRequest, budget_seconds: float
    ) -> GenerationResult:
        """Wraps one phase's attempt(s) in its own `wait_for`, independent of
        any other phase's budget (Phase 18 -- see `generate`'s docstring)."""
        deadline_at = time.monotonic() + budget_seconds
        try:
            return await asyncio.wait_for(
                self._attempt(provider, request, deadline_at), timeout=budget_seconds
            )
        except TimeoutError as exc:
            raise ProviderTimeoutError(
                f"AI router budget of {budget_seconds}s exceeded for {provider.name}"
            ) from exc

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
            except ProviderDailyQuotaError:
                # Task 18.6 (D27): no backoff -- a daily-cap 429 won't refill within
                # any retry window, and each retry still costs a request against the
                # same exhausted counter. `ProviderDailyQuotaError` IS a
                # `ProviderRateLimitError` subtype (in `_TRANSIENT_ERRORS` below), so
                # this clause must come first or it would silently get backoff-retried.
                raise
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
                if provider is self._primary:
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
