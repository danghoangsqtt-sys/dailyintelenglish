"""Task 22.7 (D50/D51): Music Library track details -- mood and tags for auto-select, licence and
credit for the YouTube description. The duration is always measured, never typed."""

from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

MOODS = {
    "lofi": "Lofi / chill",
    "acoustic": "Acoustic / warm",
    "upbeat": "Upbeat / bright",
    "calm": "Calm / ambient",
    "inspiring": "Inspiring / cinematic",
}
SOURCES = {
    "youtube_audio_library": "YouTube Audio Library",
    "pixabay": "Pixabay Music",
    "mixkit": "Mixkit",
    "incompetech": "Incompetech (Kevin MacLeod)",
    "free_music_archive": "Free Music Archive",
    "other": "Other",
}
# attribution_required: True = the licence needs a credit; None = the owner must check (other).
LICENCES = {
    "youtube_audio_library": {"label": "YouTube Audio Library (no attribution)", "attribution_required": False},
    "youtube_audio_library_attribution": {"label": "YouTube Audio Library (attribution required)",
                                          "attribution_required": True},
    "pixabay": {"label": "Pixabay Content License", "attribution_required": False},
    "mixkit": {"label": "Mixkit Free License", "attribution_required": False},
    "cc0": {"label": "CC0 (public domain)", "attribution_required": False},
    "cc_by_4": {"label": "CC BY 4.0 (attribution required)", "attribution_required": True},
    "other": {"label": "Other (check the terms)", "attribution_required": None},
}
MAX_TEXT = 120
MAX_ATTRIBUTION = 500
MAX_TAGS = 12


def _clean(value: str | None) -> str | None:
    """Collapse whitespace; an empty field is stored as NULL (cleared)."""
    if value is None:
        return None
    return " ".join(value.split()) or None


class MusicTrackPatch(BaseModel):
    """PATCH semantics: only the fields sent are changed (`exclude_unset`); an empty value clears."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=MAX_TEXT)
    artist: str | None = Field(default=None, max_length=MAX_TEXT)
    mood: str | None = None
    tags: str | None = Field(default=None, max_length=MAX_ATTRIBUTION)
    source: str | None = None
    licence: str | None = None
    attribution: str | None = Field(default=None, max_length=MAX_ATTRIBUTION)
    source_url: str | None = Field(default=None, max_length=MAX_ATTRIBUTION)

    @field_validator("title", "artist", "attribution")
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        return _clean(value)

    @field_validator("mood")
    @classmethod
    def validate_mood(cls, value: str | None) -> str | None:
        if value not in (None, "") and value not in MOODS:
            raise ValueError(f"mood must be one of {', '.join(MOODS)}")
        return value or None

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str | None) -> str | None:
        if value not in (None, "") and value not in SOURCES:
            raise ValueError(f"source must be one of {', '.join(SOURCES)}")
        return value or None

    @field_validator("licence")
    @classmethod
    def validate_licence(cls, value: str | None) -> str | None:
        if value not in (None, "") and value not in LICENCES:
            raise ValueError(f"licence must be one of {', '.join(LICENCES)}")
        return value or None

    @field_validator("tags")
    @classmethod
    def normalise_tags(cls, value: str | None) -> str | None:
        if value is None:
            return None
        tags: list[str] = []
        for raw in value.split(","):
            tag = " ".join(raw.lower().split())
            if tag and tag not in tags:
                tags.append(tag)
        if len(tags) > MAX_TAGS:
            raise ValueError(f"at most {MAX_TAGS} tags")
        return ", ".join(tags) or None

    @field_validator("source_url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        value = (value or "").strip()
        if not value:
            return None
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("source_url must be an http(s) link")
        return value
