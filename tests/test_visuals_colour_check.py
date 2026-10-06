"""Task 20.11: garment colour check (pure) and the bounded colour retry in the shot pipeline."""

import json

import pytest
from PIL import Image, ImageDraw

from app.core.config import settings
from app.services.visuals import colour_check, geometry, recipes
from tests.test_visuals_project_api import client, data, setup_project, wait_job  # noqa: F401

SIZE = (1344, 768)
CHARACTER = {
    "gender": "male", "age_group": "middle-aged", "ethnicity": "Vietnamese", "role": "English teacher",
    "hair": "short neat black hair", "eyes": "brown eyes", "top_color": "light blue",
    "top_item": "slim-fit shirt", "bottom_color": "black", "bottom_item": "slim trousers",
}
SCENE = {"place": "a cozy Vietnamese street cafe", "staging": "seated"}
# Measured medians from the 20.11 spike sheets (real cel-anime renders).
YELLOW, PALE_BLUE, TAN, JEANS = (245, 196, 66), (196, 222, 214), (208, 166, 92), (70, 102, 137)


def _painted(person: dict, top: tuple, bottom: tuple | None = None) -> Image.Image:
    image = Image.new("RGB", SIZE, (240, 236, 220))
    draw = ImageDraw.Draw(image)
    draw.rectangle(colour_check.top_box(person, SIZE), fill=top)
    box = colour_check.bottom_box(person, SIZE)
    if bottom and box:
        draw.rectangle(box, fill=bottom)
    draw.line((0, 0, SIZE[0], SIZE[1]), fill=(10, 10, 10), width=6)  # an ink outline is ignored
    return image


@pytest.mark.parametrize("kind,staging", [("single", "standing"), ("duo_close", "seated"),
                                          ("duo_wide", "seated"), ("duo_wide", "standing")])
def test_regions_sit_inside_the_frame(kind, staging):
    for person in geometry.shot_people(kind, staging, SIZE):
        x0, y0, x1, y1 = colour_check.top_box(person, SIZE)
        assert 0 <= x0 < x1 <= SIZE[0] and 0 <= y0 < y1 <= SIZE[1]
        bottom = colour_check.bottom_box(person, SIZE)
        assert (bottom is not None) == (kind == "duo_wide" and staging == "standing")


def test_calibrated_colours_pass_and_drift_fails():
    left, right = geometry.shot_people("duo_wide", "standing", SIZE)
    good = colour_check.check_person(_painted(right, PALE_BLUE, (30, 30, 34)), right, CHARACTER)
    assert good["ok"] and good["top"]["ok"] and good["bottom"]["ok"]
    drift = colour_check.check_person(_painted(right, YELLOW, JEANS), right, CHARACTER)
    assert not drift["top"]["ok"] and not drift["bottom"]["ok"] and not drift["ok"]
    tan = colour_check.check_person(_painted(left, TAN), left, CHARACTER, check_bottom=False)
    assert not tan["ok"] and "bottom" not in tan
    lan = {**CHARACTER, "top_color": "yellow", "bottom_color": "navy blue"}
    assert colour_check.check_person(_painted(left, YELLOW, JEANS), left, lan)["ok"]


def test_unmeasurable_region_never_fails():
    person = geometry.shot_people("single", "standing", SIZE)[0]
    dark = Image.new("RGB", SIZE, (5, 5, 5))  # every pixel is an "outline"
    result = colour_check.check_person(dark, person, CHARACTER, check_bottom=False)
    assert result["ok"] and result["top"]["measured"] is None


def test_garment_refine_prompt_budget_and_order():
    prompt = recipes.garment_refine_prompt(CHARACTER, SCENE)
    assert prompt.startswith(recipes.STYLE_EDITORIAL + ", plain light blue slim-fit shirt, plain black")
    assert recipes.token_count(prompt) <= 75


@pytest.mark.parametrize("retries", [0, 2])
def test_pipeline_colour_retry_is_bounded(client, monkeypatch, retries):  # noqa: F811
    monkeypatch.setattr(settings, "VISUALS_COLOUR_RETRIES", retries)
    project, _, _ = setup_project(client, 2, 1)
    base = f"/api/projects/{project['id']}/visuals"
    wait_job(client, data(client.post(f"{base}/shots")))
    shots = data(client.get(base))["shots"]
    assert all(shot["status"] == "complete" for shot in shots)
    for shot in shots:
        folder = settings.DATA_DIR / "visuals" / project["id"] / "shots" / shot["id"]
        report_path = folder / "colour_check.json"
        if retries == 0:
            assert not report_path.exists()
            continue
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert len(report) == (1 if shot["kind"] == "single" else 2)
        # The fake engine paints solid seed colours, so most people fail and retry, never past the cap.
        assert all(0 <= entry["attempts"] <= retries for entry in report)
        assert all(entry["ok"] or entry["attempts"] == retries for entry in report)
