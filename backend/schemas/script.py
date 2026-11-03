"""Pydantic models for script generation/regeneration/save requests."""

from pydantic import BaseModel, Field


class LanguageNotesEdit(BaseModel):
    """User- or Gemini-provided language annotations for one script line."""

    collocations: list[str] = Field(default_factory=list)
    idioms: list[str] = Field(default_factory=list)
    grammar_point: str = ""
    translation_vi: str = Field(default="", max_length=600)  # Phase 81: shown under the English in a slow English podcast
    roots: dict | None = None  # Phase 87: a word-roots beat card, kept with its line through Step 2 edits
    grammar: dict | None = None  # Phase 88: an easy-grammar beat (scene header and cards), kept the same way


class ScriptLineEdit(BaseModel):
    """One script line as submitted by the Step 2 editor (PUT /script)."""

    speaker_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    language_notes: LanguageNotesEdit = Field(default_factory=LanguageNotesEdit)


class ScriptUpdate(BaseModel):
    """Full script replacement payload for PUT /api/projects/{id}/script."""

    lines: list[ScriptLineEdit] = Field(min_length=1)


class RegenerateLineRequest(BaseModel):
    """Request body for POST /api/projects/{id}/script/regenerate."""

    line_id: str = Field(min_length=1)
