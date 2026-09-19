"""Pydantic models for app-level settings requests (Task 12.1, Task 13.6)."""

from pydantic import BaseModel, Field

from app.core.constants import AI_MODES


class GeminiApiKeyUpdate(BaseModel):
    """Request body for PUT /api/settings."""

    gemini_api_key: str = Field(min_length=1)


class AIModeUpdate(BaseModel):
    """Request body for PUT /api/settings/ai-mode (Phase 13, ADR-001 kill switch)."""

    ai_mode: str = Field(pattern="^(" + "|".join(AI_MODES) + ")$")
