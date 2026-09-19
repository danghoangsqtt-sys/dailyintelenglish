"""Gemini adapter: one HTTP call to the single stable configured model.

Deliberately does not implement `script_service.py`'s existing per-model
retry/backoff or multi-model `GEMINI_MODEL_FALLBACKS` chain -- that quota-spreading
behavior stays legacy-only until Task 13.4/13.5 decide whether to migrate it. This
gateway's "one visible stable Gemini fallback" (ADR-001) is a single model, one
attempt; retry/fallback policy across providers belongs to `AIRouter`, not here.
"""

from __future__ import annotations

import hashlib
import time

import httpx

from app.core.exceptions import (
    ProviderAuthError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.services.ai.contracts import GenerationRequest, GenerationResult

_GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiProvider:
    """Provider adapter for a single stable Gemini model."""

    name = "gemini"

    def __init__(self, api_key: str, model: str, timeout: float = 60.0) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Make exactly one `generateContent` call. No internal retry loop."""
        if not self._api_key:
            raise ProviderAuthError("Gemini API key is not configured")

        prompt_hash = hashlib.sha256(request.prompt.encode("utf-8")).hexdigest()[:16]
        generation_config: dict[str, object] = {"responseMimeType": "application/json"}
        if request.json_schema is not None:
            generation_config["responseJsonSchema"] = request.json_schema
        if request.temperature is not None:
            generation_config["temperature"] = request.temperature
        payload = {
            "contents": [{"parts": [{"text": request.prompt}]}],
            "generationConfig": generation_config,
        }
        url = _GEMINI_ENDPOINT.format(model=self._model)

        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, params={"key": self._api_key}, json=payload)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(f"Gemini request timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(f"Gemini is unreachable: {exc}") from exc
        latency_ms = (time.perf_counter() - started) * 1000

        if response.status_code in (401, 403):
            raise ProviderAuthError(f"Gemini rejected the API key (HTTP {response.status_code})")
        if response.status_code == 429:
            raise ProviderRateLimitError("Gemini rate/quota limit exceeded")
        if response.status_code == 503:
            raise ProviderUnavailableError("Gemini is temporarily overloaded (HTTP 503)")
        if response.status_code != 200:
            raise ProviderInvalidResponseError(
                f"Gemini returned HTTP {response.status_code}: {response.text[:200]}"
            )

        try:
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (ValueError, KeyError, IndexError) as exc:
            raise ProviderInvalidResponseError(f"Unexpected Gemini response shape: {exc}") from exc

        tokens_used = data.get("usageMetadata", {}).get("totalTokenCount")
        return GenerationResult(
            text=text,
            provider=self.name,
            model=self._model,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            attempt=1,
            prompt_hash=prompt_hash,
        )
