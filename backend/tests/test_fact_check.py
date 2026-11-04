"""Phase 84 (owner 2026-10-28): the AI fact check that lets News, VOX and long presenter videos finish by themselves."""

import json

import pytest

from backend.ai.llm.contracts import AIMode, GenerationResult
from backend.ai.llm.fake_provider import FakeProvider
from backend.ai.llm.router import AIRouter
from backend.content import project_service, script_service
from backend.core.exceptions import ValidationError
from backend.library import explainer_service, fact_check

PLAN = {"plan": {"segments": [
    {"id": "hook-1", "line_ids": ["l1"], "visual": {"kind": "text_card", "title": "Four-day weeks", "bullets": []}},
    {"id": "idea-1", "line_ids": ["l2"], "visual": {"kind": "chart", "title": "Output", "items": [{"label": "Trial", "value": 40}],
                                                     "asset": "x.png"}},
]}}
ARTICLE = "A UK trial of a four-day week ran for six months in 61 companies."


def _router(payload: dict) -> tuple[AIRouter, FakeProvider]:
    provider = FakeProvider("fake-local", [GenerationResult(text=json.dumps(payload), provider="fake", model="fake",
                                                            latency_ms=1.0, attempt=1, prompt_hash="x")])
    return AIRouter(primary=None, fallback=provider, mode=AIMode.LOCAL), provider


@pytest.fixture
def plan(monkeypatch):
    async def get_plan(db, project_id):
        return PLAN

    async def get_project(db, project_id):
        return {"topic": "Four-day work week", "explainer_style": "news", "source_text": ARTICLE}

    async def get_script(db, project_id):
        return [{"id": "l1", "text": "Would you work four days a week?"}, {"id": "l2", "text": "Output rose by 40 percent."}]

    monkeypatch.setattr(explainer_service, "get_plan", get_plan)
    monkeypatch.setattr(project_service, "get_project", get_project)
    monkeypatch.setattr(script_service, "get_script", get_script)


async def test_the_fact_check_reads_narration_screen_and_material(plan):
    router, provider = _router({"segments": [{"id": "hook-1", "verdict": "ok", "reason": ""},
                                             {"id": "idea-1", "verdict": "doubtful", "reason": "40 percent is not in the article"}]})
    result = await fact_check.check(None, "p1", router)
    assert result["all_ok"] is False and [item["id"] for item in result["doubtful"]] == ["idea-1"]
    prompt = provider.calls[0].prompt
    assert ARTICLE in prompt and "Output rose by 40 percent." in prompt and '"value": 40' in prompt
    assert "x.png" not in prompt  # file references are not screen text


async def test_a_segment_the_ai_skipped_counts_as_doubtful(plan):
    router, _ = _router({"segments": [{"id": "hook-1", "verdict": "ok", "reason": ""}]})
    result = await fact_check.check(None, "p1", router)
    assert result["all_ok"] is False and result["doubtful"][0]["id"] == "idea-1"
    all_ok, _ = _router({"segments": [{"id": "hook-1", "verdict": "ok"}, {"id": "idea-1", "verdict": "ok"}]})
    assert (await fact_check.check(None, "p1", all_ok))["all_ok"] is True


async def test_no_plan_or_an_unusable_answer_is_a_plain_error(plan, monkeypatch):
    bad, _ = _router({"verdicts": "everything fine"})
    with pytest.raises(ValidationError, match="not usable"):
        await fact_check.check(None, "p1", bad)

    async def no_plan(db, project_id):
        return {"plan": None}

    monkeypatch.setattr(explainer_service, "get_plan", no_plan)
    with pytest.raises(ValidationError, match="Propose the visual plan first"):
        await fact_check.check(None, "p1", bad)
