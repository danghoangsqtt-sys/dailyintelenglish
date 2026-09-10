"""Pydantic models for project creation and update requests."""

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.constants import (
    ACCENTS,
    CEFR_LEVELS,
    GENDERS,
    GENRES,
    MAX_SPEAKERS,
    MIN_SPEAKERS,
    PROJECT_STATUSES,
    TTS_ENGINES,
    TTS_SPEED_MAX,
    TTS_SPEED_MIN,
)


class LanguageFeatures(BaseModel):
    """Toggles controlling which language phenomena the script prompt should target."""

    collocation: bool = True
    idiom: bool = True
    slang: bool = False
    local_expressions: bool = False
    phrasal_verbs: bool = True
    business_register: bool = False


class SpeakerConfig(BaseModel):
    """Per-speaker voice and persona configuration."""

    name: str = Field(min_length=1)
    gender: str = "neutral"
    accent: str = "american"
    tts_engine: str = "omnivoice"
    voice_description: str = ""
    speed: float = Field(default=1.0, ge=TTS_SPEED_MIN, le=TTS_SPEED_MAX)
    pitch: float = Field(default=0.0, ge=-1.0, le=1.0)
    volume: float = Field(default=1.0, ge=0.0, le=2.0)

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, value: str) -> str:
        if value not in GENDERS:
            raise ValueError(f"gender must be one of {GENDERS}")
        return value

    @field_validator("accent")
    @classmethod
    def validate_accent(cls, value: str) -> str:
        if value not in ACCENTS:
            raise ValueError(f"accent must be one of {ACCENTS}")
        return value

    @field_validator("tts_engine")
    @classmethod
    def validate_tts_engine(cls, value: str) -> str:
        if value not in TTS_ENGINES:
            raise ValueError(f"tts_engine must be one of {TTS_ENGINES}")
        return value


class ScriptConfig(BaseModel):
    """Full configuration submitted from the Step 1 wizard to create a project."""

    name: str = Field(min_length=1)
    topic: str = ""
    cefr_level: str = "B1"
    duration_minutes: float = Field(default=10.0, gt=0)
    num_speakers: int = Field(default=2, ge=MIN_SPEAKERS, le=MAX_SPEAKERS)
    genre: str = "small_talk"
    accent: str = "american"
    language_features: LanguageFeatures = Field(default_factory=LanguageFeatures)
    speakers: list[SpeakerConfig] = Field(default_factory=list)

    @field_validator("cefr_level")
    @classmethod
    def validate_cefr_level(cls, value: str) -> str:
        if value not in CEFR_LEVELS:
            raise ValueError(f"cefr_level must be one of {CEFR_LEVELS}")
        return value

    @field_validator("genre")
    @classmethod
    def validate_genre(cls, value: str) -> str:
        if value not in GENRES:
            raise ValueError(f"genre must be one of {GENRES}")
        return value

    @field_validator("accent")
    @classmethod
    def validate_accent(cls, value: str) -> str:
        if value not in ACCENTS:
            raise ValueError(f"accent must be one of {ACCENTS}")
        return value

    @model_validator(mode="after")
    def validate_speakers_match_num_speakers(self) -> "ScriptConfig":
        if len(self.speakers) != self.num_speakers:
            raise ValueError(
                f"speakers has {len(self.speakers)} entries but num_speakers={self.num_speakers}"
            )
        return self


class ProjectUpdate(BaseModel):
    """Partial update payload used for auto-save.

    Only fields present in the request are written — but "present" must mean
    the client actually sent a value. Sending a field as explicit JSON `null`
    is rejected (see `forbid_explicit_null`) rather than silently nulling out
    a column; to leave a field unchanged, omit its key entirely.
    """

    name: str | None = Field(default=None, min_length=1)
    status: str | None = None
    topic: str | None = None
    cefr_level: str | None = None
    duration_minutes: float | None = Field(default=None, gt=0)
    num_speakers: int | None = Field(default=None, ge=MIN_SPEAKERS, le=MAX_SPEAKERS)
    genre: str | None = None
    accent: str | None = None
    language_features: LanguageFeatures | None = None
    speakers: list[SpeakerConfig] | None = None

    @model_validator(mode="before")
    @classmethod
    def forbid_explicit_null(cls, data: object) -> object:
        """Reject any field sent as explicit JSON null — omission is the only way to skip it."""
        if isinstance(data, dict):
            nulled = [key for key, value in data.items() if value is None]
            if nulled:
                raise ValueError(
                    f"explicit null not allowed for: {', '.join(nulled)} "
                    "— omit the field instead to leave it unchanged"
                )
        return data

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is not None and value not in PROJECT_STATUSES:
            raise ValueError(f"status must be one of {PROJECT_STATUSES}")
        return value

    @field_validator("cefr_level")
    @classmethod
    def validate_cefr_level(cls, value: str | None) -> str | None:
        if value is not None and value not in CEFR_LEVELS:
            raise ValueError(f"cefr_level must be one of {CEFR_LEVELS}")
        return value

    @field_validator("genre")
    @classmethod
    def validate_genre(cls, value: str | None) -> str | None:
        if value is not None and value not in GENRES:
            raise ValueError(f"genre must be one of {GENRES}")
        return value

    @field_validator("accent")
    @classmethod
    def validate_accent(cls, value: str | None) -> str | None:
        if value is not None and value not in ACCENTS:
            raise ValueError(f"accent must be one of {ACCENTS}")
        return value

    @model_validator(mode="after")
    def validate_num_speakers_and_speakers_atomic(self) -> "ProjectUpdate":
        """num_speakers and speakers must change together — never num_speakers alone."""
        num_speakers_set = self.num_speakers is not None
        speakers_set = self.speakers is not None
        if num_speakers_set != speakers_set:
            raise ValueError(
                "num_speakers and speakers must be updated together in the same request"
            )
        if speakers_set and len(self.speakers) != self.num_speakers:
            raise ValueError(
                f"speakers has {len(self.speakers)} entries but num_speakers={self.num_speakers}"
            )
        return self
