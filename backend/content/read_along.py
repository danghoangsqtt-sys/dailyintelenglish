"""Build a bounded single-screen reading passage for Read Along Shorts."""

from pydantic import BaseModel, Field, field_validator

MAX_WORDS = 100
MAX_CHARACTERS = 650
MAX_SENTENCE_WORDS = 18
MAX_TOKEN_CHARACTERS = 28


class Passage(BaseModel):
    title: str = Field(min_length=1, max_length=60)
    picture: str = Field(min_length=1, max_length=260)
    sentences: list[str] = Field(min_length=4, max_length=14)

    @field_validator("title", "picture")
    @classmethod
    def tidy_field(cls, value: str) -> str:
        text = " ".join(value.split())
        if not text:
            raise ValueError("Provide a title and an illustration description")
        return text


def checked_sentences(sentences: list[str]) -> list[str]:
    """Return normalized text that fits the reading panel."""
    sentences = [" ".join(sentence.split()) for sentence in sentences]
    for sentence in sentences:
        words = sentence.split()
        if not words or len(words) > MAX_SENTENCE_WORDS:
            raise ValueError(f"Each sentence must contain 1 to {MAX_SENTENCE_WORDS} words")
        if any(len(word) > MAX_TOKEN_CHARACTERS for word in words):
            raise ValueError("Use short words that fit the reading panel")
    sentences = [text if text[-1] in ".!?" else f"{text}." for text in sentences]
    text = " ".join(sentences)
    if len(text.split()) > MAX_WORDS or len(text) > MAX_CHARACTERS:
        raise ValueError(f"The passage must fit {MAX_WORDS} words and {MAX_CHARACTERS} characters")
    return sentences


def build_beats(passage: Passage) -> list[tuple[str, dict]]:
    """One spoken sentence per line, with one shared illustration and title."""
    sentences = checked_sentences(passage.sentences)
    card = {"beat": "passage", "word": "reading illustration", "title": passage.title, "picture": passage.picture}
    return [(sentence, dict(card)) for sentence in sentences]


def passage_prompt(topic: str, cefr: str, owner_words: list[str]) -> str:
    """Request one coherent and original passage at the project's CEFR level."""
    vocabulary = f" Use these words naturally if appropriate: {owner_words[:8]}." if owner_words else ""
    return (
        f"Write an original English read-along passage about {topic!r} for {cefr} learners.{vocabulary} "
        "The whole passage will be visible on one phone screen and read by one narrator. "
        "Write 6 to 12 connected sentences, ideally 65 to 90 words. "
        f"Do not exceed {MAX_WORDS} words or {MAX_CHARACTERS} characters overall, or {MAX_SENTENCE_WORDS} words per sentence. "
        "Use simple natural language, a clear beginning and ending, and no channel call to action. "
        "Return a short title, one English description of a landscape cartoon illustration of the main scene, "
        "and the sentences in order. Do not narrate the title. Return JSON only."
    )
