"""Pydantic models for TTS preview requests."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.core.constants import (
    ACCENTS, TTS_SPEED_MAX, TTS_SPEED_MIN, VOICE_PREVIEW_MAX_TEXT_LENGTH, VOICE_PREVIEW_SAMPLE_TEXT,
)


class PreviewLineRequest(BaseModel):
    """Request body for POST /api/projects/{id}/tts/preview."""

    line_id: str = Field(min_length=1)
    reuse_cached: bool = False


class VoiceInfo(BaseModel):
    """Normalized provider identity; no invented styles or unsupported engine labels."""

    engine: Literal["edge_tts"] = "edge_tts"
    voice_id: str = Field(min_length=1, max_length=80, pattern=r"^en-[A-Za-z0-9-]+Neural$")
    name: str = Field(min_length=1, max_length=300)
    locale: str = Field(min_length=3, max_length=35, pattern=r"^en-")
    gender: Literal["male", "female", "neutral"]


class VoiceCatalog(BaseModel):
    """Catalog metadata also validates last-good cache contents."""

    voices: list[VoiceInfo]
    fetched_at: str
    stale: bool


class VoiceParameters(BaseModel):
    """Existing synthesis controls, shared by auditions and the picker."""

    speed: float = Field(default=1.0, ge=TTS_SPEED_MIN, le=TTS_SPEED_MAX)
    pitch: float = Field(default=0.0, ge=-1.0, le=1.0)
    volume: float = Field(default=1.0, ge=0.0, le=2.0)


class VoicePreviewRequest(VoiceParameters):
    """An audition never accepts a project or line identifier."""

    model_config = ConfigDict(extra="forbid")

    engine: Literal["edge_tts", "omnivoice"] = "edge_tts"
    voice_id: str | None = Field(default=None, min_length=1, max_length=80)
    gender: Literal["male", "female", "neutral"] = "neutral"
    accent: str = "american"
    voice_description: str = Field(default="", max_length=500)
    text: str = Field(default=VOICE_PREVIEW_SAMPLE_TEXT, min_length=1, max_length=VOICE_PREVIEW_MAX_TEXT_LENGTH)

    @model_validator(mode="after")
    def engine_fields(self):
        if self.engine == "edge_tts" and not self.voice_id:
            raise ValueError("Select an Edge TTS voice to preview.")
        if self.accent not in ACCENTS:
            raise ValueError(f"accent must be one of {ACCENTS}")
        return self
        return self

    @field_validator("text")
    @classmethod
    def nonblank_text(cls, value: str) -> str:
        """Reject blank samples before any provider call."""
        value = value.strip()
        if not value:
            raise ValueError("Enter a sentence to preview.")
        return value


class VoicePreviewResult(BaseModel):
    """Opaque, local audition media reference and the voice that actually produced it."""

    id: str
    voice: VoiceInfo | dict
    audio_url: str
    parameters: VoiceParameters
    expires_in_seconds: int
