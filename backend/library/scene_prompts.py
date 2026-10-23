"""Expand a short Vietnamese/English scene request through the configured text AI gateway."""

from __future__ import annotations

import asyncio
import json

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import Field, TypeAdapter, field_validator

from backend.ai.image.recipes import SCENE_COMPOSITION, qwen_scene_prompt
from backend.ai.llm.contracts import GenerationRequest
from backend.ai.llm.router import AIRouter, build_ai_router_from_settings
from backend.ai.llm.validation import parse_and_validate
from backend.core.config import settings
from backend.core.exceptions import SchemaValidationError, ValidationError
from backend.core.paths import PROMPTS_DIR
from backend.schemas.visuals import SCENE_CATEGORIES, TIMES_OF_DAY, SceneInput

_environment = Environment(
    loader=FileSystemLoader(str(PROMPTS_DIR / "scenes")), undefined=StrictUndefined,
    trim_blocks=True, lstrip_blocks=True,
)


def _render_prompt(brief: str, schema: dict, error: str) -> str:
    return _environment.get_template("scene_brief.txt").render(
        categories=", ".join(SCENE_CATEGORIES), times=", ".join(TIMES_OF_DAY),
        composition=SCENE_COMPOSITION, brief_json=json.dumps(brief, ensure_ascii=False),
        schema_json=json.dumps(schema), previous_error=error,
    )


class ScenePromptDraft(SceneInput):
    """A valid library scene plus a detailed English image description."""

    image_prompt: str = Field(min_length=60, max_length=5000)

    @field_validator("image_prompt", mode="before")
    @classmethod
    def trim_prompt(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


async def generate_scene_prompt(brief: str, router: AIRouter | None = None) -> dict:
    """Return a reviewable scene draft; provider failures never overwrite or invent saved scene content."""
    brief = brief.strip()
    if not brief or len(brief) > 2000:
        raise ValidationError("Describe the scene in 1 to 2000 characters, in Vietnamese or English.")
    adapter = TypeAdapter(ScenePromptDraft)
    schema = adapter.json_schema()
    # The request is authoritative; the AI need not echo it as another generated field.
    schema["properties"].pop("source_request", None)
    router = router or build_ai_router_from_settings()
    error = ""
    for attempt in range(2):
        prompt = await asyncio.to_thread(_render_prompt, brief, schema, error)
        result = await router.generate(GenerationRequest(
            prompt=prompt, json_schema=schema, purpose="scene_prompt",
            deadline_seconds=settings.AI_REQUEST_DEADLINE_SECONDS,
        ))
        try:
            draft = parse_and_validate(result.text, adapter)
        except SchemaValidationError as exc:
            error = str(exc)
            if attempt:
                raise
            continue
        values = draft.model_dump()
        values["source_request"] = brief
        values["image_prompt"] = qwen_scene_prompt(values)
        # Validate the complete persistence contract, including the canonical composition suffix.
        return SceneInput.model_validate(values).model_dump()
    raise SchemaValidationError("Could not prepare a valid scene prompt")
