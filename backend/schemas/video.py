"""Pydantic models for video generation requests/responses (Task 1.7, Sub-task 1.7a)."""

from typing import Literal

from pydantic import BaseModel


class GenerateVideoRequest(BaseModel):
    """Request body for POST /api/projects/{id}/video/generate.

    Task 35.5 (D89): Remotion is the only renderer, so the old `template_id`, `aspect_ratio` and `renderer` fields are gone;
    a client that still sends them is not refused (extra fields are ignored).
    """

    # Task 20.2d (D20.2d-a/b): "outline" (film-subtitle style) is the owner-preferred default.
    caption_style: Literal["outline", "box", "shade"] = "outline"
    # Phase 30 (ENH-021): what is behind the captions -- a black screen, one still of a scene's plate, or (Phase 32, the
    # default since Phase 44 / D123) the two characters as talking sprites over the scene plates with generic inserts.
    # The drawn-shot "illustrated" video was removed with RealVisXL (D123).
    visual_mode: Literal["podcast_black", "podcast_still", "podcast_sprites"] = "podcast_sprites"
    still_scene_id: str | None = None
