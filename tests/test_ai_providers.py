"""Tests for the Ollama and Gemini provider adapters (httpx.MockTransport, no network)."""

import httpx
import pytest

from app.core.exceptions import (
    ProviderAuthError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.services.ai import gemini_provider as gemini_provider_module
from app.services.ai import ollama_provider as ollama_provider_module
from app.services.ai.contracts import GenerationRequest
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.ollama_provider import OllamaProvider, validate_loopback_url


def _request(**overrides) -> GenerationRequest:
    defaults = {"prompt": "hello", "deadline_seconds": 30, "purpose": "test"}
    defaults.update(overrides)
    return GenerationRequest(**defaults)


def _install_mock_transport(monkeypatch, module, handler) -> None:
    """Patch `module.httpx.AsyncClient` to route through a MockTransport for this
    test only (`monkeypatch` restores the real class automatically at teardown)."""
    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def _factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(module.httpx, "AsyncClient", _factory)


# --- validate_loopback_url ---------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:11434",  # wrong scheme
        "http://0.0.0.0:11434",  # not loopback
        "http://evil.example.com:11434",  # not loopback
        "http://user:pass@127.0.0.1:11434",  # credentials
        "http://127.0.0.1:11434/extra",  # path
        "http://127.0.0.1:11434?x=1",  # query
        "http://127.0.0.1",  # missing port
    ],
)
def test_validate_loopback_url_rejects_unsafe_urls(url):
    with pytest.raises(ValueError):
        validate_loopback_url(url)


def test_validate_loopback_url_accepts_localhost():
    assert validate_loopback_url("http://127.0.0.1:11434/") == "http://127.0.0.1:11434"


# --- OllamaProvider -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_ollama_provider_success(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": "{}", "eval_count": 42})

    _install_mock_transport(monkeypatch, ollama_provider_module, handler)
    provider = OllamaProvider(base_url="http://127.0.0.1:11434", model="qwen3.5:9b", num_ctx=16384)
    result = await provider.generate(_request())
    assert result.text == "{}"
    assert result.provider == "ollama"
    assert result.tokens_used == 42
    assert result.attempt == 1


@pytest.mark.asyncio
async def test_ollama_provider_missing_model_returns_unavailable(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="model not found")

    _install_mock_transport(monkeypatch, ollama_provider_module, handler)
    provider = OllamaProvider(base_url="http://127.0.0.1:11434", model="qwen3.5:9b", num_ctx=16384)
    with pytest.raises(ProviderUnavailableError):
        await provider.generate(_request())


@pytest.mark.asyncio
async def test_ollama_provider_server_error_is_invalid_response(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    _install_mock_transport(monkeypatch, ollama_provider_module, handler)
    provider = OllamaProvider(base_url="http://127.0.0.1:11434", model="qwen3.5:9b", num_ctx=16384)
    with pytest.raises(ProviderInvalidResponseError):
        await provider.generate(_request())


@pytest.mark.asyncio
async def test_ollama_provider_connect_error_is_unavailable(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    _install_mock_transport(monkeypatch, ollama_provider_module, handler)
    provider = OllamaProvider(base_url="http://127.0.0.1:11434", model="qwen3.5:9b", num_ctx=16384)
    with pytest.raises(ProviderUnavailableError):
        await provider.generate(_request())


@pytest.mark.asyncio
async def test_ollama_provider_timeout_is_timeout_error(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    _install_mock_transport(monkeypatch, ollama_provider_module, handler)
    provider = OllamaProvider(base_url="http://127.0.0.1:11434", model="qwen3.5:9b", num_ctx=16384)
    with pytest.raises(ProviderTimeoutError):
        await provider.generate(_request())


@pytest.mark.asyncio
async def test_ollama_provider_malformed_body_is_invalid_response(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    _install_mock_transport(monkeypatch, ollama_provider_module, handler)
    provider = OllamaProvider(base_url="http://127.0.0.1:11434", model="qwen3.5:9b", num_ctx=16384)
    with pytest.raises(ProviderInvalidResponseError):
        await provider.generate(_request())


@pytest.mark.asyncio
async def test_ollama_provider_never_logs_prompt_body(monkeypatch, caplog):
    """The provider itself must never log the prompt text (router logging is
    covered separately in test_ai_router.py)."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": "ok"})

    _install_mock_transport(monkeypatch, ollama_provider_module, handler)
    provider = OllamaProvider(base_url="http://127.0.0.1:11434", model="qwen3.5:9b", num_ctx=16384)
    secret_prompt = "SECRET_PROMPT_MARKER_12345"
    with caplog.at_level("DEBUG"):
        await provider.generate(_request(prompt=secret_prompt))
    assert secret_prompt not in caplog.text


# --- GeminiProvider -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gemini_provider_no_api_key_is_auth_error():
    provider = GeminiProvider(api_key="", model="gemini-3.8-flash")
    with pytest.raises(ProviderAuthError):
        await provider.generate(_request())


@pytest.mark.asyncio
async def test_gemini_provider_success(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        body = {
            "candidates": [{"content": {"parts": [{"text": '{"ok": true}'}]}}],
            "usageMetadata": {"totalTokenCount": 99},
        }
        return httpx.Response(200, json=body)

    _install_mock_transport(monkeypatch, gemini_provider_module, handler)
    provider = GeminiProvider(api_key="test-key", model="gemini-3.8-flash")
    result = await provider.generate(_request())
    assert result.text == '{"ok": true}'
    assert result.tokens_used == 99
    assert result.provider == "gemini"


@pytest.mark.asyncio
async def test_gemini_provider_401_is_auth_error_and_never_leaks_key(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid key"})

    _install_mock_transport(monkeypatch, gemini_provider_module, handler)
    provider = GeminiProvider(api_key="super-secret-key", model="gemini-3.8-flash")
    with pytest.raises(ProviderAuthError) as exc_info:
        await provider.generate(_request())
    assert "super-secret-key" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_gemini_provider_429_is_rate_limit(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": "quota exceeded"})

    _install_mock_transport(monkeypatch, gemini_provider_module, handler)
    provider = GeminiProvider(api_key="test-key", model="gemini-3.8-flash")
    with pytest.raises(ProviderRateLimitError):
        await provider.generate(_request())


@pytest.mark.asyncio
async def test_gemini_provider_503_is_unavailable(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "overloaded"})

    _install_mock_transport(monkeypatch, gemini_provider_module, handler)
    provider = GeminiProvider(api_key="test-key", model="gemini-3.8-flash")
    with pytest.raises(ProviderUnavailableError):
        await provider.generate(_request())


@pytest.mark.asyncio
async def test_gemini_provider_400_is_invalid_response(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "bad request"})

    _install_mock_transport(monkeypatch, gemini_provider_module, handler)
    provider = GeminiProvider(api_key="test-key", model="gemini-3.8-flash")
    with pytest.raises(ProviderInvalidResponseError):
        await provider.generate(_request())


@pytest.mark.asyncio
async def test_gemini_provider_malformed_shape_is_invalid_response(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    _install_mock_transport(monkeypatch, gemini_provider_module, handler)
    provider = GeminiProvider(api_key="test-key", model="gemini-3.8-flash")
    with pytest.raises(ProviderInvalidResponseError):
        await provider.generate(_request())
