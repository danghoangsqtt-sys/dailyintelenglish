"""Pydantic models for video generation requests/responses (Task 1.7, Sub-task 1.7a)."""

from pydantic import BaseModel, field_validator

from app.services.video_service import VIDEO_TEMPLATE_IDS


class GenerateVideoRequest(BaseModel):
    """Request body for POST /api/projects/{id}/video/generate."""

    template_id: str

    @field_validator("template_id")
    @classmethod
    def validate_template_id(cls, value: str) -> str:
        if value not in VIDEO_TEMPLATE_IDS:
            raise ValueError(f"template_id must be one of {VIDEO_TEMPLATE_IDS}")
        return value


class VideoJobOut(BaseModel):
    """A project's video generation job status/result."""

    project_id: str
    status: str
    mode: str
    mp4_path: str | None = None
    srt_path: str | None = None
    background_image: str | None = None
    error_message: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
