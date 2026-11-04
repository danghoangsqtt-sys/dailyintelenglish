"""Phase 96 (D147-D151): the Word of the day Short -- one word, its picture, said six times, then one example sentence.

The AI gives one schema-checked word; the lines are built from it here. Every line carries the same card, so the renderer
can draw the word, its explanation and the example from any of them (`language_notes.wordday`).
"""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, Field, field_validator

from backend.content.word_family import _clean_text

REPEATS = 6
EXAMPLE_WORDS = (4, 16)


class WordCard(BaseModel):
    word: str = Field(min_length=1, max_length=40)
    ipa: str = Field(min_length=1, max_length=60)
    part_of_speech: str = Field(default="", max_length=30)
    meaning_en: str = Field(min_length=1, max_length=90)
    meaning_vi: str = Field(min_length=1, max_length=90)
    example_en: str = Field(min_length=1, max_length=120)
    example_vi: str = Field(min_length=1, max_length=160)
    picture: str = Field(min_length=1, max_length=240)

    @field_validator("*", mode="before")
    @classmethod
    def _tidy(cls, value):
        return _clean_text(value) if isinstance(value, str) else value

    @field_validator("word")
    @classmethod
    def _one_word_or_short_phrase(cls, value: str) -> str:
        if len(value.split()) > 3:
            raise ValueError("the word must be one word or a phrase of at most three words")
        return value.strip(" .,!?:;\"'").lower()

    @field_validator("meaning_en", "meaning_vi")
    @classmethod
    def _no_full_stop(cls, value: str) -> str:
        return value.strip().rstrip(".;,").strip()

    @field_validator("ipa")
    @classmethod
    def _slashes(cls, value: str) -> str:
        bare = value.strip().strip("/[]").strip()
        return f"/{bare}/" if bare else ""


def _stem(word: str) -> str:
    return re.sub(r"[^a-z]", "", word.lower())[:max(3, len(word) - 3)]


def example_uses_word(card: WordCard) -> bool:
    """"He studies hard" uses "study": the first letters are enough to accept an inflected form."""
    words = re.findall(r"[a-z']+", card.example_en.lower())
    return all(any(word.startswith(_stem(part)) for word in words) for part in card.word.split())


def spoken_word(word: str) -> str:
    return f"{word[:1].upper()}{word[1:]}."


def build_beats(card: WordCard) -> list[tuple[str, dict]]:
    """(spoken text, card) per line: the word `REPEATS` times, then the example."""
    if not example_uses_word(card):
        raise ValueError(f"the example does not use the word {card.word!r}")
    if not EXAMPLE_WORDS[0] <= len(card.example_en.split()) <= EXAMPLE_WORDS[1]:
        raise ValueError(f"the example must have {EXAMPLE_WORDS[0]} to {EXAMPLE_WORDS[1]} words")
    fields = card.model_dump()
    beats: list[tuple[str, dict]] = [(spoken_word(card.word), {"beat": "repeat", "repeat": at + 1, **fields})
                                     for at in range(REPEATS)]
    example = card.example_en if card.example_en[-1] in ".!?" else f"{card.example_en}."
    beats.append((example, {"beat": "example", "repeat": REPEATS, **fields}))
    return beats


def word_prompt(topic: str, cefr: str, owner_words: list[str]) -> str:
    named = (f"Use exactly this word: {json.dumps(owner_words[0], ensure_ascii=False)}\n" if owner_words else
             f"If the topic names a word, use that word. Otherwise choose one useful English word about the topic for {cefr} "
             "learners, one that is pleasant to say and easy to picture.\n")
    return (
        "You prepare one English word for a very short vocabulary video: the word is said six times, then one example "
        "sentence, over one picture that shows its meaning.\n"
        f"Topic: {topic}\n{named}"
        "Rules:\n"
        "- word: lower case, one word (a phrase of at most three words only when the topic names it).\n"
        "- ipa: its American pronunciation in IPA between slashes.\n"
        "- part_of_speech: noun, verb, adjective, adverb...\n"
        "- meaning_en: a plain English definition in at most 10 words, without using the word.\n"
        "- meaning_vi: its natural Vietnamese meaning in at most 8 words.\n"
        f"- example_en: one natural sentence of 5 to 12 words at {cefr} level that uses the word and shows what it means.\n"
        "- example_vi: the natural Vietnamese translation of that sentence.\n"
        "- picture: one concrete scene in English, at most 30 words, that shows the situation of example_en so the meaning is "
        "clear at a glance (a thing, a place or an action, seen from behind or as hands). No writing, no signs, "
        "no famous people, nobody's face.\n"
        "Answer with the JSON object only."
    )
