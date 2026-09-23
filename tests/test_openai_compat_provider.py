"""Tests for OpenAICompatProvider (Task 18.1, ENH-011). httpx.MockTransport only --
never a real network call. The owner's OpenRouter key in .env is for Gate B-9, not
development or tests.
"""

import json as json_module

import httpx
import pytest

from app.core.exceptions import (
    ProviderAuthError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.services.ai import openai_compat_provider as openai_compat_provider_module
from app.services.ai.contracts import GenerationRequest
from app.services.ai.openai_compat_provider import OpenAICompatProvider, validate_openai_compat_base_url


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
    with pytest.raises(ProviderUnavailableError):
        await provider.generate(_request())


@pytest.mark.asyncio
async def test_openai_compat_provider_200_with_error_body_code_429_is_rate_limit(monkeypatch):
    """PM review C1: a 200-with-error body whose error code is 429 is a rate
    limit, not a generic overload -- distinct from other 200-with-error bodies
    so 18.4 can report rate-limited vs overloaded separately (D22 input)."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"error": {"message": "rate limited", "code": 429}})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    with pytest.raises(ProviderRateLimitError):
        await provider.generate(_request())


@pytest.mark.asyncio
async def test_openai_compat_provider_http_429_is_rate_limit(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "rate limited", "code": 429}})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    with pytest.raises(ProviderRateLimitError):
        await provider.generate(_request())


@pytest.mark.parametrize("status", [500, 502, 503])
@pytest.mark.asyncio
async def test_openai_compat_provider_5xx_is_unavailable(monkeypatch, status):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"error": {"message": "overloaded"}})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    with pytest.raises(ProviderUnavailableError):
        await provider.generate(_request())


@pytest.mark.parametrize("status", [401, 402, 403, 404])
@pytest.mark.asyncio
async def test_openai_compat_provider_config_error_statuses_are_auth_error(monkeypatch, status):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"error": {"message": "rejected"}})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    with pytest.raises(ProviderAuthError):
        await provider.generate(_request())


@pytest.mark.asyncio
async def test_openai_compat_provider_uncategorized_status_is_invalid_response(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"message": "bad request"}})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    with pytest.raises(ProviderInvalidResponseError):
        await provider.generate(_request())


@pytest.mark.asyncio
async def test_openai_compat_provider_missing_choices_is_invalid_response(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    with pytest.raises(ProviderInvalidResponseError):
        await provider.generate(_request())


@pytest.mark.asyncio
async def test_openai_compat_provider_empty_content_is_invalid_response(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": ""}}]})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    with pytest.raises(ProviderInvalidResponseError):
        await provider.generate(_request())


@pytest.mark.asyncio
async def test_openai_compat_provider_connect_timeout_is_timeout_error(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    with pytest.raises(ProviderTimeoutError):
        await provider.generate(_request())


@pytest.mark.asyncio
async def test_openai_compat_provider_connect_error_is_unavailable(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider()
    with pytest.raises(ProviderUnavailableError):
        await provider.generate(_request())


@pytest.mark.asyncio
async def test_openai_compat_provider_no_api_key_is_auth_error_and_makes_no_call(monkeypatch):
    called = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        called["count"] += 1
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    _install_mock_transport(monkeypatch, openai_compat_provider_module, handler)
    provider = _provider(api_key="")
    with pytest.raises(ProviderAuthError):
        await provider.generate(_request())
    assert called["count"] == 0


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
