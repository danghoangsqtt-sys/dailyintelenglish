"""Phase 96 (task 96.4): the picture-for-each-sentence Short -- "I take off my shoes" over a picture of taking off shoes.

The AI gives one schema-checked small story told in the first person; the lines are built from it here. It opens with a
challenge and closes by naming the level the viewer has reached (D155). Pictures show only hands and feet (D152), so that no
two pictures of a video show a different person.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from backend.content.word_family import _clean_text

HOOK = "Can you understand this?"
MIN_LINES, MAX_LINES = 5, 8
MAX_WORDS = 10


def closing_line(cefr: str) -> str:
    level = cefr.upper()
    return f"If you understood this, you are {'an' if level[:1] == 'A' else 'a'} {level} listener."


class StoryLine(BaseModel):
    sentence: str = Field(min_length=1, max_length=90)
    keywords: list[str] = Field(default_factory=list, max_length=4)
    translation_vi: str = Field(min_length=1, max_length=140)
    picture: str = Field(min_length=1, max_length=200)

    @field_validator("sentence", "translation_vi", "picture", mode="before")
    @classmethod
    def _tidy(cls, value):
        return _clean_text(value) if isinstance(value, str) else value


class PictureStory(BaseModel):
    title: str = Field(min_length=1, max_length=60)
    lines: list[StoryLine] = Field(min_length=MIN_LINES, max_length=MAX_LINES + 4)


def build_beats(story: PictureStory, cefr: str = "A2") -> list[tuple[str, dict]]:
    """(spoken text, card) per line: the challenge, one sentence per picture, the level. The first and last pictures carry the
    opening and closing lines too. A sentence too long for one screen is refused."""
    lines = story.lines[:MAX_LINES]
    too_long = [line.sentence for line in lines if len(line.sentence.split()) > MAX_WORDS]
    if too_long:
        raise ValueError(f"a sentence has more than {MAX_WORDS} words: {too_long[0]!r}")
    cards = [{"beat": "line", "number": number, "word": f"line {number}", "keywords": line.keywords,
              "translation_vi": line.translation_vi, "picture": line.picture} for number, line in enumerate(lines, start=1)]
    beats: list[tuple[str, dict]] = [(HOOK, {"beat": "hook", "number": 1, "word": cards[0]["word"], "picture": cards[0]["picture"]})]
    for line, card in zip(lines, cards):
        beats.append((line.sentence if line.sentence[-1] in ".!?" else f"{line.sentence}.", card))
    beats.append((closing_line(cefr), {"beat": "closing", "number": len(cards), "word": cards[-1]["word"], "picture": cards[-1]["picture"]}))
    return beats


def story_prompt(topic: str, cefr: str, owner_words: list[str]) -> str:
    named = f"Use these words in the story: {owner_words[:8]}\n" if owner_words else ""
    return (
        "You write a tiny story for a listening video: one short sentence on each screen, each over a picture that shows exactly "
        "that sentence, so a learner understands by watching.\n"
        f"Topic: {topic}\nLevel of the learners: {cefr}\n{named}"
        f"Write {MIN_LINES + 1} to {MAX_LINES} sentences that follow one ordinary task step by step, in the real order a person does it "
        "(for example cooking rice, or going into the sea), so each step leads to the next. Nothing silly or impossible, no animals. "
        "Correct grammar: read each sentence again before you answer. Rules:\n"
        f"- sentence: first person, at most {MAX_WORDS} words, one visible action done with the hands or the feet (for example: I take "
        f"off my shoes. I pour water into the pot.). Plain {cefr} English in one tense. No feelings or thoughts that cannot be seen.\n"
        "- keywords: the one to three most useful words of the sentence, exactly as written in it.\n"
        "- translation_vi: its natural Vietnamese translation.\n"
        "- picture: at most 25 English words: exactly that action seen through the speaker's own eyes, naming the hand or feet and "
        "the objects and the place (for example: two hands pulling a white sneaker off one's own foot, sitting on warm sand). One "
        "action only. No face, no other person, no writing.\n"
        "Answer with the JSON object only."
    )
