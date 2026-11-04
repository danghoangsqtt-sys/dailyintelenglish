"""Phase 84 (owner 2026-10-28): the editor pass every automatic script gets before its voice is made.

The AI scores the script 1-5 on what makes a video worth watching (the hook, one clear message, concrete examples,
natural spoken English, the CEFR level, the ending). Any score under 4 asks for one rewrite with the editor's notes; the
rewrite is kept only when it passes every existing script check, otherwise the original stays. The review is saved
(`script_reviews`) and shown on Step 2.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

import aiosqlite
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel, Field, TypeAdapter

from backend.ai.llm.contracts import GenerationRequest
from backend.ai.llm.router import AIRouter, build_ai_router_from_settings
from backend.ai.llm.validation import parse_and_validate
from backend.core.config import settings
from backend.core.exceptions import ProviderError, SchemaValidationError, ValidationError
from backend.core.paths import PROMPTS_DIR
from backend.db.transactions import read_transaction, write_transaction
from backend.schemas.project import is_short_video

logger = logging.getLogger(__name__)
_env = Environment(loader=FileSystemLoader(str(PROMPTS_DIR / "script")), undefined=StrictUndefined)
CRITERIA = ("hook", "message", "examples", "natural", "level", "ending")
PASS_SCORE = 4
SOURCE_LIMIT = 6000
# A flashcard deck and a slow podcast (with its translations) are built line by line: the editor leaves them alone
SKIPPED_STYLES = ("flashcards", "slowpod", "roots", "grammar", "wordday", "whatis", "levelup", "picstory", "loadword")  # Phase 87/88: a word family's or a lesson's beats too


class EditorScores(BaseModel):
    hook: int = Field(ge=1, le=5)
    message: int = Field(ge=1, le=5)
    examples: int = Field(ge=1, le=5)
    natural: int = Field(ge=1, le=5)
    level: int = Field(ge=1, le=5)
    ending: int = Field(ge=1, le=5)


class EditorReview(BaseModel):
    scores: EditorScores
    notes: str = Field(default="", max_length=1500)


class RewrittenLine(BaseModel):
    speaker: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=600)


class Rewrite(BaseModel):
    lines: list[RewrittenLine] = Field(min_length=1, max_length=400)


_REVIEW, _REWRITE = TypeAdapter(EditorReview), TypeAdapter(Rewrite)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def applies_to(project: dict) -> bool:
    return project.get("explainer_style") not in SKIPPED_STYLES


async def get_review(db: aiosqlite.Connection, project_id: str) -> dict | None:
    cursor = await db.execute("SELECT * FROM script_reviews WHERE project_id = ?", (project_id,))
    row = await cursor.fetchone()
    if row is None:
        return None
    value = dict(row)
    value["scores"] = json.loads(value.pop("scores_json"))
    value["rewritten"] = bool(value["rewritten"])
    return value


async def _ask(router: AIRouter, prompt: str, schema: type[BaseModel], adapter: TypeAdapter, purpose: str):
    try:
        result = await router.generate(GenerationRequest(prompt=prompt, json_schema=schema.model_json_schema(),
                                                         deadline_seconds=settings.AI_REQUEST_DEADLINE_SECONDS, purpose=purpose))
        return parse_and_validate(result.text, adapter)
    except SchemaValidationError as exc:
        raise ValidationError(f"The AI editor's answer was not usable ({exc})") from exc
    except ProviderError as exc:
        raise ValidationError(f"The AI editor could not work right now ({type(exc).__name__})") from exc


def _rewrite_problems(project: dict, lines: list[dict], target_words: int) -> list[str]:
    """Every existing whole-script check, as for a newly written script."""
    from backend.content import script_pipeline

    candidate = [script_pipeline.SectionLineOut(speaker_id=line["speaker_id"], text=line["text"]) for line in lines]
    known = {speaker["id"] for speaker in project["speakers"]}
    errors, _warnings = script_pipeline.validate_global(
        candidate, target_words, known, len(project["speakers"]), project["topic"],
        allow_repeats=project.get("explainer_style") == "listen", tolerance_share=script_pipeline.word_tolerance(project))
    return errors


async def review(db: aiosqlite.Connection, project_id: str, router: AIRouter | None = None) -> dict:
    """Score the current script, rewrite it once when a score is under 4, save the review and return it."""
    from backend.content import export_service, project_service, script_pipeline, script_service

    async with read_transaction():
        project = await project_service.get_project(db, project_id)
        lines = await script_service.get_script(db, project_id)
    if not lines:
        raise ValidationError("Write the script first: the editor reads it")
    if not applies_to(project):
        raise ValidationError("Flashcard decks and slow podcasts are built line by line; the editor leaves them as they are")
    names = {speaker["id"]: speaker["name"] for speaker in project["speakers"]}
    ids = {name.casefold(): speaker_id for speaker_id, name in names.items()}
    target_words = script_pipeline.compute_target_words(project["cefr_level"], project["duration_minutes"])
    words_before = sum(len(line["text"].split()) for line in lines)
    context = {"topic": project["topic"], "cefr_level": project["cefr_level"], "short": is_short_video(project),
               "source": (project.get("source_text") or "")[:SOURCE_LIMIT],
               "cold_open": project.get("explainer_style") == "vox",  # Phase 86: a VOX script opens on an example, no greeting
               "style": project.get("explainer_style") or "conversation", "target_words": target_words,
               "lines": [{"speaker": names.get(line["speaker_id"], "Narrator"), "text": line["text"]} for line in lines]}
    router = router or build_ai_router_from_settings()
    prompt = await asyncio.to_thread(_env.get_template("editor_review.txt").render, **context)
    verdict = await _ask(router, prompt, EditorReview, _REVIEW, "script_editor_review")
    scores = verdict.scores.model_dump()
    rewritten, words_after, outcome, rejected = False, words_before, "passed", ""
    if min(scores.values()) < PASS_SCORE:
        outcome = "kept_original"
        prompt = await asyncio.to_thread(_env.get_template("editor_rewrite.txt").render, notes=verdict.notes,
                                         scores=scores, current_words=words_before, **context)
        old_notes = {line["text"].strip(): line.get("language_notes") for line in lines}

        async def attempt(text: str) -> tuple[list[dict], list[str]]:
            try:
                answer = await _ask(router, text, Rewrite, _REWRITE, "script_editor_rewrite")
            except ValidationError as exc:
                return [], [str(exc)]
            written = [{"speaker_id": ids.get(line.speaker.strip().casefold()), "text": " ".join(line.text.split()),
                        "language_notes": old_notes.get(" ".join(line.text.split()))} for line in answer.lines]
            if any(line["speaker_id"] is None for line in written):
                return written, ["the rewrite named a speaker who is not in the cast"]
            return written, _rewrite_problems(project, written, target_words)

        new_lines, problems = await attempt(prompt)
        if problems and all(problem.startswith("total word count") for problem in problems):
            # Real run 2026-10-28: a long rewrite came back 10 % short (contractions shrink a script); it is asked once
            # to fit the length, saying how far off it is
            have = sum(len(line["text"].split()) for line in new_lines)
            note = (f"LENGTH: your previous rewrite had {have} words but the script needs about {target_words}. "
                    f"{'Add about ' + str(target_words - have) + ' words of natural lines and everyday examples' if have < target_words else 'Remove about ' + str(have - target_words) + ' words'}"
                    ", keeping every improvement.")
            retry = await asyncio.to_thread(_env.get_template("editor_rewrite.txt").render, notes=verdict.notes, scores=scores,
                                            current_words=words_before, length_note=note, **context)
            new_lines, problems = await attempt(retry)
        if problems:
            rejected = "; ".join(problems[:3])[:500]
            logger.warning("script_editor_rewrite_rejected project_id=%s problems=%s", project_id, rejected)
        else:
            for line in new_lines:
                if not line["language_notes"]:
                    line.pop("language_notes")
            async with write_transaction(db):
                await script_service.save_script(db, project_id, new_lines, set(names), commit=False)
                await project_service.mark_script_changed(db, project_id, commit=False)
            rewritten, outcome = True, "rewritten"
            words_after = sum(len(line["text"].split()) for line in new_lines)
    async with write_transaction(db):
        await db.execute(
            "INSERT INTO script_reviews (project_id, scores_json, notes, outcome, rewritten, words_before, words_after, "
            "rejected_reason, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(project_id) DO UPDATE SET "
            "scores_json = excluded.scores_json, notes = excluded.notes, outcome = excluded.outcome, "
            "rewritten = excluded.rewritten, words_before = excluded.words_before, words_after = excluded.words_after, "
            "rejected_reason = excluded.rejected_reason, created_at = excluded.created_at",
            (project_id, json.dumps(scores), verdict.notes.strip(), outcome, int(rewritten), words_before, words_after,
             rejected, _now()))
    if rewritten:
        await export_service.sync_quietly(db, project_id)
    async with read_transaction():
        return await get_review(db, project_id)
