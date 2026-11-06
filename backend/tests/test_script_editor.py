"""Phase 84 (owner 2026-10-28): the editor pass of an automatic script -- scores, one rewrite, kept only when it passes."""

import json

import pytest

from backend.ai.llm.contracts import AIMode, GenerationResult
from backend.ai.llm.fake_provider import FakeProvider
from backend.ai.llm.router import AIRouter
from backend.content import project_service, script_editor, script_pipeline, script_service
from backend.core.exceptions import ValidationError
from backend.schemas.project import ScriptConfig, SpeakerConfig

GOOD = {"hook": 5, "message": 4, "examples": 4, "natural": 5, "level": 4, "ending": 4}
WEAK = {**GOOD, "hook": 2, "examples": 3}


def _router(*payloads) -> tuple[AIRouter, FakeProvider]:
    provider = FakeProvider("fake-local", [GenerationResult(text=json.dumps(payload), provider="fake", model="fake",
                                                            latency_ms=1.0, attempt=1, prompt_hash="x") for payload in payloads])
    return AIRouter(primary=None, fallback=provider, mode=AIMode.LOCAL), provider


def _sentences(count: int, start: int = 0) -> list[str]:
    """Distinct sentences of ten words (no repeated 8-grams across a script)."""
    return [" ".join(f"w{start + index}x{word}" for word in range(10)) + "." for index in range(count)]


async def _project(db, style="top5"):
    project = await project_service.create_project(db, ScriptConfig(
        name="Edit me", topic="Small talk at work", cefr_level="B1", duration_minutes=0.95, num_speakers=1,
        genre="informational", accent="american", presentation_mode="solo_explainer", explainer_style=style,
        speakers=[SpeakerConfig(name="Lina", gender="female", accent="american")]))
    speaker = project["speakers"][0]["id"]
    target = script_pipeline.compute_target_words("B1", 0.95)
    texts = _sentences(round(target / 10))
    await script_service.save_script(db, project["id"], [{"speaker_id": speaker, "text": text} for text in texts], {speaker})
    return project, target


async def test_a_script_that_scores_well_is_left_as_it_is(db):
    project, _ = await _project(db)
    before = [line["text"] for line in await script_service.get_script(db, project["id"])]
    router, provider = _router({"scores": GOOD, "notes": ""})
    result = await script_editor.review(db, project["id"], router)
    assert (result["outcome"], result["rewritten"], result["scores"]) == ("passed", False, GOOD)
    assert [line["text"] for line in await script_service.get_script(db, project["id"])] == before
    assert provider.call_count == 1 and "Small talk at work" in provider.calls[0].prompt
    assert "NEVER ADD FACTS" in provider.calls[0].prompt  # real run: a rewrite invented a study


async def test_a_weak_script_is_rewritten_once_and_kept_when_it_passes_the_checks(db):
    project, target = await _project(db)
    rewrite = [{"speaker": "Lina", "text": text} for text in _sentences(round(target / 10), start=500)]
    router, provider = _router({"scores": WEAK, "notes": "Open with a question."}, {"lines": rewrite})
    result = await script_editor.review(db, project["id"], router)
    assert (result["outcome"], result["rewritten"]) == ("rewritten", True)
    assert [line["text"] for line in await script_service.get_script(db, project["id"])] == [line["text"] for line in rewrite]
    assert "Open with a question." in provider.calls[1].prompt
    assert "do not shorten the script" in provider.calls[1].prompt and "Keep every fact" in provider.calls[1].prompt
    assert (await project_service.get_project(db, project["id"]))["status"] == "script_generated"
    assert (await script_editor.get_review(db, project["id"]))["notes"] == "Open with a question."


@pytest.mark.parametrize("lines", [
    [{"speaker": "Somebody", "text": "Hello there, everyone."}],                      # not in the cast
    [{"speaker": "Lina", "text": "Far too short."}],                                  # misses the length check
])
async def test_a_rewrite_that_fails_a_check_keeps_the_original(db, lines):
    project, _ = await _project(db)
    before = [line["text"] for line in await script_service.get_script(db, project["id"])]
    router, _ = _router({"scores": WEAK, "notes": "Open with a question."}, {"lines": lines}, {"lines": lines})  # + length retry
    result = await script_editor.review(db, project["id"], router)
    assert (result["outcome"], result["rewritten"]) == ("kept_original", False) and result["rejected_reason"]
    assert [line["text"] for line in await script_service.get_script(db, project["id"])] == before


async def test_flashcards_and_slow_podcasts_are_left_alone(db):
    project, _ = await _project(db, style="flashcards")
    router, _ = _router({"scores": GOOD, "notes": ""})
    with pytest.raises(ValidationError, match="line by line"):
        await script_editor.review(db, project["id"], router)


async def test_a_rewrite_that_only_misses_the_length_is_asked_once_to_fit_it(db):
    """Real run 2026-10-28: a long rewrite came back 549 words for 625 and was thrown away."""
    project, target = await _project(db)
    short = [{"speaker": "Lina", "text": text} for text in _sentences(round(target / 20), start=500)]
    fitted = [{"speaker": "Lina", "text": text} for text in _sentences(round(target / 10), start=900)]
    router, provider = _router({"scores": WEAK, "notes": "Use contractions."}, {"lines": short}, {"lines": fitted})
    result = await script_editor.review(db, project["id"], router)
    assert (result["outcome"], result["rewritten"]) == ("rewritten", True) and provider.call_count == 3
    assert "LENGTH: your previous rewrite had" in provider.calls[2].prompt


async def test_the_editor_keeps_a_vox_cold_open(db):
    """Phase 86: a long VOX script opens on an English example and a question; the editor must not add a greeting."""
    project, target = await _project(db, style="vox")
    rewrite = [{"speaker": "Lina", "text": text} for text in _sentences(round(target / 10), start=700)]
    router, provider = _router({"scores": WEAK, "notes": "Sharper hook."}, {"lines": rewrite})
    await script_editor.review(db, project["id"], router)
    assert "Keep the cold open" in provider.calls[1].prompt and "Keep the greeting at the start" not in provider.calls[1].prompt


async def _doodle(db):
    """Phase 99 (D173): a 3-minute Doodle story whose first line carries its target words and hero look."""
    project = await project_service.create_project(db, ScriptConfig(
        name="Story", topic="A lost umbrella", cefr_level="B1", duration_minutes=3, num_speakers=1, genre="storytelling",
        accent="american", presentation_mode="solo_explainer", explainer_style="doodle", explainer_subject="story",
        speakers=[SpeakerConfig(name="Lina", gender="female", accent="american")]))
    speaker = project["speakers"][0]["id"]
    target = script_pipeline.compute_target_words("B1", 3)
    words = ["umbrella", "notice", "return", "honest", "rain"]
    said = " ".join(f"{word} {word} {word}" for word in words) + "."
    texts = [said, *_sentences(round(target / 10) - 2, start=900)]
    notes = {"doodle": {"words": words, "hero": "a girl in a yellow coat"}}
    await script_service.save_script(db, project["id"], [{"speaker_id": speaker, "text": texts[0], "language_notes": notes},
                                                         *[{"speaker_id": speaker, "text": text} for text in texts[1:]]], {speaker})
    return project, target, words, said


async def test_a_doodle_rewrite_keeps_the_story_words_on_its_first_line(db):
    project, target, words, said = await _doodle(db)
    rewrite = [{"speaker": "Lina", "text": "A new first line. " + said}, *[
        {"speaker": "Lina", "text": text} for text in _sentences(round(target / 10) - 2, start=700)]]
    router, _ = _router({"scores": WEAK, "notes": "Show, don't tell."}, {"lines": rewrite})
    assert (await script_editor.review(db, project["id"], router))["outcome"] == "rewritten"
    first = (await script_service.get_script(db, project["id"]))[0]
    assert first["text"].startswith("A new first line.") and first["language_notes"]["doodle"]["words"] == words


async def test_a_doodle_rewrite_that_drops_a_word_below_three_uses_is_refused(db):
    project, target, words, _said = await _doodle(db)
    before = [line["text"] for line in await script_service.get_script(db, project["id"])]
    rewrite = [{"speaker": "Lina", "text": text} for text in _sentences(round(target / 10), start=700)]  # none of the words
    router, _ = _router({"scores": WEAK, "notes": "Shorter sentences."}, {"lines": rewrite})
    result = await script_editor.review(db, project["id"], router)
    assert result["outcome"] == "kept_original" and "target words" in result["rejected_reason"]
    assert [line["text"] for line in await script_service.get_script(db, project["id"])] == before
