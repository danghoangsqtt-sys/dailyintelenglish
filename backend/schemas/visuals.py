"""Validated library inputs and fixed options for AI visuals."""

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.core.constants import TTS_SPEED_MAX, TTS_SPEED_MIN

COLORS = (
    "white", "black", "navy blue", "light blue", "red", "yellow", "green", "beige",
    "grey", "pink", "brown", "orange",
)
TOPS = ("t-shirt", "shirt", "slim-fit shirt", "sweater", "blouse", "polo shirt", "suit jacket", "mini dress")
BOTTOMS = ("jeans", "trousers", "slim trousers", "skirt", "shorts", "suit trousers", "mini dress")
# A dress is one garment: it is both the top and the bottom item, in one colour (Phase 31: Lina's white mini dress).
ONE_PIECE = ("mini dress",)
AGE_GROUPS = ("young", "adult", "middle-aged", "senior")
GENDERS = ("female", "male")
SCENE_CATEGORIES = ("home", "school", "work", "city", "countryside", "nature", "food", "travel", "other")
TIMES_OF_DAY = ("morning", "day", "sunset", "night")
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
    ethnicity: str = "Russian"
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
    def validate_extra(cls, value: str) -> str:
        """Phase 31: a short identity detail for the prompts (skin, bangs...): the CLIP text window is only 77 tokens, so at
        most 6 words and 50 letters, spaces, hyphens or commas."""
        value = " ".join(value.strip().split())
        if not value:
            return ""
        if len(value) > 50 or len(value.split()) > 6 or not re.fullmatch(r"[A-Za-z ,-]+", value):
            raise ValueError("extra must have at most 6 words and 50 letters, spaces, hyphens or commas")
        return value

    @model_validator(mode="after")
    def validate_outfit(self):
        if self.top_color not in COLORS or self.bottom_color not in COLORS:
            raise ValueError("choose one of the solid colours")
        if self.top_item not in TOPS or self.bottom_item not in BOTTOMS:
            raise ValueError("choose one top and one bottom item")
        # Phase 28: one colour for both garments is allowed (the woman all white, the man all black).
        if ((self.top_item in ONE_PIECE or self.bottom_item in ONE_PIECE)
                and (self.top_item != self.bottom_item or self.top_color != self.bottom_color)):
            raise ValueError("a dress is one garment: use it as the top and the bottom, in one colour")
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
    category: Literal["home", "school", "work", "city", "countryside", "nature", "food", "travel", "other"] = "other"
    time_of_day: Literal["morning", "day", "sunset", "night"] = "day"

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
    category: Literal["home", "school", "work", "city", "countryside", "nature", "food", "travel", "other"] | None = None
    time_of_day: Literal["morning", "day", "sunset", "night"] | None = None

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


class ShotReviewInput(BaseModel):
    """Task 29.4: the owner's one-time review of a library shot."""
    review_state: Literal["pending", "approved", "rejected"]


class ActivityMetadataInput(BaseModel):
    """Owner-editable metadata for a reusable activity cutaway."""

    character_id: str | None = None
    activity: str = Field(min_length=1, max_length=80)
    context_tags: list[str] = Field(default_factory=list, max_length=8)
    aliases: list[str] = Field(default_factory=list, max_length=20)
    variant: str = Field(default="", max_length=80)


class ActivityMetadataPatch(BaseModel):
    """Partial owner edit; omitted fields keep their stored values."""

    character_id: str | None = None
    activity: str | None = Field(default=None, min_length=1, max_length=80)
    context_tags: list[str] | None = Field(default=None, max_length=8)
    aliases: list[str] | None = Field(default=None, max_length=20)
    variant: str | None = Field(default=None, max_length=80)


class ActivityReviewInput(BaseModel):
    review_state: Literal["pending", "approved", "rejected"]


class ActivityApproveBatchInput(BaseModel):
    """Explicit selection of pending activity pictures to approve together."""

    ids: list[str] = Field(min_length=1, max_length=500)


class ApprovalInput(BaseModel):
    approved: bool


class SheetItemInput(BaseModel):
    kind: Literal["full_body", "portrait_calm", "portrait_smile", "portrait_surprised"]


class CastMemberInput(BaseModel):
    speaker_index: int = Field(ge=0)
    character_id: str


# Phase 33 (Task 33.2, Amendment A D79): character profiles. Quick create asks only what the prompt pack and the voice need.
PROFILE_ACCENTS = ("american", "british", "australian", "canadian", "irish", "scottish", "indian", "singaporean",
                   "new_zealand", "south_african")


def _free_text(value: str, field_name: str, max_length: int) -> str:
    value = " ".join(value.strip().split())
    if len(value) > max_length:
        raise ValueError(f"{field_name} must be at most {max_length} characters")
    return value


class ProfileQuickCreate(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    gender: Literal["female", "male"]
    accent: Literal[PROFILE_ACCENTS]  # type: ignore[valid-type]
    nationality: str = ""
    appearance: str = Field(min_length=1, max_length=400)
    outfit: str = Field(min_length=1, max_length=200)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = " ".join(value.strip().split())
        if not value:
            raise ValueError("name cannot be blank")
        return value

    @field_validator("nationality")
    @classmethod
    def validate_nationality(cls, value: str) -> str:
        value = value.strip()
        return _phrase(value, "nationality", 1) if value else ""

    @field_validator("appearance", "outfit")
    @classmethod
    def validate_text(cls, value: str, info) -> str:
        value = _free_text(value, info.field_name, 400 if info.field_name == "appearance" else 200)
        if not value:
            raise ValueError(f"{info.field_name} cannot be blank")
        return value


class ProfilePatch(BaseModel):
    """Autosave: every field is optional; only the fields sent are changed."""

    name: str | None = Field(default=None, min_length=1, max_length=40)
    gender: Literal["female", "male"] | None = None
    accent: Literal[PROFILE_ACCENTS] | None = None  # type: ignore[valid-type]
    nationality: str | None = None
    appearance: str | None = Field(default=None, max_length=400)
    outfit: str | None = Field(default=None, max_length=200)
    intro: str | None = Field(default=None, max_length=400)
    personality: list[str] | None = Field(default=None, max_length=8)
    speaking_style: str | None = Field(default=None, max_length=200)
    dialogue_behavior: str | None = Field(default=None, max_length=200)
    default_voice_id: str | None = Field(default=None, max_length=80)
    expected_voice_revision: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    default_speed: float | None = Field(default=None, ge=TTS_SPEED_MIN, le=TTS_SPEED_MAX)
    default_pitch: float | None = Field(default=None, ge=-1.0, le=1.0)
    default_volume: float | None = Field(default=None, ge=0.0, le=2.0)
    wizard_step: int | None = Field(default=None, ge=0, le=10)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = " ".join(value.strip().split())
        if not value:
            raise ValueError("name cannot be blank")
        return value

    @field_validator("nationality")
    @classmethod
    def validate_nationality(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None if value is None else ""
        return _phrase(value, "nationality", 1)

    @field_validator("personality")
    @classmethod
    def validate_personality(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        traits = [" ".join(item.strip().split()) for item in value]
        if any(not trait or len(trait) > 30 for trait in traits):
            raise ValueError("each personality trait must have 1–30 characters")
        return traits
