"""Phase 88: the "Easy grammar" Short -- the lesson, its review and its beats."""

import json

import pytest

from backend.content.grammar_lesson import GrammarLesson, build_beats, grammar_prompt, usable_card
from backend.schemas.project import LINE_DRAWN_STYLES, SHORT_STYLES, short_max_minutes, short_minutes
from backend.tests.test_visuals_project_api import client, locked_character  # noqa: F401


def _chips(*pairs):
    return [{"text": text, "role": role} for text, role in pairs]


PASSIVE = {
    "point": "Câu bị động", "kind": "essence",
    "hook": {"pain": "Bạn đang phải học thuộc cả chục công thức câu bị động",
             "formulas": ["S + am/is/are + V3", "S + was/were + V3", "S + has/have + been + V3", "S + will be + V3"],
             "promise": "Hôm nay mình sẽ giúp bạn hiểu bản chất câu bị động trong một phút"},
    "scenes": [
        {"label": "Bản chất cốt lõi", "title": "Câu bị động là câu miêu tả trạng thái!", "subtitle": "So sánh hai câu",
         "steps": [
             {"say": "Nhìn hai câu này nhé", "card": {"kind": "compare", "left_en": "She is beautiful.", "left_vi": "Cô ấy đẹp.",
                                                    "right_en": "The classroom is cleaned.", "right_vi": "Lớp học được dọn."}},
             {"say": "Cấu trúc giống hệt nhau: chủ ngữ, động từ to be và một từ miêu tả",
              "card": {"kind": "formula", "chips": _chips(("S", "s"), ("BE", "be"), ("ADJ / V3", "v3"))}},
             {"say": "Vậy câu bị động chỉ là miêu tả trạng thái của chủ ngữ", "card": {"kind": "sticker"}}]},  # unusable card
        {"label": "Bẻ khoá V3", "title": "Chiếc nhãn dán kết quả!",
         "steps": [
             {"say": "V3 giống như một nhãn dán", "card": {"kind": "sticker", "text": "CLEANED"}},
             {"say": "Nhãn dán đứng im, không bao giờ chia thì", "card": {"kind": "rule", "text": "V3 đứng yên, KHÔNG chia thì"}}]},
        {"label": "Vai trò to be", "title": "Kẻ duy nhất gánh thời gian!",
         "steps": [
             {"say": "Muốn đổi thì, bạn chỉ đổi động từ to be",
              "card": {"kind": "example", "en": "The classroom was cleaned yesterday.", "vi": "Lớp học đã được dọn hôm qua.",
                       "marks": _chips(("was", "be"), ("cleaned", "v3"), ("bị dọn", "v3"))}},
             {"say": "Being là to be cộng ing", "card": {"kind": "lego", "chips": _chips(("BE", "be"), ("-ING", "ing")),
                                                           "result": {"text": "BEING", "role": "be"}}}]},
        {"label": "Sai", "title": "Không có thẻ", "steps": [{"say": "Một cảnh không có thẻ nào", "card": {"kind": "rule"}}]},
    ],
    "summary": {"columns": ["Thì", "To be gánh thì", "Nhãn"],
                "rows": [{"cells": ["Đơn", "is", "cleaned"], "say": "Thì đơn: is cộng cleaned"},
                         {"cells": ["Tiếp diễn", "is being", "cleaned"], "say": "Tiếp diễn: is being cộng cleaned"},
                         {"cells": ["lỗi"], "say": "Một dòng thiếu ô"}]},
    "core_rule": "To be gánh thời gian, V3 là nhãn dán đứng im",
    "quiz": {"question": "The letter ___ yesterday.", "options": ["was sent", "is sent"], "answer": "was sent"},
}


def test_grammar_is_a_line_drawn_academic_short_up_to_three_minutes():
    assert "grammar" in SHORT_STYLES and "grammar" in LINE_DRAWN_STYLES
    assert short_minutes("grammar") == 2.0 and short_max_minutes("grammar") == 3.0


def test_the_lesson_becomes_beats_with_stacking_cards_and_a_table_that_fills():
    beats = build_beats(GrammarLesson.model_validate(PASSIVE), "vi")
    texts = [text for text, _ in beats]
    cards = [card for _, card in beats]
    assert texts[:3] == ["Bạn đang phải học thuộc cả chục công thức câu bị động.", "Quên hết đi!",
                         "Hôm nay mình sẽ giúp bạn hiểu bản chất câu bị động trong một phút."]
    assert cards[0]["beat"] == "hook" and cards[0]["cards"][0]["kind"] == "formulas"
    assert [c["kind"] for c in cards[1]["cards"]] == ["formulas", "stamp"]
    scene_one = [card for card in cards if card["beat"] == "scene" and card["scene"] == 1]
    assert [len(card["cards"]) for card in scene_one] == [1, 2, 2]  # the third step talks over the cards shown
    assert scene_one[0]["label"] == "BẢN CHẤT CỐT LÕI" and scene_one[0]["subtitle"] == "So sánh hai câu"
    assert {card["scene"] for card in cards if card["beat"] == "scene"} == {1, 2, 3}  # the card-less scene is left out
    example = next(c for card in cards for c in card["cards"] if c["kind"] == "example")
    assert [mark["text"] for mark in example["marks"]] == ["was", "cleaned"]  # a mark not in the sentence is dropped
    summary = [card for card in cards if card["beat"] == "summary"]
    assert [len(card["cards"][0]["rows"]) for card in summary] == [0, 1, 2]  # the short row is dropped
    core = next(card for card in cards if card["beat"] == "core")
    assert [c["kind"] for c in core["cards"]] == ["table", "core"]
    assert texts[-2] == "Câu hỏi nhanh: The letter ___ yesterday." and cards[-2]["cards"][0]["options"] == ["was sent", "is sent"]
    assert cards[-1]["beat"] == "follow" and texts[-1].startswith("Comment đáp án")


def test_english_fields_keep_no_vietnamese_and_too_few_scenes_fail():
    assert usable_card(GrammarLesson.model_validate(PASSIVE).scenes[0].steps[0].card)["left_en"] == "She is beautiful."
    from backend.content.grammar_lesson import GrammarCard
    assert usable_card(GrammarCard(kind="example", en="Cô ấy rất đẹp.")) is None
    assert usable_card(GrammarCard(kind="formula", chips=[{"text": "S", "role": "subject?"}])) is None
    assert GrammarCard(kind="formula", chips=[{"text": "S", "role": "SUBJECT"}]).chips[0].role == "plain"
    lesson = GrammarLesson.model_validate({**PASSIVE, "scenes": PASSIVE["scenes"][:2] + PASSIVE["scenes"][3:]})
    with pytest.raises(ValueError, match="only 2 scenes"):
        build_beats(lesson, "vi")
    english = build_beats(GrammarLesson.model_validate(PASSIVE), "en")
    assert english[1][0] == "Forget them all!" and english[0][1]["label"] == "HOOK • NO MORE ROTE LEARNING"
    assert "Vietnamese learners" in grammar_prompt("Câu bị động", "B1", "vi")


async def test_a_grammar_script_job_reviews_the_lesson_and_switches_the_narrator_to_vieneu(db):
    from backend.ai.llm import ai_job_service
    from backend.ai.llm.ai_worker import AIWorker
    from backend.content import project_service, script_pipeline, script_service
    from backend.schemas.project import ScriptConfig, SpeakerConfig
    from backend.tests.test_script_pipeline import _build_router, _result

    project = await project_service.create_project(db, ScriptConfig(
        name="Câu bị động", topic="Câu bị động", cefr_level="B1", duration_minutes=2.0, num_speakers=1, genre="informational",
        accent="american", presentation_mode="solo_explainer", explainer_style="grammar",
        speakers=[SpeakerConfig(name="Huyền", gender="female", accent="american")]))
    fixed = json.loads(json.dumps(PASSIVE))
    fixed["core_rule"] = "To be gánh thời gian, còn V3 là nhãn dán đứng im"
    review = {"issues": ["core rule reworded"], "lesson": fixed}
    router, provider, _ = _build_router([_result(json.dumps(PASSIVE, ensure_ascii=False)),
                                         _result(json.dumps(review, ensure_ascii=False))])
    job, _ = await ai_job_service.create_job(db, project["id"], "script", {"project": project, "operation": "script"})
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    await script_pipeline.make_handler(router)(claimed, AIWorker(db_getter=lambda: db))
    final = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final["status"] == "complete", final.get("error_message")
    lines = await script_service.get_script(db, project["id"])
    assert lines[0]["language_notes"]["grammar"]["beat"] == "hook"
    assert any(line["text"] == "To be gánh thời gian, còn V3 là nhãn dán đứng im." for line in lines)  # the reviewed lesson
    speaker = (await project_service.get_project(db, project["id"]))["speakers"][0]
    assert speaker["tts_engine"] == "vieneu"
    assert provider.call_count == 2


async def test_a_failed_review_keeps_the_first_lesson(db):
    from backend.ai.llm import ai_job_service
    from backend.ai.llm.ai_worker import AIWorker
    from backend.content import project_service, script_pipeline, script_service
    from backend.schemas.project import ScriptConfig, SpeakerConfig
    from backend.tests.test_script_pipeline import _build_router, _result

    project = await project_service.create_project(db, ScriptConfig(
        name="Câu bị động", topic="Câu bị động", cefr_level="B1", duration_minutes=2.0, num_speakers=1, genre="informational",
        accent="american", presentation_mode="solo_explainer", explainer_style="grammar",
        speakers=[SpeakerConfig(name="Huyền", gender="female", accent="american")]))
    router, _, _ = _build_router([_result(json.dumps(PASSIVE, ensure_ascii=False)), _result("not json"),
                                  _result("still not json"), _result("no"), _result("no")])
    job, _ = await ai_job_service.create_job(db, project["id"], "script", {"project": project, "operation": "script"})
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    await script_pipeline.make_handler(router)(claimed, AIWorker(db_getter=lambda: db))
    final = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final["status"] == "complete", final.get("error_message")
    lines = await script_service.get_script(db, project["id"])
    assert any(line["text"] == "To be gánh thời gian, V3 là nhãn dán đứng im." for line in lines)


def test_grammar_cards_reach_the_video_props_and_survive_step_2(client):  # noqa: F811
    import asyncio

    import aiosqlite

    from backend.core.config import settings
    from backend.media import video_renderer_remotion as remotion
    from backend.tests.test_visuals_project_api import data

    project = data(client.post("/api/projects", json={
        "name": "Câu bị động", "topic": "Câu bị động", "cefr_level": "B1", "duration_minutes": 2.0, "num_speakers": 1,
        "genre": "informational", "accent": "american", "presentation_mode": "solo_explainer", "explainer_style": "grammar",
        "speakers": [{"name": "Huyền", "gender": "female", "accent": "american"}]}))
    speaker = project["speakers"][0]["id"]
    beats = build_beats(GrammarLesson.model_validate(PASSIVE), "vi")[:4]
    data(client.put(f"/api/projects/{project['id']}/script", json={"lines": [
        {"speaker_id": speaker, "text": text, "language_notes": {"grammar": card}} for text, card in beats]}))
    saved = data(client.get(f"/api/projects/{project['id']}/script"))
    assert saved[1]["language_notes"]["grammar"]["cards"][1]["kind"] == "stamp"
    audio = {"mp3_path": str(settings.DATA_DIR / "x.mp3"), "word_timestamps": [{"words": []} for _ in beats],
             "timestamps": [{"start_sec": float(at), "end_sec": at + 0.9, "label": "Huyền", "speaker_id": speaker, "text": line["text"]}
                            for at, line in enumerate(saved)]}

    async def props():
        async with aiosqlite.connect(settings.db_path) as db:
            db.row_factory = aiosqlite.Row
            full = data(client.get(f"/api/projects/{project['id']}"))
            return await remotion._build_input_props(db, full, audio, None, visual_mode="podcast_black", layout="vertical")

    built = asyncio.run(props())
    assert built["shortStyle"] == "grammar"
    assert built["lines"][3]["grammar"]["beat"] == "scene" and built["lines"][3]["grammar"]["scene"] == 1


def test_the_shorts_batch_makes_grammar_shorts_of_two_minutes(client):  # noqa: F811
    from backend.schemas.project import is_short_video
    from backend.tests.test_visuals_project_api import data

    narrator = locked_character("Narrator", "red")
    result = data(client.post("/api/shorts-batch/create", json={
        "topic_name": "Shorts", "series_name": "Ngữ pháp", "template": "grammar", "cast": [narrator], "cefr_level": "B1",
        "start_date": "2026-11-04", "every_days": 1, "make_projects": True, "items": [{"title": "Câu bị động", "brief": ""}]}))
    tree = data(client.get("/api/channel"))
    series = next(s for topic in tree["topics"] for s in topic["series"] if s["id"] == result["series_id"])
    project = data(client.get(f"/api/projects/{series['episodes'][0]['project_id']}"))
    assert project["explainer_style"] == "grammar" and is_short_video(project) and project["duration_minutes"] == 2.0


def test_real_run_a_scene_never_opens_on_an_empty_screen_and_the_prompt_has_a_model_lesson():
    """Sandbox run 2026-11-03: a scene's first card was unusable and its first line showed nothing."""
    lesson = json.loads(json.dumps(PASSIVE))
    lesson["scenes"][1]["steps"][0]["card"] = {"kind": "sticker"}  # no text: dropped
    beats = build_beats(GrammarLesson.model_validate(lesson), "vi")
    scene_two = [card for _, card in beats if card["beat"] == "scene" and card["scene"] == 2]
    assert [[c["kind"] for c in card["cards"]] for card in scene_two] == [["rule"], ["rule"]]
    assert "Chiếc nhãn dán kết quả" in grammar_prompt("Thì hiện tại hoàn thành", "B1", "vi")


def test_real_run_markdown_bold_is_removed():
    from backend.content.grammar_lesson import with_clean_text

    lesson = json.loads(json.dumps(PASSIVE))
    lesson["scenes"][0]["steps"][0]["card"]["left_en"] = "The letter **IS** on the desk."
    cleaned = with_clean_text(GrammarLesson.model_validate(lesson))
    assert cleaned.scenes[0].steps[0].card.left_en == "The letter IS on the desk."
    assert cleaned.quiz.question == "The letter ___ yesterday."  # the blank stays


def test_owner_report_english_texts_are_kept_out_of_a_vietnamese_lesson():
    """Owner 2026-11-03: a Vietnamese video showed "Past Participle (V3) is an adjective; it never changes for tense."
    as a rule card; an English label or subtitle is left out the same way."""
    from backend.content.grammar_lesson import looks_english, review_prompt

    assert looks_english("Past Participle (V3) is an adjective; it never changes for tense.")
    assert not looks_english("V3 đứng im, KHÔNG chia thì")
    assert not looks_english("BE + V3")
    assert not looks_english("CLEANED")
    lesson = json.loads(json.dumps(PASSIVE))
    lesson["scenes"][1]["label"] = "The sticker of the result"
    lesson["scenes"][1]["steps"][1]["card"] = {"kind": "rule", "text": "Past Participle (V3) is an adjective; it never changes for tense."}
    beats = build_beats(GrammarLesson.model_validate(lesson), "vi")
    scene_two = [card for _, card in beats if card["beat"] == "scene" and card["scene"] == 2]
    assert scene_two[0]["label"] == "" and all(c["kind"] != "rule" for card in scene_two for c in card["cards"])
    english = build_beats(GrammarLesson.model_validate(lesson), "en")  # an English lesson keeps it
    assert any(c["kind"] == "rule" for _, card in english for c in card["cards"])
    assert "LỪNG LỘT NGÔN NGỮ" in review_prompt("{}", "vi")


def test_real_run_the_error_lesson_has_its_own_model_long_stickers_become_rules_and_an_empty_table_is_skipped():
    """Sandbox run 2026-11-03: "I very like" borrowed the passive model's idea, a sticker was a whole sentence, and a
    table with no fitting row was read out empty."""
    from backend.content.grammar_lesson import _ERROR_EXAMPLE, GrammarCard

    prompt = grammar_prompt("Lỗi người Việt hay mắc: I very like", "B1", "vi")
    assert "vietnamese_error" in prompt and "I really like this song." in prompt
    assert build_beats(GrammarLesson.model_validate(_ERROR_EXAMPLE), "vi")[-2][0] == "Câu hỏi nhanh: I ___ like this song."
    assert usable_card(GrammarCard(kind="sticker", text="LIKE sau very phải là tính từ, không phải động từ"))["kind"] == "rule"
    assert usable_card(GrammarCard(kind="sticker", text="CLEANED"))["kind"] == "sticker"
    lesson = json.loads(json.dumps(PASSIVE))
    lesson["summary"]["rows"] = [{"cells": ["chỉ một ô"], "say": "Một dòng thiếu ô"}] * 2
    beats = build_beats(GrammarLesson.model_validate(lesson), "vi")
    assert not any(card["beat"] == "summary" for _, card in beats)
    assert next(card for _, card in beats if card["beat"] == "core")["cards"][0]["kind"] == "core"


def test_a_grammar_line_cannot_be_regenerated_alone(client):  # noqa: F811
    """2026-11-03: the general rewrite prompt wrote an English line and dropped the beat's card."""
    from backend.tests.test_visuals_project_api import data

    project = data(client.post("/api/projects", json={
        "name": "Câu bị động", "topic": "Câu bị động", "cefr_level": "B1", "duration_minutes": 2.0, "num_speakers": 1,
        "genre": "informational", "accent": "american", "presentation_mode": "solo_explainer", "explainer_style": "grammar",
        "speakers": [{"name": "Huyền", "gender": "female", "accent": "american"}]}))
    speaker = project["speakers"][0]["id"]
    text, card = build_beats(GrammarLesson.model_validate(PASSIVE), "vi")[0]
    lines = data(client.put(f"/api/projects/{project['id']}/script", json={"lines": [
        {"speaker_id": speaker, "text": text, "language_notes": {"grammar": card}}]}))
    response = client.post(f"/api/projects/{project['id']}/script/regenerate", json={"line_id": lines[0]["id"]})
    assert response.status_code in (400, 422) and "cannot be regenerated alone" in response.text
