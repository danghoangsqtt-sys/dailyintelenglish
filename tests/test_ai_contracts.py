"""Tests for the AI gateway's typed request/result contracts."""

import pytest
from pydantic import ValidationError

from app.services.ai.contracts import AIMode, GenerationRequest, GenerationResult


def test_ai_mode_values():
    assert {mode.value for mode in AIMode} == {"local", "cloud", "cloud_first"}


def test_generation_request_requires_positive_deadline():
    with pytest.raises(ValidationError):
        GenerationRequest(prompt="hi", deadline_seconds=0, purpose="test")


def test_generation_request_requires_nonempty_prompt():
    with pytest.raises(ValidationError):
        GenerationRequest(prompt="", deadline_seconds=10, purpose="test")


def test_generation_request_defaults():
    request = GenerationRequest(prompt="hi", deadline_seconds=10, purpose="test")
    assert request.json_schema is None
    assert request.temperature is None


def test_generation_result_defaults():
    result = GenerationResult(
        text="hello",
        provider="fake",
        model="fake-model",
        latency_ms=1.0,
        attempt=1,
        prompt_hash="abc123",
    )
    assert result.tokens_used is None
    assert result.fallback_used is False
    assert result.fallback_reason is None
    assert result.circuit_open is False
    assert result.attempts == 1
    assert result.backoff_seconds == 0.0
    assert result.transient_errors == []


def test_generation_result_rejects_negative_latency():
    with pytest.raises(ValidationError):
        GenerationResult(
            text="hello",
            provider="fake",
            model="fake-model",
            latency_ms=-1.0,
            attempt=1,
            prompt_hash="abc123",
        )
