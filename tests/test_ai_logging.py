"""Regression tests locking down the AI gateway's no-secret-leakage logging (Task 13.8).

Section 7/9 of the controlling plan (docs/implementation/phase-13-local-first-ai-
reliability.md) requires that prompt bodies, response bodies, and API keys never
reach routine logs or API errors -- only job/provider/model/purpose/prompt_hash/
stage/attempt/latency/counters/validation-code/fallback-reason/exception-type are
allowed. `app/services/ai/router.py` is the one place in the whole AI layer that
logs anything beyond a single job-recovery-count line in `ai_worker.py` (confirmed
by auditing every logger call site before writing this file -- see
tasks/task-13.8.md). These tests exercise the router with `FakeProvider`s carrying
a deliberately distinctive "secret marker" in both the prompt and the returned
text, across success/retry/fallback/circuit-breaker/error paths, and assert that
marker never appears in captured log output -- broader than the existing single
per-provider check (test_ai_providers.py::test_ollama_provider_never_logs_prompt_body),
which covers only one provider's own log output, not the router's, and not a
retry/fallback sequence.
"""

import logging

import pytest

from app.core.exceptions import ProviderAuthError, ProviderUnavailableError
from app.services.ai.contracts import AIMode, GenerationRequest, GenerationResult
from app.services.ai.fake_provider import FakeProvider
from app.services.ai.router import AIRouter

SECRET_PROMPT_MARKER = "SECRET_PROMPT_MARKER_user_topic_12345"
SECRET_RESPONSE_MARKER = "SECRET_RESPONSE_MARKER_model_output_67890"
FAKE_API_KEY = "super-secret-fake-api-key-never-log-me"


@pytest.fixture(autouse=True)
def _patch_router_sleep(monkeypatch):
    """No-op the router's module-local `sleep` (Task 14.1) so a transient-error
    exhaustion path in these tests doesn't really wait out 1s+2s+4s of backoff --
    see tests/test_ai_router.py's `sleep_calls` fixture for the same pattern."""

    async def _fake_sleep(delay: float) -> None:
        return None

    monkeypatch.setattr("app.services.ai.router.sleep", _fake_sleep)


def _request() -> GenerationRequest:
    # 30s: comfortably above AI_TRANSIENT_MAX_ATTEMPTS=4's backoff-affordability
    # checks even with `sleep` patched to a no-op -- the deadline check uses real
    # wall-clock time, not a simulated one (see tests/test_ai_router.py).
    return GenerationRequest(
        prompt=SECRET_PROMPT_MARKER, deadline_seconds=30, purpose="test_ai_logging"
    )


def _result(provider: str, attempt: int = 1) -> GenerationResult:
    return GenerationResult(
        text=SECRET_RESPONSE_MARKER,
        provider=provider,
        model=f"{provider}-model",
        tokens_used=42,
        latency_ms=1.0,
        attempt=attempt,
        prompt_hash="abc123",
    )


def _assert_no_secrets_leaked(log_text: str) -> None:
    assert SECRET_PROMPT_MARKER not in log_text
    assert SECRET_RESPONSE_MARKER not in log_text
    assert FAKE_API_KEY not in log_text


@pytest.mark.asyncio
async def test_successful_generate_never_logs_prompt_or_response(caplog):
    local = FakeProvider("ollama", [_result("ollama")])
    gemini = FakeProvider("gemini", [_result("gemini")])
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.LOCAL)

    with caplog.at_level(logging.DEBUG):
        result = await router.generate(_request())

    assert result.text == SECRET_RESPONSE_MARKER  # the value itself is fine to return...
    _assert_no_secrets_leaked(caplog.text)  # ...but never through the logger.


@pytest.mark.asyncio
async def test_retry_sequence_never_logs_prompt_or_response(caplog):
    local = FakeProvider(
        "ollama", [ProviderUnavailableError("down"), _result("ollama", attempt=2)]
    )
    gemini = FakeProvider("gemini", [])
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.LOCAL)

    with caplog.at_level(logging.DEBUG):
        await router.generate(_request())

    _assert_no_secrets_leaked(caplog.text)


@pytest.mark.asyncio
async def test_hybrid_fallback_never_logs_prompt_or_response(caplog):
    local = FakeProvider("ollama", [ProviderUnavailableError("down")] * 4)
    gemini = FakeProvider("gemini", [_result("gemini")])
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.HYBRID)

    with caplog.at_level(logging.DEBUG):
        result = await router.generate(_request())

    assert result.fallback_used is True
    _assert_no_secrets_leaked(caplog.text)


@pytest.mark.asyncio
async def test_circuit_breaker_open_never_logs_prompt_or_response(caplog):
    local_outcomes = []
    for _ in range(3):
        local_outcomes.extend([ProviderUnavailableError("down")] * 4)
    local = FakeProvider("ollama", local_outcomes)
    gemini = FakeProvider("gemini", [_result("gemini") for _ in range(4)])
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.HYBRID, failure_threshold=3, cooldown_seconds=60.0)

    with caplog.at_level(logging.DEBUG):
        for _ in range(4):
            await router.generate(_request())

    _assert_no_secrets_leaked(caplog.text)


@pytest.mark.asyncio
async def test_total_failure_never_logs_prompt_or_response(caplog):
    """Every attempt failing (both providers exhausted) is the path most likely to
    tempt a future change into logging response/error detail for debugging --
    locked down here so that temptation is caught by a test, not code review alone."""
    local = FakeProvider("ollama", [ProviderUnavailableError("down")] * 4)
    gemini = FakeProvider("gemini", [ProviderUnavailableError("down too")] * 4)
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.HYBRID)

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(ProviderUnavailableError):
            await router.generate(_request())

    _assert_no_secrets_leaked(caplog.text)


@pytest.mark.asyncio
async def test_auth_error_never_logs_the_api_key(caplog):
    """Router-level companion to test_ai_providers.py's provider-level auth-error
    check -- confirms the *router's own* logging around a non-retryable auth
    failure also never echoes the key, not just the raised exception's message."""
    local = FakeProvider("ollama", [ProviderAuthError(f"bad key: {FAKE_API_KEY}")])
    gemini = FakeProvider("gemini", [_result("gemini")])
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.HYBRID)

    with caplog.at_level(logging.DEBUG):
        await router.generate(_request())

    # The router logs only the exception's *class name*, never str(exc) -- so even
    # though this FakeProvider's own exception message embeds the fake key (to
    # simulate a real provider doing something unsafe), the router's log output
    # must still never include it.
    assert FAKE_API_KEY not in caplog.text
    _assert_no_secrets_leaked(caplog.text)


@pytest.mark.asyncio
async def test_router_logs_only_the_documented_safe_fields(caplog):
    """Positive check (not just an absence check): every router log record's
    message is built only from the safe-field format strings in router.py --
    confirms this test suite is actually observing router.py's own logger,
    not silently matching zero log records."""
    local = FakeProvider("ollama", [_result("ollama")])
    gemini = FakeProvider("gemini", [])
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.LOCAL)

    with caplog.at_level(logging.INFO, logger="app.services.ai.router"):
        await router.generate(_request())

    router_records = [r for r in caplog.records if r.name == "app.services.ai.router"]
    assert router_records, "expected at least one log record from app.services.ai.router"
    for record in router_records:
        message = record.getMessage()
        assert "prompt_hash=" in message or "provider=" in message
        assert SECRET_PROMPT_MARKER not in message
        assert SECRET_RESPONSE_MARKER not in message
