"""Phase 90 (D128–D130): edit a word-roots or grammar Short on its video.

Each line of these Shorts carries its beat card in `language_notes` (`roots` or `grammar`). This module reads the lines
with their cards and the props of a live 9:16 preview, saves edited cards (checked by kind, the spoken text and its
audio untouched) and saves one line's spoken text (only that line's audio is made again).
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Literal

import aiosqlite
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.core.exceptions import NotFoundError, ValidationError

EDITED_STYLES = ("grammar", "roots", "slowpod", "flashcards", "chat", "wyr")
SECONDS_PER_CHARACTER = 0.075  # a silent preview's estimated timing, before the audio is made
MIN_LINE_SECONDS = 1.6
GRAMMAR_ITEM_KINDS = ("formulas", "stamp", "promise", "formula", "lego", "compare", "table", "example", "rule", "sticker",
                      "core", "quiz")
ROLES = ("s", "v", "o", "be", "ing", "v3", "modal", "have", "adj", "plain")


def _clip(value, size: int) -> str:
    return " ".join(str(value or "").split())[:size]


class _Card(BaseModel):
    model_config = ConfigDict(extra="ignore")


class Chip(_Card):
    text: str = Field(min_length=1, max_length=24)
    role: str = "plain"

    @field_validator("role", mode="before")
    @classmethod
    def known_role(cls, value):
        value = str(value or "plain").strip().lower()
        return value if value in ROLES else "plain"


class GrammarItem(_Card):
    kind: Literal[GRAMMAR_ITEM_KINDS]  # type: ignore[valid-type]
    text: str = Field(default="", max_length=200)
    items: list[str] = Field(default_factory=list, max_length=6)
    chips: list[Chip] = Field(default_factory=list, max_length=8)
    result: Chip | None = None
    left_en: str = Field(default="", max_length=100)
    left_vi: str = Field(default="", max_length=120)
    right_en: str = Field(default="", max_length=100)
    right_vi: str = Field(default="", max_length=120)
    columns: list[str] = Field(default_factory=list, max_length=4)
    rows: list[list[str]] = Field(default_factory=list, max_length=6)
    en: str = Field(default="", max_length=140)
    vi: str = Field(default="", max_length=160)
    marks: list[Chip] = Field(default_factory=list, max_length=4)
    options: list[str] = Field(default_factory=list, max_length=3)


class GrammarCard(_Card):
    beat: str = Field(min_length=1, max_length=20)
    scene: int = Field(default=0, ge=0, le=20)
    label: str = Field(default="", max_length=40)
    title: str = Field(default="", max_length=80)
    subtitle: str = Field(default="", max_length=120)
    cards: list[GrammarItem] = Field(default_factory=list, max_length=5)


class RootsPart(_Card):
    text: str = Field(min_length=1, max_length=20)
    role: Literal["prefix", "root", "suffix"]
    meaning: str = Field(default="", max_length=40)


class RootsCard(_Card):
    beat: str = Field(min_length=1, max_length=20)
    word: str = Field(default="", max_length=30)
    words: list[str] = Field(default_factory=list, max_length=10)
    parts: list[RootsPart] = Field(default_factory=list, max_length=4)
    head: str = Field(default="", max_length=30)
    kind: str = Field(default="", max_length=10)
    meaning: str = Field(default="", max_length=80)
    breakdown: str = Field(default="", max_length=160)
    origin: str = Field(default="", max_length=60)
    origin_lang: str = Field(default="", max_length=30)
    example_en: str = Field(default="", max_length=160)
    example_vi: str = Field(default="", max_length=180)
    answer: str = Field(default="", max_length=60)
    picture: str = Field(default="", max_length=160)
    icons: list[str] = Field(default_factory=list, max_length=4)


def _compact(value):
    """Empty optional fields are left out, as the script builders write them."""
    if isinstance(value, dict):
        return {key: _compact(item) for key, item in value.items() if item not in (None, "", [])}
    if isinstance(value, list):
        return [_compact(item) for item in value]
    return value


def checked_card(style: str, card: dict) -> dict:
    """The card as stored: checked by kind, unknown keys dropped (ValidationError when it cannot be drawn)."""
    try:
        model = GrammarCard if style == "grammar" else RootsCard
        checked = model.model_validate(card).model_dump()
    except Exception as exc:  # pydantic's message names the field
        raise ValidationError(f"The card cannot be saved: {str(exc)[:300]}") from exc
    if style == "grammar":
        checked["cards"] = [{key: value for key, value in item.items() if value not in (None, "", [])}
                            for item in checked["cards"]]
        checked["scene"] = card.get("scene", checked["scene"])
    return _compact(checked) | ({"cards": checked["cards"]} if style == "grammar" else {})


def card_key(project: dict) -> str:
    """The kind of on-screen data a line-drawn Short's lines carry (Phase 90: word roots, grammar; Phase 91: the slow
    podcast's translation, a flashcard's word card, chat and would-you-rather messages)."""
    style = project.get("explainer_style")
    if style not in EDITED_STYLES:
        raise ValidationError("This kind of video is not edited in this editor")
    return style


def _norm(text: str) -> str:
    return " ".join(re.sub(r"[^\w' ]", " ", re.sub(r"^to\s+", "", (text or "").strip().lower())).split())


def card_word(text: str) -> str | None:
    """The word of a flashcard line ("wash up. wash up." -> "wash up"), the rule of learning_pipeline.flashcard_words."""
    match = re.match(r"^\s*(.{1,60}?)[.!?]\s+\1[.!?]?\s*$", (text or "").strip(), re.IGNORECASE)
    return match.group(1).strip() if match else None


def _vocab_item(learning: dict | None, word: str) -> dict | None:
    return next((item for item in (learning or {}).get("vocabulary") or [] if _norm(item.get("word")) == _norm(word)), None)


def _line_card(style: str, notes: dict, text: str, learning: dict | None) -> dict:
    if style in ("grammar", "roots"):
        return notes.get(style) or {}
    if style == "slowpod":
        return {"translation_vi": notes.get("translation_vi", "")}
    if style == "flashcards":
        word = card_word(text)
        if not word:
            return {}
        item = _vocab_item(learning, word) or {}
        return {"word": word, "part_of_speech": item.get("part_of_speech", ""), "ipa": item.get("ipa", ""),
                "definition_vi": item.get("definition_vi", "")}
    return {}


def _learning_props(learning: dict | None, project: dict) -> dict | None:
    """The lesson as the render gives it (video_renderer_remotion._build_input_props)."""
    if learning is None:
        return None
    return {"vocab": [{"word": item["word"], "partOfSpeech": item["part_of_speech"], "ipa": item["ipa"],
                       "definitionEn": item["definition_en"], "definitionVi": item["definition_vi"],
                       "exampleSentence": item["example_sentence"]} for item in learning["vocabulary"]],
            "idioms": [{"phrase": item["phrase"], "meaningEn": item["meaning_en"], "meaningVi": item["meaning_vi"],
                        "exampleSentence": item["example_sentence"]} for item in learning["idioms"]],
            "audience": project.get("audience_effective") or "both"}


async def _lines(db: aiosqlite.Connection, project_id: str) -> list[dict]:
    cursor = await db.execute(
        "SELECT id, line_index, speaker_id, text, language_notes, audio_cache_path FROM script_lines "
        "WHERE project_id = ? ORDER BY line_index", (project_id,))
    return [dict(row) for row in await cursor.fetchall()]


def _estimated(lines: list[dict]) -> list[tuple[float, float]]:
    spans, start = [], 0.3
    for line in lines:
        length = max(MIN_LINE_SECONDS, len(line["text"]) * SECONDS_PER_CHARACTER)
        spans.append((round(start, 3), round(start + length, 3)))
        start += length + 0.25
    return spans


def picture_url(project_id: str, name: str) -> str:
    return f"/api/projects/{project_id}/beats/pictures/{name}"


async def load(db: aiosqlite.Connection, project_id: str) -> dict:
    """The lines with their cards and the props of a live 9:16 preview (with the audio when it matches the script, else
    silent with estimated timings). Only public URLs reach the browser."""
    from backend.ai.tts import tts_service
    from backend.content import learning_service, project_service
    from backend.media import audio_service, roots_pictures
    from backend.media.video_renderer_remotion import VIDEO_FPS, _words_to_props

    project = await project_service.get_project(db, project_id)
    key = card_key(project)
    lines = await _lines(db, project_id)
    if not lines:
        raise NotFoundError("This Short has no script yet")
    learning = await learning_service.get_learning_content(db, project_id)
    audio = await audio_service.get_audio_job(db, project_id)
    timestamps = (audio or {}).get("timestamps") or []
    with_audio = (audio or {}).get("status") == "complete" and [entry["text"] for entry in timestamps] == [
        line["text"] for line in lines]
    words = (audio or {}).get("word_timestamps") or [] if with_audio else []
    spans = [(entry["start_sec"], entry["end_sec"]) for entry in timestamps] if with_audio else _estimated(lines)
    folder = roots_pictures.roots_folder(project_id)
    speakers = {speaker["id"]: speaker for speaker in project["speakers"]}
    out_lines, prop_lines = [], []
    for index, line in enumerate(lines):
        card = _line_card(key, json.loads(line["language_notes"] or "{}") or {}, line["text"], learning)
        speaker = speakers.get(line["speaker_id"]) or project["speakers"][0]
        audio_ok = await asyncio.to_thread(tts_service.cache_matches, project, line)
        out_lines.append({"id": line["id"], "index": index, "text": line["text"], "card": card, "audio_ok": audio_ok,
                          "speaker": speaker["name"]})
        prop = {"startSec": spans[index][0], "endSec": spans[index][1], "speaker": speaker["name"],
                "speakerId": speaker["id"], "text": line["text"],
                "words": _words_to_props(words[index]["words"]) if index < len(words) else []}
        if key in ("grammar", "roots"):
            drawn = dict(card)
            if key == "roots" and card.get("word"):
                name = f"{roots_pictures.picture_key(card['word'])}.png"
                if (folder / name).is_file():
                    drawn["pictureUrl"] = picture_url(project_id, name)
            prop[key] = drawn
        elif key == "slowpod":
            prop["translation"] = card["translation_vi"]
        prop_lines.append(prop)
    props = {"episodeId": project_id, "lines": prop_lines, "shortStyle": project["explainer_style"],
             "speakers": [{"id": s["id"], "name": s["name"], "gender": s["gender"]} for s in project["speakers"]],
             "audioPath": f"/api/projects/{project_id}/audio/download?format=mp3" if with_audio else "",
             "fps": VIDEO_FPS, "width": 1080, "height": 1920, "title": project["name"], "topic": project["topic"],
             "cefrLevel": project["cefr_level"], "chapters": [], "captionStyle": "outline", "introSec": 0, "outroSec": 0,
             "outroText": "", "visualMode": "podcast_black", "layout": "vertical", "presentationMode": "classic",
             "durationSeconds": round(spans[-1][1] + 0.6, 3)}
    if (lesson := _learning_props(learning, project)) is not None:
        props["learning"] = lesson
    return {"style": project["explainer_style"], "key": key, "with_audio": with_audio, "lines": out_lines, "props": props}


class SlowpodCard(_Card):
    translation_vi: str = Field(default="", max_length=600)


class FlashCard(_Card):
    part_of_speech: str = Field(default="", max_length=30)
    ipa: str = Field(default="", max_length=60)
    definition_vi: str = Field(default="", max_length=160)


async def save_cards(db: aiosqlite.Connection, project_id: str, edits: list[dict]) -> int:
    """Each edited line's card, checked by kind; the text and its audio stay (D130). The caller holds a write
    transaction. A project whose video was made goes back to "audio made" (the video is out of date)."""
    from backend.content import learning_service, project_service

    project = await project_service.get_project(db, project_id)
    key = card_key(project)
    if key in ("chat", "wyr"):
        raise ValidationError("A chat or would-you-rather Short shows its messages: edit the spoken lines")
    lines = {line["id"]: line for line in await _lines(db, project_id)}
    learning = await learning_service.get_learning_content(db, project_id) if key == "flashcards" else None
    vocabulary = [dict(item) for item in (learning or {}).get("vocabulary") or []]
    for edit in edits:
        line = lines.get(edit.get("line_id"))
        if line is None:
            raise NotFoundError(f"Script line {edit.get('line_id')} not found in project {project_id}")
        notes = json.loads(line["language_notes"] or "{}") or {}
        if key == "flashcards":  # Phase 91: a word card's fields live in the lesson's vocabulary
            word = card_word(line["text"])
            if not word:
                raise ValidationError("Only a word line of the deck has a card")
            if learning is None:
                raise ValidationError("Make the lesson (Step 3) first: the cards come from its vocabulary")
            card = FlashCard.model_validate(edit.get("card") or {})
            item = _vocab_item({"vocabulary": vocabulary}, word)
            if item is None:
                item = {"word": word, "part_of_speech": "", "ipa": "", "definition_en": "", "definition_vi": "",
                        "example_sentence": ""}
                vocabulary.append(item)
            item.update(part_of_speech=_clip(card.part_of_speech, 30), ipa=_clip(card.ipa, 60),
                        definition_vi=_clip(card.definition_vi, 160))
            continue
        if key == "slowpod":  # Phase 91: the Vietnamese translation under the line
            notes["translation_vi"] = _clip(SlowpodCard.model_validate(edit.get("card") or {}).translation_vi, 600)
        else:
            notes[key] = checked_card(key, edit.get("card") or {})
        await db.execute("UPDATE script_lines SET language_notes = ? WHERE id = ? AND project_id = ?",
                         (json.dumps(notes, ensure_ascii=False), line["id"], project_id))
    if key == "flashcards" and learning is not None:
        await learning_service.update_learning_content(db, project_id, {"vocabulary": vocabulary}, commit=False)
    if project["status"] in ("video_generated", "complete"):
        await db.execute("UPDATE projects SET status = 'audio_generated' WHERE id = ?", (project_id,))
    return len(edits)


async def save_text(db: aiosqlite.Connection, project_id: str, line_id: str, text: str) -> dict:
    """One line's spoken text, for any kind of video (Phase 91.3); its notes are kept and only its audio must be made
    again. The caller holds a write transaction."""
    from backend.content import project_service, script_service

    await project_service.get_project(db, project_id)
    line = await script_service.get_script_line(db, project_id, line_id)
    updated = await script_service.update_script_line(db, project_id, line_id, text, line["language_notes"] or {},
                                                      commit=False)
    await project_service.mark_script_changed(db, project_id, commit=False)
    return updated


async def spoken_lines(db: aiosqlite.Connection, project_id: str) -> list[dict]:
    """Every line of any kind of video with its speaker and whether its voice still matches (Phase 91.3)."""
    from backend.ai.tts import tts_service
    from backend.content import project_service

    project = await project_service.get_project(db, project_id)
    speakers = {speaker["id"]: speaker["name"] for speaker in project["speakers"]}
    out = []
    for index, line in enumerate(await _lines(db, project_id)):
        out.append({"id": line["id"], "index": index, "text": line["text"], "speaker": speakers.get(line["speaker_id"], ""),
                    "audio_ok": await asyncio.to_thread(tts_service.cache_matches, project, line)})
    return out


def picture_path(project_id: str, name: str) -> Path:
    """A drawn word picture of this project (the name only, no path)."""
    from backend.media import roots_pictures

    path = roots_pictures.roots_folder(project_id) / Path(name).name
    if path.suffix.lower() != ".png" or not path.is_file():
        raise NotFoundError("No such picture")
    return path
