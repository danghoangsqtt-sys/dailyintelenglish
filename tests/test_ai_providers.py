"""Tests for the Ollama provider adapter (httpx.MockTransport, no network).

The old Gemini provider adapter tests lived here too until Phase 18/Task 18.2
deleted `GeminiProvider` (D23 -- replaced by the generic `OpenAICompatProvider`,
whose own tests are in `tests/test_openai_compat_provider.py`, added in 18.1).
"""

import httpx
import pytest

from app.core.exceptions import ProviderInvalidResponseError, ProviderTimeoutError, ProviderUnavailableError
from app.services.ai import ollama_provider as ollama_provider_module
from app.services.ai.contracts import GenerationRequest
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
