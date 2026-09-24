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
    AI_TOTAL_CLOUD_BUDGET_SECONDS,
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


def compute_effective_mode(configured_mode: AIMode, allow_cloud: bool, any_provider_configured: bool) -> AIMode:
    """Phase 18, invariant 32/D24: cloud is only ever effective when the kill
    switch is on and at least one cloud provider is configured -- otherwise
    the app behaves exactly like today's local-only mode, regardless of what
    `configured_mode` (the stored/env setting) says.

    Task 18.8 (D28): generalized from "a single key+model pair" to "at least
    one provider in the chain has a key" -- `any_provider_configured` is the
    caller's own OR across however many providers it knows about (today:
    openrouter/opencode-zen/gemini), computed once by the caller rather than
    this function re-reading `settings.*` itself, matching how it never did
    before either."""
    if configured_mode is AIMode.LOCAL:
        return AIMode.LOCAL
    if not allow_cloud or not any_provider_configured:
        return AIMode.LOCAL
    return configured_mode


def _configured_cloud_provider_names(settings) -> list[str]:
    """Task 18.8: `settings.CLOUD_PROVIDER_ORDER` (comma-separated, same
    parse/shape as 18.6's `OPENAI_COMPAT_FALLBACK_MODELS`) filtered to only the
    providers that actually have a key configured -- an unconfigured entry is
    skipped silently (point 1's "a provider with no key is skipped silently",
    invariant 32 extended)."""
    order = parse_fallback_models(settings.CLOUD_PROVIDER_ORDER)
    configured = []
    for name in order:
        if name == "openrouter" and settings.OPENAI_COMPAT_API_KEY:
            configured.append(name)
        elif name == "opencode-zen" and settings.OPENCODE_ZEN_API_KEY:
            configured.append(name)
        elif name == "gemini" and settings.GEMINI_API_KEY:
            configured.append(name)
    return configured


def _chain_entry(name: str, provider: Provider, circuits: "dict[str, CircuitBreaker] | None") -> "ChainEntry":
    """`circuits.setdefault(...)` (when `circuits` is given) is what makes a
    provider's breaker survive across the many routers `build_ai_router_from_
    settings` builds over the app's lifetime -- the same per-name identity
    `app/main.py`'s `_ai_circuits` dict relies on."""
    if circuits is not None:
        circuit = circuits.setdefault(name, CircuitBreaker(AI_CIRCUIT_FAILURE_THRESHOLD, AI_CIRCUIT_COOLDOWN_SECONDS))
    else:
        circuit = CircuitBreaker(AI_CIRCUIT_FAILURE_THRESHOLD, AI_CIRCUIT_COOLDOWN_SECONDS)
    return ChainEntry(name=name, provider=provider, circuit=circuit)


def _configured_chain_entry_names(settings) -> list[str]:
    """Task 18.8: the full expanded list of dispatch-chain entry names the live
    chain would use right now, accounting for Gemini's multi-model expansion --
    e.g. `["openrouter", "gemini-3.1-flash-lite", "gemini-flash-lite-latest"]`.
    Read-only, builds no `Provider` instances (never raises on a bad base URL),
    safe for a cheap health-check read (`app/api/ai_jobs.py`) as well as
    `build_ai_router_from_settings`'s own real construction."""
    names: list[str] = []
    for provider_name in _configured_cloud_provider_names(settings):
        if provider_name == "gemini":
            names.extend(parse_fallback_models(settings.GEMINI_MODELS))
        else:
            names.append(provider_name)
    return names


def _build_chain_entries(name: str, settings, circuits: "dict[str, CircuitBreaker] | None") -> list["ChainEntry"]:
    """Task 18.8: one named provider's real construction -- a *list*, not one
    entry, because Gemini (Amendment F) expands into several: its free limits
    are per MODEL per project, so each configured model in `GEMINI_MODELS`
    dispatches as its own chain position with its own circuit, all sharing the
    one `GEMINI_API_KEY`/`GEMINI_BASE_URL` (Gemini has no OpenRouter-style
    server-side `models:[]` array to try them within one HTTP call). Only three
    top-level names are known (the plan's fixed provider set, not a
    user-extensible list) -- explicit branches, not a generic table, matching
    how little there is to generalize over just three."""
    if name == "openrouter":
        provider: Provider = OpenAICompatProvider(
            base_url=settings.OPENAI_COMPAT_BASE_URL,
            api_key=settings.OPENAI_COMPAT_API_KEY,
            model=settings.OPENAI_COMPAT_MODEL,
            timeout=settings.AI_CLOUD_DEADLINE_SECONDS,
            fallback_models=parse_fallback_models(settings.OPENAI_COMPAT_FALLBACK_MODELS),
            name="openrouter",
            vendor="openrouter",
        )
        return [_chain_entry("openrouter", provider, circuits)]
    if name == "opencode-zen":
        # Amendment F: kept generic/addable, but its free tier returned 403 "can
        # only be used from within OpenCode" for 6/7 real probed models -- never
        # in the default CLOUD_PROVIDER_ORDER, and no header/user-agent here ever
        # mimics that client.
        provider = OpenAICompatProvider(
            base_url=settings.OPENCODE_ZEN_BASE_URL,
            api_key=settings.OPENCODE_ZEN_API_KEY,
            model=settings.OPENCODE_ZEN_MODEL,
            timeout=settings.AI_CLOUD_DEADLINE_SECONDS,
            name="opencode-zen",
            vendor="generic",
        )
        return [_chain_entry("opencode-zen", provider, circuits)]
    if name == "gemini":
        entries = []
        for model in parse_fallback_models(settings.GEMINI_MODELS):
            provider = OpenAICompatProvider(
                base_url=settings.GEMINI_BASE_URL,
                api_key=settings.GEMINI_API_KEY,
                model=model,
                timeout=settings.AI_CLOUD_DEADLINE_SECONDS,
                name=model,
                vendor="gemini",
            )
            entries.append(_chain_entry(model, provider, circuits))
        return entries
    raise ValueError(f"unknown cloud provider name {name!r}")


def build_ai_router_from_settings(circuits: "dict[str, CircuitBreaker] | None" = None) -> "AIRouter":
    """Construct the Task 13.2 provider gateway from current app settings.

    The one shared factory for every cloud-AI consumer -- previously duplicated
    per-service (`script_service._build_ai_router`). A fresh instance per call is
    fine: there is no shared-lifespan client the way a lifespan-managed worker
    would want, matching each provider's own per-call `httpx.AsyncClient`
    lifetime. `circuits` is `None` by default (a fresh breaker per configured
    provider per call, matching today's per-call-fresh router semantics) -- a
    caller that needs circuit-breaker state to persist across calls (the
    durable job worker, `app/main.py`) holds its own `dict[str, CircuitBreaker]`
    for the app's whole lifetime and passes it here on every call instead
    (Task 18.8: generalizes the single `circuit=` param 18.2/18.6 had, one
    breaker per provider name instead of one breaker total).
    """
    from app.core.config import settings  # local import: avoids a config<->ai import cycle

    fallback = OllamaProvider(
        base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL, num_ctx=settings.OLLAMA_NUM_CTX
    )
    configured_names = _configured_cloud_provider_names(settings)
    effective_mode = compute_effective_mode(AIMode(settings.AI_MODE), settings.AI_ALLOW_CLOUD, bool(configured_names))

    chain: list[ChainEntry] = []
    if effective_mode is not AIMode.LOCAL:
        for name in configured_names:
            try:
                chain.extend(_build_chain_entries(name, settings, circuits))
            except ValueError:
                logger.warning("ai_router_invalid_cloud_base_url provider=%s -- skipping", name)
        if not chain:
            logger.warning("ai_router_no_valid_cloud_providers -- falling back to local")
            effective_mode = AIMode.LOCAL

    return AIRouter(
        chain=chain, fallback=fallback, mode=effective_mode,
        cloud_deadline_seconds=settings.AI_CLOUD_DEADLINE_SECONDS,
        total_cloud_budget_seconds=AI_TOTAL_CLOUD_BUDGET_SECONDS,
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


@dataclass
class ChainEntry:
    """Task 18.8 (D28): one cloud provider's slot in the dispatch chain --
    bundles its `Provider` instance with its OWN `CircuitBreaker` (generalizes
    18.6's single primary/circuit pair to N independently healthy-or-paused
    providers). `name` is kept in sync, by construction, with three other
    things that must always agree: the circuits-dict key
    (`app/main.py`'s `_ai_circuits`), the provider's own `.name` (its
    per-instance name, `openai_compat_provider.py`), and the Settings-page row
    identifier."""

    name: str
    provider: Provider
    circuit: CircuitBreaker


class AIRouter:
    """Routes one `GenerationRequest` through a chain of cloud providers, then
    the local fallback, per `AI_MODE`.

    Circuit-breaker state is in-process only, not persisted -- Task 13.3's durable
    job layer is the real persistence/recovery boundary, not this router.
    """

    def __init__(
        self,
        *,
        chain: list[ChainEntry] | None = None,
        primary: Provider | None = None,
        fallback: Provider,
        mode: AIMode,
        cloud_deadline_seconds: float = AI_CLOUD_DEADLINE_SECONDS,
        total_cloud_budget_seconds: float = AI_TOTAL_CLOUD_BUDGET_SECONDS,
        failure_threshold: int = AI_CIRCUIT_FAILURE_THRESHOLD,
        cooldown_seconds: float = AI_CIRCUIT_COOLDOWN_SECONDS,
        circuit: CircuitBreaker | None = None,
    ) -> None:
        """Two ways to build the chain:
        - `chain=`: Task 18.8's real shape -- an already-built `list[ChainEntry]`.
          `build_ai_router_from_settings` always uses this.
        - `primary=` (or neither): a single-entry convenience, kept because it's
          a genuinely valid chain of one, not a compatibility shim over dead
          code -- every router-mechanics test (retry/backoff/budget) that
          constructs a router directly, whitebox, doesn't care how many
          providers are configured. `failure_threshold`/`cooldown_seconds`/
          `circuit` only apply on this path (a `chain=` caller already built
          each entry's own breaker). Neither given defaults `primary` to
          `fallback` -- the historical `AIMode.LOCAL` placeholder ("never
          called when effective_mode is LOCAL").
        `cloud_deadline_seconds`/`total_cloud_budget_seconds` are read once,
        here, at construction -- consistent with everything else here being
        frozen at construction, not re-read from `settings` on every call."""
        if chain is not None:
            self._chain = chain
        else:
            single = primary if primary is not None else fallback
            single_circuit = circuit if circuit is not None else CircuitBreaker(failure_threshold, cooldown_seconds)
            self._chain = [ChainEntry(name=single.name, provider=single, circuit=single_circuit)]
        self._fallback = fallback
        self._mode = mode
        self._cloud_deadline_seconds = cloud_deadline_seconds
        self._total_cloud_budget_seconds = total_cloud_budget_seconds

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Route one request. `local` mode and the fallback phase of `cloud`/
        `cloud_first` are bounded by `request.deadline_seconds`; the whole cloud
        chain (every entry attempted before falling back) shares one
        `total_cloud_budget_seconds` budget, each entry capped at
        `cloud_deadline_seconds` within it -- never shared with the fallback's
        own budget (Phase 18: a shared deadline is exactly how a slow primary
        once starved the fallback of any time at all; Task 18.8: the same
        principle, now at the chain level -- worst case `total_cloud_budget_
        seconds` on cloud, then a full fresh `request.deadline_seconds` on
        local).

        `AIMode.CLOUD` (a diagnostic escape hatch) walks the same chain but
        never falls back to local -- it raises the chain's own last error (or
        a generic one if nothing was even configured) once the chain is
        exhausted.

        Raises:
            ProviderError (or a subclass): If every attempt fails and this is
                `AIMode.CLOUD` (no fallback in that mode), or the relevant
                budget elapses first.
        """
        if self._mode is AIMode.LOCAL:
            return await self._run_with_budget(self._fallback, request, request.deadline_seconds)

        total_deadline_at = time.monotonic() + self._total_cloud_budget_seconds
        tried: list[str] = []
        last_error: ProviderError | None = None

        for entry in self._chain:
            if entry.circuit.is_open():
                logger.info("ai_router_circuit_open provider=%s purpose=%s", entry.name, request.purpose)
                continue
            remaining_total = total_deadline_at - time.monotonic()
            if remaining_total <= 0:
                logger.warning("ai_router_total_cloud_budget_exhausted purpose=%s", request.purpose)
                break
            entry_budget = min(self._cloud_deadline_seconds, remaining_total)
            try:
                result = await self._run_with_budget(entry.provider, request, entry_budget, circuit=entry.circuit)
            except ProviderError as exc:
                tried.append(entry.name)
                last_error = exc
                if isinstance(exc, ProviderDailyQuotaError):
                    entry.circuit.open_until(exc.reset_at_epoch_seconds)
                elif isinstance(exc, ProviderAuthError):
                    entry.circuit.open_immediately()
                else:
                    entry.circuit.record_failure()
                logger.warning(
                    "ai_router_chain_entry_failed provider=%s purpose=%s error=%s",
                    entry.name, request.purpose, type(exc).__name__,
                )
                continue
            tried.append(entry.name)
            result.providers_tried = list(tried)
            return result

        # Chain exhausted (every entry failed, was paused, or the total budget ran out).
        if self._mode is AIMode.CLOUD:
            if last_error is not None:
                raise last_error
            raise ProviderUnavailableError("no cloud provider configured or all circuits open")

        result = await self._run_with_budget(self._fallback, request, request.deadline_seconds)
        result.fallback_used = True
        result.fallback_reason = type(last_error).__name__ if last_error is not None else "no_cloud_provider_configured"
        result.providers_tried = list(tried)
        # True only when nothing was even attempted (every configured entry was
        # skipped for being paused) -- matches 18.1-18.6's single-provider
        # meaning ("we skipped the primary entirely"), generalized to N entries.
        result.circuit_open = bool(self._chain) and not tried
        return result

    def is_cloud_result(self, result: GenerationResult) -> bool:
        """Task 18.8 (generalizes 18.6 C2's `is_primary_result`): True only when
        `result` was genuinely served by one of the chain's real providers --
        not a hardcoded provider name, survives a future provider
        rename/addition. Excludes `AIMode.LOCAL`, where the single-entry
        placeholder chain's provider is the same object as `fallback` -- a bare
        name-membership check would otherwise wrongly return `True` for an
        ordinary local-mode result."""
        return self._mode is not AIMode.LOCAL and result.provider in {entry.name for entry in self._chain}

    async def generate_on_fallback(self, request: GenerationRequest) -> GenerationResult:
        """Task 18.6 item 4: force exactly one call on the local fallback,
        bypassing the whole chain/circuits entirely -- used by a pipeline's
        call wrapper for the one-shot local retry after a cloud-served result
        fails JSON parse/validation, before the pipeline's own normal repair
        path. Reuses `_run_with_budget`/`_attempt` unchanged, so it gets the
        same per-call retry/backoff policy any other fallback-phase call gets.
        Deliberately never touches any entry's circuit: a malformed-JSON
        content failure says nothing about that provider's health (it
        answered, on time, just with unparseable content), so it must never
        count toward a circuit's failure threshold the way an infra error
        does."""
        return await self._run_with_budget(self._fallback, request, request.deadline_seconds)

    async def _run_with_budget(
        self,
        provider: Provider,
        request: GenerationRequest,
        budget_seconds: float,
        circuit: CircuitBreaker | None = None,
    ) -> GenerationResult:
        """Wraps one phase's attempt(s) in its own `wait_for`, independent of
        any other phase's budget (Phase 18 -- see `generate`'s docstring).
        `circuit` (Task 18.8: explicit now, not `self._circuit`/`is self._
        primary` -- there can be several) records a success on `provider`'s own
        breaker; `None` (the fallback/`generate_on_fallback` case) means no
        breaker is touched at all."""
        deadline_at = time.monotonic() + budget_seconds
        try:
            return await asyncio.wait_for(
                self._attempt(provider, request, deadline_at, circuit=circuit), timeout=budget_seconds
            )
        except TimeoutError as exc:
            raise ProviderTimeoutError(
                f"AI router budget of {budget_seconds}s exceeded for {provider.name}"
            ) from exc

    async def _attempt(
        self,
        provider: Provider,
        request: GenerationRequest,
        deadline_at: float,
        circuit: CircuitBreaker | None = None,
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
                if circuit is not None:
                    circuit.record_success()
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
