"""Phase 84 (owner 2026-10-28): the AI fact check that lets News, VOX and long presenter videos finish by themselves.

A second AI pass reads each segment's narration and on-screen text against the topic and the owner's material and
answers `ok` or `doubtful` with a reason. Automation approves the plan only when every segment is `ok`; a doubtful
segment stops the episode for the owner. Nothing is saved here.
"""
from __future__ import annotations

import asyncio
import json
from datetime import date
from typing import Literal

import aiosqlite
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel, Field, TypeAdapter

from backend.ai.llm.contracts import GenerationRequest
from backend.ai.llm.router import AIRouter, build_ai_router_from_settings
from backend.ai.llm.validation import parse_and_validate
from backend.core.config import settings
from backend.core.exceptions import ProviderError, SchemaValidationError, ValidationError
from backend.core.paths import PROMPTS_DIR

_env = Environment(loader=FileSystemLoader(str(PROMPTS_DIR / "explainer")), undefined=StrictUndefined)
SOURCE_LIMIT = 6000
SCREEN_KEYS_SKIPPED = ("asset", "prompt", "kind")


class FactVerdict(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    verdict: Literal["ok", "doubtful"]
    reason: str = Field(default="", max_length=300)


class FactCheck(BaseModel):
    segments: list[FactVerdict] = Field(min_length=1, max_length=60)


_ADAPTER = TypeAdapter(FactCheck)


def screen_text(visual: dict) -> str:
    """What the viewer reads on screen for a segment: every text field of its visual, without file references."""
    return json.dumps({key: value for key, value in (visual or {}).items() if key not in SCREEN_KEYS_SKIPPED and value},
                      ensure_ascii=False)[:800]


async def check(db: aiosqlite.Connection, project_id: str, router: AIRouter | None = None) -> dict:
    """The AI's verdict per segment of the current plan: {"verdicts": [...], "all_ok": bool, "doubtful": [...]}."""
    from backend.content import project_service, script_service
    from backend.library import explainer_service

    view = await explainer_service.get_plan(db, project_id)
    plan = view.get("plan")
    if not plan:
        raise ValidationError("Propose the visual plan first: the fact check reads its segments")
    project = await project_service.get_project(db, project_id)
    texts = {line["id"]: line["text"] for line in await script_service.get_script(db, project_id)}
    segments = [{"id": segment["id"], "narration": " ".join(texts.get(line_id, "") for line_id in segment["line_ids"]).strip(),
                 "screen": screen_text(segment.get("visual") or {})} for segment in plan["segments"]]
    prompt = await asyncio.to_thread(
        _env.get_template("fact_check.txt").render, topic=project["topic"], style=project.get("explainer_style") or "",
        source=(project.get("source_text") or "")[:SOURCE_LIMIT], today=date.today().isoformat(), segments=segments)
    router = router or build_ai_router_from_settings()
    try:
        result = await router.generate(GenerationRequest(prompt=prompt, json_schema=FactCheck.model_json_schema(),
                                                         deadline_seconds=settings.AI_REQUEST_DEADLINE_SECONDS,
                                                         purpose="fact_check"))
        answer = parse_and_validate(result.text, _ADAPTER)
    except SchemaValidationError as exc:  # a ProviderError subclass: said plainly first
        raise ValidationError(f"The AI's fact check was not usable ({exc}); try again") from exc
    except ProviderError as exc:
        raise ValidationError(f"The AI could not check the facts right now ({type(exc).__name__}); try again") from exc
    by_id = {item.id: item for item in answer.segments}
    verdicts = [(by_id.get(segment["id"]) or FactVerdict(id=segment["id"], verdict="doubtful",
                                                         reason="The fact check did not answer for this segment")).model_dump()
                for segment in segments]
    doubtful = [item for item in verdicts if item["verdict"] != "ok"]
    return {"verdicts": verdicts, "all_ok": not doubtful, "doubtful": doubtful}
