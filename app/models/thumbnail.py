"""Pydantic contracts for thumbnail templates, Gemini suggestions, and API requests."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from app.core.constants import (
    THUMBNAIL_MAX_VARIANTS,
    THUMBNAIL_MIN_VARIANTS,
    THUMBNAIL_TEMPLATE_IDS,
)

HexColor = Annotated[str, StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}$")]
ThumbnailAspect = Literal["16x9", "9x16"]
ThumbnailFormat = Literal["png", "jpg"]


class ThumbnailPalette(BaseModel):
    """Strict four-color palette returned by Gemini."""

    primary: HexColor
    secondary: HexColor
    accent: HexColor
    text: HexColor

    @field_validator("primary", "secondary", "accent", "text")
    @classmethod
    def normalize_hex_color(cls, value: str) -> str:
        """Normalize validated colors so duplicate detection is case-insensitive."""
        return value.upper()


class ThumbnailSuggestion(BaseModel):
    """One validated headline/palette concept returned by Gemini."""

    model_config = ConfigDict(str_strip_whitespace=True)

    headline: str = Field(min_length=1, max_length=80)
    supporting_text: str = Field(default="", max_length=120)
    topic_keywords: list[str] = Field(min_length=1, max_length=5)
    palette: ThumbnailPalette

    @field_validator("topic_keywords")
    @classmethod
    def validate_keywords(cls, values: list[str]) -> list[str]:
        """Reject blank or duplicate topic keywords after trimming."""
        cleaned = [value.strip() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("topic_keywords must not contain blank values")
        if len({value.casefold() for value in cleaned}) != len(cleaned):
            raise ValueError("topic_keywords must be unique")
        return cleaned


class ThumbnailSuggestionPack(BaseModel):
    """Gemini output containing a bounded set of distinct A/B suggestions."""

    variants: list[ThumbnailSuggestion] = Field(
        min_length=THUMBNAIL_MIN_VARIANTS,
        max_length=THUMBNAIL_MAX_VARIANTS,
    )

    @model_validator(mode="after")
    def reject_duplicate_variants(self) -> "ThumbnailSuggestionPack":
        """Require every suggestion to differ in text, keywords, or palette."""
        signatures = [variant.model_dump_json() for variant in self.variants]
        if len(set(signatures)) != len(signatures):
            raise ValueError("thumbnail variants must be distinct")
        return self


class ThumbnailGenerateRequest(BaseModel):
    """Request one 3-5 variant batch using exactly one selected template."""

    template_name: str
    variant_count: int = Field(
        default=THUMBNAIL_MIN_VARIANTS,
        ge=THUMBNAIL_MIN_VARIANTS,
        le=THUMBNAIL_MAX_VARIANTS,
    )

    @field_validator("template_name")
    @classmethod
    def validate_template_name(cls, value: str) -> str:
        """Reject unknown template identifiers before filesystem access."""
        if value not in THUMBNAIL_TEMPLATE_IDS:
            raise ValueError(f"template_name must be one of: {', '.join(THUMBNAIL_TEMPLATE_IDS)}")
        return value


class TextZone(BaseModel):
    """Normalized text rectangle and font-size bounds for a template."""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)
    min_font_size: int = Field(ge=8)
    max_font_size: int = Field(ge=8)
    align: Literal["left", "center", "right"] = "left"

    @model_validator(mode="after")
    def validate_bounds(self) -> "TextZone":
        """Keep text zones inside the normalized canvas with valid font bounds."""
        if self.x + self.width > 1 or self.y + self.height > 1:
            raise ValueError("text zone must stay inside the canvas")
        if self.min_font_size > self.max_font_size:
            raise ValueError("min_font_size must not exceed max_font_size")
        return self


class ThumbnailTemplateConfig(BaseModel):
    """Validated renderer configuration loaded from a checked-in template JSON file."""

    id: str
    display_name: str = Field(min_length=1)
    category: Literal["minimal", "bold", "split", "dark", "educational"]
    description: str = Field(min_length=1)
    base_image: str = Field(min_length=1)
    headline_zone: TextZone
    supporting_zone: TextZone
    uppercase_headline: bool = False

    @model_validator(mode="after")
    def validate_asset_identity(self) -> "ThumbnailTemplateConfig":
        """Bind config id to an approved same-directory PNG filename."""
        if self.id not in THUMBNAIL_TEMPLATE_IDS:
            raise ValueError(f"unknown thumbnail template id: {self.id}")
        if self.base_image != f"{self.id}.png":
            raise ValueError("base_image must match the template id")
        return self

