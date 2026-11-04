"""Phase 96 (task 96.5): the "What is this called?" Short -- one everyday object at a time: the question, a silent 1-2-3, the
name. The AI gives one schema-checked list of objects on a theme; the lines are built from it here.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from backend.content.word_family import _clean_text

QUESTION = "What is this called?"
COUNTDOWN_MS = 3000
MIN_OBJECTS, MAX_OBJECTS = 5, 7  # about eight seconds each with the delay, under a minute


class ObjectItem(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    ipa: str = Field(min_length=1, max_length=60)
    meaning_en: str = Field(default="", max_length=80)
    meaning_vi: str = Field(default="", max_length=60)
    picture: str = Field(min_length=1, max_length=160)

    @field_validator("*", mode="before")
    @classmethod
    def _tidy(cls, value):
        return _clean_text(value) if isinstance(value, str) else value

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return value.strip(" .,!?:;\"'")

    @field_validator("meaning_en", "meaning_vi")
    @classmethod
    def _no_full_stop(cls, value: str) -> str:
        return value.strip().rstrip(".;,").strip()

    @field_validator("ipa")
    @classmethod
    def _slashes(cls, value: str) -> str:
        bare = value.strip().strip("/[]").strip()
        return f"/{bare}/" if bare else ""


class ObjectQuiz(BaseModel):
    theme: str = Field(min_length=1, max_length=60)
    items: list[ObjectItem] = Field(min_length=MIN_OBJECTS, max_length=MAX_OBJECTS + 4)


def build_beats(quiz: ObjectQuiz) -> list[tuple[str, dict]]:
    """(spoken text, card) per line: for each object the question, then its name."""
    seen: set[str] = set()
    items = []
    for item in quiz.items:
        key = item.name.lower()
        if key not in seen:
            seen.add(key)
            items.append(item)
    if len(items) < MIN_OBJECTS:
        raise ValueError(f"only {len(items)} different objects")
    beats: list[tuple[str, dict]] = []
    for number, item in enumerate(items[:MAX_OBJECTS], start=1):
        fields = {"number": number, "word": item.name, "ipa": item.ipa, "meaning_en": item.meaning_en,
                  "meaning_vi": item.meaning_vi, "picture": item.picture}
        beats.append((QUESTION, {"beat": "ask", "pause_after_ms": COUNTDOWN_MS, **fields}))
        beats.append((f"{item.name[:1].upper()}{item.name[1:]}.", {"beat": "answer", **fields}))
    return beats


def quiz_prompt(topic: str, cefr: str, owner_words: list[str]) -> str:
    named = (f"Use exactly these objects, in this order: {owner_words[:MAX_OBJECTS]}\n" if owner_words else
             f"Choose {MAX_OBJECTS} everyday objects of the topic whose English names learners often do not know, from easier to harder.\n")
    return (
        "You prepare a very short vocabulary quiz video: it shows one object, asks \"What is this called?\", counts down, "
        "then says the name.\n"
        f"Topic: {topic}\nLevel of the learners: {cefr}\n{named}"
        "Rules:\n"
        "- name: the everyday American English name that a dictionary lists, in lower case, one or two words. Only ordinary "
        "objects found in most homes or shops of that topic; never an invented compound or a rare gadget.\n"
        "- ipa: its pronunciation in IPA between slashes.\n"
        "- meaning_en: what it is, in at most 8 plain words.\n"
        "- meaning_vi: its Vietnamese name, in at most 5 words.\n"
        "- picture: the object alone, in at most 15 English words, clear enough to recognise (for example: a white wall "
        "socket with two round holes). No people, no writing on it.\n"
        "Answer with the JSON object only."
    )
