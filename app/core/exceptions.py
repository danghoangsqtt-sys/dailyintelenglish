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


class ScriptGenerationError(AppError):
    """Raised when the Gemini API fails or returns content violating script rules."""

    status_code = 502


class LearningGenerationError(AppError):
    """Raised when the Gemini API fails or returns content violating Learning Content rules."""

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
