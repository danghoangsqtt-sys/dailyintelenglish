"""Pydantic models for video generation requests/responses (Task 1.7, Sub-task 1.7a)."""

from typing import Literal

from pydantic import BaseModel, field_validator

from app.core.constants import VIDEO_ASPECT_RATIOS
from app.services.video_service import VIDEO_TEMPLATE_IDS


class GenerateVideoRequest(BaseModel):
    """Request body for POST /api/projects/{id}/video/generate."""

    template_id: str
    aspect_ratio: str = "16:9"
    # Task 19.7 (D19.7-b): optional -- omitting it (every pre-Phase-19 client) resolves to
    # "ffmpeg" in video_service._resolve_renderer regardless. "remotion" only actually takes
    # effect when the DIE_VIDEO_RENDERER kill switch already allows it.
    renderer: Literal["ffmpeg", "remotion"] = "ffmpeg"
    # Task 20.2d (D20.2d-a/b): caption treatment for the Remotion path only -- the ffmpeg
    # path ignores it. "outline" (film-subtitle style) is the owner-preferred default.
    caption_style: Literal["outline", "box", "shade"] = "outline"
    # Phase 30 (ENH-021): what is behind the captions in an Enhanced render. "illustrated" = the drawn shots (before);
    # the podcast modes need no shots: a black screen, or one still of a scene's plate; Phase 32: the two characters as talking
    # sprites over the scene plates ("podcast_sprites", needs the cast characters' sprite sets).
    visual_mode: Literal["illustrated", "podcast_black", "podcast_still", "podcast_sprites"] = "illustrated"
    still_scene_id: str | None = None

    @field_validator("template_id")
    @classmethod
    def validate_template_id(cls, value: str) -> str:
        if value not in VIDEO_TEMPLATE_IDS:
            raise ValueError(f"template_id must be one of {VIDEO_TEMPLATE_IDS}")
        return value

    @field_validator("aspect_ratio")
    @classmethod
    def validate_aspect_ratio(cls, value: str) -> str:
        if value not in VIDEO_ASPECT_RATIOS:
            raise ValueError(f"aspect_ratio must be one of {VIDEO_ASPECT_RATIOS}")
        return value


class VideoJobOut(BaseModel):
    """A project's video generation job status/result."""

    project_id: str
    status: str
    mode: str
    mp4_path: str | None = None
    mp4_path_vertical: str | None = None
    srt_path: str | None = None
    background_image: str | None = None
    error_message: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
