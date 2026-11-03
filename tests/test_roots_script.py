"""Phase 87: the "Word roots, prefixes and suffixes" Short -- the word family and its beats."""

import json

import pytest
from pydantic import ValidationError as PydanticValidationError

from backend.content.word_family import WordFamily, build_beats, find_seed, parts_spell_word, roots_prompt
from tests.test_visuals_project_api import client, locked_character  # noqa: F401
from backend.schemas.project import (
    LINE_DRAWN_STYLES, SHORT_STYLES, ScriptConfig, SpeakerConfig, is_short_video, short_max_minutes, short_minutes,
)


def _word(word, parts, meaning, logic="Logic.", example="", example_vi="", picture="a thing"):
    return {"word": word, "parts": [{"text": t, "role": r, "meaning": m} for t, r, m in parts], "meaning": meaning,
            "logic": logic, "example_en": example, "example_vi": example_vi, "picture": picture}


PRESS = {
    "kind": "root", "head": "press", "origin_lang": "Latin", "origin_form": "premere → pressus", "head_meaning": "ấn, ép",
    "head_logic": "Ngay ở press, bạn thấy hành động dùng lực lên một vật", "head_example_en": "press the button to open the door",
    "head_example_vi": "Hãy ấn nút để mở cửa.",
    "words": [
        _word("express", [("ex", "prefix", "ra ngoài"), ("press", "root", "ép")], "bày tỏ",
              "EX là ra ngoài, PRESS là ép: ép ý nghĩ ra ngoài là bày tỏ.", "She expresses her ideas through dance.",
              "Cô ấy bày tỏ ý tưởng qua điệu múa."),
        _word("impress", [("im", "prefix", "vào trong"), ("press", "root", "ấn")], "gây ấn tượng"),
        _word("compress", [("com", "prefix", "cùng nhau"), ("press", "root", "ép")], "nén lại",
              picture="a computer monitor showing a zipped folder"),
        _word("depress", [("de", "prefix", "xuống"), ("press", "root", "ấn")], "làm suy giảm"),
        _word("pressure", [("press", "root", "ép"), ("ure", "suffix", "danh từ")], "áp lực"),
        _word("oppress", [("op", "prefix", "chống"), ("press", "root", "đè")], "áp bức"),
        _word("expression", [("ex", "prefix", "ra"), ("press", "root", "ép")], "biểu cảm"),  # parts do not spell it
    ],
    "quiz": _word("suppress", [("sup", "prefix", "dưới"), ("press", "root", "đè")], "kìm nén",
                  picture="a newspaper locked in a drawer"),
    "quiz_clue": "Một bản tin đã viết xong nhưng bị khoá trong ngăn kéo, không được công bố.",
}


def test_roots_is_a_line_drawn_academic_short_up_to_three_minutes():
    assert "roots" in SHORT_STYLES and "roots" in LINE_DRAWN_STYLES
    assert short_minutes("roots") == 2.0 and short_max_minutes("roots") == 3.0 and short_max_minutes("flashcards") == 1.0
    config = dict(name="Gốc PRESS", topic="PRESS", cefr_level="B1", num_speakers=1, genre="informational", accent="american",
                  presentation_mode="solo_explainer", speakers=[SpeakerConfig(name="Huyền", gender="female")])
    assert is_short_video(ScriptConfig(**config, explainer_style="roots", duration_minutes=2.5).model_dump())
    with pytest.raises(PydanticValidationError):
        ScriptConfig(**config, explainer_style="roots", duration_minutes=3.5)
    with pytest.raises(PydanticValidationError):
        ScriptConfig(**config, explainer_style="flashcards", duration_minutes=2.0)


def test_the_checked_list_is_found_from_the_topic():
    assert find_seed("Tập 8: gốc PRESS")[1]["origin_form"] == "premere → pressus"
    assert find_seed("Tiền tố un- trong tiếng Anh")[0] == "prefix"
    assert find_seed("Hậu tố -tion và họ từ")[0] == "suffix"
    assert find_seed("mittere: gốc MISS")[1]["head"] == "mit / miss"
    assert find_seed("Daily routines") is None
    assert "premere → pressus" in roots_prompt("gốc PRESS", "B1", "vi", [])
    assert "in Vietnamese" in roots_prompt("gốc PRESS", "B1", "vi", []) and "in English" in roots_prompt("x", "B1", "en", [])


def test_vietnamese_beats_follow_the_sample_formula():
    family = WordFamily.model_validate(PRESS)
    assert not parts_spell_word(family.words[-1])
    beats = build_beats(family, "vi")
    texts = [text for text, _ in beats]
    kinds = [card["beat"] for _, card in beats]
    assert texts[:3] == ["Bạn có biết Express là bày tỏ,", "nhưng Express và Impress cùng một gốc?",
                         "Sau video này, bạn sẽ hiểu và nhớ được 7 từ tiếng Anh chỉ từ một gốc duy nhất!"]
    assert texts[3] == "Gốc của chúng ta hôm nay là press, bắt nguồn từ Latin premere, nghĩa là ấn, ép."
    assert texts[4:7] == ["Press, ấn, ép.", "Ngay ở press, bạn thấy hành động dùng lực lên một vật.",
                          "Press the button to open the door."]
    # per word: whole, split, example (only when there is one); "expression" was dropped
    assert kinds.count("whole") == 6 and kinds.count("example") == 1 and "Expression" not in " ".join(texts)
    split = next(card for _, card in beats if card["beat"] == "split" and card["word"] == "compress")
    assert split["breakdown"] == "COM: cùng nhau · PRESS: ép" and split["picture"].startswith("a computer monitor")
    assert texts[-2].startswith("Đoán từ cuối nhé! Một bản tin") and beats[-2][1]["answer"] == "kìm nén"
    assert texts[-1] == "Comment đáp án và theo dõi Daily Beyond English nhé!"
    wheel = beats[2][1]
    assert wheel["words"][-1] == "suppress" and len(wheel["words"]) == 7


def test_english_beats_for_the_international_audience():
    family = WordFamily.model_validate({**PRESS, "origin_form": "", "head_logic": "", "head_example_en": ""})
    texts = [text for text, _ in build_beats(family, "en")]
    assert texts[0] == "Did you know Express means bày tỏ,"  # the AI writes meanings in the narration language
    assert texts[2].startswith("After this video, you'll remember 7 English words")
    assert texts[3] == "Press, ấn, ép."  # no origin beat without a checked origin
    assert texts[-1] == "Comment your answer and follow Daily Beyond English!"


def test_a_family_with_too_few_usable_words_is_refused():
    family = WordFamily.model_validate({**PRESS, "words": PRESS["words"][:3] + [PRESS["words"][-1]]})
    with pytest.raises(ValueError, match="only 3 words"):
        build_beats(family, "vi")


async def test_a_roots_script_job_builds_beats_and_switches_the_narrator_to_vieneu(db):
    from backend.ai.llm import ai_job_service
    from backend.ai.llm.ai_worker import AIWorker
    from backend.content import project_service, script_pipeline, script_service
    from tests.test_script_pipeline import _build_router, _result

    project = await project_service.create_project(db, ScriptConfig(
        name="Gốc PRESS", topic="Gốc PRESS", cefr_level="B1", duration_minutes=2.0, num_speakers=1, genre="informational",
        accent="american", presentation_mode="solo_explainer", explainer_style="roots",
        speakers=[SpeakerConfig(name="Huyền", gender="female", accent="american")]))
    assert project["speakers"][0]["tts_engine"] == "edge_tts"
    router, provider, _ = _build_router([_result(json.dumps(PRESS, ensure_ascii=False))])
    job, _ = await ai_job_service.create_job(db, project["id"], "script", {"project": project, "operation": "script"})
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    await script_pipeline.make_handler(router)(claimed, AIWorker(db_getter=lambda: db))
    final = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final["status"] == "complete", final.get("error_message")
    lines = await script_service.get_script(db, project["id"])
    assert lines[0]["text"] == "Bạn có biết Express là bày tỏ," and lines[0]["language_notes"]["roots"]["beat"] == "hook"
    assert lines[-1]["language_notes"]["roots"]["beat"] == "follow"
    speaker = (await project_service.get_project(db, project["id"]))["speakers"][0]
    assert speaker["tts_engine"] == "vieneu" and speaker["resolved_voice_id"] == "Ngọc Huyền"
    assert provider.call_count == 1


def test_roots_cards_and_drawn_pictures_reach_the_video_props(client, monkeypatch, tmp_path):  # noqa: F811
    import asyncio

    import aiosqlite

    from backend.core.config import settings
    from backend.media import roots_pictures
    from backend.media import video_renderer_remotion as remotion
    from tests.test_visuals_project_api import data

    project = data(client.post("/api/projects", json={
        "name": "Gốc PRESS", "topic": "Gốc PRESS", "cefr_level": "B1", "duration_minutes": 2.0, "num_speakers": 1,
        "genre": "informational", "accent": "american", "presentation_mode": "solo_explainer", "explainer_style": "roots",
        "speakers": [{"name": "Huyền", "gender": "female", "accent": "american"}]}))
    speaker = project["speakers"][0]["id"]
    family = WordFamily.model_validate(PRESS)
    beats = build_beats(family, "vi")[:4]
    data(client.put(f"/api/projects/{project['id']}/script", json={"lines": [
        {"speaker_id": speaker, "text": text, "language_notes": {"roots": card}} for text, card in beats]}))
    saved = data(client.get(f"/api/projects/{project['id']}/script"))
    assert saved[0]["language_notes"]["roots"]["beat"] == "hook"  # the card survives the Step 2 save

    drawn = tmp_path / "express.png"
    drawn.write_bytes(b"\x89PNG fake")

    async def fake_pictures(db, project_id, cards):
        assert roots_pictures.wanted_pictures(cards) == {"express": "a thing"}
        return {"express": drawn}

    monkeypatch.setattr(roots_pictures, "ensure_pictures", fake_pictures)
    monkeypatch.setattr(remotion, "REMOTION_VISUALS_DIR", tmp_path / "public")
    audio = {"mp3_path": str(settings.DATA_DIR / "x.mp3"), "word_timestamps": [{"words": []} for _ in beats],
             "timestamps": [{"start_sec": float(at), "end_sec": at + 0.9, "label": "Huyền", "speaker_id": speaker, "text": line["text"]}
                            for at, line in enumerate(saved)]}

    async def props():
        async with aiosqlite.connect(settings.db_path) as db:
            db.row_factory = aiosqlite.Row
            full = data(client.get(f"/api/projects/{project['id']}"))
            return await remotion._build_input_props(db, full, audio, None, visual_mode="podcast_black", layout="vertical")

    built = asyncio.run(props())
    assert built["shortStyle"] == "roots"
    assert built["lines"][0]["roots"]["pictureUrl"] == f"remotion-render/visuals/{project['id']}/roots/express.png"
    assert built["lines"][1]["roots"]["beat"] == "twins" and "pictureUrl" not in built["lines"][1]["roots"]
    assert (tmp_path / "public" / project["id"] / "roots" / "express.png").is_file()


async def test_missing_pictures_are_drawn_once_kept_in_the_library_and_reused(db, monkeypatch, tmp_path):
    from backend.ai.image.engine import FakeImageEngine
    from backend.core.config import settings
    from backend.media import roots_pictures

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr(settings, "IMAGE_ENGINE", "fake")
    monkeypatch.setattr(settings, "AI_VISUALS_ENABLED", True)
    FakeImageEngine.qwen_calls.clear()
    cards = [{"beat": "whole", "word": "compress", "picture": "a monitor with a zipped folder"},
             {"beat": "split", "word": "compress", "picture": "a monitor with a zipped folder"},
             {"beat": "twins", "words": ["a", "b"]}, {"beat": "quiz", "word": "suppress", "picture": "a locked drawer"}]
    drawn = await roots_pictures.ensure_pictures(db, "p1", cards)
    assert sorted(drawn) == ["compress", "suppress"] and len(FakeImageEngine.qwen_calls) == 1
    assert "line art" in FakeImageEngine.qwen_calls[0]["items"][0]["prompt"]
    cursor = await db.execute("SELECT COUNT(*) FROM activity_library WHERE review_state = 'approved'")
    assert (await cursor.fetchone())[0] == 2
    again = await roots_pictures.ensure_pictures(db, "p1", cards)  # cached: no second draw
    assert sorted(again) == ["compress", "suppress"] and len(FakeImageEngine.qwen_calls) == 1
    monkeypatch.setattr(settings, "AI_VISUALS_ENABLED", False)  # without the image model the video is still made
    assert await roots_pictures.ensure_pictures(db, "p2", cards) == {}


def test_the_shorts_batch_makes_roots_shorts_of_two_minutes(client):  # noqa: F811
    from tests.test_visuals_project_api import data

    narrator = locked_character("Narrator", "red")
    result = data(client.post("/api/shorts-batch/create", json={
        "topic_name": "Shorts", "series_name": "Gốc từ", "template": "roots", "cast": [narrator], "cefr_level": "B1",
        "start_date": "2026-11-04", "every_days": 1, "make_projects": True, "items": [{"title": "Gốc PRESS", "brief": ""}]}))
    tree = data(client.get("/api/channel"))
    series = next(s for topic in tree["topics"] for s in topic["series"] if s["id"] == result["series_id"])
    project = data(client.get(f"/api/projects/{series['episodes'][0]['project_id']}"))
    assert project["explainer_style"] == "roots" and is_short_video(project) and project["duration_minutes"] == 2.0
