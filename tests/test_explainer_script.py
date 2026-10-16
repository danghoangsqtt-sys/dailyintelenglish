"""Solo structures through actual prompt, bounded repair, generation and single-line regeneration paths."""
import copy
import json

import pytest

from backend.ai.llm import ai_job_service, prompt_loader
from backend.ai.llm.ai_worker import AIWorker
from backend.content import project_service, script_pipeline, script_service
from backend.core.exceptions import ScriptGenerationError, ValidationError
from backend.schemas.project import ScriptConfig, SpeakerConfig
from tests.test_script_pipeline import _build_router, _result, _words
from tests.test_script_service import SAMPLE_CONFIG


def solo_config(level="B1", structure="why"):
    config = copy.deepcopy(SAMPLE_CONFIG)
    config.update(name="Hoang habits", topic="Why do we build habits?", presentation_mode="solo_explainer",
                  explainer_structure=structure, num_speakers=1, cefr_level=level, duration_minutes=.8)
    config["speakers"] = config["speakers"][:1]
    config["speakers"][0]["name"] = "Hoang"
    return config


@pytest.mark.parametrize("structure", ["why", "how", "list"])
@pytest.mark.parametrize("level", ["A2", "B1", "C1"])
async def test_solo_prompt_structure_cefr_one_presenter_and_no_dialogue_genre(structure, level):
    config = solo_config(level, structure)
    prompt = await prompt_loader.render_script_prompt(**{key: value for key, value in config.items() if key != "name"})
    assert "Solo Explainer — " + structure.upper() in prompt
    assert "ONE presenter" in prompt and "addressed directly to the viewer" in prompt
    assert "CEFR " + level in prompt and "Language Features to Target" in prompt
    assert config["speakers"][0]["id"] in prompt and SAMPLE_CONFIG["speakers"][1]["id"] not in prompt
    assert await prompt_loader.load_genre_block("interview") not in prompt
    assert "Do not fabricate" in prompt


@pytest.mark.parametrize("mode,structure,count", [("unknown", "why", 1), ("solo_explainer", "html", 1), ("solo_explainer", "why", 2)])
async def test_invalid_solo_presentation_cannot_reach_a_template_or_provider(mode, structure, count):
    with pytest.raises(ValidationError):
        await prompt_loader.load_presentation_block(mode, structure, count)


async def test_classic_default_is_identical_to_explicit_classic_prompt():
    config = copy.deepcopy(SAMPLE_CONFIG)
    default = await prompt_loader.render_script_prompt(**config)
    explicit = await prompt_loader.render_script_prompt(**config, presentation_mode="classic", explainer_structure="why")
    assert default == explicit and "Solo Explainer" not in default


async def test_solo_service_rejects_two_speakers_before_provider_and_regeneration():
    config = solo_config()
    config["speakers"] = copy.deepcopy(SAMPLE_CONFIG["speakers"])
    router, provider, _ = _build_router([])
    with pytest.raises(ScriptGenerationError, match="one presenter"):
        await script_service.generate_script("p", config, router)
    with pytest.raises(ScriptGenerationError, match="one presenter"):
        await script_service.regenerate_line("p", config, "line", "A habit can help.", config["speakers"][0]["id"], router)
    assert provider.call_count == 0


@pytest.mark.parametrize("structure", ["why", "how", "list"])
async def test_single_line_regeneration_keeps_owner_id_voice_and_explanation_purpose(structure):
    config = solo_config("C1", structure)
    sid = config["speakers"][0]["id"]
    router, provider, _ = _build_router([_result(json.dumps({"id": "untrusted-new-id", "speaker_id": sid,
                                                           "text": "A familiar cue can make a routine easier to repeat."}))])
    line = await script_service.regenerate_line("p", config, "original-line-id", "Old text.", sid, router)
    assert line.id == "original-line-id" and line.speaker_id == sid
    assert "Solo Explainer — " + structure.upper() in provider.calls[0].prompt
    assert await prompt_loader.load_cefr_block("C1") in provider.calls[0].prompt


@pytest.mark.parametrize("structure", ["why", "how", "list"])
@pytest.mark.parametrize("repair", [False, True])
async def test_pipeline_solo_outline_sections_and_bounded_repair_persist_one_speaker(db, structure, repair):
    config = solo_config("B1", structure)
    project = await project_service.create_project(db, ScriptConfig(**{**config, "speakers": [SpeakerConfig(name="Hoang", gender="male", accent="american")]}))
    target = script_pipeline.compute_target_words("B1", .8)
    outline = {"title": "Habits", "sections": [{"index": 1, "objective": "Explain the everyday idea with a clear example", "target_words": target}]}
    # Unique test tokens exercise budget/ID logic only, not prose quality or CEFR certification.
    valid = [{"speaker": "S1", "text": _words(10, index * 10)} for index in range(10)]
    outcomes = [_result(json.dumps(outline))]
    if repair:
        outcomes.append(_result(json.dumps([{"speaker": "UNKNOWN-VOICE", "text": _words(100)}])))
    outcomes.append(_result(json.dumps(valid)))
    router, provider, _ = _build_router(outcomes)
    job, _ = await ai_job_service.create_job(db, project["id"], "script", {"project": project, "operation": "script"})
    claimed = await ai_job_service.claim_job(db, job["id"], "solo-worker")
    await script_pipeline.make_handler(router)(claimed, AIWorker(db_getter=lambda: db))
    final = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final["status"] == "complete", final.get("error_message")
    lines = await script_service.get_script(db, project["id"])
    assert len(lines) == 10 and {line["speaker_id"] for line in lines} == {project["speakers"][0]["id"]}
    assert provider.call_count == (3 if repair else 2)
    assert all("Solo Explainer — " + structure.upper() in call.prompt for call in provider.calls)
    assert script_pipeline.compute_config_hash(project, "script") != script_pipeline.compute_config_hash({**project, "explainer_structure": "different"}, "script")


async def test_invalid_second_speaker_after_bounded_repair_does_not_replace_saved_script(db):
    project = await project_service.create_project(db, ScriptConfig(**{**solo_config(), "speakers": [SpeakerConfig(name="Hoang", gender="male", accent="american")]}))
    sid = project["speakers"][0]["id"]
    await script_service.save_script(db, project["id"], [{"speaker_id": sid, "text": "The previous approved idea remains."}])
    # Refresh snapshot after saving, as the actual job entry does.
    project = await project_service.get_project(db, project["id"])
    outline = {"title": "Habits", "sections": [{"index": 1, "objective": "Explain the everyday habit with examples", "target_words": 100}]}
    bad = [{"speaker": "UNKNOWN-VOICE", "text": _words(100)}]
    router, provider, _ = _build_router([_result(json.dumps(outline)), _result(json.dumps(bad)), _result(json.dumps(bad))])
    job, _ = await ai_job_service.create_job(db, project["id"], "script", {"project": project, "operation": "script"})
    claimed = await ai_job_service.claim_job(db, job["id"], "solo-worker")
    await script_pipeline.make_handler(router)(claimed, AIWorker(db_getter=lambda: db))
    final = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final["status"] == "error" and provider.call_count == 3
    saved = await script_service.get_script(db, project["id"])
    assert saved[0]["text"] == "The previous approved idea remains."
