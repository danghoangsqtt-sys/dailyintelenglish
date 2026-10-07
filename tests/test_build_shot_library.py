"""Task 29.6: the resumable Shot Library batch builder (fake engine, real app over HTTP)."""

import importlib.util
import json
import urllib.request
from pathlib import Path
from typing import Generator

import pytest

from app.api import visuals as visuals_api
from app.core.config import settings
from tests.conftest import live_server
from tests.test_visuals_project_api import locked_character

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "build_shot_library.py"


@pytest.fixture(scope="module")
def builder():
    spec = importlib.util.spec_from_file_location("build_shot_library", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.POLL_SECONDS = 0.05  # no 5 s polls in a test
    return module


@pytest.fixture(scope="module")
def base(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    pretend_image_python = tmp_path_factory.mktemp("builder-venv") / "python.exe"
    pretend_image_python.touch()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(settings, "IMAGE_ENGINE", "fake")
        patch.setattr(settings, "AI_VISUALS_ENABLED", True)
        patch.setattr(settings, "VISUALS_COLOUR_RETRIES", 0)
        patch.setattr(visuals_api, "IMAGE_PYTHON", pretend_image_python)
        with live_server(tmp_path_factory, "build-shot-library") as url:
            locked_character("Lan", "white")
            locked_character("Minh", "black")
            yield url


def _get(base: str, path: str):
    with urllib.request.urlopen(f"{base}{path}", timeout=30) as response:
        return json.load(response)["data"]


def test_the_builder_fills_the_library_a_scene_at_a_time_and_cleans_up_after_itself(builder, base):
    scenes = ["builtin-cafe", "builtin-park"]
    report = builder.build(base, scenes, ["Lan", "Minh"], None, say=lambda text: None)
    library = _get(base, "/api/visuals/library/shots")
    assert [report["scenes"][scene]["added"] for scene in scenes] == [4, 4]
    assert len(library) == 8 and {shot["review_state"] for shot in library} == {"pending"}
    assert {shot["scene_id"] for shot in library} == set(scenes)
    assert sorted(shot["kind"] for shot in library if shot["scene_id"] == "builtin-cafe") == [
        "duo_close", "duo_wide", "single", "single"]
    assert not [p for p in _get(base, "/api/projects") if p["name"] == "[Shot Library Builder]"]  # builder project deleted
    assert all(urllib.request.urlopen(f"{base}{shot['content_url']}", timeout=30).status == 200 for shot in library)


def test_a_second_run_skips_complete_scenes_and_a_budget_stops_cleanly(builder, base):
    again = builder.build(base, ["builtin-cafe", "builtin-park"], ["Lan", "Minh"], None, say=lambda text: None)
    assert again["skipped"] == ["builtin-cafe", "builtin-park"] and not again["scenes"]
    before = len(_get(base, "/api/visuals/library/shots"))
    stopped = builder.build(base, ["builtin-office", "builtin-kitchen"], ["Lan", "Minh"], 0.0000001, say=lambda text: None)
    assert stopped["stopped_early"] and not stopped["scenes"]
    assert len(_get(base, "/api/visuals/library/shots")) == before  # nothing half done is left behind
    assert "not reached" in builder.render_report(stopped, ["builtin-office", "builtin-kitchen"], ["Lan", "Minh"])
    assert "already complete" in builder.render_report(again, ["builtin-cafe", "builtin-park"], ["Lan", "Minh"])
