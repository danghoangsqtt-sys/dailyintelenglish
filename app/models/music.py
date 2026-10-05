"""Task 22.2: AI music generation input (Phase 22, D49 style families)."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Base captions measured in the 22.1 spike (docs/operations/phase22-spike-music.md).
MUSIC_STYLES = {
    "lofi": {
        "label": "Lofi / chill",
        "caption": "lofi hip hop, mellow, soft electric piano, warm bass, vinyl crackle, relaxed, "
                   "background music, instrumental",
    },
    "acoustic": {
        "label": "Acoustic / piano",
        "caption": "acoustic guitar and warm piano, gentle, soft strings, calm, background music, instrumental",
    },
    "upbeat": {
        "label": "Upbeat / corporate",
        "caption": "bright upbeat corporate pop, light percussion, ukulele, claps, positive, "
                   "background music, instrumental",
    },
}
MIN_DURATION_S, MAX_DURATION_S = 10, 1200
MAX_BRIEF_CHARS = 200
MAX_SEED = 2**31 - 1


class MusicGenerateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    style: str
    brief: str = Field(default="", max_length=MAX_BRIEF_CHARS)
    duration_s: int = Field(ge=MIN_DURATION_S, le=MAX_DURATION_S)
    seed: int | None = Field(default=None, ge=1, le=MAX_SEED)

    @field_validator("style")
    @classmethod
    def validate_style(cls, value: str) -> str:
        if value not in MUSIC_STYLES:
            raise ValueError(f"style must be one of {', '.join(MUSIC_STYLES)}")
        return value

    @field_validator("brief")
    @classmethod
    def validate_brief(cls, value: str) -> str:
        return " ".join(value.split())


# Task 22.3: the project's music brief (D45). The AI answer and the owner's edit use one model.
PREVIEW_SECONDS = 30
PREVIEW_COUNT = 3
BRIEF_SCRIPT_LINES = 12
EPISODE_MARGIN_S = 15
# Rule fallback when the AI is unavailable or wrong: one family per script genre (owner can edit).
GENRE_STYLE = {
    "small_talk": "upbeat", "directions": "upbeat", "negotiation": "upbeat",
    "storytelling": "acoustic", "interview": "acoustic", "news": "acoustic",
    "opinion": "lofi", "debate": "lofi", "informational": "lofi", "instructions": "lofi",
}
GENRE_BRIEF = {
    "upbeat": "friendly and lively, medium tempo, light and positive",
    "acoustic": "warm and gentle, calm tempo, soft guitar and piano",
    "lofi": "relaxed and focused, slow tempo, soft keys",
}


class MusicBriefInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    style: str
    brief: str = Field(default="", max_length=MAX_BRIEF_CHARS)
    duration_s: int = Field(ge=MIN_DURATION_S, le=MAX_DURATION_S)

    _validate_style = field_validator("style")(MusicGenerateInput.validate_style.__func__)
    _validate_brief = field_validator("brief")(MusicGenerateInput.validate_brief.__func__)


class MusicFullInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed: int = Field(ge=1, le=MAX_SEED)
