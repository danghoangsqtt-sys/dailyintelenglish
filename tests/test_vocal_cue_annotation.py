"""Structured AI cue plans never own the validated dialogue text."""

import json

import pytest

from backend.ai.llm.contracts import GenerationResult
from backend.ai.tts.vocal_cues import caption_text
from backend.content.vocal_cue_annotation import (
    CuePlacement, CuePlan, annotate_script_lines, apply_cue_plan, cue_quota,
)


def _lines(count: int = 4) -> list[dict]:
    return [{"speaker_id": "speaker-1", "text": f"Line {index} has several ordinary words here."}
            for index in range(count)]


def _project() -> dict:
    return {"topic": "A friendly office chat", "duration_minutes": 1.0,
            "speakers": [{"id": "speaker-1", "name": "Lina", "gender": "female",
                          "accent": "american", "voice_description": "bright and warm"}]}


def test_quota_variant_immutability_and_one_cue_per_line():
    original = _lines()
    plan = CuePlan(cues=[
        CuePlacement(line_index=0, after_word_index=2, cue_type="laugh", variant="hi-hi"),
        CuePlacement(line_index=0, after_word_index=3, cue_type="sigh"),
        CuePlacement(line_index=1, after_word_index=1, cue_type="ahem"),
        CuePlacement(line_index=3, after_word_index=1, cue_type="laugh", variant="ha-ha"),
    ])
    result, accepted = apply_cue_plan(original, plan, duration_minutes=1.0, min_gap_seconds=0)
    assert accepted == cue_quota(1.0) == 2
    assert "[cười:hi-hi]" in result[0]["text"]
    assert "[hắng giọng]" in result[1]["text"]
    assert "[cười:ha-ha]" not in result[3]["text"]
    assert [caption_text(line["text"]) for line in result] == [line["text"] for line in original]
    assert all("[" not in line["text"] for line in original)


def test_invalid_variant_and_word_position_are_skipped():
    original = _lines(2)
    result, accepted = apply_cue_plan(original, CuePlan(cues=[
        CuePlacement(line_index=0, after_word_index=999, cue_type="sigh"),
        CuePlacement(line_index=1, after_word_index=0, cue_type="laugh"),
    ]), duration_minutes=1)
    assert accepted == 0
    assert result == original


class _Router:
    def __init__(self, cues: list[dict] | None = None, *, fail: bool = False):
        self.cues = cues or []
        self.fail = fail
        self.calls = 0

    async def generate(self, request):
        self.calls += 1
        assert request.purpose == "script_vocal_cues"
        assert request.json_schema
        if self.fail:
            raise RuntimeError("offline")
        return GenerationResult(
            text=json.dumps({"cues": self.cues}), provider="fake", model="fake",
            latency_ms=1, attempt=1, prompt_hash="abc",
        )


@pytest.mark.asyncio
async def test_optional_annotation_accepts_only_positions_and_falls_back_cleanly():
    clean = _lines()
    router = _Router([{"line_index": 0, "after_word_index": 0,
                       "cue_type": "laugh", "variant": "ha-ha"}])
    annotated, warning = await annotate_script_lines(clean, _project(), router)
    assert warning is None
    assert router.calls == 1
    assert annotated[0]["text"].startswith("[cười:ha-ha]")
    assert clean[0]["text"].startswith("Line")

    fallback, warning = await annotate_script_lines(clean, _project(), _Router(fail=True))
    assert fallback == clean
    assert "clean dialogue preserved" in warning


@pytest.mark.asyncio
async def test_existing_cues_exhaust_budget_without_provider_call():
    lines = _lines(2)
    lines[0]["text"] += " [cười] [thở dài]"
    router = _Router()
    result, warning = await annotate_script_lines(lines, _project(), router)
    assert result == lines
    assert warning is None
    assert router.calls == 0
