"""Request expansion is validated; copied and local scene prompts share a canonical composition."""

import json
from types import SimpleNamespace

import pytest

from backend.ai.image.recipes import SCENE_COMPOSITION, qwen_scene_prompt
from backend.core.exceptions import ProviderUnavailableError, SchemaValidationError, ValidationError
from backend.library.scene_prompts import generate_scene_prompt


DRAFT = {
    "name": "Rainy evening cafe", "place": "a quiet riverside cafe", "staging": "seated",
    "category": "food", "time_of_day": "night",
    "image_prompt": (
        "A photorealistic riverside cafe interior on a rainy evening, viewed at eye level through a wide lens. "
        "Warm amber pendant lamps illuminate oak tables, worn leather chairs and muted cream plaster walls. "
        "The windows reveal a wet riverside walkway and distant reflections on the water. "
        "Keep the center foreground open, with tables along the back and side walls. "
        "Natural perspective, believable material textures, restrained warm and cool contrast, inviting quiet mood."
    ),
}


class StubRouter:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    async def generate(self, request):
        self.calls.append(request)
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return SimpleNamespace(text=result if isinstance(result, str) else json.dumps(result))


@pytest.mark.parametrize("brief", [
    "Quán cà phê ven sông vào tối mưa, ánh đèn vàng ấm", "A quiet riverside cafe on a rainy evening",
])
async def test_vi_and_en_requests_return_persistable_english_prompt(brief):
    router = StubRouter(DRAFT)
    draft = await generate_scene_prompt(f"  {brief}  ", router)
    assert draft["source_request"] == brief
    assert draft["place"] == DRAFT["place"]
    assert draft["image_prompt"].startswith(DRAFT["image_prompt"])
    assert draft["image_prompt"].endswith(SCENE_COMPOSITION)
    assert qwen_scene_prompt(draft) == draft["image_prompt"]
    assert draft["image_prompt"].count(SCENE_COMPOSITION) == 1
    request = router.calls[0]
    assert brief in request.prompt
    assert request.purpose == "scene_prompt"
    assert request.json_schema["properties"]["image_prompt"]["minLength"] == 60
    assert "source_request" not in request.json_schema["properties"]
    assert "no people" in request.prompt


async def test_one_schema_repair_retains_original_request():
    router = StubRouter({**DRAFT, "place": "a place with far too many words"}, DRAFT)
    draft = await generate_scene_prompt("A quiet cafe", router)
    assert len(router.calls) == 2
    assert "previous response was invalid" in router.calls[1].prompt
    assert "A quiet cafe" in router.calls[1].prompt
    assert draft["place"] == DRAFT["place"]


async def test_repeated_invalid_response_has_no_fake_translation_fallback():
    router = StubRouter("not JSON", {**DRAFT, "image_prompt": "too short"})
    with pytest.raises(SchemaValidationError):
        await generate_scene_prompt("A quiet cafe", router)
    assert len(router.calls) == 2


async def test_provider_unavailable_is_reported_without_inventing_prompt():
    router = StubRouter(ProviderUnavailableError("Configure a text AI provider"))
    with pytest.raises(ProviderUnavailableError, match="Configure"):
        await generate_scene_prompt("A quiet cafe", router)
    assert len(router.calls) == 1


@pytest.mark.parametrize("brief", ["", "   ", "a" * 2001])
async def test_blank_or_oversized_brief_never_calls_provider(brief):
    router = StubRouter()
    with pytest.raises(ValidationError):
        await generate_scene_prompt(brief, router)
    assert not router.calls


def test_manual_custom_prompt_keeps_local_and_external_constraints():
    scene = {"place": "a quiet cafe", "image_prompt": "Warm daylight through tall cafe windows."}
    prompt = qwen_scene_prompt(scene)
    assert prompt.startswith(scene["image_prompt"])
    assert prompt.endswith(SCENE_COMPOSITION)
    assert qwen_scene_prompt({**scene, "image_prompt": prompt}) == prompt


def test_old_scene_without_custom_prompt_keeps_existing_recipe():
    prompt = qwen_scene_prompt({"place": "a quiet cafe", "time_of_day": "sunset"})
    assert "a quiet cafe" in prompt and "golden sunset light" in prompt
    assert "with no people at all" in prompt


async def test_local_scene_job_sends_the_same_saved_prompt_as_external_copy(db, tmp_path, monkeypatch):
    from backend.ai.image import pipelines
    from backend.core.config import settings
    from backend.library import library_service
    from backend.schemas.visuals import SceneInput

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    scene = await library_service.create_scene(db, SceneInput(
        **DRAFT, source_request="A quiet riverside cafe",
    ))
    await db.commit()
    captured = []

    async def draw(_engine, pictures, purpose):
        captured.extend(pictures)
        assert purpose == "visuals_scene_preview"

    async def boundary(*_args):
        pass

    monkeypatch.setattr(pipelines, "_qwen_pictures", draw)
    monkeypatch.setattr(pipelines, "get_image_engine", lambda: object())
    runner = SimpleNamespace(get_db=lambda: db, boundary=boundary)
    await pipelines.scene_preview({"id": "test-job", "target_id": scene["id"]}, runner)
    row = await library_service.get_scene_row(db, scene["id"])
    assert captured[0]["prompt"] == qwen_scene_prompt(row)
    assert captured[0]["prompt"].startswith(DRAFT["image_prompt"])
    assert captured[0]["prompt"].endswith(SCENE_COMPOSITION)
