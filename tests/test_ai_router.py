"""Tests for AIRouter: mode selection, transient-error backoff (Task 14.1),
content-error retry, fallback, circuit breaker, and (Phase 18) separate
primary/fallback time budgets and `compute_effective_mode`/
`build_ai_router_from_settings`'s live-settings/shared-circuit wiring.

Phase 18/D21 inverted the provider roles: cloud (`primary`) is attempted
first, local (`fallback`) is the automatic fallback -- the reverse of the old
`hybrid` mode's "local first, one visible Gemini fallback". Every test below
that used to exercise `AIMode.HYBRID` with `local=`/`gemini=` FakeProviders
was re-derived by hand for the new `AIMode.CLOUD_FIRST` with `primary=`/
`fallback=` -- not just renamed, since the provider that gets which scripted
outcome inverts too (see each test's docstring for the old-vs-new mapping).
"""

import asyncio
import logging

import pytest

from app.core.exceptions import (
    ProviderAuthError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    SchemaValidationError,
)
from app.services.ai.contracts import AIMode, GenerationRequest, GenerationResult
from app.services.ai.fake_provider import FakeProvider
from app.services.ai.router import AIRouter, CircuitBreaker, build_ai_router_from_settings, compute_effective_mode


@pytest.fixture(autouse=True)
def sleep_calls(monkeypatch):
    """Patch the router's module-local `sleep` (never `asyncio.sleep` globally --
    see task-14.1.md for why) to a fast no-op that records every requested delay.

    Autouse so every test in this file runs fast and deterministic; tests that
    care about the actual delay sequence take this fixture as a parameter to
    inspect the recorded list.
    """
    calls: list[float] = []

    async def _fake_sleep(delay: float) -> None:
        calls.append(delay)

    monkeypatch.setattr("app.services.ai.router.sleep", _fake_sleep)
    return calls


def _request(**overrides) -> GenerationRequest:
    # 30s default: comfortably above every AI_TRANSIENT_MAX_ATTEMPTS=4 backoff
    # check (1.0+5.0, 2.0+5.0, 4.0+5.0 => needs >= 9.0) even with `sleep` patched
    # to a no-op, since the deadline check uses real wall-clock time, not a
    # simulated one -- see task-14.1.md's execution record.
    defaults = {"prompt": "hello", "deadline_seconds": 30, "purpose": "test"}
    defaults.update(overrides)
    return GenerationRequest(**defaults)


def _result(provider: str, attempt: int = 1) -> GenerationResult:
    return GenerationResult(
        text="ok",
        provider=provider,
        model=f"{provider}-model",
        latency_ms=1.0,
        attempt=attempt,
        prompt_hash="abc123",
    )


# --- mode selection ------------------------------------------------------------------


async def test_local_mode_never_calls_primary():
    fallback = FakeProvider("ollama", [_result("ollama")])
    primary = FakeProvider("openai_compat", [_result("openai_compat")])
    router = AIRouter(primary=primary, fallback=fallback, mode=AIMode.LOCAL)

    result = await router.generate(_request())

    assert result.provider == "ollama"
    assert fallback.call_count == 1
    assert primary.call_count == 0


async def test_cloud_mode_never_calls_fallback():
    fallback = FakeProvider("ollama", [_result("ollama")])
    primary = FakeProvider("openai_compat", [_result("openai_compat")])
    router = AIRouter(primary=primary, fallback=fallback, mode=AIMode.CLOUD)

    result = await router.generate(_request())

    assert result.provider == "openai_compat"
    assert primary.call_count == 1
    assert fallback.call_count == 0


async def test_local_mode_raises_without_any_primary_fallback_when_fallback_fails():
    """Task 13.7 verification: 'disabled fallback yields a clear local error' --
    AI_MODE=local is the disabled-fallback configuration (see ADR-001/config.py),
    so a fallback failure must surface directly, never silently reach the primary.
    Task 14.1: exhausting the transient policy takes 4 attempts, not 2."""
    fallback = FakeProvider("ollama", [ProviderUnavailableError("down")] * 4)
    primary = FakeProvider("openai_compat", [])
    router = AIRouter(primary=primary, fallback=fallback, mode=AIMode.LOCAL)

    with pytest.raises(ProviderUnavailableError):
        await router.generate(_request())

    assert fallback.call_count == 4  # AI_TRANSIENT_MAX_ATTEMPTS, no more
    assert primary.call_count == 0


# --- cloud_first: happy path, retry, fallback -----------------------------------------


async def test_cloud_first_mode_uses_primary_when_it_succeeds():
    """Old (HYBRID): local succeeds immediately, gemini never called -- the
    provider holding the immediate-success outcome was `local=`. New
    (CLOUD_FIRST): the provider attempted first is the PRIMARY, so the
    immediate-success outcome moves to `primary=`; `fallback=` is the one
    that must go untouched."""
    primary = FakeProvider("openai_compat", [_result("openai_compat")])
    fallback = FakeProvider("ollama", [_result("ollama")])
    router = AIRouter(primary=primary, fallback=fallback, mode=AIMode.CLOUD_FIRST)

    result = await router.generate(_request())

    assert result.provider == "openai_compat"
    assert result.fallback_used is False
    assert fallback.call_count == 0


async def test_cloud_first_mode_retries_primary_once_on_retryable_error_then_succeeds(sleep_calls):
    """Old (HYBRID): `local=` held [transient-error, success] and retried in
    place, no fallback needed. New (CLOUD_FIRST): that same in-place-retry
    behaviour belongs to whichever provider is attempted FIRST, which is now
    `primary=`."""
    primary = FakeProvider("openai_compat", [ProviderUnavailableError("down"), _result("openai_compat", attempt=2)])
    fallback = FakeProvider("ollama", [])
    router = AIRouter(primary=primary, fallback=fallback, mode=AIMode.CLOUD_FIRST)

    result = await router.generate(_request())

    assert result.provider == "openai_compat"
    assert result.attempt == 2
    assert result.attempts == 2
    assert result.backoff_seconds == 1.0
    assert primary.call_count == 2
    assert fallback.call_count == 0
    assert sleep_calls == [1.0]


async def test_cloud_first_mode_falls_back_to_ollama_after_primary_exhausts_its_retry():
    """Old (HYBRID): `local=` (4x failure) exhausted, `gemini=` (the fallback
    role) succeeded. New (CLOUD_FIRST): the exhausting-first-attempt role is
    now `primary=`, and the rescuing role is `fallback=` -- both scripted
    outcome lists swap which parameter they're passed to, not just renamed.
    Task 14.1: local/primary now exhausts after 4 attempts, not 2."""
    primary = FakeProvider("openai_compat", [ProviderUnavailableError("down")] * 4)
    fallback = FakeProvider("ollama", [_result("ollama")])
    router = AIRouter(primary=primary, fallback=fallback, mode=AIMode.CLOUD_FIRST)

    result = await router.generate(_request())

    assert result.provider == "ollama"
    assert result.fallback_used is True
    assert result.fallback_reason == "ProviderUnavailableError"
    # exactly 4 primary attempts + 1 fallback attempt -- no nested retries.
    assert primary.call_count == 4
    assert fallback.call_count == 1


async def test_cloud_first_mode_does_not_retry_on_auth_error_and_falls_back_immediately():
    primary = FakeProvider("openai_compat", [ProviderAuthError("bad config")])
    fallback = FakeProvider("ollama", [_result("ollama")])
    router = AIRouter(primary=primary, fallback=fallback, mode=AIMode.CLOUD_FIRST)

    result = await router.generate(_request())

    assert result.provider == "ollama"
    assert result.fallback_reason == "ProviderAuthError"
    assert primary.call_count == 1  # no retry on a non-retryable error
    assert fallback.call_count == 1


async def test_cloud_first_mode_bounded_total_attempts_even_when_fallback_also_fails():
    """Old (HYBRID): both `local=` and `gemini=` exhausted at 4 attempts each
    (Task 14.1), 8 total, raises. New (CLOUD_FIRST): same shape, `primary=`/
    `fallback=` swapped in for `local=`/`gemini=`."""
    primary = FakeProvider("openai_compat", [ProviderUnavailableError("down")] * 4)
    fallback = FakeProvider("ollama", [ProviderUnavailableError("down too")] * 4)
    router = AIRouter(primary=primary, fallback=fallback, mode=AIMode.CLOUD_FIRST)

    with pytest.raises(ProviderUnavailableError):
        await router.generate(_request())

    # 4 primary attempts + 4 fallback attempts = 8 total, never more (no nested retries).
    assert primary.call_count == 4
    assert fallback.call_count == 4


# --- Task 14.1: transient backoff -------------------------------------------------------
# LOCAL mode exercises `_attempt`'s own retry/backoff loop on a single provider
# (the fallback role) -- structurally unaffected by the primary/fallback role
# inversion, so these are a parameter rename only, not a semantic inversion.


async def test_delay_sequence_is_one_two_four_on_repeated_transient_errors(sleep_calls):
    fallback = FakeProvider(
        "ollama",
        [
            ProviderUnavailableError("down"),
            ProviderUnavailableError("down"),
            ProviderUnavailableError("down"),
            _result("ollama", attempt=4),
        ],
    )
    primary = FakeProvider("openai_compat", [])
    router = AIRouter(primary=primary, fallback=fallback, mode=AIMode.LOCAL)

    result = await router.generate(_request())

    assert sleep_calls == [1.0, 2.0, 4.0]
    assert result.attempts == 4
    assert result.backoff_seconds == 7.0
    assert result.transient_errors == ["ProviderUnavailableError"] * 3
    assert fallback.call_count == 4


async def test_transient_exhaustion_raises_the_last_error_and_logs_exhausted(sleep_calls, caplog):
    fallback = FakeProvider("ollama", [ProviderUnavailableError("down")] * 4)
    primary = FakeProvider("openai_compat", [])
    router = AIRouter(primary=primary, fallback=fallback, mode=AIMode.LOCAL)

    with caplog.at_level(logging.WARNING, logger="app.services.ai.router"):
        with pytest.raises(ProviderUnavailableError):
            await router.generate(_request())

    assert fallback.call_count == 4
    assert sleep_calls == [1.0, 2.0, 4.0]
    exhausted_lines = [r.getMessage() for r in caplog.records if "ai_router_exhausted" in r.getMessage()]
    assert len(exhausted_lines) == 1
    assert "attempts=4" in exhausted_lines[0]


async def test_backoff_stops_before_a_sleep_the_deadline_cannot_afford(sleep_calls):
    """deadline_seconds=6.5 (task-14.1.md's own worked example uses 6.0; nudged up
    slightly here to stay clear of real-clock measurement noise at the exact
    boundary -- `remaining` is real wall-clock time, so an exact-equality boundary
    would be flaky by a few microseconds of test-harness overhead, not a router
    bug): the first backoff (1.0s) still fits (remaining ~6.5 is not <
    1.0 + AI_BACKOFF_MIN_REMAINING_SECONDS(5.0)=6.0), but the second (2.0s) does
    not (remaining ~6.5 < 2.0+5.0=7.0) -- the router stops and raises instead of
    sleeping 2.0s."""
    fallback = FakeProvider("ollama", [ProviderUnavailableError("down"), ProviderUnavailableError("still down")])
    primary = FakeProvider("openai_compat", [])
    router = AIRouter(primary=primary, fallback=fallback, mode=AIMode.LOCAL)

    with pytest.raises(ProviderUnavailableError):
        await router.generate(_request(deadline_seconds=6.5))

    assert sleep_calls == [1.0]
    assert fallback.call_count == 2


async def test_schema_validation_error_gets_one_immediate_retry_and_no_sleep(sleep_calls):
    fallback = FakeProvider(
        "ollama", [SchemaValidationError("bad json"), _result("ollama", attempt=2)]
    )
    primary = FakeProvider("openai_compat", [])
    router = AIRouter(primary=primary, fallback=fallback, mode=AIMode.LOCAL)

    result = await router.generate(_request())

    assert result.provider == "ollama"
    assert fallback.call_count == 2
    assert sleep_calls == []
    assert result.backoff_seconds == 0.0
    assert result.transient_errors == []


async def test_auth_error_gets_no_retry_and_no_sleep(sleep_calls):
    fallback = FakeProvider("ollama", [ProviderAuthError("bad key")])
    primary = FakeProvider("openai_compat", [])
    router = AIRouter(primary=primary, fallback=fallback, mode=AIMode.LOCAL)

    with pytest.raises(ProviderAuthError):
        await router.generate(_request())

    assert fallback.call_count == 1
    assert sleep_calls == []


async def test_cloud_first_primary_exhausts_four_attempts_then_fallback_succeeds(sleep_calls):
    primary = FakeProvider("openai_compat", [ProviderUnavailableError("down")] * 4)
    fallback = FakeProvider("ollama", [_result("ollama")])
    router = AIRouter(primary=primary, fallback=fallback, mode=AIMode.CLOUD_FIRST)

    result = await router.generate(_request())

    assert result.provider == "ollama"
    assert result.fallback_used is True
    assert primary.call_count == 4
    assert fallback.call_count == 1
    assert sleep_calls == [1.0, 2.0, 4.0]


# --- circuit breaker -------------------------------------------------------------------


async def test_circuit_opens_after_threshold_and_skips_primary():
    """Old (HYBRID): 3 consecutive LOCAL failure-streaks trip the breaker,
    then a 4th request skips local entirely. New (CLOUD_FIRST): the breaker
    tracks the PRIMARY now (Amendment A/point 3: `_attempt` only records
    success/failure `if provider is self._primary`), so the failing provider
    moves from `local=` to `primary=`, and the never-exhausted rescuing
    provider moves from `gemini=` to `fallback=`."""
    primary_outcomes = []
    for _ in range(3):
        primary_outcomes.extend([ProviderUnavailableError("down")] * 4)
    primary = FakeProvider("openai_compat", primary_outcomes)
    fallback = FakeProvider("ollama", [_result("ollama") for _ in range(4)])
    router = AIRouter(
        primary=primary, fallback=fallback, mode=AIMode.CLOUD_FIRST, failure_threshold=3, cooldown_seconds=60.0
    )

    for _ in range(3):
        result = await router.generate(_request())
        assert result.provider == "ollama"
        assert result.fallback_used is True

    # circuit should now be open -- 4th request must not touch primary at all.
    result = await router.generate(_request())
    assert result.provider == "ollama"
    assert result.circuit_open is True
    assert primary.call_count == 12  # unchanged from the first 3 requests (4 each)


async def test_circuit_closes_again_after_a_primary_success():
    primary = FakeProvider(
        "openai_compat",
        [
            ProviderUnavailableError("down"),
            ProviderUnavailableError("down"),
            ProviderUnavailableError("down"),
            ProviderUnavailableError("down"),  # streak 1: exhausts (4 attempts) -> failure_count=1
            _result("openai_compat"),  # streak 2: succeeds -> resets failure_count
        ],
    )
    fallback = FakeProvider("ollama", [_result("ollama")])
    router = AIRouter(
        primary=primary, fallback=fallback, mode=AIMode.CLOUD_FIRST, failure_threshold=1, cooldown_seconds=0.01
    )

    first = await router.generate(_request())
    assert first.provider == "ollama"  # fell back, circuit now open (threshold=1)

    await asyncio.sleep(0.02)  # let the short cooldown elapse (real asyncio.sleep -- not the patched router.sleep)
    second = await router.generate(_request())
    assert second.provider == "openai_compat"  # circuit closed again, primary succeeds


async def test_circuit_opens_immediately_on_primary_auth_error():
    """Phase 18, Amendment A/point 3 (new behaviour): a config error can't
    self-resolve on retry, so it opens the circuit at once -- not after the
    normal `failure_threshold` count of ordinary transient failures. Contrast
    with `test_circuit_opens_after_threshold_and_skips_primary` above, which
    needs 3 full streaks of `ProviderUnavailableError` (transient) before the
    same threshold=3 breaker opens."""
    primary = FakeProvider("openai_compat", [ProviderAuthError("bad key")])
    fallback = FakeProvider("ollama", [_result("ollama"), _result("ollama")])
    router = AIRouter(
        primary=primary, fallback=fallback, mode=AIMode.CLOUD_FIRST, failure_threshold=3, cooldown_seconds=60.0
    )

    first = await router.generate(_request())
    assert first.provider == "ollama"
    assert first.fallback_used is True

    # threshold=3 would normally need 3 failure streaks -- one auth error opens
    # it immediately, so a second request must skip the primary entirely.
    second = await router.generate(_request())
    assert second.provider == "ollama"
    assert second.circuit_open is True
    assert primary.call_count == 1  # unchanged -- the second request never touched it


# --- deadline / separate budgets (Phase 18) ---------------------------------------------


async def test_generate_raises_timeout_when_deadline_elapses():
    async def _slow_generate(request):
        await asyncio.sleep(1.0)
        return _result("ollama")

    class _SlowProvider:
        name = "ollama"
        generate = staticmethod(_slow_generate)

    fallback = _SlowProvider()
    primary = FakeProvider("openai_compat", [])
    router = AIRouter(primary=primary, fallback=fallback, mode=AIMode.LOCAL)

    with pytest.raises(ProviderTimeoutError):
        await router.generate(_request(deadline_seconds=0.05))


async def test_primary_budget_exhaustion_does_not_starve_the_fallback_budget():
    """Required test (plan §3 18.2 verification, PM's specified revert target):
    the primary's own `cloud_deadline_seconds` budget and the fallback's own
    `request.deadline_seconds` budget are independent -- Phase 18's whole
    reason for existing is that a shared deadline is exactly how both smoke
    jobs died (a slow primary left nothing for the fallback). A primary given
    a tiny 0.05s budget that needs 0.2s to answer must time out and fall back
    to a provider given its own, much larger 0.5s budget -- which must still
    get the *entire* 0.5s, not whatever the primary happened to leave over."""

    async def _slow_primary_generate(request):
        await asyncio.sleep(0.2)
        return _result("openai_compat")

    class _SlowPrimary:
        name = "openai_compat"
        generate = staticmethod(_slow_primary_generate)

    fallback = FakeProvider("ollama", [_result("ollama")])
    router = AIRouter(
        primary=_SlowPrimary(), fallback=fallback, mode=AIMode.CLOUD_FIRST, cloud_deadline_seconds=0.05
    )

    result = await router.generate(_request(deadline_seconds=0.5))

    assert result.provider == "ollama"
    assert result.fallback_used is True
    assert result.fallback_reason == "ProviderTimeoutError"
    assert fallback.call_count == 1


async def test_fallback_gets_its_own_fresh_budget_not_the_leftover_of_the_primarys():
    """PM review N1 (test gap found before accepting 18.2): the previous test
    above used `cloud_deadline_seconds=0.05 < request.deadline_seconds=0.5`,
    so it can't distinguish truly independent budgets from a *leftover*-based
    bug (`fallback_budget = max(epsilon, request.deadline_seconds -
    elapsed_since_generate_start)`) -- with that shape of numbers there's
    always plenty of leftover either way. Production is the opposite shape
    (`AI_CLOUD_DEADLINE_SECONDS=150 > AI_REQUEST_DEADLINE_SECONDS=120`), where
    a leftover-based bug would give the fallback nothing or a negative budget.

    This test uses that same shape: `cloud_deadline_seconds=0.3 >
    request.deadline_seconds=0.2`. The primary sleeps 0.35s (exceeds its own
    0.3s budget, so it times out there). The fallback needs 0.15s to answer --
    less than its own fresh 0.2s budget, but *more* than what a leftover
    calculation would hand it (`request.deadline_seconds(0.2) -
    elapsed(~0.3)` is negative, clamped to some tiny epsilon). Correct
    (independent-budget) code returns the fallback's result; a leftover-style
    revert raises `ProviderTimeoutError` instead, because 0.15s doesn't fit in
    an epsilon-sized leftover budget."""

    async def _slow_primary_generate(request):
        await asyncio.sleep(0.35)
        return _result("openai_compat")

    class _SlowPrimary:
        name = "openai_compat"
        generate = staticmethod(_slow_primary_generate)

    async def _slow_fallback_generate(request):
        await asyncio.sleep(0.15)
        return _result("ollama")

    class _SlowFallback:
        name = "ollama"
        generate = staticmethod(_slow_fallback_generate)

    router = AIRouter(
        primary=_SlowPrimary(), fallback=_SlowFallback(), mode=AIMode.CLOUD_FIRST, cloud_deadline_seconds=0.3
    )

    result = await router.generate(_request(deadline_seconds=0.2))

    assert result.provider == "ollama"
    assert result.fallback_used is True
    assert result.fallback_reason == "ProviderTimeoutError"


# --- compute_effective_mode (invariant 32/D24) -------------------------------------------


@pytest.mark.parametrize(
    "configured_mode,allow_cloud,api_key,model,expected",
    [
        (AIMode.LOCAL, True, "key", "model", AIMode.LOCAL),  # local stays local regardless
        (AIMode.CLOUD, False, "key", "model", AIMode.LOCAL),  # kill switch off
        (AIMode.CLOUD_FIRST, False, "key", "model", AIMode.LOCAL),  # kill switch off
        (AIMode.CLOUD, True, "", "model", AIMode.LOCAL),  # no key
        (AIMode.CLOUD, True, "key", "", AIMode.LOCAL),  # no model
        (AIMode.CLOUD, True, "key", "model", AIMode.CLOUD),  # fully enabled -- passes through
        (AIMode.CLOUD_FIRST, True, "key", "model", AIMode.CLOUD_FIRST),  # fully enabled -- passes through
    ],
)
def test_compute_effective_mode(configured_mode, allow_cloud, api_key, model, expected):
    assert compute_effective_mode(configured_mode, allow_cloud, api_key, model) == expected


async def test_router_local_mode_matches_the_effective_local_collapse():
    """Invariant 32's second proof (the first is `LOCAL`'s branch being a
    verbatim copy of the pre-Phase-18 code, in the router itself): a router
    built from a *collapsed* effective mode (configured cloud_first, no key)
    behaves identically to one built directly with `mode=AIMode.LOCAL` --
    same result fields, same zero primary calls -- proving the collapse path
    and the explicit-local path are observably indistinguishable."""
    collapsed_mode = compute_effective_mode(AIMode.CLOUD_FIRST, allow_cloud=True, api_key="", model="")
    assert collapsed_mode is AIMode.LOCAL

    fallback_a = FakeProvider("ollama", [_result("ollama")])
    primary_a = FakeProvider("openai_compat", [])
    router_a = AIRouter(primary=primary_a, fallback=fallback_a, mode=collapsed_mode)

    fallback_b = FakeProvider("ollama", [_result("ollama")])
    primary_b = FakeProvider("openai_compat", [])
    router_b = AIRouter(primary=primary_b, fallback=fallback_b, mode=AIMode.LOCAL)

    request = _request()
    result_a = await router_a.generate(request)
    result_b = await router_b.generate(request)

    assert result_a.provider == result_b.provider == "ollama"
    assert result_a.fallback_used is False
    assert result_b.fallback_used is False
    assert primary_a.call_count == primary_b.call_count == 0


# --- build_ai_router_from_settings (Phase 18: live settings, shared circuit) -------------


def test_build_ai_router_from_settings_reads_current_settings_each_call(monkeypatch):
    """Point 1's 'a changed setting reaches the next job without a restart':
    each call reads `settings.*` live, so a Settings-page change between two
    job dispatches (`app/main.py`'s `_build_ai_router`, which this function
    backs) is reflected on the very next call, no restart needed."""
    from app.core import config

    monkeypatch.setattr(config.settings, "OLLAMA_MODEL", "qwen3.5:9b")
    router1 = build_ai_router_from_settings()
    assert router1._fallback._model == "qwen3.5:9b"

    monkeypatch.setattr(config.settings, "OLLAMA_MODEL", "a-different-model:latest")
    router2 = build_ai_router_from_settings()
    assert router2._fallback._model == "a-different-model:latest"


def test_build_ai_router_from_settings_threads_the_same_circuit_breaker_through_every_call():
    """Point 1's 'breaker state survives across two jobs': `app/main.py` holds
    ONE `CircuitBreaker` for the app's whole lifetime and passes it to every
    per-job router it builds -- simulated here by building two routers
    ("job 1", "job 2") with the same breaker and confirming both hold the
    exact same object, not a fresh one each time (the default, used when no
    `circuit` is passed, as every other caller of this function still gets)."""
    shared_circuit = CircuitBreaker(failure_threshold=1, cooldown_seconds=60.0)

    router1 = build_ai_router_from_settings(circuit=shared_circuit)
    router2 = build_ai_router_from_settings(circuit=shared_circuit)

    assert router1._circuit is shared_circuit
    assert router2._circuit is shared_circuit

    router1._circuit.record_failure()
    assert router2._circuit.is_open() is True  # job 2 sees job 1's breaker state


def test_build_ai_router_from_settings_default_circuit_is_fresh_per_call():
    """Every other caller of `build_ai_router_from_settings` (the 4
    `*_service.py` files) doesn't pass `circuit`, and must keep getting a
    fresh breaker per call -- matching today's per-call-fresh router
    semantics, not `app/main.py`'s special app-lifetime sharing."""
    router1 = build_ai_router_from_settings()
    router2 = build_ai_router_from_settings()

    assert router1._circuit is not router2._circuit
