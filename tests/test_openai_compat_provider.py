"""Tests for OpenAICompatProvider (Task 18.1, ENH-011). httpx.MockTransport only --
never a real network call. The owner's OpenRouter key in .env is for Gate B-9, not
development or tests.
"""

import json as json_module
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx
import pytest

from app.core.exceptions import (
    ProviderAuthError,
    ProviderDailyQuotaError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.services.ai import openai_compat_provider as openai_compat_provider_module
from app.services.ai.contracts import GenerationRequest
from app.services.ai.openai_compat_provider import (
    OpenAICompatProvider,
    parse_fallback_models,
    validate_openai_compat_base_url,
)


def _request(**overrides) -> GenerationRequest:
    defaults = {"prompt": "hello", "deadline_seconds": 30, "purpose": "test"}
    defaults.update(overrides)
    return GenerationRequest(**defaults)


def _install_mock_transport(monkeypatch, module, handler) -> None:
    """Patch `module.httpx.AsyncClient` to route through a MockTransport for this
    test only (`monkeypatch` restores the real class automatically at teardown) --
    same pattern as tests/test_ai_providers.py."""
    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def _factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(module.httpx, "AsyncClient", _factory)


def _provider(**overrides) -> OpenAICompatProvider:
    defaults = {"base_url": "https://openrouter.ai/api/v1", "api_key": "test-key", "model": "test/model"}
    defaults.update(overrides)
    return OpenAICompatProvider(**defaults)


# --- validate_openai_compat_base_url -------------------------------------------------


def test_validate_openai_compat_base_url_accepts_https_with_path():
    assert validate_openai_compat_base_url("https://openrouter.ai/api/v1/") == "https://openrouter.ai/api/v1"


def test_validate_openai_compat_base_url_accepts_http_loopback():
    assert validate_openai_compat_base_url("http://127.0.0.1:8080/v1") == "http://127.0.0.1:8080/v1"


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/v1",  # http, not loopback
        "http://user:pass@openrouter.ai/api/v1",  # credentials, wrong scheme too
        "https://user:pass@openrouter.ai/api/v1",  # credentials
    ],
)
def test_validate_openai_compat_base_url_rejects_unsafe_urls(url):
    with pytest.raises(ValueError):
        validate_openai_compat_base_url(url)


# --- success / request shape ----------------------------------------------------------


@pytest.mark.asyncio
async def test_openai_compat_provider_success(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        body = {
            "choices": [{"message": {"content": '{"ok": true}'}}],
            "usage": {"total_tokens": 123},
        }
        return httpx.Response(200, json=body)

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    result = await provider.generate(_request())
    assert result.text == '{"ok": true}'
    assert result.provider == "openai_compat"
    assert result.model == "test/model"
    assert result.tokens_used == 123
    assert result.attempt == 1


@pytest.mark.asyncio
async def test_openai_compat_provider_strips_json_fenced_code_block(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        body = {"choices": [{"message": {"content": '```json\n[{"a": 1}]\n```'}}]}
        return httpx.Response(200, json=body)

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    result = await provider.generate(_request())
    assert result.text == '[{"a": 1}]'


@pytest.mark.asyncio
async def test_openai_compat_provider_strips_bare_fenced_code_block(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        body = {"choices": [{"message": {"content": '```\n[{"a": 1}]\n```'}}]}
        return httpx.Response(200, json=body)

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    result = await provider.generate(_request())
    assert result.text == '[{"a": 1}]'


@pytest.mark.asyncio
async def test_openai_compat_provider_request_body_never_sends_response_format(monkeypatch):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["json"] = json_module.loads(request.content)
        captured["headers"] = request.headers
        body = {"choices": [{"message": {"content": "{}"}}]}
        return httpx.Response(200, json=body)

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider(api_key="the-bearer-key")
    await provider.generate(_request(prompt="write me a script", json_schema={"type": "object"}))

    sent = captured["json"]
    assert "response_format" not in sent
    assert sent["reasoning"] == {"exclude": True}
    assert sent["messages"] == [{"role": "user", "content": "write me a script"}]
    assert sent["model"] == "test/model"
    assert captured["headers"]["authorization"] == "Bearer the-bearer-key"


# --- error mapping ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_openai_compat_provider_200_with_error_body_is_unavailable(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"error": {"message": "Service temporarily overloaded", "code": 503}})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    with pytest.raises(ProviderUnavailableError) as exc_info:
        await provider.generate(_request())
    # PM review C1: for a 200-with-error body, upstream_status is the body's own
    # numeric code (503), not the literal transport-level 200.
    assert exc_info.value.upstream_status == 503


@pytest.mark.asyncio
async def test_openai_compat_provider_200_with_error_body_code_429_is_rate_limit(monkeypatch):
    """PM review C1: a 200-with-error body whose error code is 429 is a rate
    limit, not a generic overload -- distinct from other 200-with-error bodies
    so 18.4 can report rate-limited vs overloaded separately (D22 input)."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"error": {"message": "rate limited", "code": 429}})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    with pytest.raises(ProviderRateLimitError) as exc_info:
        await provider.generate(_request())
    assert exc_info.value.upstream_status == 429


@pytest.mark.asyncio
async def test_openai_compat_provider_http_429_is_rate_limit(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "rate limited", "code": 429}})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    with pytest.raises(ProviderRateLimitError) as exc_info:
        await provider.generate(_request())
    assert exc_info.value.upstream_status == 429


@pytest.mark.parametrize("status", [500, 502, 503])
@pytest.mark.asyncio
async def test_openai_compat_provider_5xx_is_unavailable(monkeypatch, status):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"error": {"message": "overloaded"}})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    with pytest.raises(ProviderUnavailableError) as exc_info:
        await provider.generate(_request())
    assert exc_info.value.upstream_status == status


@pytest.mark.parametrize("status", [401, 402, 403, 404])
@pytest.mark.asyncio
async def test_openai_compat_provider_config_error_statuses_are_auth_error(monkeypatch, status):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"error": {"message": "rejected"}})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    with pytest.raises(ProviderAuthError) as exc_info:
        await provider.generate(_request())
    assert exc_info.value.upstream_status == status


@pytest.mark.asyncio
async def test_openai_compat_provider_uncategorized_status_is_invalid_response(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"message": "bad request"}})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    with pytest.raises(ProviderInvalidResponseError) as exc_info:
        await provider.generate(_request())
    assert exc_info.value.upstream_status == 400


@pytest.mark.asyncio
async def test_openai_compat_provider_missing_choices_is_invalid_response(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    with pytest.raises(ProviderInvalidResponseError) as exc_info:
        await provider.generate(_request())
    assert exc_info.value.upstream_status == 200


@pytest.mark.asyncio
async def test_openai_compat_provider_empty_content_is_invalid_response(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": ""}}]})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    with pytest.raises(ProviderInvalidResponseError) as exc_info:
        await provider.generate(_request())
    assert exc_info.value.upstream_status == 200


@pytest.mark.asyncio
async def test_openai_compat_provider_connect_timeout_is_timeout_error(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    with pytest.raises(ProviderTimeoutError) as exc_info:
        await provider.generate(_request())
    assert exc_info.value.upstream_status is None


@pytest.mark.asyncio
async def test_openai_compat_provider_connect_error_is_unavailable(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    with pytest.raises(ProviderUnavailableError) as exc_info:
        await provider.generate(_request())
    assert exc_info.value.upstream_status is None


@pytest.mark.asyncio
async def test_openai_compat_provider_no_api_key_is_auth_error_and_makes_no_call(monkeypatch):
    called = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        called["count"] += 1
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider(api_key="")
    with pytest.raises(ProviderAuthError) as exc_info:
        await provider.generate(_request())
    assert called["count"] == 0
    assert exc_info.value.upstream_status is None


# --- key safety (required by the plan, PM review C2) ------------------------------------


@pytest.mark.asyncio
async def test_openai_compat_provider_never_leaks_key_when_401_body_echoes_it(monkeypatch, caplog):
    """PM review C2: some upstreams echo (part of) the key back in an error
    body -- a 401 whose JSON body contains the marker key must still never
    surface it in the raised exception message or in any log record. A
    separate assertion in the success-path test confirms the key *is*
    actually sent on the wire, so this isn't a false pass from a provider
    that silently never uses the key at all."""
    marker = "SECRET_OPENROUTER_KEY_MARKER_98765"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": f"invalid key: {marker}", "code": 401}})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider(api_key=marker)
    with caplog.at_level("DEBUG"):
        with pytest.raises(ProviderAuthError) as exc_info:
            await provider.generate(_request())
    assert marker not in str(exc_info.value)
    assert marker not in caplog.text


@pytest.mark.asyncio
async def test_openai_compat_provider_never_leaks_key_on_a_plain_500(monkeypatch, caplog):
    """The more ordinary case: the key never appears in any exception message
    or log record even when the error body doesn't mention it at all."""
    marker = "SECRET_OPENROUTER_KEY_MARKER_98765"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": {"message": "internal error"}})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider(api_key=marker)
    with caplog.at_level("DEBUG"):
        with pytest.raises(ProviderUnavailableError) as exc_info:
            await provider.generate(_request())
    assert marker not in str(exc_info.value)
    assert marker not in caplog.text


@pytest.mark.asyncio
async def test_openai_compat_provider_success_path_really_sends_the_key(monkeypatch):
    marker = "SECRET_OPENROUTER_KEY_MARKER_98765"
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers["authorization"]
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider(api_key=marker)
    await provider.generate(_request())
    assert captured["authorization"] == f"Bearer {marker}"


@pytest.mark.asyncio
async def test_openai_compat_provider_never_logs_prompt_body(monkeypatch, caplog):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    secret_prompt = "SECRET_PROMPT_MARKER_12345"
    with caplog.at_level("DEBUG"):
        await provider.generate(_request(prompt=secret_prompt))
    assert secret_prompt not in caplog.text


# --- Task 18.6 (D27): model chain ------------------------------------------------------


def test_parse_fallback_models_splits_strips_and_drops_empties():
    assert parse_fallback_models("a/b:free, c/d:free ,, e/f:free") == ["a/b:free", "c/d:free", "e/f:free"]


def test_parse_fallback_models_empty_string_is_empty_list():
    assert parse_fallback_models("") == []


@pytest.mark.asyncio
async def test_openai_compat_provider_sends_models_array_when_fallback_models_set(monkeypatch):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["json"] = json_module.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider(fallback_models=["fallback/one:free", "fallback/two:free"])
    await provider.generate(_request())

    assert captured["json"]["models"] == ["test/model", "fallback/one:free", "fallback/two:free"]
    assert "model" not in captured["json"]


@pytest.mark.asyncio
async def test_openai_compat_provider_sends_plain_model_when_no_fallback_models(monkeypatch):
    """Regression: the default (empty fallback_models) request shape is unchanged."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["json"] = json_module.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    await provider.generate(_request())

    assert captured["json"]["model"] == "test/model"
    assert "models" not in captured["json"]


@pytest.mark.asyncio
async def test_openai_compat_provider_records_the_model_that_actually_answered(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        body = {"choices": [{"message": {"content": "ok"}}], "model": "fallback/two:free"}
        return httpx.Response(200, json=body)

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider(fallback_models=["fallback/one:free", "fallback/two:free"])
    result = await provider.generate(_request())

    assert result.model == "fallback/two:free"


@pytest.mark.asyncio
async def test_openai_compat_provider_falls_back_to_configured_model_when_response_omits_it(monkeypatch):
    """Backward compatibility: every existing mock response (including all the
    tests above this section) has no top-level "model" key at all."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    result = await provider.generate(_request())

    assert result.model == "test/model"


# --- Task 18.6 (D27): daily-cap 429 -> ProviderDailyQuotaError -------------------------


_REAL_DAILY_QUOTA_BODY_SHAPE = {
    "error": {
        "message": "Rate limit exceeded: free-models-per-day. Please wait before retrying, or add "
        "credits to increase your rate limit.",
        "code": 429,
        "metadata": {"limit_source": "openrouter_free_tier_daily", "user_id": "synthetic-test-user"},
    }
}


@pytest.mark.asyncio
async def test_openai_compat_provider_daily_cap_429_is_provider_daily_quota_error(monkeypatch):
    reset_epoch_ms = 1_900_000_000_000  # synthetic, far future -- never a real timestamp

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json=_REAL_DAILY_QUOTA_BODY_SHAPE,
            headers={
                "X-RateLimit-Limit": "50",
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_epoch_ms),
            },
        )

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    with pytest.raises(ProviderDailyQuotaError) as exc_info:
        await provider.generate(_request())
    assert exc_info.value.reset_at_epoch_seconds == reset_epoch_ms / 1000.0
    assert isinstance(exc_info.value, ProviderRateLimitError)  # still a rate-limit subtype
    assert exc_info.value.upstream_status == 429


@pytest.mark.asyncio
async def test_openai_compat_provider_daily_cap_429_falls_back_to_next_utc_midnight_when_reset_header_missing(
    monkeypatch,
):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json=_REAL_DAILY_QUOTA_BODY_SHAPE)  # no X-RateLimit-Reset header

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    before = datetime.now(timezone.utc)
    with pytest.raises(ProviderDailyQuotaError) as exc_info:
        await provider.generate(_request())
    reset_at = datetime.fromtimestamp(exc_info.value.reset_at_epoch_seconds, tz=timezone.utc)
    assert reset_at > before
    assert reset_at.hour == 0 and reset_at.minute == 0 and reset_at.second == 0
    assert (reset_at - before) <= timedelta(days=1)


@pytest.mark.asyncio
async def test_openai_compat_provider_plain_429_is_not_daily_quota_error(monkeypatch):
    """Regression guard: an ordinary 429 (no daily-quota signal) still raises
    the plain ProviderRateLimitError, not the new subtype."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "rate limited", "code": 429}})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    with pytest.raises(ProviderRateLimitError) as exc_info:
        await provider.generate(_request())
    assert not isinstance(exc_info.value, ProviderDailyQuotaError)


@pytest.mark.asyncio
async def test_openai_compat_provider_daily_cap_429_detected_by_message_substring_without_metadata(monkeypatch):
    """Backstop path: metadata.limit_source absent, but the message still names
    free-models-per-day."""

    def handler(request: httpx.Request) -> httpx.Response:
        body = {"error": {"message": "Rate limit exceeded: free-models-per-day.", "code": 429}}
        return httpx.Response(429, json=body, headers={"X-RateLimit-Reset": "1900000000000"})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    with pytest.raises(ProviderDailyQuotaError):
        await provider.generate(_request())


# --- Task 18.8 (D28, Amendment F): Gemini vendor + array-wrapped error bodies -----------


_GEMINI_RESOURCE_EXHAUSTED_DICT = {
    "error": {"code": 429, "message": "Resource has been exhausted (e.g. check quota).", "status": "RESOURCE_EXHAUSTED"}
}
# Amendment F: some real Gemini error bodies wrap the error object in a JSON array.
_GEMINI_RESOURCE_EXHAUSTED_ARRAY = [_GEMINI_RESOURCE_EXHAUSTED_DICT]


@pytest.mark.asyncio
async def test_gemini_vendor_resource_exhausted_dict_shape_is_daily_quota_error(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json=_GEMINI_RESOURCE_EXHAUSTED_DICT)

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider(vendor="gemini")
    before = datetime.now(timezone.utc)
    with pytest.raises(ProviderDailyQuotaError) as exc_info:
        await provider.generate(_request())
    # No X-RateLimit-Reset header on Gemini -- always the next midnight
    # America/Los_Angeles (Amendment F), which is always in the future.
    reset_at = datetime.fromtimestamp(exc_info.value.reset_at_epoch_seconds, tz=timezone.utc)
    assert reset_at > before


@pytest.mark.asyncio
async def test_gemini_vendor_resource_exhausted_array_wrapped_shape_is_daily_quota_error(monkeypatch):
    """The exact real-world shape Amendment F called out: `[{"error": {...}}]`
    instead of `{"error": {...}}`."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json=_GEMINI_RESOURCE_EXHAUSTED_ARRAY)

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider(vendor="gemini")
    with pytest.raises(ProviderDailyQuotaError):
        await provider.generate(_request())


@pytest.mark.asyncio
async def test_gemini_vendor_resets_at_next_midnight_los_angeles(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json=_GEMINI_RESOURCE_EXHAUSTED_DICT)

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider(vendor="gemini")
    with pytest.raises(ProviderDailyQuotaError) as exc_info:
        await provider.generate(_request())
    reset_at_la = datetime.fromtimestamp(exc_info.value.reset_at_epoch_seconds, tz=ZoneInfo("America/Los_Angeles"))
    assert reset_at_la.hour == 0 and reset_at_la.minute == 0 and reset_at_la.second == 0


@pytest.mark.asyncio
async def test_gemini_vendor_404_not_found_is_auth_error_config_error(monkeypatch):
    """Amendment F: NOT_FOUND/404 (a real observed Gemini response, e.g.
    gemini-2.5-flash being retired) -> a config error, fail fast -- already
    handled by the existing generic 401/402/403/404 branch, unchanged by the
    Gemini vendor addition."""

    def handler(request: httpx.Request) -> httpx.Response:
        body = {"error": {"code": 404, "message": "models/gemini-2.5-flash is not found", "status": "NOT_FOUND"}}
        return httpx.Response(404, json=body)

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider(vendor="gemini")
    with pytest.raises(ProviderAuthError):
        await provider.generate(_request())


@pytest.mark.asyncio
async def test_gemini_vendor_503_unavailable_is_transient(monkeypatch):
    """Amendment F: UNAVAILABLE/503 -> transient -- already handled by the
    existing generic 5xx branch, unchanged by the Gemini vendor addition."""

    def handler(request: httpx.Request) -> httpx.Response:
        body = {"error": {"code": 503, "message": "The model is overloaded.", "status": "UNAVAILABLE"}}
        return httpx.Response(503, json=body)

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider(vendor="gemini")
    with pytest.raises(ProviderUnavailableError):
        await provider.generate(_request())


@pytest.mark.asyncio
async def test_generic_vendor_never_detects_daily_quota_even_with_an_openrouter_shaped_body(monkeypatch):
    """OpenCode Zen (vendor="generic") -- even a 429 body that looks exactly
    like OpenRouter's daily-cap shape must NOT be classified as a daily quota
    for a generic-vendor provider; it stays an ordinary ProviderRateLimitError,
    handled by the router's normal threshold/cooldown circuit path."""

    def handler(request: httpx.Request) -> httpx.Response:
        body = {"error": {"message": "Rate limit exceeded: free-models-per-day.", "code": 429}}
        return httpx.Response(429, json=body, headers={"X-RateLimit-Reset": "1900000000000"})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider(vendor="generic")
    with pytest.raises(ProviderRateLimitError) as exc_info:
        await provider.generate(_request())
    assert not isinstance(exc_info.value, ProviderDailyQuotaError)


@pytest.mark.asyncio
async def test_array_wrapped_error_body_is_parsed_on_a_plain_5xx_too(monkeypatch):
    """The array-wrap fix applies to every error-parsing path, not just the
    daily-quota one -- _error_message must also handle it (affects the
    exception's message text, exercised here via a 5xx)."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json=[{"error": {"code": 503, "message": "overloaded"}}])

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider(vendor="gemini")
    with pytest.raises(ProviderUnavailableError) as exc_info:
        await provider.generate(_request())
    assert "overloaded" in str(exc_info.value)


@pytest.mark.asyncio
async def test_array_wrapped_error_body_on_a_200_response_is_parsed(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"error": {"code": 429, "message": "rate limited"}}])

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    with pytest.raises(ProviderRateLimitError):
        await provider.generate(_request())
