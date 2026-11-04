"""Phase 96 (task 96.6): the Basic vs Advanced Short -- a plain phrase, then the natural one said twice, over a full-frame picture
of what it means (owner 2026-11-04: nobody on screen, the content and the picture are what the viewer remembers).

The AI gives one schema-checked list of pairs; the lines are built from it here.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from backend.content.word_family import _clean_text

MIN_PAIRS, MAX_PAIRS = 3, 5  # about ten seconds a pair, under a minute


class LevelPair(BaseModel):
    basic: str = Field(min_length=1, max_length=40)
    advanced: str = Field(min_length=1, max_length=40)
    meaning_en: str = Field(min_length=1, max_length=80)
    meaning_vi: str = Field(min_length=1, max_length=60)
    picture: str = Field(min_length=1, max_length=160)

    @field_validator("*", mode="before")
    @classmethod
    def _tidy(cls, value):
        return _clean_text(value) if isinstance(value, str) else value

    @field_validator("basic", "advanced")
    @classmethod
    def _phrase(cls, value: str) -> str:
        return value.strip().rstrip(".!,;:").strip()

    @field_validator("meaning_en", "meaning_vi")
    @classmethod
    def _no_full_stop(cls, value: str) -> str:
        return value.strip().rstrip(".;,").strip()


class LevelUp(BaseModel):
    theme: str = Field(min_length=1, max_length=60)
    pairs: list[LevelPair] = Field(min_length=MIN_PAIRS, max_length=MAX_PAIRS + 4)


def build_beats(level: LevelUp) -> list[tuple[str, dict]]:
    """(spoken text, card) per line: for each pair the basic phrase, then the advanced one twice."""
    seen: set[str] = set()
    pairs = []
    for pair in level.pairs:
        key = pair.advanced.lower()
        if key not in seen and key != pair.basic.lower():
            seen.add(key)
            pairs.append(pair)
    if len(pairs) < MIN_PAIRS:
        raise ValueError(f"only {len(pairs)} different pairs")
    beats: list[tuple[str, dict]] = []
    for number, pair in enumerate(pairs[:MAX_PAIRS], start=1):
        fields = {"number": number, "word": pair.advanced, "basic": pair.basic, "advanced": pair.advanced,
                  "meaning_en": pair.meaning_en, "meaning_vi": pair.meaning_vi, "picture": pair.picture}
        beats.append((f"{pair.basic}.", {"beat": "basic", **fields}))
        beats.append((f"{pair.advanced}.", {"beat": "advanced", **fields}))
        beats.append((f"{pair.advanced}.", {"beat": "advanced", **fields}))
    return beats


def level_prompt(topic: str, cefr: str, owner_words: list[str]) -> str:
    named = f"Use these advanced phrases: {owner_words[:MAX_PAIRS]}\n" if owner_words else ""
    return (
        "You prepare a very short video for English learners: a voice says a basic phrase, then twice a more natural phrase that "
        "native speakers use with the same meaning, over one picture that makes its meaning unforgettable.\n"
        f"Topic: {topic}\nLevel of the learners: {cefr}\n{named}"
        f"Give {MAX_PAIRS} pairs. Rules:\n"
        "- basic: a plain phrase every beginner knows, at most 4 words (for example: I'm very busy).\n"
        "- advanced: a well-known idiom or fixed expression native speakers really say, with the same meaning, at most 6 words "
        "(for example: I'm swamped; Break a leg; I'm over the moon), and the same strength of meaning. Not a longer or fancier sentence. Only phrases found in a "
        "good dictionary; never invent one; polite enough to say at work.\n"
        "- meaning_en: when to use it, in at most 8 plain words.\n"
        "- meaning_vi: its natural Vietnamese meaning, in at most 6 words.\n"
        "- picture: at most 30 English words: an ordinary person in the real moment when you would say this phrase, so the feeling is "
        "clear at a glance, in one simple pose doing one thing (never two actions with the hands). Never draw the words of an idiom literally (no moon for 'over the moon', no water for 'swamped'). For "
        "'I'm beat': a tired office worker just home at night, slumped on the sofa, tie loose, eyes half closed, bag on the floor. "
        "For 'I'm starving': a hungry person at a desk holding their stomach, dreaming of a big bowl of noodles in a thought cloud. "
        "No writing, no famous people.\n"
        "Answer with the JSON object only."
    )
