"""Phase 87: the "Word roots, prefixes and suffixes" Short -- one word family turned into beats.

The AI returns a schema-checked `WordFamily` (a root, a prefix or a suffix and 4-7 words made with it); the server
builds the script from fixed beat templates (the formula of the owner's sample video): hook, surprise, promise, origin,
the bare head, then for each word its whole form, its split and an example, a quiz and a follow line. Every line keeps
its beat's card in `language_notes.roots`, which the renderer draws.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

FAMILY_MIN_WORDS = 4
FAMILY_MAX_WORDS = 7
ROOTS_FOLLOW = {"vi": "Comment đáp án và theo dõi Daily Beyond English nhé!",
                "en": "Comment your answer and follow Daily Beyond English!"}
_SEED_PATH = Path(__file__).resolve().parent / "data" / "word_roots.json"
_ICONS_PATH = Path(__file__).resolve().parent / "data" / "lineart_icons.json"
_ORIGIN_VI = {"Latin": "Latin", "Greek": "Hy Lạp", "Old English": "Anh cổ"}
_KIND_VI = {"root": "gốc", "prefix": "tiền tố", "suffix": "hậu tố"}
_KIND_EN = {"root": "root", "prefix": "prefix", "suffix": "suffix"}


class FamilyPart(BaseModel):
    text: str = Field(min_length=1, max_length=20)
    role: Literal["prefix", "root", "suffix"]
    meaning: str = Field(default="", max_length=40)


class FamilyWord(BaseModel):
    word: str = Field(min_length=2, max_length=30)
    parts: list[FamilyPart] = Field(min_length=1, max_length=4)
    meaning: str = Field(min_length=1, max_length=60)
    logic: str = Field(min_length=1, max_length=220)
    example_en: str = Field(default="", max_length=140)
    example_vi: str = Field(default="", max_length=160)
    picture: str = Field(default="", max_length=160)
    # Phase 87.4: one or two bundled line icons, drawn when the word has no Qwen picture
    icons: list[str] = Field(default_factory=list, max_length=4)

    @field_validator("icons")
    @classmethod
    def known_icons(cls, value: list[str]) -> list[str]:
        known = set(icon_names())
        return [name for name in (str(v).strip().lower() for v in value) if name in known][:2]


class WordFamily(BaseModel):
    kind: Literal["root", "prefix", "suffix"]
    head: str = Field(min_length=1, max_length=30)
    origin_lang: str = Field(default="", max_length=30)
    origin_form: str = Field(default="", max_length=60)
    head_meaning: str = Field(min_length=1, max_length=60)
    head_logic: str = Field(default="", max_length=220)
    head_example_en: str = Field(default="", max_length=140)
    head_example_vi: str = Field(default="", max_length=160)
    words: list[FamilyWord] = Field(min_length=FAMILY_MIN_WORDS, max_length=FAMILY_MAX_WORDS + 3)
    quiz: FamilyWord
    quiz_clue: str = Field(min_length=1, max_length=200)


@lru_cache(maxsize=1)
def icon_names() -> list[str]:
    return json.loads(_ICONS_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def seed() -> dict:
    return json.loads(_SEED_PATH.read_text(encoding="utf-8"))


def _bare(text: str) -> str:
    return re.sub(r"[^a-z]", "", text.lower())


def find_seed(topic: str) -> tuple[str, dict] | None:
    """The checked entry a topic names ("PRESS", "gốc press", "tiền tố un-", "-tion"), if any."""
    text = topic.lower()
    for kind, key in (("root", "roots"), ("prefix", "prefixes"), ("suffix", "suffixes")):
        for entry in seed()[key]:
            for alt in entry["head"].split("/"):
                alt = alt.strip()
                bare = _bare(alt)
                if not bare:
                    continue
                if kind == "prefix" and re.search(rf"(?<![a-z]){re.escape(bare)}-", text):
                    return kind, entry
                if kind == "suffix" and re.search(rf"-{re.escape(bare)}(?![a-z])", text):
                    return kind, entry
                if kind == "root" and re.search(rf"(?<![a-z]){re.escape(bare)}(?![a-z])", text):
                    return kind, entry
    return None


def parts_spell_word(word: FamilyWord) -> bool:
    """The parts, joined, must spell the word (a split the viewer cannot see is no help)."""
    return _bare("".join(part.text for part in word.parts)) == _bare(word.word)


def usable_words(family: WordFamily) -> list[FamilyWord]:
    seen: set[str] = set()
    kept = []
    for word in family.words:
        key = _bare(word.word)
        if key and key not in seen and parts_spell_word(word) and _bare(word.word) != _bare(family.quiz.word):
            seen.add(key)
            kept.append(word)
    return kept[:FAMILY_MAX_WORDS]


def _cap(text: str) -> str:
    text = " ".join(text.split())
    return text[:1].upper() + text[1:] if text else text


def _sentence(text: str) -> str:
    text = _cap(text)
    return text if not text or text[-1] in ".!?…" else text + "."


def _spoken_head(head: str, lang: str) -> str:
    alts = [alt.strip().strip("-") for alt in head.split("/") if alt.strip().strip("-")]
    return (" hoặc " if lang == "vi" else " or ").join(alts) or head


def _card(beat: str, **fields) -> dict:
    return {"beat": beat, **{key: value for key, value in fields.items() if value not in (None, "", [])}}


def _word_card(beat: str, word: FamilyWord, **extra) -> dict:
    return _card(beat, word=word.word, parts=[part.model_dump() for part in word.parts], meaning=word.meaning,
                 picture=word.picture, icons=word.icons, **extra)


def _breakdown(word: FamilyWord) -> str:
    """The one-line split shown under the meaning: "COM: cùng nhau · PRESS: ép"."""
    return " · ".join(f"{part.text.strip('-').upper()}: {part.meaning}" for part in word.parts if part.meaning)


def build_beats(family: WordFamily, lang: str) -> list[tuple[str, dict]]:
    """(spoken text, card) per line, in order. `lang` is the narration language: "vi" or "en"."""
    words = usable_words(family)
    if len(words) < FAMILY_MIN_WORDS:
        raise ValueError(f"only {len(words)} words of the family have parts that spell them")
    vi = lang == "vi"
    first, second = words[0], words[1]
    kind = _KIND_VI[family.kind] if vi else _KIND_EN[family.kind]
    head = _spoken_head(family.head, lang)
    count = len(words) + 1  # the quiz word counts too
    beats: list[tuple[str, dict]] = []

    if vi:
        beats.append((f"Bạn có biết {_cap(first.word)} là {first.meaning},", _word_card("hook", first)))
        beats.append((f"nhưng {_cap(first.word)} và {_cap(second.word)} cùng một {kind}?",
                      _card("twins", words=[first.word, second.word], head=family.head, kind=family.kind)))
        beats.append((f"Sau video này, bạn sẽ hiểu và nhớ được {count} từ tiếng Anh chỉ từ một {kind} duy nhất!",
                      _card("wheel", head=family.head, kind=family.kind, words=[w.word for w in words] + [family.quiz.word])))
    else:
        beats.append((f"Did you know {_cap(first.word)} means {first.meaning},", _word_card("hook", first)))
        beats.append((f"but {_cap(first.word)} and {_cap(second.word)} share one {kind}?",
                      _card("twins", words=[first.word, second.word], head=family.head, kind=family.kind)))
        beats.append((f"After this video, you'll remember {count} English words from just one {kind}!",
                      _card("wheel", head=family.head, kind=family.kind, words=[w.word for w in words] + [family.quiz.word])))

    if family.origin_form.strip():
        spoken_form = family.origin_form.split("→")[0].strip()
        origin = (f"{_ORIGIN_VI.get(family.origin_lang, family.origin_lang)} {spoken_form}" if vi
                  else f"{family.origin_lang} {spoken_form}")
        text = (f"{_cap(kind)} của chúng ta hôm nay là {head}, bắt nguồn từ {origin}, nghĩa là {family.head_meaning}." if vi
                else f"Our {kind} today is {head}, from the {origin}, meaning {family.head_meaning}.")
        beats.append((text, _card("origin", head=family.head, kind=family.kind, origin=family.origin_form,
                                  origin_lang=family.origin_lang, meaning=family.head_meaning)))
    beats.append((f"{_cap(head)}, {family.head_meaning}.",
                  _card("head", head=family.head, kind=family.kind, meaning=family.head_meaning)))
    if family.head_logic.strip():
        beats.append((_sentence(family.head_logic), _card("head_logic", head=family.head, kind=family.kind,
                                                         meaning=family.head_meaning)))
    if family.head_example_en.strip():
        beats.append((_sentence(family.head_example_en),
                      _card("head_example", head=family.head, kind=family.kind, meaning=family.head_meaning,
                            example_en=_sentence(family.head_example_en), example_vi=family.head_example_vi)))

    for word in words:
        beats.append((f"{_cap(word.word)}, {word.meaning}.", _word_card("whole", word)))
        beats.append((_sentence(word.logic), _word_card("split", word, breakdown=_breakdown(word))))
        if word.example_en.strip():
            beats.append((_sentence(word.example_en), _word_card("example", word, breakdown=_breakdown(word),
                                                                 example_en=_sentence(word.example_en),
                                                                 example_vi=word.example_vi)))

    quiz = family.quiz
    beats.append((("Đoán từ cuối nhé! " if vi else "Guess the last word! ") + _sentence(family.quiz_clue),
                  _card("quiz", word=quiz.word, parts=[part.model_dump() for part in quiz.parts], picture=quiz.picture,
                        icons=quiz.icons, answer=quiz.meaning)))
    beats.append((ROOTS_FOLLOW[lang], _card("follow", word=quiz.word)))
    return beats


def roots_prompt(topic: str, cefr: str, lang: str, owner_words: list[str]) -> str:
    """The AI's brief: facts from the checked list when the topic names a listed head."""
    found = find_seed(topic)
    language = "Vietnamese" if lang == "vi" else "English"
    facts = ""
    if found:
        kind, entry = found
        facts = (f"Checked facts (copy them exactly): kind={kind}, head={entry['head']!r}, origin_lang="
                 f"{entry['origin_lang']!r}, origin_form={entry['origin_form']!r}, meaning of the head="
                 f"{entry['meaning_vi'] if lang == 'vi' else entry['meaning_en']!r}. Common family words to choose "
                 f"from: {', '.join(entry['words'])}.\n")
    words = (f"Use exactly these words, in this order (the last one is the quiz word): "
             f"{json.dumps(owner_words[:FAMILY_MAX_WORDS + 1], ensure_ascii=False)}\n" if owner_words else
             f"Choose {FAMILY_MIN_WORDS + 1} to {FAMILY_MAX_WORDS} common English words built with this head, useful for "
             f"{cefr} learners, plus one more for the quiz (not repeated in words).\n")
    return (
        "You prepare one word family for a short English-vocabulary video for learners (Vietnamese learners when the "
        "language below is Vietnamese).\n"
        f"Topic: {topic}\n{facts}{words}"
        f"Write meaning, logic, head_meaning, head_logic, example_vi and quiz_clue in {language}; example_en is English.\n"
        "Rules:\n"
        "- kind is root, prefix or suffix; head is written as in a dictionary of roots (press, mit / miss, un-, -tion).\n"
        "- parts: the word split into prefix / root / suffix; the parts joined MUST spell the word exactly "
        "(com + press = compress, press + ure = pressure). meaning of a part: two to four words.\n"
        "- meaning: the word's usual meaning in two to five words.\n"
        "- logic: ONE short sentence that explains how the parts give the meaning, like a memory trick "
        "(e.g. 'COM là cùng nhau, PRESS là ép: ép sát vào nhau thì chiếm ít chỗ hơn, nên compress là nén lại.').\n"
        "- example_en: one short natural B1 sentence with the word; example_vi: its translation.\n"
        "- picture: a simple object scene for a line drawing that shows the meaning, in English, no people's faces "
        "and no text (e.g. 'a computer monitor showing a zipped folder').\n"
        f"- icons: one or two names from this list that show the same idea: {', '.join(icon_names())}.\n"
        "- origin_lang / origin_form: only when you are sure (e.g. Latin, 'premere → pressus'); otherwise empty.\n"
        "- head_logic: one sentence showing the head's own meaning in an everyday action; head_example_en a short "
        "sentence with the bare head when it is a word (else empty).\n"
        "- quiz: one more family word, with parts; quiz_clue describes a situation that shows its meaning without "
        "saying the word or its translation.\n"
        "Return ONLY a JSON object that validates against the schema."
    )
