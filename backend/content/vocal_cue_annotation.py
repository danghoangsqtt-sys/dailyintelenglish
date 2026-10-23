"""Optional, validated AI placements for inline vocal directions."""

from __future__ import annotations

import logging
import math
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from backend.ai.llm.contracts import GenerationRequest
from backend.ai.llm.prompt_loader import render_vocal_cue_prompt
from backend.ai.llm.router import AIRouter
from backend.ai.llm.validation import parse_and_validate
from backend.ai.tts.vocal_cues import caption_text, split_vocal_cues
from backend.core.config import settings
from backend.core.constants import (
    VOCAL_CUE_MAX_PER_MINUTE, VOCAL_CUE_MIN_GAP_SECONDS,
    VOCAL_CUE_PROMPT_MAX_LINES, VOCAL_CUE_PROMPT_MAX_WORDS_PER_LINE,
)

logger = logging.getLogger(__name__)
_WORDS = re.compile(r"\S+")


class CuePlacement(BaseModel):
    """One model-proposed cue location; dialogue text is never model-owned."""

    model_config = ConfigDict(extra="forbid")
    line_index: int = Field(ge=0)
    after_word_index: int = Field(ge=0)
    cue_type: Literal["laugh", "sigh", "ahem"]
    variant: Literal["ha-ha", "hi-hi"] | None = None


class CuePlan(BaseModel):
    """The entire optional annotation response."""

    model_config = ConfigDict(extra="forbid")
    cues: list[CuePlacement]


_PLAN = TypeAdapter(CuePlan)


def cue_quota(duration_minutes: float) -> int:
    """Return the hard maximum for the episode's requested duration."""
    return max(0, math.ceil(float(duration_minutes) * VOCAL_CUE_MAX_PER_MINUTE))


def count_cues(lines: list[dict]) -> int:
    """Count recognized tags already present in user or generated dialogue."""
    return sum(part.kind == "cue" for line in lines for part in split_vocal_cues(line["text"]))


def _tag(cue: CuePlacement) -> str | None:
    if cue.cue_type == "laugh":
        if cue.variant not in ("ha-ha", "hi-hi"):
            return None
        return f"[cười:{cue.variant}]"
    if cue.variant is not None:
        return None
    return "[thở dài]" if cue.cue_type == "sigh" else "[hắng giọng]"


def _insert(text: str, word_index: int, tag: str) -> str | None:
    words = list(_WORDS.finditer(text))
    if not words or word_index > len(words):
        return None
    offset = 0 if word_index == 0 else words[word_index - 1].end()
    left, right = text[:offset], text[offset:]
    inserted = f"{left}{' ' if left and not left[-1].isspace() else ''}{tag}{' ' if right and not right[0].isspace() else ''}{right}"
    return inserted if caption_text(inserted) == caption_text(text) else None


def apply_cue_plan(lines: list[dict], plan: CuePlan, *, duration_minutes: float,
                   existing_count: int = 0,
                   min_gap_seconds: float = VOCAL_CUE_MIN_GAP_SECONDS) -> tuple[list[dict], int]:
    """Apply valid placements without allowing the model to rewrite dialogue."""
    result = [dict(line) for line in lines]
    remaining = max(0, cue_quota(duration_minutes) - existing_count - count_cues(result))
    if not remaining:
        return result, 0
    word_counts = [len(_WORDS.findall(caption_text(line["text"]))) for line in result]
    total_words = max(1, sum(word_counts))
    elapsed_words = [sum(word_counts[:i]) for i in range(len(result))]
    used_lines: set[int] = set()
    positions: list[float] = []
    for index, line in enumerate(result):
        prior_words = 0
        for part in split_vocal_cues(line["text"]):
            if part.kind == "speech":
                prior_words += len(_WORDS.findall(part.text))
            elif part.kind == "cue":
                positions.append((elapsed_words[index] + prior_words) / total_words * duration_minutes * 60)
    accepted = 0
    for cue in plan.cues:
        index = cue.line_index
        if index >= len(result) or index in used_lines or accepted >= remaining:
            continue
        if any(part.kind == "cue" for part in split_vocal_cues(result[index]["text"])):
            continue
        tag = _tag(cue)
        if tag is None or cue.after_word_index > word_counts[index]:
            continue
        position = (elapsed_words[index] + cue.after_word_index) / total_words * duration_minutes * 60
        if any(abs(position - previous) < min_gap_seconds for previous in positions):
            continue
        inserted = _insert(result[index]["text"], cue.after_word_index, tag)
        if inserted is None:
            continue
        result[index]["text"] = inserted
        used_lines.add(index)
        positions.append(position)
        accepted += 1
    return result, accepted


async def annotate_script_lines(lines: list[dict], project: dict, router: AIRouter, *,
                                existing_count: int = 0,
                                min_gap_seconds: float = VOCAL_CUE_MIN_GAP_SECONDS) -> tuple[list[dict], str | None]:
    """Get optional cue placements; return original clean lines on provider failure."""
    quota = cue_quota(project["duration_minutes"])
    available = max(0, quota - existing_count - count_cues(lines))
    if not available or not lines:
        return lines, None
    context_indices = [int(index * len(lines) / min(len(lines), VOCAL_CUE_PROMPT_MAX_LINES))
                       for index in range(min(len(lines), VOCAL_CUE_PROMPT_MAX_LINES))]
    context = [{"line_index": i, "speaker_id": lines[i]["speaker_id"],
                "text": " ".join(lines[i]["text"].split()[:VOCAL_CUE_PROMPT_MAX_WORDS_PER_LINE])}
               for i in context_indices]
    speakers = [{"id": speaker["id"], "name": str(speaker.get("name") or "")[:80],
                 "gender": speaker.get("gender", ""), "accent": speaker.get("accent", ""),
                 "voice_description": str(speaker.get("voice_description") or "")[:160]}
                for speaker in project["speakers"]]
    try:
        prompt = await render_vocal_cue_prompt(topic=project["topic"], speakers=speakers,
                                               lines=context, max_new_cues=available)
        result = await router.generate(GenerationRequest(
            prompt=prompt, json_schema=_PLAN.json_schema(),
            deadline_seconds=settings.AI_REQUEST_DEADLINE_SECONDS,
            purpose="script_vocal_cues",
        ))
        plan = parse_and_validate(result.text, _PLAN)
        eligible = set(context_indices)
        unseen = sum(cue.line_index not in eligible for cue in plan.cues)
        if unseen:
            logger.warning("Skipped %s vocal cue placements outside supplied context", unseen)
        plan = plan.model_copy(update={"cues": [cue for cue in plan.cues if cue.line_index in eligible]})
        annotated, accepted = apply_cue_plan(
            lines, plan, duration_minutes=project["duration_minutes"],
            existing_count=existing_count, min_gap_seconds=min_gap_seconds,
        )
        if accepted < len(plan.cues):
            logger.warning("Skipped %s invalid or over-budget vocal cue placements", len(plan.cues) - accepted)
        return annotated, None
    except Exception as exc:  # optional enhancement must not discard validated dialogue
        logger.warning("Optional vocal cue annotation failed: %s", type(exc).__name__)
        return lines, f"Vocal cue annotation unavailable ({type(exc).__name__}); clean dialogue preserved"
