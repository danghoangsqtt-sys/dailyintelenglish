"""Pydantic models for app-level settings requests (Task 12.1)."""

from pydantic import BaseModel, Field


class GeminiApiKeyUpdate(BaseModel):
    """Request body for PUT /api/settings."""

    gemini_api_key: str = Field(min_length=1)
