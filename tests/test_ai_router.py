"""Tests for AIRouter: mode selection, transient-error backoff (Task 14.1),
content-error retry, fallback, circuit breaker."""

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
from app.services.ai.router import AIRouter


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


async def test_local_mode_never_calls_gemini():
    local = FakeProvider("ollama", [_result("ollama")])
    gemini = FakeProvider("gemini", [_result("gemini")])
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.LOCAL)

    result = await router.generate(_request())

    assert result.provider == "ollama"
    assert local.call_count == 1
    assert gemini.call_count == 0


async def test_gemini_mode_never_calls_local():
    local = FakeProvider("ollama", [_result("ollama")])
    gemini = FakeProvider("gemini", [_result("gemini")])
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.GEMINI)

    result = await router.generate(_request())

    assert result.provider == "gemini"
    assert local.call_count == 0
    assert gemini.call_count == 1


async def test_local_mode_raises_without_any_gemini_fallback_when_local_fails():
    """Task 13.7 verification: 'disabled fallback yields a clear local error' --
    AI_MODE=local is the disabled-fallback configuration (see ADR-001/config.py),
    so a local failure must surface directly, never silently reach Gemini. Updated
    for Task 14.1: exhausting the transient policy now takes 4 attempts, not 2."""
    local = FakeProvider("ollama", [ProviderUnavailableError("down")] * 4)
    gemini = FakeProvider("gemini", [])
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.LOCAL)

    with pytest.raises(ProviderUnavailableError):
        await router.generate(_request())

    assert local.call_count == 4  # AI_TRANSIENT_MAX_ATTEMPTS, no more
    assert gemini.call_count == 0


# --- hybrid: happy path, retry, fallback ----------------------------------------------


async def test_hybrid_mode_uses_local_when_it_succeeds():
    local = FakeProvider("ollama", [_result("ollama")])
    gemini = FakeProvider("gemini", [_result("gemini")])
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.HYBRID)

    result = await router.generate(_request())

    assert result.provider == "ollama"
    assert result.fallback_used is False
    assert gemini.call_count == 0


async def test_hybrid_mode_retries_local_once_on_retryable_error_then_succeeds(sleep_calls):
    local = FakeProvider("ollama", [ProviderUnavailableError("down"), _result("ollama", attempt=2)])
    gemini = FakeProvider("gemini", [])
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.HYBRID)

    result = await router.generate(_request())

    assert result.provider == "ollama"
    assert result.attempt == 2
    assert result.attempts == 2
    assert result.backoff_seconds == 1.0
    assert local.call_count == 2
    assert gemini.call_count == 0
    assert sleep_calls == [1.0]


async def test_hybrid_mode_falls_back_to_gemini_after_local_exhausts_its_retry():
    """Updated for Task 14.1: local now exhausts after 4 attempts, not 2."""
    local = FakeProvider("ollama", [ProviderUnavailableError("down")] * 4)
    gemini = FakeProvider("gemini", [_result("gemini")])
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.HYBRID)

    result = await router.generate(_request())

    assert result.provider == "gemini"
    assert result.fallback_used is True
    # exactly 4 local attempts + 1 gemini attempt -- no nested retries.
    assert local.call_count == 4
    assert gemini.call_count == 1


async def test_hybrid_mode_does_not_retry_on_auth_error_and_falls_back_immediately():
    local = FakeProvider("ollama", [ProviderAuthError("bad config")])
    gemini = FakeProvider("gemini", [_result("gemini")])
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.HYBRID)

    result = await router.generate(_request())

    assert result.provider == "gemini"
    assert local.call_count == 1  # no retry on a non-retryable error
    assert gemini.call_count == 1


async def test_hybrid_mode_bounded_total_attempts_even_when_gemini_also_fails():
    """Updated for Task 14.1: each provider route now exhausts at 4 attempts."""
    local = FakeProvider("ollama", [ProviderUnavailableError("down")] * 4)
    gemini = FakeProvider("gemini", [ProviderUnavailableError("down too")] * 4)
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.HYBRID)

    with pytest.raises(ProviderUnavailableError):
        await router.generate(_request())

    # 4 local attempts + 4 gemini attempts = 8 total, never more (no nested retries).
    assert local.call_count == 4
    assert gemini.call_count == 4


# --- Task 14.1: transient backoff -------------------------------------------------------


async def test_delay_sequence_is_one_two_four_on_repeated_transient_errors(sleep_calls):
    local = FakeProvider(
        "ollama",
        [
            ProviderUnavailableError("down"),
            ProviderUnavailableError("down"),
            ProviderUnavailableError("down"),
            _result("ollama", attempt=4),
        ],
    )
    gemini = FakeProvider("gemini", [])
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.LOCAL)

    result = await router.generate(_request())

    assert sleep_calls == [1.0, 2.0, 4.0]
    assert result.attempts == 4
    assert result.backoff_seconds == 7.0
    assert result.transient_errors == ["ProviderUnavailableError"] * 3
    assert local.call_count == 4


async def test_transient_exhaustion_raises_the_last_error_and_logs_exhausted(sleep_calls, caplog):
    local = FakeProvider("ollama", [ProviderUnavailableError("down")] * 4)
    gemini = FakeProvider("gemini", [])
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.LOCAL)

    with caplog.at_level(logging.WARNING, logger="app.services.ai.router"):
        with pytest.raises(ProviderUnavailableError):
            await router.generate(_request())

    assert local.call_count == 4
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
    local = FakeProvider("ollama", [ProviderUnavailableError("down"), ProviderUnavailableError("still down")])
    gemini = FakeProvider("gemini", [])
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.LOCAL)

    with pytest.raises(ProviderUnavailableError):
        await router.generate(_request(deadline_seconds=6.5))

    assert sleep_calls == [1.0]
    assert local.call_count == 2


async def test_schema_validation_error_gets_one_immediate_retry_and_no_sleep(sleep_calls):
    local = FakeProvider(
        "ollama", [SchemaValidationError("bad json"), _result("ollama", attempt=2)]
    )
    gemini = FakeProvider("gemini", [])
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.LOCAL)

    result = await router.generate(_request())

    assert result.provider == "ollama"
    assert local.call_count == 2
    assert sleep_calls == []
    assert result.backoff_seconds == 0.0
    assert result.transient_errors == []


async def test_auth_error_gets_no_retry_and_no_sleep(sleep_calls):
    local = FakeProvider("ollama", [ProviderAuthError("bad key")])
    gemini = FakeProvider("gemini", [])
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.LOCAL)

    with pytest.raises(ProviderAuthError):
        await router.generate(_request())

    assert local.call_count == 1
    assert sleep_calls == []


async def test_hybrid_local_exhausts_four_attempts_then_gemini_succeeds(sleep_calls):
    local = FakeProvider("ollama", [ProviderUnavailableError("down")] * 4)
    gemini = FakeProvider("gemini", [_result("gemini")])
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.HYBRID)

    result = await router.generate(_request())

    assert result.provider == "gemini"
    assert result.fallback_used is True
    assert local.call_count == 4
    assert gemini.call_count == 1
    assert sleep_calls == [1.0, 2.0, 4.0]


# --- circuit breaker -------------------------------------------------------------------


async def test_circuit_opens_after_threshold_and_skips_local():
    # 3 consecutive local failure-streaks (each streak = 4 exhausted attempts under
    # Task 14.1) trip the breaker at failure_threshold=3, then a 4th request should
    # skip local entirely.
    local_outcomes = []
    for _ in range(3):
        local_outcomes.extend([ProviderUnavailableError("down")] * 4)
    local = FakeProvider("ollama", local_outcomes)
    gemini = FakeProvider("gemini", [_result("gemini") for _ in range(4)])
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.HYBRID, failure_threshold=3, cooldown_seconds=60.0)

    for _ in range(3):
        result = await router.generate(_request())
        assert result.provider == "gemini"
        assert result.fallback_used is True

    # circuit should now be open -- 4th request must not touch local at all.
    result = await router.generate(_request())
    assert result.provider == "gemini"
    assert result.circuit_open is True
    assert local.call_count == 12  # unchanged from the first 3 requests (4 each)


async def test_circuit_closes_again_after_a_local_success():
    local = FakeProvider(
        "ollama",
        [
            ProviderUnavailableError("down"),
            ProviderUnavailableError("down"),
            ProviderUnavailableError("down"),
            ProviderUnavailableError("down"),  # streak 1: exhausts (4 attempts) -> failure_count=1
            _result("ollama"),  # streak 2: succeeds -> resets failure_count
        ],
    )
    gemini = FakeProvider("gemini", [_result("gemini")])
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.HYBRID, failure_threshold=1, cooldown_seconds=0.01)

    first = await router.generate(_request())
    assert first.provider == "gemini"  # fell back, circuit now open (threshold=1)

    await asyncio.sleep(0.02)  # let the short cooldown elapse (real asyncio.sleep -- not the patched router.sleep)
    second = await router.generate(_request())
    assert second.provider == "ollama"  # circuit closed again, local succeeds


# --- deadline ----------------------------------------------------------------------


async def test_generate_raises_timeout_when_deadline_elapses():
    async def _slow_generate(request):
        await asyncio.sleep(1.0)
        return _result("ollama")

    class _SlowProvider:
        name = "ollama"
        generate = staticmethod(_slow_generate)

    local = _SlowProvider()
    gemini = FakeProvider("gemini", [])
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.LOCAL)

    with pytest.raises(ProviderTimeoutError):
        await router.generate(_request(deadline_seconds=0.05))
