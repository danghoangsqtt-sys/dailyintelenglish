"""Pydantic contracts for YouTube Package generation (Task 1.9, Sub-task 1.9a)."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.core.constants import YOUTUBE_TAGS_MAX_CHARS, YOUTUBE_TITLE_MAX_CHARS

TitleVariant = Literal["click_worthy", "educational", "seo"]


class TitleOption(BaseModel):
    """One Gemini-generated title suggestion for a specific angle."""

    model_config = {"str_strip_whitespace": True}

    variant: TitleVariant
    text: str = Field(min_length=1, max_length=YOUTUBE_TITLE_MAX_CHARS)


class YouTubePackageOut(BaseModel):
    """Gemini output for one YouTube package: title options, description, tags."""

    model_config = {"str_strip_whitespace": True}

    titles: list[TitleOption] = Field(min_length=3, max_length=3)
    description: str = Field(min_length=1, max_length=5000)
    tags: list[str] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def validate_titles_and_tags(self) -> "YouTubePackageOut":
        """Require exactly one title per variant, and tags to be nonblank and fit the joined limit."""
        variants = [title.variant for title in self.titles]
        if set(variants) != {"click_worthy", "educational", "seo"}:
            raise ValueError("titles must contain exactly one click_worthy, educational, and seo option")
        cleaned_tags = [tag.strip() for tag in self.tags]
        if any(not tag for tag in cleaned_tags):
            raise ValueError("tags must not contain blank values")
        joined = ", ".join(cleaned_tags)
        if len(joined) > YOUTUBE_TAGS_MAX_CHARS:
            raise ValueError(
                f"joined tags exceed {YOUTUBE_TAGS_MAX_CHARS} characters ({len(joined)})"
            )
        self.tags = cleaned_tags
        return self
