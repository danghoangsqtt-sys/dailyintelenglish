"""Phase 31: the characters Alex (navy suit, white shirt, black bow tie) and Lina (white mini dress), both Russian."""

from __future__ import annotations

import pytest
from PIL import Image

from app.core.config import settings
from app.models.visuals import CharacterInput
from app.services.visuals import colour_check, recipes
from tests.test_shot_library import _library, _make_shots, requests_log  # noqa: F401
from tests.test_visuals_phase28 import _real_tokenizer
from tests.test_visuals_project_api import client, data, setup_project  # noqa: F401

LINA = {
    "gender": "female", "age_group": "young", "ethnicity": "Russian", "role": "English teacher",
    "hair": "long dark brown hair", "eyes": "brown eyes",
    "top_color": "white", "top_item": "mini dress", "bottom_color": "white", "bottom_item": "mini dress",
}
ALEX = {
    "gender": "male", "age_group": "young", "ethnicity": "Russian", "role": "university student",
    "hair": "side-swept highlighted brown hair", "eyes": "brown eyes",
    "top_color": "navy blue", "top_item": "suit jacket", "bottom_color": "navy blue", "bottom_item": "suit trousers",
}
SCENE = {"place": "a cozy street cafe", "staging": "seated", "time_of_day": "day"}


def test_the_two_characters_are_valid_and_a_dress_is_one_garment():
    assert CharacterInput(name="Lina", **LINA).top_item == "mini dress"
    assert CharacterInput(name="Alex", **ALEX).bottom_item == "suit trousers"
    with pytest.raises(ValueError, match="one garment"):
        CharacterInput(name="Lina", **{**LINA, "bottom_item": "skirt"})
    with pytest.raises(ValueError, match="one garment"):
        CharacterInput(name="Lina", **{**LINA, "bottom_color": "black"})
    with pytest.raises(ValueError, match="one garment"):
        CharacterInput(name="Alex", **{**ALEX, "top_item": "mini dress"})


def test_the_outfit_phrases_and_the_negatives_do_not_fight_the_suit_or_the_dress():
    assert recipes.outfit_phrase(LINA) == "plain white mini dress"
    assert recipes.outfit_phrase(ALEX) == "plain navy blue suit jacket and suit trousers, white shirt, black bow tie"
    assert recipes.duo_person(LINA) == "woman in plain white mini dress"
    assert "jacket" not in recipes.negative_for(ALEX) and "multicolored" not in recipes.negative_for(ALEX)
    assert "blazer" not in recipes.negative_for(LINA, ALEX)  # a duo with the suit must not forbid a jacket
    assert "blazer" in recipes.negative_for(LINA) and "blue jeans" in recipes.negative_for(LINA)
    assert "jacket" in recipes.NEGATIVE  # the other characters keep the old rule


def test_the_prompts_of_alex_and_lina_fit_the_real_clip_budget():
    tok = _real_tokenizer()
    for character in (LINA, ALEX):
        prompts = [
            recipes.single_prompt(character, SCENE, gaze="right"), recipes.refine_prompt(character, SCENE, gaze="left"),
            recipes.garment_refine_prompt(character, SCENE, gaze="right"), recipes.candidate_prompt(character),
            recipes.beat_single_prompt(character, SCENE, "pointing at a very detailed city map", "smile", gaze="right"),
            recipes.insert_person_prompt(character, "eating a bowl of oatmeal near a window"),
            *(recipes.sheet_prompt(character, kind) for kind in recipes.SHEET_KINDS),
        ]
        for prompt in prompts:
            assert len(tok(prompt)["input_ids"]) - 2 <= 77, prompt
        for negative in (recipes.negative_for(character), recipes.negative_for(LINA, ALEX)):
            assert len(tok(negative)["input_ids"]) - 2 <= 77, negative
    for kind in ("duo_close", "duo_wide"):
        for prompt in (recipes.duo_prompt(LINA, ALEX, SCENE, kind, gaze=True),
                       recipes.beat_duo_prompt(LINA, ALEX, SCENE, kind, "drinking coffee together", "laugh", gaze=True)):
            assert len(tok(prompt)["input_ids"]) - 2 <= 77, prompt


def _person_boxes():
    # a standing person: shoulders, hips and knees inside a 1344 x 768 picture
    points = {"r_shoulder": (560, 250), "l_shoulder": (700, 250), "r_hip": (580, 420), "l_hip": (690, 420),
              "r_knee": (580, 560), "l_knee": (690, 560)}
    from app.services.visuals.geometry import _KEYS
    return {"points": [points.get(key) for key in _KEYS]}


def test_the_colour_check_measures_the_navy_suit_but_not_the_skin_below_a_dress():
    person = _person_boxes()
    skin_and_white = Image.new("RGB", (1344, 768), (236, 190, 160))  # legs
    skin_and_white.paste(Image.new("RGB", (400, 200), (250, 250, 250)), (440, 250))  # the dress over the torso
    result = colour_check.check_person(skin_and_white, person, LINA, check_bottom=True)
    assert result["ok"] and "bottom" not in result and result["top"]["ok"]
    navy = Image.new("RGB", (1344, 768), (28, 40, 100))
    suit = colour_check.check_person(navy, person, ALEX, check_bottom=True)
    assert suit["ok"] and suit["top"]["ok"] and suit["bottom"]["ok"]
    brown = Image.new("RGB", (1344, 768), (120, 70, 40))
    assert not colour_check.check_person(brown, person, ALEX, check_bottom=True)["ok"]  # a brown suit is not navy


def test_deleting_a_character_removes_its_library_pictures(client, requests_log):  # noqa: F811
    project, ids, _ = setup_project(client, 2, 1)
    shots = _make_shots(client, project["id"])
    for shot in shots:
        data(client.post(f"/api/projects/{project['id']}/visuals/shots/{shot['id']}/to-library"))
    files = [settings.DATA_DIR / "library" / "shots" / f"{row['id']}.png" for row in _library(client)]
    assert files and all(path.is_file() for path in files)
    assert client.delete(f"/api/visuals/characters/{ids[0]}?force=true").status_code == 200
    remaining = _library(client)
    assert all(ids[0] not in row["character_ids"] for row in remaining)
    removed = [path for path in files if not path.is_file()]
    assert len(removed) == len(files) - len(remaining) and removed  # the first character's pictures are gone, files too
