"""Validated library inputs and fixed options for AI visuals."""

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

COLORS = (
    "white", "black", "navy blue", "light blue", "red", "yellow", "green", "beige",
    "grey", "pink", "brown", "orange",
)
TOPS = ("t-shirt", "shirt", "slim-fit shirt", "sweater", "blouse", "polo shirt")
BOTTOMS = ("jeans", "trousers", "slim trousers", "skirt", "shorts")
AGE_GROUPS = ("young", "adult", "middle-aged", "senior")
GENDERS = ("female", "male")
SHEET_KINDS = ("full_body", "portrait_calm", "portrait_smile", "portrait_surprised")


def _phrase(value: str, field_name: str, max_words: int) -> str:
    value = " ".join(value.strip().split())
    if not value or len(value) > 40 or len(value.split()) > max_words or not re.fullmatch(r"[A-Za-z -]+", value):
        raise ValueError(f"{field_name} must have 1–{max_words} words, at most 40 letters, spaces or hyphens")
    return value


class CharacterInput(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    gender: Literal["female", "male"]
    age_group: Literal["young", "adult", "middle-aged", "senior"]
    ethnicity: str = "Vietnamese"
    role: str
    hair: str
    eyes: str
    extra: str = ""
    top_color: str
    top_item: str
    bottom_color: str
    bottom_item: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name cannot be blank")
        return value

    @field_validator("role", "hair", "eyes", "ethnicity")
    @classmethod
    def validate_phrase(cls, value: str, info) -> str:
        limits = {"role": 2, "hair": 4, "eyes": 2, "ethnicity": 1}
        return _phrase(value, info.field_name, limits[info.field_name])

    @field_validator("extra")
    @classmethod
    def reject_extra(cls, value: str) -> str:
        if value:
            raise ValueError("extra is not supported in this phase")
        return ""

    @model_validator(mode="after")
    def validate_outfit(self):
        if self.top_color not in COLORS or self.bottom_color not in COLORS:
            raise ValueError("choose one of the solid colours")
        if self.top_item not in TOPS or self.bottom_item not in BOTTOMS:
            raise ValueError("choose one top and one bottom item")
        if self.top_color == self.bottom_color:
            raise ValueError("top and bottom colours must differ")
        return self


class CharacterPatch(BaseModel):
    name: str | None = None
    gender: str | None = None
    age_group: str | None = None
    ethnicity: str | None = None
    role: str | None = None
    hair: str | None = None
    eyes: str | None = None
    extra: str | None = None
    top_color: str | None = None
    top_item: str | None = None
    bottom_color: str | None = None
    bottom_item: str | None = None


class SceneInput(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    place: str
    staging: Literal["standing", "seated"]

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name cannot be blank")
        return value

    @field_validator("place")
    @classmethod
    def validate_place(cls, value: str) -> str:
        return _phrase(value, "place", 5)


class ScenePatch(BaseModel):
    name: str | None = None
    place: str | None = None
    staging: Literal["standing", "seated"] | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        return SceneInput.validate_name(value) if value is not None else None

    @field_validator("place")
    @classmethod
    def validate_place(cls, value: str | None) -> str | None:
        return SceneInput.validate_place(value) if value is not None else None


class ReferenceInput(BaseModel):
    asset_id: str


class ApprovalInput(BaseModel):
    approved: bool


class SheetItemInput(BaseModel):
    kind: Literal["full_body", "portrait_calm", "portrait_smile", "portrait_surprised"]


class CastMemberInput(BaseModel):
    speaker_index: int = Field(ge=0)
    character_id: str
