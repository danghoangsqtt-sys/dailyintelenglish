"""Read Along: script job, shared landscape art, and Step 5 render props."""

from io import BytesIO

import pytest
from PIL import Image

from backend.ai.llm import ai_job_service
from backend.ai.llm.ai_worker import AIWorker
from backend.ai.llm.contracts import AIMode, GenerationResult
from backend.ai.llm.fake_provider import FakeProvider
from backend.ai.llm.router import AIRouter
from backend.content import beats_service, project_service, read_along, script_pipeline, script_service
from backend.core.config import settings
from backend.core.exceptions import ValidationError
from backend.media import short_pictures, video_renderer_remotion
from backend.schemas.project import ScriptConfig, SpeakerConfig, is_short_video

PASSAGE = read_along.Passage(
    title="A Small Step",
    picture="Two friends talking beside a sunny garden path",
    sentences=["I felt shy at first", "My friend waited for me.", "I said hello.", "Then we walked to class."],
)


async def test_read_along_from_generation_to_video_props(db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr(video_renderer_remotion, "REMOTION_VISUALS_DIR", tmp_path / "stage")
    project = await project_service.create_project(db, ScriptConfig(
        name="Reading sample", topic="Small steps", cefr_level="A2", duration_minutes=0.75,
        genre="storytelling", accent="american", num_speakers=1, presentation_mode="solo_explainer",
        explainer_style="readalong", speakers=[SpeakerConfig(name="Lina", gender="female", accent="american")],
    ))
    assert is_short_video(project)
    response = GenerationResult(
        text=PASSAGE.model_dump_json(), provider="fake-gemini", model="fake-model",
        latency_ms=1.0, attempt=1, prompt_hash="test",
    )
    router = AIRouter(primary=FakeProvider("openai_compat", [response]),
                      fallback=FakeProvider("ollama", []), mode=AIMode.CLOUD)
    job, _ = await ai_job_service.create_job(db, project["id"], "script", {"project": project, "operation": "script"})
    claimed = await ai_job_service.claim_job(db, job["id"], "read-along-test")
    await script_pipeline.make_handler(router)(claimed, AIWorker(db_getter=lambda: db))
    final = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final["status"] == "complete", final
    lines = await script_service.get_script(db, project["id"])
    assert [line["text"] for line in lines] == ["I felt shy at first.", *PASSAGE.sentences[1:]]
    lines = await script_service.save_script(
        db, project["id"], [*lines, {"speaker_id": lines[0]["speaker_id"], "text": "I felt more confident."}],
    )
    cards = [line["language_notes"]["readalong"] for line in lines]
    assert len({card["word"] for card in cards}) == 1
    assert beats_service.checked_card("readalong", cards[0])["title"] == PASSAGE.title
    with pytest.raises(ValidationError, match="Each sentence"):
        await script_service.update_script_line(db, project["id"], lines[0]["id"], "too " * 19, lines[0]["language_notes"])
    assert (await script_service.get_script_line(db, project["id"], lines[0]["id"]))["text"] == lines[0]["text"]

    image = BytesIO()
    Image.new("RGB", (500, 300), "#d2e1c5").save(image, "PNG")
    picture = await short_pictures.upload(project["id"], cards[0]["word"], image.getvalue(), style="readalong")
    with Image.open(picture) as fitted:
        assert fitted.size == short_pictures.READ_ALONG_SIZE

    audio = {"timestamps": [], "word_timestamps": []}
    for index, line in enumerate(lines):
        start = index * 3
        audio["timestamps"].append({"start_sec": start, "end_sec": start + 2, "label": "Lina",
                                    "speaker_id": line["speaker_id"], "text": line["text"]})
        audio["word_timestamps"].append({"words": [{"text": line["text"].split()[0], "start_sec": start,
                                                  "end_sec": start + 0.2}]})
    props = await video_renderer_remotion._build_input_props(
        db, project, audio, None, "outline", visual_mode="podcast_black", layout="vertical",
    )
    assert props["shortStyle"] == "readalong"
    assert all(line["readalong"]["title"] == PASSAGE.title for line in props["lines"])
    assert len({line["readalong"]["pictureUrl"] for line in props["lines"]}) == 1
    assert props["lines"][1]["words"][0]["startSec"] == 3


def test_passage_rejects_text_that_does_not_fit():
    with pytest.raises(ValueError, match="passage must fit"):
        read_along.build_beats(PASSAGE.model_copy(update={"sentences": ["little " * 17] * 7}))
    with pytest.raises(ValueError, match="Each sentence"):
        read_along.build_beats(PASSAGE.model_copy(update={"sentences": [" "] * 4}))
