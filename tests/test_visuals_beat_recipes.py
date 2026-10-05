"""Task 24.3: action poses and beat prompts (action + expression within the CLIP budget)."""

import pytest

from app.db.database import BUILTIN_SCENES
from app.models.storyboard import EXPRESSIONS
from app.services.visuals import geometry, recipes

SIZE = (1344, 768)
LONGEST = {
    "gender": "female", "age_group": "middle-aged", "ethnicity": "Vietnamese", "role": "English teacher",
    "hair": "long wavy black hair", "eyes": "brown eyes", "top_color": "light blue", "top_item": "slim-fit shirt",
    "bottom_color": "navy blue", "bottom_item": "slim trousers",
}
LONG_ACTION = "pointing at a large city map on the wall"


@pytest.mark.parametrize("action,category", [  # the real Gemini actions from Task 24.2's runs
    ("drinking coffee in a local cafe", "drink"),
    ("looking at a laptop screen together", "work"),
    ("pointing at a city map", "point"),
    ("walking through a green park", "walk"),
    ("talking earnestly", "talk"),
    ("gesturing to screens with advice", "point"),
    ("waving goodbye to camera", "wave"),
    ("sipping tea on a sofa", "drink"),
    ("", "talk"),
])
def test_action_category(action, category):
    assert geometry.action_category(action) == category


@pytest.mark.parametrize("kind,staging", [("single", "standing"), ("duo_close", "seated"),
                                          ("duo_wide", "seated"), ("duo_wide", "standing")])
@pytest.mark.parametrize("category", geometry.ACTION_CATEGORIES)
def test_beat_poses_stay_in_frame_and_talk_is_unchanged(kind, staging, category):
    count = 1 if kind == "single" else 2
    people = geometry.beat_people(kind, staging, SIZE, [category] * count)
    for person in people:
        for point in person["points"]:
            if point is not None:
                assert -0.05 * SIZE[0] <= point[0] <= 1.05 * SIZE[0] and point[1] <= 1.35 * SIZE[1]
    if category == "talk":
        assert people == geometry.shot_people(kind, staging, SIZE)


def test_duo_arms_reach_toward_the_partner():
    left, right = geometry.beat_people("duo_close", "seated", SIZE, ["point", "point"])
    named_left = dict(zip(geometry._KEYS, left["points"]))
    named_right = dict(zip(geometry._KEYS, right["points"]))
    assert named_left["l_wrist"][0] > named_left["neck"][0]    # the left person points right
    assert named_right["r_wrist"][0] < named_right["neck"][0]  # the right person points left
    walker = geometry.beat_people("duo_wide", "standing", SIZE, ["walk", "talk"])[0]
    assert dict(zip(geometry._KEYS, walker["points"]))["r_ankle"] != dict(
        zip(geometry._KEYS, geometry.shot_people("duo_wide", "standing", SIZE)[0]["points"]))["r_ankle"]


def test_beat_prompts_carry_expression_and_action():
    scene = {"place": "a cozy Vietnamese street cafe", "staging": "seated"}
    lan = {**LONGEST, "age_group": "young", "hair": "long black hair", "top_color": "yellow", "top_item": "sweater",
           "bottom_item": "jeans"}
    single = recipes.beat_single_prompt(lan, scene, "drinking coffee", "smile")
    assert single.endswith("close-up, warm smile, drinking coffee, in a cozy Vietnamese street cafe")
    assert "English teacher" not in single and "brown eyes" not in single
    assert recipes.beat_single_prompt(lan, scene, "", "surprised").endswith("surprised face, talking, in a cozy "
                                                                          "Vietnamese street cafe")


def test_budget_holds_for_every_builtin_expression_and_long_action():
    for _, _, place, staging, _ in BUILTIN_SCENES:
        scene = {"place": place, "staging": staging}
        for expression in EXPRESSIONS:
            prompts = [recipes.beat_single_prompt(LONGEST, scene, LONG_ACTION, expression),
                       *(recipes.beat_duo_prompt(LONGEST, LONGEST, scene, kind, LONG_ACTION, expression)
                         for kind in ("duo_close", "duo_wide"))]
            for prompt in prompts:
                assert recipes.token_count(prompt) <= recipes.BEAT_TOKEN_BUDGET, (place, expression, prompt)
                assert recipes.EXPRESSION_WORDS[expression] in prompt
                assert prompt.rstrip().split()[-1].lower() not in {"a", "the", "at", "in", "on", "to"}


def test_fit_budget_order():
    def build(action, place):
        return " ".join(["word"] * 67 + action.split() + ([place] if place else []))

    assert recipes.fit_budget(build, "one two three four five six", "cafe").split()[-5:] == [
        "one", "two", "three", "four", "cafe"]  # the action shrinks to 4 words, the place stays

    def crowded(action, place):
        return " ".join(["word"] * 69 + action.split() + ([place] if place else []))

    # 69 + 4 + place = 74: the place goes, then the action shrinks to fit (69 + 3 = 72)
    assert recipes.fit_budget(crowded, "one two three four five six", "place").split()[-3:] == ["one", "two", "three"]
