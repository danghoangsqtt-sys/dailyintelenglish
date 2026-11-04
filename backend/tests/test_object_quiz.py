"""Phase 96.5: the "What is this called?" Short -- objects, a silent 3-2-1 and the names."""

import json

import pytest
from pydantic import ValidationError

from backend.content.object_quiz import COUNTDOWN_MS, QUESTION, ObjectQuiz, build_beats, quiz_prompt
from backend.media.audio_service import pause_after_ms
from backend.schemas.project import LINE_DRAWN_STYLES, SHORT_STYLES


def _quiz(count=6):
    names = ["plug", "tap", "drain", "stopper", "extension cord", "light switch", "outlet", "strainer", "ladle", "kettle"]
    return {"theme": "home", "items": [{"name": name, "ipa": "plʌɡ", "meaning_en": "a thing.", "meaning_vi": "phích cắm.",
                                        "picture": f"a {name}"} for name in names[:count]]}


def test_each_object_is_the_question_then_its_name():
    beats = build_beats(ObjectQuiz.model_validate(_quiz()))
    assert [text for text, _ in beats[:4]] == [QUESTION, "Plug.", QUESTION, "Tap."]
    assert [card["beat"] for _, card in beats[:2]] == ["ask", "answer"]
    assert beats[0][1]["pause_after_ms"] == COUNTDOWN_MS and "pause_after_ms" not in beats[1][1]
    assert beats[1][1]["word"] == "plug" and beats[1][1]["ipa"] == "/plʌɡ/" and beats[1][1]["meaning_vi"] == "phích cắm"
    assert beats[0][1]["word"] == beats[1][1]["word"] and beats[2][1]["number"] == 2


def test_at_most_eight_objects_and_no_repeats():
    assert len(build_beats(ObjectQuiz.model_validate(_quiz(10)))) == 14
    twice = _quiz(5)
    twice["items"][1] = twice["items"][0]
    with pytest.raises(ValueError, match="different objects"):
        build_beats(ObjectQuiz.model_validate(twice))
    with pytest.raises(ValidationError):
        ObjectQuiz.model_validate(_quiz(3))


def test_only_a_line_that_asks_has_a_pause():
    assert pause_after_ms({"language_notes": json.dumps({"whatis": {"pause_after_ms": 3000}})}) == 3000
    for line in ({}, {"language_notes": None}, {"language_notes": "{}"}, {"language_notes": json.dumps({"wordday": {"repeat": 1}})},
                 {"language_notes": "not json"}, {"language_notes": json.dumps({"whatis": {"pause_after_ms": "x"}})}):
        assert pause_after_ms(line) == 0


def test_the_mix_adds_the_pause_and_nothing_else(tmp_path):
    from pydub import AudioSegment

    from backend.core.constants import SILENCE_SAME_SPEAKER_MS
    from backend.media.audio_service import _mix_project_sync

    path = tmp_path / "line.mp3"
    AudioSegment.silent(duration=500, frame_rate=24000).export(path, format="mp3")
    plain = {"id": "l1", "speaker_id": "s", "audio_cache_path": str(path), "text": "a", "language_notes": "{}"}
    asking = {**plain, "language_notes": json.dumps({"whatis": {"pause_after_ms": 3000}})}
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    without = _mix_project_sync({"s": "Lina"}, [plain, plain], None, tmp_path / "a")["timestamps"]
    with_pause = _mix_project_sync({"s": "Lina"}, [asking, plain], None, tmp_path / "b")["timestamps"]
    gap = without[1]["start_sec"] - without[0]["end_sec"]
    assert round(gap * 1000) == SILENCE_SAME_SPEAKER_MS
    assert round((with_pause[1]["start_sec"] - with_pause[0]["end_sec"]) * 1000) == SILENCE_SAME_SPEAKER_MS + 3000


async def test_the_lines_read_for_the_real_mix_carry_the_pause(db):
    """Real run 2026-11-04: the mix's own query left the notes out, so the answer came straight after the question."""
    from backend.content import project_service
    from backend.media.audio_service import get_lines_for_mixing
    from backend.schemas.project import ScriptConfig, SpeakerConfig

    project = await project_service.create_project(db, ScriptConfig(
        name="Quiz", topic="Home", cefr_level="A2", duration_minutes=0.75, num_speakers=1, genre="informational", accent="american",
        presentation_mode="solo_explainer", explainer_style="whatis", speakers=[SpeakerConfig(name="Lina", gender="female", accent="american")]))
    await db.execute("INSERT INTO script_lines (id, project_id, line_index, speaker_id, text, language_notes) VALUES (?, ?, 0, ?, ?, ?)",
                     ("l1", project["id"], project["speakers"][0]["id"], QUESTION, json.dumps({"whatis": {"pause_after_ms": COUNTDOWN_MS}})))
    await db.commit()
    lines = await get_lines_for_mixing(db, project["id"])
    assert pause_after_ms(lines[0]) == COUNTDOWN_MS


def test_the_prompt_and_the_lists():
    prompt = quiz_prompt("In the bathroom", "A2", [])
    assert "What is this called?" in prompt and "No people" in prompt
    assert "whatis" in LINE_DRAWN_STYLES and "whatis" in SHORT_STYLES
