"""Phase 88: the "Easy grammar" Short -- one grammar lesson turned into beats (the owner's sample B).

The AI returns a schema-checked `GrammarLesson`: the rote formulas it breaks, three to six scenes of cards that stack
as the narration reaches them, a summary table and the one core rule. A second AI pass checks the grammar (rules and
English examples) and returns the lesson corrected. The server builds the script lines: every line keeps its scene and
the cards shown so far in `language_notes.grammar`, which the renderer draws.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from backend.content.word_family import _clean_text

SCENES_MIN = 3
SCENES_MAX = 6
ROLES = ("s", "v", "o", "be", "ing", "v3", "modal", "have", "adj", "plain")
Role = Literal["s", "v", "o", "be", "ing", "v3", "modal", "have", "adj", "plain"]
CardKind = Literal["formula", "compare", "table", "rule", "example", "sticker", "stamp", "lego"]
GRAMMAR_FOLLOW = {"vi": "Comment đáp án và theo dõi Daily Beyond English nhé!",
                  "en": "Comment your answer and follow Daily Beyond English!"}
_STAMP = {"vi": "Quên hết đi!", "en": "Forget them all!"}
_HOOK_LABEL = {"vi": "HOOK • ĐẬP TAN HỌC VẸT", "en": "HOOK • NO MORE ROTE LEARNING"}
_SUMMARY_LABEL = {"vi": "TỔNG KẾT BẢN CHẤT", "en": "THE SUMMARY"}
_SUMMARY_INTRO = {"vi": "Tổng kết lại tất cả trong một bảng nhé.", "en": "Let's put it all in one table."}
_CORE_LABEL = {"vi": "CỐT LÕI DUY NHẤT", "en": "THE ONE CORE RULE"}
_QUIZ_LABEL = {"vi": "CÂU HỎI NHANH", "en": "QUICK QUIZ"}
_QUIZ_LEAD = {"vi": "Câu hỏi nhanh: ", "en": "Quick quiz: "}
# Vietnamese letters (beyond plain Latin) never belong in an English example
_VI_LETTERS = re.compile(r"[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹáàãéèíìóòõúùýđ]", re.IGNORECASE)


class Chip(BaseModel):
    text: str = Field(min_length=1, max_length=24)
    role: Role = "plain"

    @field_validator("role", mode="before")
    @classmethod
    def known_role(cls, value):
        value = str(value or "plain").strip().lower()
        return value if value in ROLES else "plain"


class GrammarCard(BaseModel):
    """One card; a flat object (the fields its kind needs are checked in `usable_card`)."""

    kind: CardKind
    text: str = Field(default="", max_length=140)
    chips: list[Chip] = Field(default_factory=list, max_length=8)
    left_en: str = Field(default="", max_length=80)
    left_vi: str = Field(default="", max_length=90)
    right_en: str = Field(default="", max_length=80)
    right_vi: str = Field(default="", max_length=90)
    columns: list[str] = Field(default_factory=list, max_length=4)
    rows: list[list[str]] = Field(default_factory=list, max_length=5)
    en: str = Field(default="", max_length=120)
    vi: str = Field(default="", max_length=140)
    marks: list[Chip] = Field(default_factory=list, max_length=4)
    result: Chip | None = None


class Step(BaseModel):
    say: str = Field(min_length=3, max_length=240)
    card: GrammarCard | None = None


class Scene(BaseModel):
    label: str = Field(min_length=1, max_length=30)
    title: str = Field(min_length=1, max_length=60)
    subtitle: str = Field(default="", max_length=90)
    steps: list[Step] = Field(min_length=1, max_length=4)


class Hook(BaseModel):
    pain: str = Field(min_length=3, max_length=200)
    formulas: list[str] = Field(min_length=2, max_length=6)
    promise: str = Field(min_length=3, max_length=200)


class SummaryRow(BaseModel):
    cells: list[str] = Field(min_length=1, max_length=4)  # a row that does not fit the columns is dropped
    say: str = Field(min_length=3, max_length=200)


class Summary(BaseModel):
    columns: list[str] = Field(min_length=2, max_length=4)
    rows: list[SummaryRow] = Field(min_length=2, max_length=5)


class Quiz(BaseModel):
    question: str = Field(min_length=3, max_length=140)
    options: list[str] = Field(min_length=2, max_length=3)
    answer: str = Field(default="", max_length=60)


class GrammarLesson(BaseModel):
    point: str = Field(min_length=2, max_length=60)
    kind: Literal["essence", "vietnamese_error"] = "essence"
    hook: Hook
    scenes: list[Scene] = Field(min_length=SCENES_MIN, max_length=SCENES_MAX + 2)
    summary: Summary
    core_rule: str = Field(min_length=3, max_length=200)
    quiz: Quiz | None = None


class LessonReview(BaseModel):
    """The second pass: what was wrong, and the lesson with it fixed."""

    issues: list[str] = Field(default_factory=list, max_length=20)
    lesson: GrammarLesson


def _english(text: str) -> str:
    """An English field keeps no Vietnamese letters; one that has them is not English and is emptied."""
    return "" if _VI_LETTERS.search(text or "") else " ".join((text or "").split())


def usable_card(card: GrammarCard | None) -> dict | None:
    """The card as drawn, or None when it lacks what its kind needs."""
    if card is None:
        return None
    kind = card.kind
    text = " ".join(card.text.split())
    if kind == "formula":
        chips = [chip.model_dump() for chip in card.chips if chip.text.strip()]
        return {"kind": kind, "chips": chips, **({"text": text} if text else {})} if len(chips) >= 2 else None
    if kind == "lego":
        chips = [chip.model_dump() for chip in card.chips if chip.text.strip()]
        if len(chips) >= 2 and card.result and card.result.text.strip():
            return {"kind": kind, "chips": chips, "result": card.result.model_dump()}
        return None
    if kind == "compare":
        left, right = _english(card.left_en), _english(card.right_en)
        if left and right:
            return {"kind": kind, "left_en": left, "left_vi": card.left_vi, "right_en": right, "right_vi": card.right_vi,
                    **({"text": text} if text else {})}
        return None
    if kind == "table":
        width = len(card.columns)
        rows = [row for row in card.rows if len(row) == width]
        return {"kind": kind, "columns": card.columns, "rows": rows} if width >= 2 and rows else None
    if kind == "example":
        en = _english(card.en)
        if not en:
            return None
        marks = [mark.model_dump() for mark in card.marks if mark.text.strip() and mark.text.lower() in en.lower()]
        return {"kind": kind, "en": en, "vi": card.vi, "marks": marks}
    # rule, sticker, stamp: a short text
    return {"kind": kind, "text": text} if text else None


def with_clean_text(lesson: GrammarLesson) -> GrammarLesson:
    """Stray Chinese / Japanese / Korean characters are removed from every text (as for the word family)."""
    return GrammarLesson.model_validate(_clean_text(lesson.model_dump()))


def _sentence(text: str) -> str:
    text = " ".join(text.split())
    text = text[:1].upper() + text[1:] if text else text
    return text if not text or text[-1] in ".!?…:" else text + "."


def _header(beat: str, scene: int, label: str, title: str, subtitle: str = "") -> dict:
    return {"beat": beat, "scene": scene, "label": label, "title": title, **({"subtitle": subtitle} if subtitle else {})}


def build_beats(lesson: GrammarLesson, lang: str) -> list[tuple[str, dict]]:
    """(spoken text, card) per line, in order. `lang` is the narration language: "vi" or "en". Each line's card carries
    its scene header and every card shown so far in that scene."""
    lang = "vi" if lang == "vi" else "en"
    beats: list[tuple[str, dict]] = []
    hook = _header("hook", 0, _HOOK_LABEL[lang], lesson.point.upper())
    formulas = {"kind": "formulas", "items": [" ".join(f.split()) for f in lesson.hook.formulas if f.strip()][:6]}
    beats.append((_sentence(lesson.hook.pain), {**hook, "cards": [formulas]}))
    beats.append((_STAMP[lang], {**hook, "cards": [formulas, {"kind": "stamp", "text": _STAMP[lang].rstrip("!").upper()}]}))
    beats.append((_sentence(lesson.hook.promise), {**hook, "cards": [{"kind": "promise", "text": _sentence(lesson.hook.promise)}]}))

    number = 0
    for scene in lesson.scenes:
        cards: list[dict] = []
        steps = []
        for step in scene.steps:
            card = usable_card(step.card)
            if card:
                cards = [*cards, card][-4:]  # at most four cards on screen; the oldest goes
            steps.append((_sentence(step.say), list(cards)))
        if not any(shown for _, shown in steps):
            continue  # a scene with no card to show is left out
        number += 1
        header = _header("scene", number, scene.label.upper(), scene.title, scene.subtitle)
        beats.extend((say, {**header, "cards": shown}) for say, shown in steps)
        if number == SCENES_MAX:
            break
    if number < SCENES_MIN:
        raise ValueError(f"only {number} scenes of the lesson have cards to show")

    summary = _header("summary", number + 1, _SUMMARY_LABEL[lang], lesson.point.upper())
    width = len(lesson.summary.columns)
    rows = [row for row in lesson.summary.rows if len(row.cells) == width]
    table = {"kind": "table", "columns": lesson.summary.columns}
    beats.append((_SUMMARY_INTRO[lang], {**summary, "cards": [{**table, "rows": []}]}))
    for count, row in enumerate(rows, start=1):
        beats.append((_sentence(row.say), {**summary, "cards": [{**table, "rows": [r.cells for r in rows[:count]]}]}))
    full = {**table, "rows": [r.cells for r in rows]}
    core = _header("core", number + 1, _CORE_LABEL[lang], lesson.point.upper())
    beats.append((_sentence(lesson.core_rule), {**core, "cards": [full, {"kind": "core", "text": _sentence(lesson.core_rule)}]}))

    quiz = lesson.quiz
    if quiz and _english(quiz.question) and all(_english(option) for option in quiz.options):
        card = {"kind": "quiz", "text": _english(quiz.question), "options": [_english(o) for o in quiz.options]}
        quiz_header = _header("quiz", number + 2, _QUIZ_LABEL[lang], lesson.point.upper())
        beats.append((_QUIZ_LEAD[lang] + _english(quiz.question), {**quiz_header, "cards": [card]}))
        beats.append((GRAMMAR_FOLLOW[lang], {**quiz_header, "beat": "follow", "cards": [card]}))
    else:
        beats.append((GRAMMAR_FOLLOW[lang], {**core, "beat": "follow", "cards": [full]}))
    return beats


_RULES = (
    "Card kinds (one card per step, or none when the step only talks about the cards already shown):\n"
    "- formula: chips that spell a structure, each with a colour role (S + BE + V3 → chips S/s, BE/be, V3/v3).\n"
    "- compare: two English sentences side by side (left_en/right_en) with their translations (left_vi/right_vi); text: "
    "what they share.\n"
    "- table: columns and up to five rows of short cells.\n"
    "- rule: one short rule in a pink box (text).\n"
    "- example: one natural English sentence (en), its translation (vi) and up to four words of it to colour (marks, "
    "each with a role).\n"
    "- sticker: a short word shown as a yellow label (text, e.g. CLEANED).\n"
    "- stamp: a red stamp with two or three words (text, e.g. KHÔNG CHIA THÌ).\n"
    "- lego: pieces that join (chips, e.g. BE/be + -ING/ing) and their result (result, e.g. BEING/be).\n"
    "Colour roles: s (subject), v (main verb), o (object), be (any form of to be), ing (-ing form), v3 (past participle), "
    "modal (can, must, will...), have (have / has / had), adj (adjective), plain (anything else).\n"
)


def grammar_prompt(topic: str, cefr: str, lang: str) -> str:
    language = "Vietnamese" if lang == "vi" else "English"
    learners = "Vietnamese learners" if lang == "vi" else "learners"
    return (
        f"You prepare one grammar lesson for a short English-learning video (about two minutes) for {learners} at CEFR "
        f"{cefr}. It explains the point by its essence instead of rote formulas.\n"
        f"Topic: {topic}\n"
        "Kinds: 'essence' explains one grammar point by one idea that makes every formula obvious (e.g. the passive is "
        "a sentence describing a state: S + BE + V3 like S + BE + adjective; TO BE carries the tense, V3 never changes). "
        "'vietnamese_error' explains a mistake Vietnamese speakers make because of Vietnamese (I very like, a missing "
        "tense or article, people is) and the one idea that fixes it.\n"
        f"Write every spoken sentence (say, pain, promise, core_rule), labels, titles, subtitles, Vietnamese fields "
        f"(*_vi, vi) and rule/stamp texts in {language}; English examples and formula chips are English.\n"
        "Structure:\n"
        "- hook.pain: one sentence about the pain of memorising many formulas for this point; hook.formulas: two to six "
        "of those rote formulas as short text (e.g. 'S + am/is/are + V3', 'S + has/have + been + V3'); hook.promise: one "
        "sentence promising to understand the point's essence in a minute.\n"
        f"- scenes: {SCENES_MIN} to {SCENES_MAX} scenes, ONE idea each, in teaching order, each with one easy memory "
        "image (a sticker that never moves, the one who carries the time, Lego pieces). label: two or three words "
        "(e.g. 'BẢN CHẤT CỐT LÕI'); title: a short punchy line; subtitle: optional.\n"
        "- steps: two to four per scene; say is ONE spoken sentence (at most 28 words) that goes with its card.\n"
        "- summary: a table (columns two to four, rows two to five) that sums up the whole point; each row's say reads "
        "the row as one sentence.\n"
        "- core_rule: the one rule to remember, one sentence.\n"
        "- quiz (optional): one English sentence with a blank (___) and two or three English options; answer is the "
        "right option.\n"
        f"{_RULES}"
        "Every English sentence must be natural and grammatically correct, and every rule must be true.\n"
        "Return ONLY a JSON object that validates against the schema."
    )


def review_prompt(lesson_json: str, lang: str) -> str:
    language = "Vietnamese" if lang == "vi" else "English"
    return (
        "You are an experienced English grammar teacher checking a lesson before it is published.\n"
        "Check: every rule and explanation is true; every English sentence is natural and grammatically correct; formula "
        "chips spell the structure and have the right colour role; summary rows agree with the scenes; the quiz has "
        "exactly one right option and answer is it; English fields contain only English and "
        f"{language} fields only {language}.\n"
        "Fix what is wrong and keep everything else exactly as it is. List each fix in issues (empty when nothing was "
        "wrong).\n"
        f"Lesson:\n{lesson_json}\n"
        "Return ONLY a JSON object {\"issues\": [...], \"lesson\": {...}} that validates against the schema."
    )
