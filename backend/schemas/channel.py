"""Task 36.5 (D103-D105): the channel plan -- topics (playlists) -> series -> episodes, and the AI channel map."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.core.constants import CEFR_LEVELS, GENRES

_URL = re.compile(r"^(https?://\S+)?$")


def _genre(value: str) -> str:
    value = (value or "").strip().lower().replace(" ", "_").replace("-", "_")
    return value if value in GENRES else "small_talk"


def _cefr(value: str) -> str:
    value = (value or "").strip().upper()[:2]
    return value if value in CEFR_LEVELS else "B1"


class TopicInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=400)
    playlist_url: str = Field(default="", max_length=300)

    @field_validator("playlist_url")
    @classmethod
    def url(cls, value: str) -> str:
        value = value.strip()
        if not _URL.match(value):
            raise ValueError("playlist_url must be an http(s) link or empty")
        return value


class TopicPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=400)
    playlist_url: str | None = Field(default=None, max_length=300)
    position: int | None = Field(default=None, ge=0)

    _url = field_validator("playlist_url")(lambda cls, value: TopicInput.url(value) if value is not None else value)


class SeriesInput(BaseModel):
    presentation_mode: Literal["classic", "solo_explainer"] = "classic"
    explainer_structure: Literal["why", "how", "list"] = "why"
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=600)
    genre: str = "small_talk"
    cefr_level: str = "B1"
    cast: list[str] = Field(default_factory=list, max_length=6)
    duration_minutes: float = Field(default=5.0, gt=0, le=30)
    playlist_url: str = Field(default="", max_length=300)

    _genre = field_validator("genre")(lambda cls, value: _genre(value))
    _cefr = field_validator("cefr_level")(lambda cls, value: _cefr(value))
    _url = field_validator("playlist_url")(lambda cls, value: TopicInput.url(value))


class SeriesPatch(BaseModel):
    presentation_mode: Literal["classic", "solo_explainer"] | None = None
    explainer_structure: Literal["why", "how", "list"] | None = None
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=600)
    genre: str | None = None
    cefr_level: str | None = None
    cast: list[str] | None = Field(default=None, max_length=6)
    duration_minutes: float | None = Field(default=None, gt=0, le=30)
    playlist_url: str | None = Field(default=None, max_length=300)
    position: int | None = Field(default=None, ge=0)

    _genre = field_validator("genre")(lambda cls, value: _genre(value) if value is not None else value)
    _cefr = field_validator("cefr_level")(lambda cls, value: _cefr(value) if value is not None else value)
    _url = field_validator("playlist_url")(lambda cls, value: TopicInput.url(value) if value is not None else value)


class EpisodeInput(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    brief: str = Field(default="", max_length=600)


class EpisodePatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    brief: str | None = Field(default=None, max_length=600)
    status: str | None = None
    publish_date: str | None = None
    video_url: str | None = Field(default=None, max_length=300)

    @field_validator("status")
    @classmethod
    def status_value(cls, value: str | None) -> str | None:
        if value is not None and value not in ("planned", "created", "published"):
            raise ValueError("status must be planned, created or published")
        return value

    @field_validator("publish_date")
    @classmethod
    def date_value(cls, value: str | None) -> str | None:
        if value and not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            raise ValueError("publish_date must be YYYY-MM-DD")
        return value or None

    _url = field_validator("video_url")(lambda cls, value: TopicInput.url(value) if value is not None else value)


# ---------------------------------------------------------------- the AI channel map (D104)

class PlanRequest(BaseModel):
    """The owner's direction for the channel."""

    audience: str = Field(default="Vietnamese learners of English", max_length=300)
    focus: str = Field(default="", max_length=600)  # what the channel should cover, in the owner's words
    cefr_levels: list[str] = Field(default_factory=lambda: ["B1"], min_length=1, max_length=6)
    topics: int = Field(default=4, ge=1, le=8)
    series_per_topic: int = Field(default=2, ge=1, le=4)
    episodes_per_series: int = Field(default=5, ge=3, le=10)
    existing_topics: list[str] = Field(default_factory=list)  # filled by the service, never by the owner

    _cefr = field_validator("cefr_levels")(lambda cls, values: list(dict.fromkeys(_cefr(value) for value in values)))


class PlannedEpisode(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    brief: str = Field(default="", max_length=600)


class PlannedSeries(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=600)
    genre: str = "small_talk"
    cefr_level: str = "B1"
    episodes: list[PlannedEpisode] = Field(min_length=1, max_length=12)

    _genre = field_validator("genre")(lambda cls, value: _genre(value))
    _cefr = field_validator("cefr_level")(lambda cls, value: _cefr(value))


class PlannedTopic(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=400)
    series: list[PlannedSeries] = Field(min_length=1, max_length=6)


class ChannelPlan(BaseModel):
    topics: list[PlannedTopic] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def distinct_names(self) -> "ChannelPlan":
        names = [topic.name.strip().lower() for topic in self.topics]
        if len(names) != len(set(names)):
            raise ValueError("topic names must be distinct")
        return self


class ScheduleRequest(BaseModel):
    start_date: str
    weekdays: list[int] = Field(default_factory=lambda: [0, 2, 4], min_length=1, max_length=7)  # Monday = 0
    include_published: bool = False

    @field_validator("start_date")
    @classmethod
    def date_value(cls, value: str) -> str:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            raise ValueError("start_date must be YYYY-MM-DD")
        return value

    @field_validator("weekdays")
    @classmethod
    def weekdays_value(cls, values: list[int]) -> list[int]:
        if any(day < 0 or day > 6 for day in values):
            raise ValueError("weekdays are 0 (Monday) to 6 (Sunday)")
        return sorted(set(values))
