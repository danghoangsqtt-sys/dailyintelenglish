"""Shared JSON-parse + Pydantic-schema validation primitive for AI provider output."""

from __future__ import annotations

import json
from typing import Any

from pydantic import TypeAdapter
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import SchemaValidationError


def parse_and_validate(text: str, adapter: TypeAdapter) -> Any:
    """Parse `text` as JSON and validate it against `adapter`.

    The one shared primitive behind every provider's structured-output path --
    replaces the ad hoc `json.loads` + `TypeAdapter.validate_python`/
    `BaseModel.model_validate` pairs duplicated across `script_service.py`.

    Args:
        text: Raw provider response text, expected to be a JSON document.
        adapter: A `pydantic.TypeAdapter` (works for both a single `BaseModel` and
            a `list[...]`/other generic shape).

    Returns:
        The validated Python value.

    Raises:
        SchemaValidationError: If `text` is not valid JSON, or fails validation.
            The message never echoes the raw text -- only an error count/summary.
    """
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SchemaValidationError(f"Provider response is not valid JSON: {exc}") from exc

    try:
        return adapter.validate_python(parsed)
    except PydanticValidationError as exc:
        raise SchemaValidationError(
            f"Provider response failed schema validation ({exc.error_count()} error(s))"
        ) from exc
