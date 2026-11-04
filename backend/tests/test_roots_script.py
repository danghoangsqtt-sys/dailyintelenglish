"""Phase 87: the "Word roots, prefixes and suffixes" Short -- the word family and its beats."""

import json

import pytest
from pydantic import ValidationError as PydanticValidationError

from backend.content.word_family import WordFamily, build_beats, find_seed, parts_spell_word, roots_prompt
from backend.tests.test_visuals_project_api import client, locked_character  # noqa: F401
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
    from backend.tests.test_script_pipeline import _build_router, _result

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
    from backend.tests.test_visuals_project_api import data

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
    from backend.tests.test_visuals_project_api import data

    narrator = locked_character("Narrator", "red")
    result = data(client.post("/api/shorts-batch/create", json={
        "topic_name": "Shorts", "series_name": "Gốc từ", "template": "roots", "cast": [narrator], "cefr_level": "B1",
        "start_date": "2026-11-04", "every_days": 1, "make_projects": True, "items": [{"title": "Gốc PRESS", "brief": ""}]}))
    tree = data(client.get("/api/channel"))
    series = next(s for topic in tree["topics"] for s in topic["series"] if s["id"] == result["series_id"])
    project = data(client.get(f"/api/projects/{series['episodes'][0]['project_id']}"))
    assert project["explainer_style"] == "roots" and is_short_video(project) and project["duration_minutes"] == 2.0


def test_real_run_splits_are_fitted_and_checked_facts_are_kept():
    """Real run 2026-11-03: an empty "-" suffix part, base-word splits of a suffix family, and an empty origin."""
    from backend.content.word_family import FamilyWord, fit_parts, with_checked_facts

    empty = FamilyWord.model_validate(_word("express", [("ex-", "prefix", "ra"), ("press", "root", "ép"), ("-", "suffix", "")], "bày tỏ"))
    assert [p.text for p in fit_parts(empty).parts] == ["ex-", "press"]
    decision = FamilyWord.model_validate(_word("decision", [("decide", "root", "quyết định"), ("-sion", "suffix", "danh từ")], "quyết định"))
    assert [p.text for p in fit_parts(decision).parts] == ["deci", "-sion"]
    happiness = FamilyWord.model_validate(_word("happiness", [("happy", "root", "vui"), ("ness", "suffix", "trạng thái")], "hạnh phúc"))
    assert [p.text for p in fit_parts(happiness).parts] == ["happi", "ness"]
    wrong = FamilyWord.model_validate(_word("expression", [("ex", "prefix", "ra"), ("press", "root", "ép")], "biểu cảm"))
    assert fit_parts(wrong) is None
    family = WordFamily.model_validate({**PRESS, "origin_form": "", "origin_lang": "", "head_meaning": "ép mạnh"})
    checked = with_checked_facts(family, "Gốc PRESS: express, impress", "vi")
    assert checked.origin_form == "premere → pressus" and checked.head_meaning == "ấn, ép"
    assert with_checked_facts(family, "Daily routines", "vi").origin_form == ""


def test_word_cards_carry_the_family_kind_and_combined_heads_match_the_checked_list():
    from backend.content.word_family import with_checked_facts

    beats = build_beats(WordFamily.model_validate(PRESS), "vi")
    assert all(card.get("kind") == "root" for _, card in beats if card.get("parts"))
    suffix = WordFamily.model_validate({**PRESS, "kind": "suffix", "head": "-tion / -sion", "origin_form": ""})
    assert with_checked_facts(suffix, "Hậu tố -tion: action, education", "vi").origin_form == "-tio"
    with pytest.raises(PydanticValidationError):  # every word needs a picture description
        WordFamily.model_validate({**PRESS, "quiz": {**PRESS["quiz"], "picture": ""}})


def test_stray_chinese_characters_are_removed():
    from backend.content.word_family import with_checked_facts

    bad = {**PRESS, "words": [{**PRESS["words"][0], "logic": "DE là xuống: ấn xuống thì tâm trạng也跟着 đi xuống."}] + PRESS["words"][1:]}
    clean = with_checked_facts(WordFamily.model_validate(bad), "Gốc PRESS", "vi")
    assert clean.words[0].logic == "DE là xuống: ấn xuống thì tâm trạng đi xuống."


def _story_family():
    return {**PRESS, "puzzle": "Vì sao express lại có press?", "puzzle_word": "impress",
            "story": [{"text": "Ngày xưa người ta in bằng cách ép", "picture": "an old printing press"},
                      {"text": "Vết ép để lại dấu ấn", "picture": "a stamp on paper"}]}


def test_a_puzzle_opens_the_video_and_its_story_comes_before_the_words():
    beats = build_beats(WordFamily.model_validate(_story_family()), "vi")
    kinds = [card["beat"] for _, card in beats]
    assert kinds[:2] == ["puzzle", "wheel"] and "hook" not in kinds and "twins" not in kinds
    assert beats[0][0] == "Vì sao express lại có press?" and beats[0][1]["word"] == "impress"
    assert kinds.index("story") < kinds.index("whole") and kinds.count("story") == 2
    assert beats[kinds.index("story")][1]["word"] == "story 1" and beats[kinds.index("story")][1]["picture"] == "an old printing press"


def test_without_a_story_the_opening_is_as_before():
    for family in (PRESS, {**PRESS, "puzzle": "Vì sao?"}, {**_story_family(), "story": _story_family()["story"][:1]}):
        kinds = [card["beat"] for _, card in build_beats(WordFamily.model_validate(family), "vi")]
        assert kinds[:2] == ["hook", "twins"] and "story" not in kinds and "puzzle" not in kinds


def test_a_story_comes_only_from_the_checked_list():
    from backend.content.word_family import with_checked_facts

    sept = {**PRESS, "head": "sept", "origin_lang": "", "origin_form": ""}
    checked = with_checked_facts(WordFamily.model_validate(sept), "gốc sept", "vi")
    assert checked.puzzle == "Vì sao September là tháng 9, trong khi gốc SEPT lại là số 7?" and checked.puzzle_word == "september"
    assert len(checked.story) == 4 and "mười tháng" in checked.story[0].text and checked.origin_form == "septem"
    beats = build_beats(checked, "vi")
    assert beats[0][1]["beat"] == "puzzle" and beats[0][1]["word"] == "september"  # even when the AI left the word out
    assert "meaning" not in beats[0][1]  # the story gives its meaning, not the AI
    told = with_checked_facts(WordFamily.model_validate({**sept, "words": [{**PRESS["words"][0], "word": "september", "parts": [
        {"text": "septem", "role": "root", "meaning": ""}, {"text": "ber", "role": "suffix", "meaning": ""}]}, *PRESS["words"]]}), "sept", "vi")
    assert "september" not in [word.word for word in told.words]  # it is not told a second time with the AI's meaning
    english = with_checked_facts(WordFamily.model_validate(sept), "sept", "en")
    assert english.story[0].text.startswith("The old Roman calendar")
    # what the AI sends is not used: a head without a checked story keeps the usual opening
    made_up = with_checked_facts(WordFamily.model_validate(PRESS), "press", "vi")
    assert made_up.puzzle == "" and made_up.story == []


def test_the_desktop_build_ships_the_word_roots_data():
    """Phase 87 install check: the packaged app reads backend/content/data/*.json next to its modules."""
    from pathlib import Path

    spec = Path("installer/daily_intel_english_studio.spec").read_text(encoding="utf-8")
    assert '("backend/content/data", "backend/content/data")' in spec


def test_real_run_a_root_family_word_is_split_around_the_whole_root():
    """Sandbox run 2026-11-03: suspect came as SUS + PECT and spectator as SPECTA + TOR."""
    from backend.content.word_family import FamilyWord, around_root

    suspect = FamilyWord.model_validate(_word("suspect", [("sus", "prefix", "dưới"), ("pect", "root", "nhìn")], "nghi ngờ"))
    assert [(p.text, p.role, p.meaning) for p in around_root(suspect, "spect").parts] == [
        ("su", "prefix", "dưới"), ("spect", "root", "nhìn")]
    spectator = FamilyWord.model_validate(_word("spectator", [("specta", "root", "nhìn"), ("tor", "suffix", "người")], "khán giả"))
    assert [p.text for p in around_root(spectator, "spect").parts] == ["spect", "ator"]
    inspect = FamilyWord.model_validate(_word("inspect", [("in", "prefix", "vào"), ("spect", "root", "nhìn")], "kiểm tra"))
    assert around_root(inspect, "spect") is inspect
    dismiss = FamilyWord.model_validate(_word("dismiss", [("dis", "prefix", "rời"), ("mis", "root", "gửi"), ("s", "suffix", "")], "giải tán"))
    assert [p.text for p in around_root(dismiss, "mit / miss").parts] == ["dis", "miss"]


def test_real_run_an_english_quiz_clue_in_a_vietnamese_video_becomes_the_parts_meanings():
    """Sandbox run 2026-11-03: the RE- Short read "What do you do with old newspapers...?" in a Vietnamese video, and
    meanings ended in a stray ";"."""
    from backend.content.word_family import with_checked_facts

    data = json.loads(json.dumps(PRESS))
    data["quiz_clue"] = "What do you do with a newspaper that must never be published?"
    data["words"][0]["meaning"] = "bày tỏ;"
    family = with_checked_facts(WordFamily.model_validate(data), "gốc PRESS", "vi")
    assert family.quiz_clue == "Gợi ý: SUP là dưới, PRESS là đè"
    assert family.words[0].meaning == "bày tỏ"
    english = with_checked_facts(WordFamily.model_validate(data), "PRESS", "en")
    assert english.quiz_clue.startswith("What do you do")
