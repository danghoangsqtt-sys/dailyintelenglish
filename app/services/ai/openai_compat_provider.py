"""OpenAI-compatible adapter (OpenRouter, or any /chat/completions-shaped
endpoint): one HTTP call per `generate()`, no internal retry.

Every behaviour here is dictated by the real OpenRouter smoke test
(`docs/operations/enh011-nemotron-smoke.md`), not guessed: plain prompt-only
JSON (never `response_format` -- `json_schema` returned malformed JSON,
`json_object` breaks the array contract), `reasoning: {"exclude": true}`
(Nemotron reasons before answering; excluding it keeps that out of `content`),
and upstream errors that arrive as HTTP 200 with an `error` body.
"""

from __future__ import annotations

import hashlib
import re
import time
from urllib.parse import urlparse

import httpx

from app.core.exceptions import (
    ProviderAuthError,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.services.ai.contracts import GenerationRequest, GenerationResult

_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}

_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", re.DOTALL)


def validate_openai_compat_base_url(base_url: str) -> str:
    """`https` only, except loopback (a local self-hosted OpenAI-compatible
    server) -- and, unlike `ollama_provider.validate_loopback_url`, a path is
    allowed and expected (e.g. OpenRouter's `https://openrouter.ai/api/v1`),
    so this is intentionally not shared code with that function."""
    parsed = urlparse(base_url)
    if parsed.username or parsed.password:
        raise ValueError("OpenAI-compatible base URL cannot contain credentials")
    is_https = parsed.scheme == "https"
    is_loopback_http = parsed.scheme == "http" and parsed.hostname in _LOOPBACK_HOSTS
    if not (is_https or is_loopback_http):
        raise ValueError("OpenAI-compatible base URL must use HTTPS (or HTTP on loopback)")
    return base_url.rstrip("/")


def _strip_code_fences(text: str) -> str:
    """Strips a ```json ... ``` or bare ``` ... ``` wrapper, if present."""
    stripped = text.strip()
    match = _FENCE_RE.match(stripped)
    return match.group(1).strip() if match else stripped


def _extract_error_info(error_value: object) -> tuple[object, str]:
    """`error_value` is OpenRouter's `error` field -- a dict with `code`/
    `message`, or (seen on some upstreams) a plain string. Never returns more
    than 200 chars of the message, and never the raw response body."""
    if isinstance(error_value, dict):
        return error_value.get("code"), str(error_value.get("message", ""))[:200]
    return None, str(error_value)[:200]


class OpenAICompatProvider:
    """Provider adapter for an OpenAI-compatible `/chat/completions` endpoint."""

    name = "openai_compat"

    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 180.0) -> None:
        """Args:
        base_url: Must pass `validate_openai_compat_base_url`.
        api_key: Sent as `Authorization: Bearer <api_key>` -- never in the URL.
        model: The upstream model id (e.g. `nvidia/nemotron-3-super-120b-a12b:free`).
        timeout: Per-request httpx timeout in seconds (independent of the
            router's own `deadline_seconds` budget) -- 180s default reflects
            the smoke test's observed 8-296s latency spread; callers building
            from settings should pass the real configured value.
        """
        self._base_url = validate_openai_compat_base_url(base_url)
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    def _raise(
        self, exc: ProviderError, upstream_status: int | None, cause: BaseException | None = None
    ) -> None:
        """PM review C1: `upstream_status` is the real HTTP status this
        provider got back (or, for a 200-with-error body, that body's own
        numeric `code` -- e.g. OpenRouter's `{"error": {"code": 503}}` is far
        more useful to a caller than the literal transport-level 200). `None`
        for a case with no real HTTP response at all (timeout/unreachable).
        Set as a plain instance attribute -- `app/core/exceptions.py` is not
        touched, and `ProviderError` is not `status_code` here, since
        `AppError.status_code` already means the HTTP status *this app's own
        API* returns, a different thing entirely. `cause` preserves `raise ...
        from exc`-style chaining for the two httpx-exception call sites."""
        exc.upstream_status = upstream_status
        if cause is not None:
            raise exc from cause
        raise exc

    def _redact(self, message: str) -> str:
        """Backstop for invariant 31: some upstreams echo (part of) the
        request back in an error body, including the key. Every exception
        message this provider raises passes through here before being
        raised, regardless of whether the key is expected to appear."""
        if self._api_key and self._api_key in message:
            return message.replace(self._api_key, "[REDACTED]")
        return message

    def _format_error(self, prefix: str, status: int, code: object, message: str) -> str:
        """Builds a message from the HTTP status plus, at most, an upstream
        `error` field's `code`/`message` -- never the raw response body (some
        upstreams echo request data, including the key, elsewhere in the
        body). Always passed through `_redact` as a backstop."""
        text = f"{prefix} (HTTP {status}"
        if code is not None:
            text += f", code={code}"
        text += ")"
        if message:
            text += f": {message}"
        return self._redact(text)

    def _error_message(self, response: httpx.Response, prefix: str) -> str:
        """Same as `_format_error`, but parses `code`/`message` out of
        `response` itself -- for a non-200 status, where the body (if any)
        hasn't already been parsed by the caller."""
        try:
            data = response.json()
        except ValueError:
            data = None
        code, message = (None, "")
        if isinstance(data, dict) and "error" in data:
            code, message = _extract_error_info(data["error"])
        return self._format_error(prefix, response.status_code, code, message)

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Make exactly one `/chat/completions` call. No internal retry loop."""
        if not self._api_key:
            self._raise(ProviderAuthError("OpenAI-compatible API key is not configured"), None)

        prompt_hash = hashlib.sha256(request.prompt.encode("utf-8")).hexdigest()[:16]
        payload: dict[str, object] = {
            "model": self._model,
            "messages": [{"role": "user", "content": request.prompt}],
            "reasoning": {"exclude": True},
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        headers = {"Authorization": f"Bearer {self._api_key}"}

        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(f"{self._base_url}/chat/completions", json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            self._raise(
                ProviderTimeoutError(self._redact(f"OpenAI-compatible request timed out: {exc}")), None, cause=exc
            )
        except httpx.RequestError as exc:
            self._raise(
                ProviderUnavailableError(self._redact(f"OpenAI-compatible endpoint is unreachable: {exc}")),
                None,
                cause=exc,
            )
        latency_ms = (time.perf_counter() - started) * 1000

        status = response.status_code

        if status in (401, 402, 403, 404):
            self._raise(
                ProviderAuthError(self._error_message(response, "OpenAI-compatible endpoint rejected the request")),
                status,
            )

        if status == 200:
            try:
                data = response.json()
            except ValueError as exc:
                self._raise(
                    ProviderInvalidResponseError(self._redact(f"Unexpected response body: {exc}")), status, cause=exc
                )

            if isinstance(data, dict) and "error" in data:
                code, message = _extract_error_info(data["error"])
                text = self._format_error("OpenAI-compatible endpoint returned an error body", status, code, message)
                error_status = code if isinstance(code, int) else None
                if code == 429:
                    self._raise(ProviderRateLimitError(text), error_status)
                self._raise(ProviderUnavailableError(text), error_status)

            try:
                content = data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as exc:
                self._raise(
                    ProviderInvalidResponseError(self._redact(f"Unexpected response shape: {exc}")),
                    status,
                    cause=exc,
                )
            if not content:
                self._raise(ProviderInvalidResponseError("OpenAI-compatible response had empty content"), status)

            text = _strip_code_fences(content)
            tokens_used = None
            usage = data.get("usage")
            if isinstance(usage, dict):
                tokens_used = usage.get("total_tokens")
            return GenerationResult(
                text=text,
                provider=self.name,
                model=self._model,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                attempt=1,
                prompt_hash=prompt_hash,
            )

        if status == 429:
            self._raise(
                ProviderRateLimitError(self._error_message(response, "OpenAI-compatible endpoint rate-limited")),
                status,
            )

        if 500 <= status < 600:
            self._raise(
                ProviderUnavailableError(
                    self._error_message(response, "OpenAI-compatible endpoint returned a server error")
                ),
                status,
            )

        self._raise(
            ProviderInvalidResponseError(
                self._error_message(response, "OpenAI-compatible endpoint returned an unexpected status")
            ),
            status,
        )
