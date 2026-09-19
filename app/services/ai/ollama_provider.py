"""Ollama adapter: one HTTP call to a loopback-only /api/generate, no internal retry."""

from __future__ import annotations

import hashlib
import time
from urllib.parse import urlparse

import httpx

from app.core.exceptions import (
    ProviderInvalidResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.services.ai.contracts import GenerationRequest, GenerationResult

_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def validate_loopback_url(base_url: str) -> str:
    """Reject anything but a plain HTTP loopback base URL (anti-SSRF).

    Mirrors `scripts/qualify_local_ai.py::validate_loopback_url` -- duplicated
    rather than imported, since that file is a standalone diagnostic script, not
    product code (Task 13.1's allowed files did not include `app/`).
    """
    parsed = urlparse(base_url)
    if parsed.scheme != "http" or parsed.hostname not in _LOOPBACK_HOSTS:
        raise ValueError("Ollama base URL must use HTTP on a loopback host")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Ollama base URL cannot contain credentials, query, or fragment")
    if parsed.path not in {"", "/"}:
        raise ValueError("Ollama base URL cannot contain a path")
    if parsed.port is None:
        raise ValueError("Ollama base URL must include an explicit port")
    return base_url.rstrip("/")


class OllamaProvider:
    """Provider adapter for a local loopback Ollama server."""

    name = "ollama"

    def __init__(self, base_url: str, model: str, num_ctx: int, timeout: float = 60.0) -> None:
        """Args:
        base_url: Must pass `validate_loopback_url` (e.g. `http://127.0.0.1:11434`).
        model: Exact local tag, e.g. `qwen3.5:9b`.
        num_ctx: Context window size passed as `options.num_ctx`.
        timeout: Per-request httpx timeout in seconds (independent of the
            router's own `deadline_seconds` budget).
        """
        self._base_url = validate_loopback_url(base_url)
        self._model = model
        self._num_ctx = num_ctx
        self._timeout = timeout

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Make exactly one `/api/generate` call. No internal retry loop."""
        prompt_hash = hashlib.sha256(request.prompt.encode("utf-8")).hexdigest()[:16]
        options: dict[str, object] = {"num_ctx": self._num_ctx}
        if request.temperature is not None:
            options["temperature"] = request.temperature
        payload: dict[str, object] = {
            "model": self._model,
            "prompt": request.prompt,
            "stream": False,
            "think": False,
            "options": options,
            "keep_alive": "5m",
        }
        if request.json_schema is not None:
            payload["format"] = request.json_schema

        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:
                response = await client.post("/api/generate", json=payload)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(f"Ollama request timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(f"Ollama is unreachable: {exc}") from exc
        latency_ms = (time.perf_counter() - started) * 1000

        if response.status_code == 404:
            raise ProviderUnavailableError(f"Ollama model is missing: {self._model!r}")
        if response.status_code != 200:
            raise ProviderInvalidResponseError(
                f"Ollama returned HTTP {response.status_code}: {response.text[:200]}"
            )

        try:
            data = response.json()
            text = data["response"]
        except (ValueError, KeyError) as exc:
            raise ProviderInvalidResponseError(f"Unexpected Ollama response shape: {exc}") from exc

        return GenerationResult(
            text=text,
            provider=self.name,
            model=self._model,
            tokens_used=data.get("eval_count"),
            latency_ms=latency_ms,
            attempt=1,
            prompt_hash=prompt_hash,
        )
