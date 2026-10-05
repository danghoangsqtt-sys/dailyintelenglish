"""Task 24.1: storyboard beats -- story moments that tile a project's script lines."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.visuals import _phrase

EXPRESSIONS = ("calm", "smile", "laugh", "surprised", "thinking", "worried", "serious")


class BeatInput(BaseModel):
    line_from: int = Field(ge=0)
    line_to: int = Field(ge=0)
    kind: Literal["scene", "insert"] = "scene"
    scene_id: str | None = None
    new_place: str | None = None
    speakers: list[int] = Field(default_factory=list, max_length=2)
    action: str = ""
    expression: Literal["calm", "smile", "laugh", "surprised", "thinking", "worried", "serious"] = "calm"

    @field_validator("new_place")
    @classmethod
    def validate_new_place(cls, value: str | None) -> str | None:
        return _phrase(value, "new_place", 5) if value else None

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: str) -> str:
        value = " ".join(value.strip().split())
        return _phrase(value, "action", 8) if value else ""

    @field_validator("speakers")
    @classmethod
    def validate_speakers(cls, value: list[int]) -> list[int]:
        if len(set(value)) != len(value) or any(index < 0 for index in value):
            raise ValueError("speakers must be distinct speaker indexes")
        return value

    @model_validator(mode="after")
    def validate_shape(self) -> "BeatInput":
        if self.line_from > self.line_to:
            raise ValueError("line_from must not exceed line_to")
        if self.kind == "scene" and bool(self.scene_id) == bool(self.new_place):
            raise ValueError("a scene beat needs exactly one of scene_id or new_place")
        return self


class StoryboardInput(BaseModel):
    beats: list[BeatInput] = Field(min_length=1)
    status: Literal["draft", "approved"] = "draft"
