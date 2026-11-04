"""Phase 97 (D159): the "Load the word" Short -- one word said over and over, faster and faster, on a wall of that word, while a bar
counts up to 100%; then the word with its IPA and meaning, and one example. The AI gives one schema-checked word.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from backend.content.word_family import _clean_text
from backend.content.word_repeat import example_uses_word, spoken_word

LOOP_MS = 16000


class LoadCard(BaseModel):
    word: str = Field(min_length=1, max_length=30)
    ipa: str = Field(min_length=1, max_length=60)
    part_of_speech: str = Field(default="", max_length=30)
    meaning_en: str = Field(min_length=1, max_length=70)
    meaning_vi: str = Field(min_length=1, max_length=50)
    example_en: str = Field(min_length=1, max_length=100)
    example_vi: str = Field(min_length=1, max_length=140)

    @field_validator("*", mode="before")
    @classmethod
    def _tidy(cls, value):
        return _clean_text(value) if isinstance(value, str) else value

    @field_validator("word")
    @classmethod
    def _word(cls, value: str) -> str:
        if len(value.split()) > 2:
            raise ValueError("one word or a phrase of two words")
        return value.strip(" .,!?:;\"'").lower()

    @field_validator("meaning_en", "meaning_vi")
    @classmethod
    def _no_full_stop(cls, value: str) -> str:
        return value.strip().rstrip(".;,").strip()

    @field_validator("ipa")
    @classmethod
    def _slashes(cls, value: str) -> str:
        return f"/{value.strip().strip('/[]').strip()}/"


def build_beats(card: LoadCard) -> list[tuple[str, dict]]:
    """(spoken text, card) per line: the loop, the word once, the example."""
    if not example_uses_word(card):
        raise ValueError(f"the example does not use the word {card.word!r}")
    fields = card.model_dump()
    example = card.example_en if card.example_en[-1] in ".!?" else f"{card.example_en}."
    return [(spoken_word(card.word), {"beat": "load", "loop_ms": LOOP_MS, **fields}),
            (spoken_word(card.word), {"beat": "reveal", **fields}),
            (example, {"beat": "example", **fields})]


def load_prompt(topic: str, cefr: str, owner_words: list[str]) -> str:
    named = (f"Use exactly this word: {owner_words[0]!r}\n" if owner_words else
             f"If the topic names a word, use that word. Otherwise choose one useful English word about the topic for {cefr} learners "
             "that is hard to remember and has a clear rhythm when said many times.\n")
    return (
        "You prepare one English word for a very short video that says it over and over until the viewer remembers it.\n"
        f"Topic: {topic}\n{named}"
        "Rules:\n"
        "- word: lower case, one word.\n"
        "- ipa: its American pronunciation in IPA between slashes.\n"
        "- part_of_speech: noun, verb, adjective, adverb...\n"
        "- meaning_en: a plain definition in at most 8 words, without using the word.\n"
        "- meaning_vi: its natural Vietnamese meaning in at most 5 words.\n"
        f"- example_en: one natural sentence of 5 to 10 words at {cefr} level with the word.\n"
        "- example_vi: its natural Vietnamese translation.\n"
        "Answer with the JSON object only."
    )
