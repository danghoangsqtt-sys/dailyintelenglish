"""Ollama adapter: one HTTP call to a loopback-only /api/generate, no internal retry.

Task 20.1: every generate call runs inside a GPU lease (`consumer="ollama"`,
`min_free_mb=0` -- wait for the card, never measure or evict), so qwen cannot load while
StyleTTS 2 or an image model is mid-inference (D20.1-c, owner-approved 2026-09-30). The
wait is bounded by the router's own per-phase `wait_for` budget, and a timeout surfaces
as the `ProviderTimeoutError` the router already handles. `unload_all_resident` is the
manager's eviction hook (D20.1-b).
"""

from __future__ import annotations

import hashlib
import logging
import time
from urllib.parse import urlparse

import httpx

from app.core.exceptions import (
    ProviderError,
    ProviderInvalidResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.services.ai.contracts import GenerationRequest, GenerationResult
from app.services.gpu_model_manager import get_gpu_manager

logger = logging.getLogger(__name__)

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

        async with get_gpu_manager().lease("ollama", min_free_mb=0):
            # Timed inside the lease: latency_ms stays the provider's own latency; the
            # lease wait is logged separately by the manager.
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

    async def list_resident_models(self) -> list[str]:
        """Names of the models Ollama currently holds in memory (`GET /api/ps`).

        Parsed defensively: an entry without a string `name` is skipped, and a body
        without a `models` list raises `ProviderInvalidResponseError`. The shape comes
        from Ollama's API docs and is to be confirmed live on the owner's machine
        (task-20.1.md D20.1-b).
        """
        try:
            async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:
                response = await client.get("/api/ps")
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(f"Ollama /api/ps timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(f"Ollama is unreachable: {exc}") from exc
        if response.status_code != 200:
            raise ProviderInvalidResponseError(f"Ollama /api/ps returned HTTP {response.status_code}")
        try:
            models = response.json()["models"]
        except (ValueError, KeyError, TypeError) as exc:
            raise ProviderInvalidResponseError(f"Unexpected Ollama /api/ps shape: {exc}") from exc
        if not isinstance(models, list):
            raise ProviderInvalidResponseError("Unexpected Ollama /api/ps shape: 'models' is not a list")
        return [entry["name"] for entry in models if isinstance(entry, dict) and isinstance(entry.get("name"), str)]

    async def unload(self, model: str) -> None:
        """Ask Ollama to drop `model` from memory now (`keep_alive: 0`, no prompt).

        This is Ollama's documented unload request (its FAQ, "How do I unload a model
        from memory?"; the CLI equivalent is `ollama stop`). It deliberately takes **no**
        GPU lease: it is only ever called by the manager while the evicting consumer
        already holds one.
        """
        try:
            async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:
                response = await client.post("/api/generate", json={"model": model, "keep_alive": 0})
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(f"Ollama unload of {model!r} timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(f"Ollama is unreachable: {exc}") from exc
        if response.status_code != 200:
            raise ProviderInvalidResponseError(f"Ollama unload of {model!r} returned HTTP {response.status_code}")

    async def unload_all_resident(self) -> list[str]:
        """The GPU manager's eviction hook: unload every resident model and return the
        names actually unloaded. **Never raises**: Ollama not running, an unexpected
        response shape, or a failed unload is logged and simply frees nothing. The
        manager then re-measures and lets the consumer fall back, instead of a GPU step
        crashing on an Ollama problem."""
        try:
            resident = await self.list_resident_models()
        except ProviderError as exc:
            logger.warning("ollama_evict_list_failed error=%s", type(exc).__name__)
            return []
        unloaded: list[str] = []
        for model in resident:
            try:
                await self.unload(model)
            except ProviderError as exc:
                logger.warning("ollama_evict_unload_failed model=%s error=%s", model, type(exc).__name__)
                continue
            unloaded.append(model)
        return unloaded
