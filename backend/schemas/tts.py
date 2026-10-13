"""Pydantic models for TTS preview requests."""

from pydantic import BaseModel, Field


class PreviewLineRequest(BaseModel):
    """Request body for POST /api/projects/{id}/tts/preview."""

    line_id: str = Field(min_length=1)
