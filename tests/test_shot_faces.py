"""Task 28.5: count the faces of a shot on photographs (the anime cut-out could not) and mark a shot to check."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from app.core.config import settings
from app.services.visuals import pipelines, shot_checks
from app.services.visuals.engine import FakeImageEngine
from tests.test_visuals_project_api import client, data, setup_project, wait_job  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent
IMAGE_PYTHON = ROOT / "venv-image" / "Scripts" / "python.exe"
MODEL = ROOT / "models" / "image" / "face" / "ultraface-rfb-320.onnx"
WORKER = ROOT / "scripts" / "image_worker.py"
PORTRAITS = ROOT / "docs" / "operations" / "phase28-characters"
THREE = ROOT / "tests" / "fixtures" / "three_people_cafe.png"
PINNED_SHA256 = "34cd7e60aeff28744c657de7a3dc64e872d506741de66987f3426f2b79f88017"

needs_model = pytest.mark.skipif(not (MODEL.is_file() and IMAGE_PYTHON.is_file()),
                                 reason="the face model or venv-image is not present")


# ---- the pure rule ----------------------------------------------------------------------------------------------

def test_extra_faces_counts_only_faces_beyond_the_people_in_the_shot():
    assert shot_checks.extra_faces(2, 2) == 0
    assert shot_checks.extra_faces(3, 2) == 1
    assert shot_checks.extra_faces(1, 2) == 0   # a person turned away is not an extra person
    assert shot_checks.extra_faces(0, 0) == 0   # an insert shows nobody
    assert shot_checks.extra_faces(1, 0) == 1


# ---- the real model, run in the image environment ---------------------------------------------------------------

def _faces(path: Path) -> int:
    code = (
        "import importlib.util, json, sys\n"
        f"spec = importlib.util.spec_from_file_location('image_worker', r'{WORKER}')\n"
        "module = importlib.util.module_from_spec(spec); sys.modules['image_worker'] = module\n"
        "spec.loader.exec_module(module)\n"
        f"print('FACES', len(module.detect_faces(r'{path}')))\n"
    )
    result = subprocess.run([str(IMAGE_PYTHON), "-c", code], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr[-800:]
    # the worker module moves `print` to stderr (stdout carries its protocol), so read both streams
    output = result.stdout.splitlines() + result.stderr.splitlines()
    return int(next(line for line in output if line.startswith("FACES")).split()[1])


@needs_model
def test_the_model_file_is_the_pinned_one():
    assert MODEL.stat().st_size == 1_270_727
    assert hashlib.sha256(MODEL.read_bytes()).hexdigest() == PINNED_SHA256


@needs_model
def test_the_real_model_counts_zero_one_two_and_three_faces(tmp_path):
    blank = tmp_path / "blank.png"
    Image.new("RGB", (1344, 768), (230, 225, 215)).save(blank)
    man, woman = Image.open(PORTRAITS / "man_face_front.png"), Image.open(PORTRAITS / "woman_face_front.png")
    one = tmp_path / "one.png"
    canvas = Image.new("RGB", (1344, 768), "white")
    canvas.paste(man.resize((600, 600)), (372, 84))
    canvas.save(one)
    two = tmp_path / "two.png"
    canvas = Image.new("RGB", (1344, 768), "white")
    canvas.paste(man.resize((600, 600)), (60, 84))
    canvas.paste(woman.resize((600, 600)), (684, 84))
    canvas.save(two)
    assert [_faces(blank), _faces(one), _faces(two)] == [0, 1, 2]
    # the shot the anime cut-out let through (Task 28.4b, shot 12): three people at a cafe table
    assert _faces(THREE) == 3


# ---- the pipeline, with a scripted fake engine ------------------------------------------------------------------

@pytest.fixture
def faces(monkeypatch):
    """Scripted `count_faces` answers: plan[(expected, 'raw' | 'final')] is a list consumed in order (the last
    value repeats); anything not scripted answers the expected number (a clean shot)."""
    plan: dict[tuple[int, str], list[int]] = {}
    calls: list[dict] = []
    original = FakeImageEngine.request

    async def request(self, payload):
        if payload.get("command") != "count_faces":
            return await original(self, payload)
        calls.append(dict(payload))
        expected = payload["expected_faces"]
        kind = "final" if Path(payload["input_path"]).name == "final.png" else "raw"
        queue = plan.get((expected, kind))
        count = (queue.pop(0) if len(queue) > 1 else queue[0]) if queue else expected
        return {"status": "ok", "faces": count, "boxes": []}

    monkeypatch.setattr(FakeImageEngine, "request", request)
    monkeypatch.setattr(settings, "VISUALS_COLOUR_RETRIES", 0)
    monkeypatch.setattr(pipelines, "_colour_result", lambda path, person, character, bottom: {
        "ok": True, "top": {"expected": character["top_color"], "ok": True}, "bottom": None})
    return type("Faces", (), {"plan": plan, "calls": calls})


def _run(client, scenes=1):  # noqa: F811
    project, ids, _ = setup_project(client, 2, scenes)
    base = f"/api/projects/{project['id']}/visuals"
    wait_job(client, data(client.post(f"{base}/shots")))
    shots = data(client.get(base))["shots"]
    return project, base, shots


def _folder(project, shot) -> Path:
    return settings.DATA_DIR / "visuals" / project["id"] / "shots" / shot["id"]


def test_a_clean_set_has_no_notes_and_every_shot_is_counted(client, faces):  # noqa: F811
    project, _, shots = _run(client)
    assert shots and all(shot["review_note"] is None for shot in shots)
    expected = {shot["kind"]: len(shot["speaker_indexes"]) for shot in shots}
    first_raw = [call for call in faces.calls if Path(call["input_path"]).name == "raw.png"]
    assert len(first_raw) == len(shots)  # singles are counted too
    assert {call["expected_faces"] for call in first_raw} == set(expected.values())


def test_an_extra_face_is_rerendered_and_the_cleanest_render_is_kept(client, faces):  # noqa: F811
    faces.plan[(2, "raw")] = [3, 3, 2]       # two bad renders, then a clean one
    project, _, shots = _run(client)
    duo = next(shot for shot in shots if shot["kind"] == "duo_close")
    report = json.loads((_folder(project, duo) / "extra_person_check.json").read_text(encoding="utf-8"))
    assert [item["faces"] for item in report["tries"]] == [3, 3, 2]
    first_seed = report["tries"][0]["seed"]
    assert report["chosen_seed"] == first_seed + 2 * pipelines.EXTRA_PERSON_SEED_STEP == duo["seed"]
    assert (_folder(project, duo) / "raw_retry_2.png").is_file()
    assert duo["review_note"] is None


def test_a_shot_that_still_has_an_extra_face_after_the_retries_is_marked(client, faces):  # noqa: F811
    faces.plan[(2, "raw")] = [3]
    faces.plan[(2, "final")] = [3]
    project, _, shots = _run(client)
    duos = [shot for shot in shots if len(shot["speaker_indexes"]) == 2]
    assert duos and all(shot["review_note"] == "3 faces found for 2 people" for shot in duos)
    singles = [shot for shot in shots if len(shot["speaker_indexes"]) == 1]
    assert singles and all(shot["review_note"] is None for shot in singles)
    report = json.loads((_folder(project, duos[0]) / "extra_person_check.json").read_text(encoding="utf-8"))
    assert len(report["tries"]) == 1 + settings.VISUALS_EXTRA_PERSON_RETRIES


def test_a_colour_failure_that_survives_the_retries_is_marked_with_who_and_what(client, faces, monkeypatch):  # noqa: F811
    def failing(path, person, character, bottom):
        return {"ok": False, "top": {"expected": "black", "ok": False}, "bottom": None}

    monkeypatch.setattr(pipelines, "_colour_result", failing)
    monkeypatch.setattr(settings, "VISUALS_COLOUR_RETRIES", 1)  # 0 switches the colour check off
    _, _, shots = _run(client)
    assert shots and all(shot["review_note"] and "is not black" in shot["review_note"]
                         for shot in shots if shot["kind"] != "insert")


def test_regenerating_a_shot_clears_its_old_note(client, faces):  # noqa: F811
    import sqlite3
    project, base, shots = _run(client)
    shot = next(item for item in shots if item["kind"] != "insert")
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute("UPDATE project_shots SET review_note = 'old note' WHERE id = ?", (shot["id"],))
    wait_job(client, data(client.post(f"{base}/shots/{shot['id']}/regenerate")))
    again = next(item for item in data(client.get(base))["shots"] if item["id"] == shot["id"])
    assert again["review_note"] is None


def test_the_note_text_names_the_person_and_the_garment():
    character = {"name": "Minh", "top_color": "black", "bottom_color": "black"}
    result = {"ok": False, "top": {"expected": "black", "ok": False}, "bottom": {"expected": "black", "ok": False}}
    assert pipelines.colour_notes(character, result) == ["Minh's top is not black", "Minh's bottom is not black"]
    assert pipelines.colour_notes(character, {"ok": True, "top": {"ok": True}, "bottom": None}) == []
    assert pipelines.face_note(3, 2) == "3 faces found for 2 people"
    assert pipelines.face_note(2, 2) is None and pipelines.face_note(1, 2) is None
    assert pipelines.face_note(2, 1) == "2 faces found for 1 person"
