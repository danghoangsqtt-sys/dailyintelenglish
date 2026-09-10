"""Pydantic models for script generation/regeneration/save requests."""

from pydantic import BaseModel, Field


class LanguageNotesEdit(BaseModel):
    """User- or Gemini-provided language annotations for one script line."""

    collocations: list[str] = Field(default_factory=list)
    idioms: list[str] = Field(default_factory=list)
    grammar_point: str = ""


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
