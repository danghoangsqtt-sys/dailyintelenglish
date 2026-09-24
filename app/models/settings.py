"""Pydantic models for app-level settings requests (Task 12.1, 13.6, 18.3)."""

from pydantic import BaseModel, Field

from app.core.constants import AI_MODES


class AIModeUpdate(BaseModel):
    """Request body for PUT /api/settings/ai-mode (Phase 13, ADR-001 kill switch)."""

    ai_mode: str = Field(pattern="^(" + "|".join(AI_MODES) + ")$")


class CloudSettingsUpdate(BaseModel):
    """Request body for PUT /api/settings/cloud (Task 18.3).

    Real validation (URL shape, non-empty-after-strip, length) happens in
    `settings_service.set_cloud_settings`, not here (PM review C2) -- these
    fields are deliberately unconstrained at the Pydantic level so a
    whitespace-only value doesn't produce a generic Pydantic error instead of
    the service's own specific message, and so `api_key` can never fail
    request validation in a way that would echo it back in a 422 body.
    """

    base_url: str
    model: str
    api_key: str | None = None


class CloudTestConnectionRequest(BaseModel):
    """Request body for POST /api/settings/cloud/test-connection (Task 18.3).

    Every field is optional -- an omitted one falls back to the currently
    effective `settings.OPENAI_COMPAT_*` value (see `settings_service.
    test_cloud_connection`), so a caller can test a partial change (e.g. just
    a new model) without retyping an already-saved key.
    """

    base_url: str | None = None
    model: str | None = None
    api_key: str | None = None
