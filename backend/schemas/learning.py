"""Pydantic models for Learning Content (Task 1.5) generation and persistence."""

from pydantic import BaseModel, Field, model_validator


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


class PhraseItem(BaseModel):
    """Task 36.1 (D95): one collocation or phrasal verb from the script, with its meaning and the sentence it is in."""

    phrase: str = Field(min_length=1)
    meaning_en: str = Field(min_length=1)
    meaning_vi: str = Field(min_length=1)
    example_sentence: str = Field(min_length=1)


class PatternItem(BaseModel):
    """Task 36.1 (D95): one reusable sentence pattern (its structure) and the sentence of the script that uses it."""

    pattern: str = Field(min_length=1)
    use_en: str = Field(min_length=1)
    use_vi: str = Field(min_length=1)
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
    # Task 36.1 (D95): optional extras -- older packs and answers without them stay valid.
    collocations: list[PhraseItem] = Field(default_factory=list)
    phrasal_verbs: list[PhraseItem] = Field(default_factory=list)
    patterns: list[PatternItem] = Field(default_factory=list)


class LearningPackUpdate(BaseModel):
    """Partial user-edit payload for an existing Learning Content pack.

    Only fields present in the request are written — omitted fields are left
    unchanged (see learning_service.update_learning_content).
    Sending explicit null is rejected — omission is the only way to skip a field.
    """

    vocabulary: list[VocabularyItem] | None = None
    idioms: list[IdiomItem] | None = None
    grammar: list[GrammarItem] | None = None
    questions: list[QuestionItem] | None = None
    collocations: list[PhraseItem] | None = None
    phrasal_verbs: list[PhraseItem] | None = None
    patterns: list[PatternItem] | None = None

    @model_validator(mode="before")
    @classmethod
    def forbid_explicit_null(cls, data: object) -> object:
        """Reject any field sent as explicit JSON null — omission is the only way to leave unchanged."""
        if isinstance(data, dict):
            nulled = [key for key, value in data.items() if value is None]
            if nulled:
                raise ValueError(
                    f"explicit null not allowed for: {', '.join(nulled)} "
                    "— omit the field instead to leave it unchanged"
                )
        return data
