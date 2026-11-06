"""Phase 98: a Doodle story -- one whole story, target words woven in, one still hand-drawn picture for every sentence or two."""

import json

import pytest
from pydantic import ValidationError as SchemaError

from backend.ai.image import pipelines, recipes
from backend.ai.llm.prompt_loader import load_presentation_block, render_explainer_prompt
from backend.content import project_service, script_pipeline, youtube_service
from backend.core.exceptions import ValidationError
from backend.library import activity_library_service, explainer_service
from backend.library.explainer_timing import ScriptIndex, SpeechTimeline
from backend.schemas.explainer import ExplainerPlan
from backend.schemas.project import VOICE_ONLY_STYLES, ScriptConfig, is_short_video

STORY = ("The ancient Greeks told a story about a boy. His name was Icarus, and he lived on an island with his father, who "
         "was the cleverest maker in the whole world at that time, they said. He wanted to fly! Could he do it?")


def _config(**changes) -> dict:
    return {"name": "n", "topic": "Icarus", "cefr_level": "B1", "genre": "storytelling", "accent": "american", "num_speakers": 1,
            "presentation_mode": "solo_explainer", "explainer_style": "doodle", "duration_minutes": 8,
            "speakers": [{"name": "Narrator", "gender": "female", "accent": "american", "voice_id": "en-US-JennyNeural"}], **changes}


@pytest.mark.parametrize("subject", ["history", "myth", "field", "story"])
def test_the_four_kinds_of_story(subject):
    project = ScriptConfig(**_config(explainer_subject=subject))
    assert project.explainer_subject == subject and project.explainer_structure
    assert "doodle" in VOICE_ONLY_STYLES and not is_short_video(project.model_dump())


def test_it_lasts_three_to_twelve_minutes_and_takes_only_its_own_kinds():
    config = _config()
    del config["duration_minutes"]
    project = ScriptConfig(**config)
    assert project.explainer_subject == "history" and project.duration_minutes == 8
    for bad in (2.5, 12.5):
        with pytest.raises(SchemaError, match="3 to 12 minutes"):
            ScriptConfig(**_config(duration_minutes=bad))
    with pytest.raises(SchemaError, match="history, a myth"):
        ScriptConfig(**_config(explainer_subject="product"))


def test_history_myth_and_story_belong_to_a_doodle_story_only():
    with pytest.raises(SchemaError, match="belong to a Doodle story"):
        ScriptConfig(**_config(explainer_style="vox", explainer_subject="myth"))


def test_a_pasted_article_is_allowed_here_and_still_refused_elsewhere():
    assert ScriptConfig(**_config(source_kind="article", source_text="Some long enough material " * 5)).source_kind == "article"
    with pytest.raises(SchemaError, match="news article"):
        ScriptConfig(**_config(explainer_style="vox", source_kind="article", source_text="Some long enough material " * 5))


def test_code_cuts_the_narration_into_pictures_covering_every_word_once():
    lines = [{"id": "a", "text": STORY}, {"id": "b", "text": "Yes. Follow Daily Beyond English."}]
    spans = explainer_service.doodle_spans(lines)
    assert " ".join(span["narration"] for span in spans) == f"{STORY} Yes. Follow Daily Beyond English."
    assert all(len(span["narration"].split()) <= explainer_service.VOX_MAX_SEGMENT_WORDS for span in spans)
    assert spans[0]["narration"].endswith("about a boy.") and spans[0]["start"] == {"line_id": "a", "token_index": 0}
    assert spans[-1]["end"] == {"line_id": "b", "token_index": 5} and spans[-1]["line_ids"] == ["a", "b"]


def test_a_sentence_without_a_stop_is_still_cut_within_the_limit():
    lines = [{"id": "a", "text": " ".join(f"word{i}" for i in range(100))}]
    spans = explainer_service.doodle_spans(lines)
    assert max(len(span["narration"].split()) for span in spans) <= explainer_service.VOX_MAX_SEGMENT_WORDS


def test_picture_cuts_use_measured_audio_and_respect_the_word_limit_at_the_end():
    lines = [{"id": "a", "text": " ".join(f"word{i}" for i in range(26))}]
    assert [len(span["narration"].split()) for span in explainer_service.doodle_spans(lines)] == [24, 2]
    timing = SpeechTimeline(ScriptIndex(lines), (), tuple(range(27)), 26)
    assert [len(span["narration"].split()) for span in explainer_service.doodle_spans(lines, timing)] == [12, 12, 2]


def test_the_ais_pictures_become_the_segments():
    lines = [{"id": "a", "text": STORY}]
    spans = explainer_service.doodle_spans(lines)
    pictures = [{"id": span["id"], "description": f"Drawing of {span['id']}.", "labels": []} for span in spans]
    pictures[0]["labels"] = ["CRETE", "Historical doodle of the island"]
    wire = json.loads(explainer_service.doodle_wire(json.dumps({"pictures": pictures}), spans))
    first = wire["segments"][0]
    assert first["visual"]["kind"] == "photo" and first["visual"]["asset"] is None and first["visual"]["fit"] == "cover"
    assert 'reading exactly "CRETE"' in first["visual"]["prompt"]
    assert "Historical doodle" not in first["visual"]["prompt"]  # the sample's fault: the picture's own title drawn on it
    for subject in ("myth", "story"):
        wire = json.loads(explainer_service.doodle_wire(json.dumps({"pictures": pictures}), spans, subject))
        assert wire["segments"][0]["visual"]["prompt"] == f"Drawing of {spans[0]['id']}"


def test_an_answer_missing_many_pictures_is_asked_for_again_and_one_gap_is_filled():
    lines = [{"id": "a", "text": " ".join(f"This is short sentence number {i} of the story." for i in range(20))}]
    spans = explainer_service.doodle_spans(lines)
    all_but_one = [{"id": span["id"], "description": "x", "labels": []} for span in spans[:-1]]
    wire = json.loads(explainer_service.doodle_wire(json.dumps({"pictures": all_but_one}), spans))
    assert wire["segments"][-1]["visual"]["prompt"] == spans[-1]["narration"]
    with pytest.raises(ValidationError, match="are missing"):
        explainer_service.doodle_wire(json.dumps({"pictures": all_but_one[:1]}), spans)


def _plan_segment(number: int) -> dict:
    return {"id": f"pic-{number}", "intent": "x", "line_ids": ["l"], "start": {"line_id": "l", "token_index": number},
            "end": {"line_id": "l", "token_index": number + 1}, "visual": {"kind": "photo", "asset": None, "prompt": "x"}}


def test_a_long_plan_fits_and_an_endless_one_does_not():
    base = {"project_id": "p", "revision": 1, "source_fingerprint": "0" * 64, "aspects": ["16:9"],
            "presenter": {"speaker_id": "s", "profile_id": "c", "identity_version": 1}}
    assert len(ExplainerPlan.model_validate({**base, "segments": [_plan_segment(i) for i in range(94)]}).segments) == 94
    with pytest.raises(SchemaError):
        ExplainerPlan.model_validate({**base, "segments": [_plan_segment(i) for i in range(151)]})


def test_the_picture_prompt_keeps_the_hero_and_allows_only_quoted_words():
    with_label = recipes.qwen_doodle_prompt('a map of Crete; hand-lettered label reading exactly "CRETE"', "a stick figure with a red scarf")
    assert "aged warm parchment" in with_label and "fresh green and warm yellow" in with_label
    assert "a stick figure with a red scarf" in with_label and "Only the labels written in quotes" in with_label
    assert "No words or letters anywhere" in recipes.qwen_doodle_prompt('a model of the capsule named "Columbia"')
    redraw = recipes.qwen_doodle_prompt('a dog beside the door; hand-lettered label reading exactly "shelter"', allow_labels=False)
    assert '"shelter"' not in redraw
    assert "a dog beside the door" in redraw and "No words or letters anywhere" in redraw


async def _draw(monkeypatch, tmp_path, style: str, count: int) -> tuple[list[int], list, list[int]]:
    plan = {"revision": 3, "aspects": ["16:9"], "segments": [
        {"id": f"pic-{i}", "intent": "x", "line_ids": ["l"], "start": {"line_id": "l", "token_index": i}, "end": {"line_id": "l", "token_index": i + 1},
         "visual": {"kind": "photo", "asset": None, "prompt": "a drawing"}} for i in range(count)]}
    groups, kept, saves = [], [], []

    class Runner:
        def get_db(self):
            return object()

        async def boundary(self, *args):
            return None

    class Engine:
        async def qwen_batch(self, model, items, consumer):
            groups.append(len(items))
            for item in items:
                with open(item["output_path"], "wb") as stream:
                    stream.write(b"png")

    class NoLock:
        async def __aenter__(self):
            return None

        async def __aexit__(self, *args):
            return False

    async def get_plan(db, project_id):
        return {"plan": plan, "current_source_fingerprint": "f" * 64}

    async def import_illustration(db, project_id, content, name):
        return {"asset": {"asset_id": name.removesuffix(".png").replace("pic-", "a"), "version": 1, "content_hash": "0" * 64}}

    async def save_plan(db, project_id, body):
        saves.append(sum(1 for segment in body.segments if segment.visual.asset))
        plan["segments"] = [segment.model_dump() for segment in body.segments]

    async def upload(db, name, content, fields):
        kept.append(fields)
        return {"id": "lib"}

    async def review(db, item, status):
        return None

    async def notes(db, project_id):
        return {"hero": "a stick figure with a red scarf"}

    async def get_project(db, project_id):
        return {"explainer_style": style}

    monkeypatch.setattr(pipelines, "get_image_engine", lambda: Engine())
    monkeypatch.setattr(pipelines.settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr(pipelines, "write_transaction", lambda db: NoLock())
    monkeypatch.setattr(pipelines, "read_transaction", lambda: NoLock())
    monkeypatch.setattr(explainer_service, "get_plan", get_plan)
    monkeypatch.setattr(explainer_service, "import_illustration", import_illustration)
    monkeypatch.setattr(explainer_service, "save_plan", save_plan)
    monkeypatch.setattr(explainer_service, "doodle_notes", notes)
    monkeypatch.setattr(activity_library_service, "upload_activity_bytes", upload)
    monkeypatch.setattr(activity_library_service, "set_review", review)
    monkeypatch.setattr(project_service, "get_project", get_project)
    await pipelines.explainer_illustrations({"id": "j", "target_id": "p1"}, Runner())
    return groups, kept, saves


async def test_doodle_pictures_are_saved_group_by_group_and_stay_out_of_the_library(monkeypatch, tmp_path):
    groups, kept, saves = await _draw(monkeypatch, tmp_path, "doodle", 45)
    assert groups == [20, 20, 5] and saves == [20, 40, 45]  # a late failure keeps what was drawn
    assert kept == []


async def test_a_vox_plan_is_still_drawn_at_once_and_kept_in_the_library(monkeypatch, tmp_path):
    groups, kept, saves = await _draw(monkeypatch, tmp_path, "vox", 45)
    assert groups == [45] and saves == [45] and len(kept) == 45


def test_target_words_are_counted_with_their_forms():
    texts = ["He tried to escape. The escapes failed.", "Escaping was hard, and escaped men ran.", "A wax wing. Waxes melt."]
    assert script_pipeline.term_uses("escape", texts) == 4
    assert script_pipeline.term_uses("wax", texts) == 2
    assert script_pipeline.doodle_short_terms(["escape", "wax"], texts) == ["wax"]


def test_a_doodle_outline_chooses_its_words_before_any_line():
    outline = script_pipeline.DoodleOutline.model_validate({"title": "t", "target_terms": [" escape ", "WAX", "wing", "island", "trial"], "hero": "h",
                                                            "sections": [{"index": 1, "objective": "the objective", "target_words": 10}]})
    assert outline.target_terms == ["escape", "wax", "wing", "island", "trial"]
    with pytest.raises(SchemaError):
        script_pipeline.DoodleOutline.model_validate({"title": "t", "sections": [{"index": 1, "objective": "the objective", "target_words": 10}]})


@pytest.mark.parametrize(("subject", "expected"), [("history", "KIND: HISTORY"), ("myth", "KIND: MYTH"), ("field", "KIND: A SPECIALISED"),
                                                   ("story", "KIND: AN ORIGINAL SHORT STORY")])
async def test_each_kind_gets_its_arc_and_never_the_old_explainer_formula(subject, expected):
    block = await load_presentation_block("solo_explainer", "why", 1, subject, "doodle")
    assert expected in block and "ONE WHOLE STORY" in block and "WHY structure" not in block and "OPENING (the first section only)" not in block
    assert "A FIELD OR JOB" not in block


async def test_the_vox_and_presenter_prompts_do_not_change():
    for style in ("vox", "presenter"):
        block = await load_presentation_block("solo_explainer", "why", 1, "topic", style)
        assert "Doodle Story" not in block and "Solo Explainer — WHY" in block
    vox = await render_explainer_prompt(vox=True, style="vox", topic="t", cefr_level="B1", structure="why", lines=[], assets=[], scenes=[],
                                        activities=[], previous=None, output_schema={}, previous_error="", previous_output="")
    assert "VOX-style explainer" in vox


async def test_the_picture_prompt_lists_every_span_and_asks_for_no_style_words():
    prompt = await render_explainer_prompt(vox=True, style="doodle", subject="myth", hero="a boy with a red scarf", terms=["wax"], topic="Icarus",
                                           cefr_level="B1", lines=[{"id": "pic-1", "narration": "He flew."}], output_schema={}, source_text="",
                                           previous_error="", previous_output="")
    assert 'pic-1: "He flew."' in prompt and "never mention style" in prompt and "wax" in prompt and "return an empty array" in prompt
    history = await render_explainer_prompt(vox=True, style="doodle", subject="history", hero="a boy with a red scarf", terms=[],
                                             topic="Apollo 11", cefr_level="B1", lines=[], output_schema={}, source_text="",
                                             previous_error="", previous_output="")
    assert "Apollo lunar module Eagle" in history and "red scarf" not in history


def test_a_short_story_says_it_is_fiction_in_the_description():
    package = {"description": "A story.", "hook": "", "hashtags": []}
    project = {"explainer_style": "doodle", "explainer_subject": "story", "audience_effective": "both", "name": "n", "topic": "t", "speakers": []}
    composed = youtube_service.compose(package, project, [], None, None)
    assert composed["description"].startswith("This story is fiction")
    history = youtube_service.compose(package, {**project, "explainer_subject": "history"}, [], None, None)
    assert "fiction" not in history["description"]


def test_the_shortfall_counts_each_use_a_word_still_lacks():
    """Phase 99 (D172): a rewrite that adds uses is progress even before a word reaches three."""
    texts = ["The wax melted. Wax again.", "An island."]
    assert script_pipeline.doodle_shortfall(["wax", "island", "wing"], texts) == ["wax", "island", "island", "wing", "wing", "wing"]
    assert script_pipeline.doodle_shortfall(["wax"], texts + ["More wax."]) == []


def test_a_word_the_story_could_not_use_three_times_is_dropped_when_five_remain():
    """Phase 99 (D172): never forced in; with fewer than five words left the script still fails."""
    said = " ".join(f"{word} {word} {word}." for word in ("escape", "wax", "wing", "island", "trial"))
    kept, dropped = script_pipeline.settle_doodle_terms(["escape", "wax", "wing", "island", "trial", "labyrinth"], [said])
    assert kept == ["escape", "wax", "wing", "island", "trial"] and dropped == ["labyrinth"]
    kept, dropped = script_pipeline.settle_doodle_terms(["escape", "wax", "wing", "island", "labyrinth", "minotaur"],
                                                        ["escape escape escape wax wax wax wing wing wing island island island"])
    assert kept == [] and dropped == ["labyrinth", "minotaur"]
    kept, dropped = script_pipeline.settle_doodle_terms(["escape", "wax", "wing", "island", "trial"], [said])
    assert (kept, dropped) == (["escape", "wax", "wing", "island", "trial"], [])


def test_the_doodle_word_repair_walks_every_section():
    """Phase 99 (D172): one repair per section in story order (the first real automatic run failed with one repair)."""
    import inspect

    source = inspect.getsource(script_pipeline)
    assert "for spec in outline.sections:" in source and "section_index=spec.index" in source
    assert "missing_of=doodle_shortfall" in source
