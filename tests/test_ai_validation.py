"""Tests for the shared parse_and_validate primitive."""

import pytest
from pydantic import BaseModel, TypeAdapter

from app.core.exceptions import SchemaValidationError
from app.services.ai.validation import parse_and_validate


class _Item(BaseModel):
    name: str
    count: int


_ADAPTER = TypeAdapter(_Item)
_LIST_ADAPTER = TypeAdapter(list[_Item])


def test_parse_and_validate_success():
    result = parse_and_validate('{"name": "widget", "count": 3}', _ADAPTER)
    assert result.name == "widget"
    assert result.count == 3


def test_parse_and_validate_list_success():
    result = parse_and_validate('[{"name": "a", "count": 1}, {"name": "b", "count": 2}]', _LIST_ADAPTER)
    assert [item.name for item in result] == ["a", "b"]


def test_parse_and_validate_rejects_invalid_json():
    with pytest.raises(SchemaValidationError, match="not valid JSON"):
        parse_and_validate("{not json", _ADAPTER)


def test_parse_and_validate_rejects_schema_mismatch():
    with pytest.raises(SchemaValidationError, match="schema validation"):
        parse_and_validate('{"name": "widget"}', _ADAPTER)


def test_parse_and_validate_error_never_echoes_raw_text():
    secret_marker = "TOP_SECRET_PROMPT_CONTENT"
    try:
        parse_and_validate(f"not json at all {secret_marker}", _ADAPTER)
    except SchemaValidationError as exc:
        assert secret_marker not in str(exc)
    else:
        pytest.fail("expected SchemaValidationError")
