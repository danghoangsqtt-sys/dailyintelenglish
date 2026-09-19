"""Tests for AIRouter: mode selection, one-retry policy, fallback, circuit breaker."""

import asyncio

import pytest

from app.core.exceptions import ProviderAuthError, ProviderTimeoutError, ProviderUnavailableError
from app.services.ai.contracts import AIMode, GenerationRequest, GenerationResult
from app.services.ai.fake_provider import FakeProvider
from app.services.ai.router import AIRouter


def _request(**overrides) -> GenerationRequest:
    defaults = {"prompt": "hello", "deadline_seconds": 5, "purpose": "test"}
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


# --- hybrid: happy path, retry, fallback ----------------------------------------------


async def test_hybrid_mode_uses_local_when_it_succeeds():
    local = FakeProvider("ollama", [_result("ollama")])
    gemini = FakeProvider("gemini", [_result("gemini")])
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.HYBRID)

    result = await router.generate(_request())

    assert result.provider == "ollama"
    assert result.fallback_used is False
    assert gemini.call_count == 0


async def test_hybrid_mode_retries_local_once_on_retryable_error_then_succeeds():
    local = FakeProvider("ollama", [ProviderUnavailableError("down"), _result("ollama", attempt=2)])
    gemini = FakeProvider("gemini", [])
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.HYBRID)

    result = await router.generate(_request())

    assert result.provider == "ollama"
    assert result.attempt == 2
    assert local.call_count == 2
    assert gemini.call_count == 0


async def test_hybrid_mode_falls_back_to_gemini_after_local_exhausts_its_retry():
    local = FakeProvider(
        "ollama", [ProviderUnavailableError("down"), ProviderUnavailableError("still down")]
    )
    gemini = FakeProvider("gemini", [_result("gemini")])
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.HYBRID)

    result = await router.generate(_request())

    assert result.provider == "gemini"
    assert result.fallback_used is True
    # exactly local attempt 1 + local retry + gemini attempt 1 -- no nested retries.
    assert local.call_count == 2
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
    local = FakeProvider(
        "ollama", [ProviderUnavailableError("down"), ProviderUnavailableError("still down")]
    )
    gemini = FakeProvider(
        "gemini", [ProviderUnavailableError("down too"), ProviderUnavailableError("still down too")]
    )
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.HYBRID)

    with pytest.raises(ProviderUnavailableError):
        await router.generate(_request())

    # 2 local attempts + 2 gemini attempts = 4 total, never more (no nested retries).
    assert local.call_count == 2
    assert gemini.call_count == 2


# --- circuit breaker -------------------------------------------------------------------


async def test_circuit_opens_after_threshold_and_skips_local():
    # 3 consecutive local failure-streaks (each streak = 1 attempt + 1 retry) trip the
    # breaker at failure_threshold=3, then a 4th request should skip local entirely.
    local_outcomes = []
    for _ in range(3):
        local_outcomes.extend([ProviderUnavailableError("down"), ProviderUnavailableError("down")])
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
    assert local.call_count == 6  # unchanged from the first 3 requests (2 each)


async def test_circuit_closes_again_after_a_local_success():
    local = FakeProvider(
        "ollama",
        [
            ProviderUnavailableError("down"),
            ProviderUnavailableError("down"),  # streak 1: both fail -> failure_count=1
            _result("ollama"),  # streak 2: succeeds -> resets failure_count
        ],
    )
    gemini = FakeProvider("gemini", [_result("gemini")])
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.HYBRID, failure_threshold=1, cooldown_seconds=0.01)

    first = await router.generate(_request())
    assert first.provider == "gemini"  # fell back, circuit now open (threshold=1)

    await asyncio.sleep(0.02)  # let the short cooldown elapse
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
