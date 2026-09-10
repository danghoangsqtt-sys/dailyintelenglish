"""Pydantic models for Learning Content (Task 1.5) generation and persistence."""

from pydantic import BaseModel, Field


class VocabularyItem(BaseModel):
    """One target-vocabulary entry extracted from the script."""

    word: str = Field(min_length=1)
    part_of_speech: str = Field(min_length=1)
    ipa: str = Field(min_length=1)
    definition_en: str = Field(min_length=1)
    definition_vi: str = Field(min_length=1)
    example_sentence: str = Field(min_length=1)


class IdiomItem(BaseModel):
    """One idiom or collocation found in the script, with context."""

    phrase: str = Field(min_length=1)
    meaning_en: str = Field(min_length=1)
    meaning_vi: str = Field(min_length=1)
    example_sentence: str = Field(min_length=1)


class GrammarItem(BaseModel):
    """One grammar spotlight point drawn from the script."""

    point: str = Field(min_length=1)
    structure: str = Field(min_length=1)
    explanation_en: str = Field(min_length=1)
    explanation_vi: str = Field(min_length=1)
    examples: list[str] = Field(default_factory=list)


class QuestionItem(BaseModel):
    """One comprehension/discussion question for the listener."""

    question: str = Field(min_length=1)
    options: list[str] = Field(default_factory=list)
    correct_answer: str = ""
    explanation: str = ""


class LearningPackOut(BaseModel):
    """Full validated Learning Content pack parsed from the Gemini response."""

    vocabulary: list[VocabularyItem] = Field(default_factory=list)
    idioms: list[IdiomItem] = Field(default_factory=list)
    grammar: list[GrammarItem] = Field(default_factory=list)
    questions: list[QuestionItem] = Field(default_factory=list)


class LearningPackUpdate(BaseModel):
    """Partial user-edit payload for an existing Learning Content pack.

    Only fields present in the request are written — omitted fields are left
    unchanged (see learning_service.update_learning_content).
    """

    vocabulary: list[VocabularyItem] | None = None
    idioms: list[IdiomItem] | None = None
    grammar: list[GrammarItem] | None = None
    questions: list[QuestionItem] | None = None
