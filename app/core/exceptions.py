"""Typed exceptions raised by services. Routes never construct error responses directly."""


class AppError(Exception):
    """Base class for all application errors. Carries an HTTP status code."""

    status_code: int = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    status_code = 404


class ValidationError(AppError):
    """Raised when input fails a business-rule check beyond Pydantic schema validation."""

    status_code = 422


class ConflictError(AppError):
    """Raised when an optimistic write targets a stale resource revision."""

    status_code = 409


class ScriptGenerationError(AppError):
    """Raised when the Gemini API fails or returns content violating script rules."""

    status_code = 502


class LearningGenerationError(AppError):
    """Raised when the Gemini API fails or returns content violating Learning Content rules."""

    status_code = 502


class YouTubePackageGenerationError(AppError):
    """Raised when the Gemini API fails or returns content violating YouTube package rules."""

    status_code = 502


class TTSError(AppError):
    """Raised when all configured TTS engines fail to synthesize a line."""

    status_code = 502


class AudioMixError(AppError):
    """Raised when pydub/ffmpeg audio mixing fails."""

    status_code = 500


class VideoRenderError(AppError):
    """Raised when ffmpeg/LivePortrait video rendering fails."""

    status_code = 500


class ThumbnailGenerationError(AppError):
    """Raised when thumbnail suggestion, rendering, or persistence fails."""

    status_code = 502


class MusicUploadTooLargeError(AppError):
    """Raised when a music upload exceeds the configured size limit."""

    status_code = 413


class AvatarUploadTooLargeError(AppError):
    """Raised when a speaker avatar upload exceeds the configured size limit."""

    status_code = 413


class ProviderError(AppError):
    """Base class for all AI provider gateway errors (Phase 13)."""

    status_code = 502


class ProviderTimeoutError(ProviderError):
    """Raised when a provider call exceeds its request or router deadline."""


class ProviderAuthError(ProviderError):
    """Raised on a provider auth failure. Message never includes the key itself."""


class ProviderRateLimitError(ProviderError):
    """Raised when a provider reports rate/quota exhaustion (retryable)."""


class ProviderDailyQuotaError(ProviderRateLimitError):
    """Raised when a provider's account-wide daily free-tier cap is hit (Task
    18.6, D27) -- a `ProviderRateLimitError` subtype, but never worth
    retrying with backoff, since the quota will not refill within any retry
    window. Callers set a `reset_at_epoch_seconds` attribute (not a
    constructor field, same pattern as `OpenAICompatProvider`'s
    `upstream_status`)."""


class ProviderUnavailableError(ProviderError):
    """Raised when a provider is unreachable, down, or the model is missing."""


class ProviderInvalidResponseError(ProviderError):
    """Raised when a provider returns an unexpected shape or non-2xx status
    that isn't one of the more specific categories above."""


class SchemaValidationError(ProviderError):
    """Raised when a provider's response is structurally valid but fails JSON
    parsing or the caller's Pydantic schema. Message never echoes prompt/response
    content -- only error counts/field paths."""
