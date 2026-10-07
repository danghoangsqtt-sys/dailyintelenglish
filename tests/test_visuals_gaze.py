"""Task 29.1: the two people look at each other, not into the lens (gaze words, a turned face reference, a turned head)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from app.core.config import settings
from app.services.visuals import geometry, pipelines, recipes
from app.services.visuals.engine import FakeImageEngine
from tests.test_visuals_phase28 import LAN, MINH, _real_tokenizer
from tests.test_visuals_project_api import client, data, setup_project, wait_job  # noqa: F401

SCENE = {"place": "a cozy Vietnamese street cafe", "staging": "seated", "time_of_day": "day"}


# ---- the words -----------------------------------------------------------------------------------------------------

def test_gaze_words_are_off_by_default_so_old_prompts_do_not_change():
    assert recipes.single_prompt(LAN, SCENE) == recipes.single_prompt(LAN, SCENE, gaze=None)
    assert recipes.duo_prompt(LAN, MINH, SCENE, "duo_wide") == recipes.duo_prompt(LAN, MINH, SCENE, "duo_wide", gaze=False)
    assert "looking" not in recipes.refine_prompt(LAN, SCENE)
    assert "looking" not in recipes.beat_duo_prompt(LAN, MINH, SCENE, "duo_wide", "drinking coffee", "smile")


def test_a_duo_looks_at_each_other_and_each_person_looks_toward_the_other():
    assert "looking at each other" in recipes.duo_prompt(LAN, MINH, SCENE, "duo_wide", gaze=True)
    assert "looking at each other" in recipes.beat_duo_prompt(LAN, MINH, SCENE, "duo_close", "talking", "smile", gaze=True)
    assert "looking to the right" in recipes.refine_prompt(LAN, SCENE, gaze="right")
    assert "looking to the left" in recipes.garment_refine_prompt(MINH, SCENE, gaze="left")
    assert "looking to the side" in recipes.single_prompt(LAN, SCENE, gaze="right").replace("to the right", "to the side") \
        or "looking to the right" in recipes.single_prompt(LAN, SCENE, gaze="right")
    assert "looking to the left" in recipes.beat_single_prompt(MINH, SCENE, "drinking coffee", "smile", gaze="left")


def test_every_gaze_prompt_still_fits_the_real_clip_budget():
    tok = _real_tokenizer()
    from app.db.database import BUILTIN_SCENES

    for _, _, place, staging, _ in BUILTIN_SCENES:
        scene = {"place": place, "staging": staging, "time_of_day": "day"}
        prompts = [
            recipes.single_prompt(LAN, scene, gaze="right"), recipes.duo_prompt(LAN, MINH, scene, "duo_close", gaze=True),
            recipes.duo_prompt(LAN, MINH, scene, "duo_wide", gaze=True),
            recipes.refine_prompt(MINH, scene, gaze="left"), recipes.garment_refine_prompt(MINH, scene, gaze="left"),
            recipes.beat_single_prompt(MINH, scene, "gesturing while explaining a long idea", "laugh", gaze="left"),
            recipes.beat_duo_prompt(LAN, MINH, scene, "duo_wide", "gesturing to describe walking outside", "smile", gaze=True),
        ]
        for prompt in prompts:
            assert len(tok(prompt, truncation=False).input_ids) <= 77, (place, prompt)


# ---- the skeleton --------------------------------------------------------------------------------------------------

def test_turn_head_moves_only_the_head_keypoints_toward_the_partner():
    person = geometry.shot_people("single", "seated", (1344, 768))[0]
    keys = geometry._KEYS
    before = dict(zip(keys, person["points"], strict=True))
    for side, sign in (("right", 1), ("left", -1)):
        turned = dict(zip(keys, geometry.turn_head(person, side)["points"], strict=True))
        assert (turned["nose"][0] - before["neck"][0]) * sign > 0           # the nose leads toward the partner
        assert turned["nose"][1] == before["nose"][1]
        for key in ("r_shoulder", "l_shoulder", "r_hip", "l_hip", "r_wrist", "l_wrist", "neck"):
            assert turned[key] == before[key]                               # the body is untouched
        far_ear = "l_ear" if side == "right" else "r_ear"
        assert turned[far_ear] is None and before[far_ear] is not None       # the far ear is hidden
    with pytest.raises(ValueError):
        geometry.turn_head(person, "up")


# ---- the reference and the pipeline --------------------------------------------------------------------------------

def test_the_left_person_gets_the_turned_face_as_is_and_the_right_person_a_mirror(tmp_path):
    turned = tmp_path / "face_turned.png"
    image = Image.new("RGB", (64, 64), "white")
    image.putpixel((10, 20), (255, 0, 0))
    image.save(turned)
    face = tmp_path / "face.png"
    Image.new("RGB", (64, 64), "grey").save(face)
    assert pipelines.gaze_reference(str(face), str(turned), "right", tmp_path) == str(turned)
    mirrored = Path(pipelines.gaze_reference(str(face), str(turned), "left", tmp_path))
    assert mirrored != turned and mirrored.parent == tmp_path
    assert Image.open(mirrored).getpixel((64 - 1 - 10, 20)) == (255, 0, 0)
    assert pipelines.gaze_reference(str(face), None, "left", tmp_path) == str(face)  # no turned view: the front face


def _character_with_turned_face(character_id: str) -> Path:
    import sqlite3
    folder = settings.DATA_DIR / "library" / "characters" / character_id
    path = folder / "face_turned.png"
    Image.new("RGB", (512, 512), (200, 60, 60)).save(path)
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute("INSERT INTO character_assets (id, character_id, kind, path, created_at) "
                           "VALUES (?, ?, 'face_turned', ?, 'now')", (f"turned-{character_id}", character_id, str(path)))
    return path


def _run(client, mode, monkeypatch):  # noqa: F811
    log = []
    original = FakeImageEngine.request

    async def recording(self, payload):
        log.append(dict(payload))
        return await original(self, payload)

    monkeypatch.setattr(FakeImageEngine, "request", recording)
    monkeypatch.setattr(settings, "VISUALS_COLOUR_RETRIES", 0)
    monkeypatch.setattr(settings, "VISUALS_GAZE", mode)
    project, ids, _ = setup_project(client, 2, 1)
    for character_id in ids:
        _character_with_turned_face(character_id)
    wait_job(client, data(client.post(f"/api/projects/{project['id']}/visuals/shots")))
    return log, ids


def test_off_changes_nothing_in_the_requests(client, monkeypatch):  # noqa: F811
    log, _ = _run(client, "off", monkeypatch)
    assert not any("looking" in (call.get("prompt") or "") for call in log)
    assert not any("face_turned" in json.dumps(call) for call in log)


def test_words_mode_adds_gaze_words_but_keeps_the_front_faces(client, monkeypatch):  # noqa: F811
    log, _ = _run(client, "words", monkeypatch)
    refines = [c for c in log if c.get("mask_image") and "looking" in c.get("prompt", "")]
    assert {("right" if "looking to the right" in c["prompt"] else "left") for c in refines} == {"right", "left"}
    assert any("looking at each other" in item["prompt"] for c in log if c.get("command") == "encode"
               for item in c["items"])
    assert not any("face_turned" in json.dumps(call) for call in log)


def test_turned_mode_gives_each_duo_person_the_face_turned_toward_the_other(client, monkeypatch):  # noqa: F811
    log, ids = _run(client, "turned", monkeypatch)
    refines = [c for c in log if c.get("mask_image") and "looking" in c.get("prompt", "")
               and "face_turned" in c.get("ip_adapter_image", "")]
    sides = {("right" if "looking to the right" in c["prompt"] else "left"): c["ip_adapter_image"] for c in refines}
    assert set(sides) == {"right", "left"}
    assert sides["right"].endswith("face_turned.png") and sides["left"].endswith("face_turned_flipped.png")
    assert Path(sides["left"]).is_file()
