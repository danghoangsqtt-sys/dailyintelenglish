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
    # required (real run 2026-11-03: left optional, the AI described only the quiz word and the others had no picture)
    picture: str = Field(min_length=3, max_length=160)
    # Phase 87.4: one or two bundled line icons, drawn when the word has no Qwen picture
    icons: list[str] = Field(default_factory=list, max_length=4)

    @field_validator("icons")
    @classmethod
    def known_icons(cls, value: list[str]) -> list[str]:
        known = set(icon_names())
        return [name for name in (str(v).strip().lower() for v in value) if name in known][:2]


class StoryBeat(BaseModel):
    """Phase 97 (D158): one sentence of the true story behind a word, with its line drawing."""
    text: str = Field(min_length=1, max_length=170)
    picture: str = Field(min_length=3, max_length=160)


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
    # Phase 97 (D158): only for a true, well-documented origin; empty keeps the usual opening
    puzzle: str = Field(default="", max_length=150)
    puzzle_word: str = Field(default="", max_length=30)
    story: list[StoryBeat] = Field(default_factory=list, max_length=5)


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


def _common_prefix(a: str, b: str) -> int:
    size = 0
    while size < min(len(a), len(b)) and a[size] == b[size]:
        size += 1
    return size


def fit_parts(word: FamilyWord) -> FamilyWord | None:
    """The word with parts that spell it, or None. Real run 2026-11-03: the AI adds an empty "-" suffix, and splits a
    suffix family by the base word (decide + sion for decision); the base part then becomes the letters the word
    really has (deci + sion), keeping its meaning. Anything that cannot be fitted this way is not used."""
    parts = [part for part in word.parts if _bare(part.text)]
    if not parts:
        return None
    fitted = word.model_copy(update={"parts": parts})
    if parts_spell_word(fitted):
        return fitted
    text = _bare(word.word)
    last = _bare(parts[-1].text)
    if len(parts) >= 2 and text.endswith(last):
        before = "".join(_bare(part.text) for part in parts[:-2])
        base = text[:len(text) - len(last)]
        if base.startswith(before):
            rest = base[len(before):]
            if rest and _common_prefix(rest, _bare(parts[-2].text)) >= min(3, len(rest)):
                new = [*parts[:-2], parts[-2].model_copy(update={"text": rest}), parts[-1]]
                return word.model_copy(update={"parts": new})
    return None


def around_root(word: FamilyWord, head: str) -> FamilyWord:
    """A root family's word split around the whole root: what comes before it, the root, what comes after. Sandbox run
    2026-11-03: the AI split suspect as SUS + PECT and spectator as SPECTA + TOR, so the root SPECT never showed whole.
    The parts' meanings are kept by role; a word whose root part is already the root is unchanged."""
    text = _bare(word.word)
    alternatives = sorted({_bare(alt) for alt in head.split("/") if _bare(alt)}, key=len, reverse=True)
    roots = [part for part in word.parts if part.role == "root"]
    if not roots or _bare(roots[0].text) in alternatives:
        return word
    for alt in alternatives:
        at = text.find(alt)
        if at < 0:
            continue
        meaning = {part.role: part.meaning for part in word.parts}
        pieces = [(text[:at], "prefix"), (alt, "root"), (text[at + len(alt):], "suffix")]
        parts = [FamilyPart(text=piece, role=role, meaning=meaning.get(role, "")) for piece, role in pieces if piece]
        return word.model_copy(update={"parts": parts})
    return word


def usable_words(family: WordFamily) -> list[FamilyWord]:
    seen: set[str] = set()
    kept = []
    for word in family.words:
        key = _bare(word.word)
        fitted = fit_parts(word)
        if fitted and family.kind == "root":
            fitted = around_root(fitted, family.head)
        if key and key not in seen and fitted and key != _bare(family.quiz.word):
            seen.add(key)
            kept.append(fitted)
    return kept[:FAMILY_MAX_WORDS]


# Real run 2026-11-03: one Vietnamese sentence came back with Chinese characters in it ("tâm trạng也跟着 đi xuống")
_CJK = re.compile(r"[　-〿぀-ヿ㐀-䶿一-鿿가-힯＀-￯]+")


def _clean_text(value):
    if isinstance(value, str):
        return " ".join(_CJK.sub(" ", value).split())
    if isinstance(value, list):
        return [_clean_text(item) for item in value]
    if isinstance(value, dict):
        return {key: _clean_text(item) for key, item in value.items()}
    return value


def with_checked_facts(family: WordFamily, topic: str, lang: str) -> WordFamily:
    """Real run 2026-11-03: the AI left the origin empty although it was given; a listed head keeps its checked origin
    and meaning whatever the AI wrote, and the quiz word's parts are fitted like the others. Stray Chinese / Japanese /
    Korean characters are removed from every text."""
    family = WordFamily.model_validate(_clean_text(family.model_dump()))
    update: dict = {}
    quiz = fit_parts(family.quiz)
    if quiz:
        update["quiz"] = quiz
    found = find_seed(topic)
    if found:
        kind, entry = found
        heads = {_bare(alt) for alt in entry["head"].split("/")}
        given = {_bare(alt) for alt in family.head.split("/")}
        if entry.get("story") and given & heads:  # Phase 97 (D158): a true story comes only from this checked list, never from the AI
            update.update(puzzle=entry[f"puzzle_{lang}"], puzzle_word=entry["puzzle_word"],
                          story=[StoryBeat(text=beat[lang], picture=beat["picture"]) for beat in entry["story"]])
            # the story tells the puzzle's word itself; the other words come from the checked list when enough of them do
            others = [word for word in family.words if _bare(word.word) != _bare(entry["puzzle_word"])]
            listed = [word for word in others if _bare(word.word) in {_bare(item) for item in entry["words"]}]
            update["words"] = listed if len(listed) >= FAMILY_MIN_WORDS else others
        if given & heads:  # "-tion / -sion" or "-tion" both name the listed "-tion / -sion"
            update.update(kind=kind, head=entry["head"], origin_lang=entry["origin_lang"], origin_form=entry["origin_form"],
                          head_meaning=entry["meaning_vi"] if lang == "vi" else entry["meaning_en"])
    family = family.model_copy(update=update)
    if family.kind == "root":  # the quiz word is split around the whole root like the others
        family = family.model_copy(update={"quiz": around_root(family.quiz, family.head)})
    # sandbox run 2026-11-03: meanings ended in a stray ";" ("phát lại; xem lại...;")
    tidy = lambda word: word.model_copy(update={"meaning": word.meaning.strip().rstrip(";,.:").strip()})  # noqa: E731
    family = family.model_copy(update={"words": [tidy(word) for word in family.words], "quiz": tidy(family.quiz)})
    from backend.content.grammar_lesson import looks_english  # a local import: grammar_lesson imports this module

    if lang == "vi" and looks_english(family.quiz_clue):
        # sandbox run 2026-11-03: the RE- Short read an English clue in a Vietnamese video; the clue becomes the parts'
        # meanings ("Gợi ý: RE là lại, CYCLE là vòng.")
        hints = [f"{part.text.strip('-').upper()} là {part.meaning}" for part in family.quiz.parts if part.meaning.strip()]
        clue = "Gợi ý: " + ", ".join(hints) if hints else "Hãy đoán nghĩa từ các phần của nó"
        family = family.model_copy(update={"quiz_clue": clue})
    return family


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
    wheel = _card("wheel", head=family.head, kind=family.kind, words=[w.word for w in words] + [family.quiz.word])
    story = family.story[:4] if family.puzzle.strip() and len(family.story) >= 2 else []

    if story:  # Phase 97 (D158): the puzzle opens the video, the story further on answers it
        beats.append((family.puzzle.strip(), _card("puzzle", word=family.puzzle_word, head=family.head, kind=family.kind)))
        beats.append(((f"Sau video này, bạn sẽ hiểu và nhớ được {count} từ tiếng Anh chỉ từ một {kind} duy nhất!" if vi
                       else f"After this video, you'll remember {count} English words from just one {kind}!"), wheel))
    elif vi:
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

    for number, beat in enumerate(story, start=1):
        beats.append((_sentence(beat.text), _card("story", word=f"story {number}", picture=beat.picture)))

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
    for _, card in beats:  # the renderer marks the family's own part (root, prefix or suffix) in brand green
        if card.get("parts"):
            card["kind"] = family.kind
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
             f"Use first every word the topic names. Choose {FAMILY_MIN_WORDS + 1} to {FAMILY_MAX_WORDS} common English words found in a learner's dictionary, that truly come from this head (not words that only look alike), useful for "
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
        "- meaning: the word's usual meaning as a short dictionary gloss of two to four words (bày tỏ; nén lại; gây ấn "
        "tượng), never a whole explanation.\n"
        "- parts: never add an empty part; for a suffix family the base part is the letters the word really has "
        "(deci + sion for decision, happi + ness for happiness).\n"
        "- logic: never write the labels ROOT, PREFIX or SUFFIX and never invent an origin; name the parts themselves. "
        "ONE short sentence that explains how the parts give the meaning, like a memory trick "
        "(e.g. 'COM là cùng nhau, PRESS là ép: ép sát vào nhau thì chiếm ít chỗ hơn, nên compress là nén lại.').\n"
        "- example_en: one short natural B1 sentence with the word; example_vi: its translation.\n"
        "- picture: a simple object scene for a line drawing that shows the meaning, in English, no people's faces "
        "and no text (e.g. 'a computer monitor showing a zipped folder').\n"
        f"- icons: one or two names from this list that show the same idea: {', '.join(icon_names())}.\n"
        "- origin_lang / origin_form: only when you are sure (e.g. Latin, 'premere → pressus'); otherwise empty.\n"
        "- head_logic: one sentence showing the head's own meaning in an everyday action; head_example_en a short "
        "sentence with the bare head when it is a word (else empty).\n"
        "- quiz: one more family word, with parts; quiz_clue is ONE sentence of at most 20 words that describes a situation that shows its meaning without "
        "saying the word or its translation.\n"
        "Return ONLY a JSON object that validates against the schema."
    )
