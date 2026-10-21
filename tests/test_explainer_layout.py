"""Production layout proof: alpha extents, platform polygon, text bounds and full paths."""
import copy
import json
from pathlib import Path

import pytest

from backend.core.exceptions import ValidationError
from backend.library import explainer_layout_service as geometry
from tests.test_explainer_plan import solo, draft  # noqa: F401
from tests.test_explainer_api import client, setup, prepared_front_files, synthetic_audio, wait, data, Router  # noqa: F401
from backend import main

FIXTURE = json.loads((Path(__file__).parent / "fixtures/explainer_geometry.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", FIXTURE["safeCases"])
def test_shared_platform_polygon(case):
    assert geometry.inside_safe(case["rect"], case["aspect"]) is case["valid"]


def test_actual_pixel_ratio_and_protected_motion_envelope():
    for item in FIXTURE["placements"]:
        spec = geometry.RULES["aspects"][item["aspect"]]
        alpha, canvas = geometry.presenter_boxes(item["placement"], FIXTURE["metrics"], item["aspect"])
        assert alpha["height"] == item["placement"]["height"]
        assert canvas["width"] * spec["width"] / (canvas["height"] * spec["height"]) == pytest.approx(1280 / 1536)
    a, b, text = {"x": .1, "y": .3, "width": .08, "height": .2}, {"x": .8, "y": .3, "width": .08, "height": .2}, {"x": .4, "y": .3, "width": .2, "height": .2}
    assert not geometry.intersects(a, text) and not geometry.intersects(b, text)
    assert geometry.intersects(geometry.envelope(a, b), text)


def test_unreadable_nodes_and_unannotated_crop_are_refused():
    panel = geometry.RULES["aspects"]["16:9"]["panels"]["left"]
    with pytest.raises(ValidationError, match="fit readably"):
        geometry.text_metrics({"kind": "diagram", "title": "W" * 120, "nodes": [{"id": str(i), "label": "W" * 100, "detail": "W" * 180} for i in range(6)]}, panel, "16:9")
    with pytest.raises(ValidationError, match="unannotated"):
        geometry.protected_regions({"kind": "photo", "fit": "cover"}, panel, "16:9", {})


def test_important_photo_region_must_survive_cover_crop():
    photo = {"kind": "photo", "fit": "cover", "asset": {"asset_id": "photo", "version": 1},
             "important_regions": [{"x": 0, "y": 0, "width": .2, "height": .2}]}
    with pytest.raises(ValidationError, match="crop removes"):
        geometry.protected_regions(photo, {"x": .3, "y": .2, "width": .2, "height": .4}, "16:9", {("photo", 1): {"width": 1600, "height": 400}})


def test_real_geometry_arrange_save_approve_and_locked_collision(client, monkeypatch):  # noqa: F811
    pid, cid, lines, wire = setup(client)
    prepared_front_files(client, cid)
    synthetic_audio(client, pid, lines)
    monkeypatch.setattr(main, "_build_ai_router", lambda: Router(json.dumps(wire)))
    assert wait(client, pid, client.post(f"/api/projects/{pid}/explainer-plan/propose", json={"expected_revision": 0}))["status"] == "complete"
    view = data(client.get(f"/api/projects/{pid}/explainer-plan"))
    before = data(client.get(f"/api/projects/{pid}/explainer-plan/history"))
    request = {"expected_revision": 1, "source_fingerprint": view["current_source_fingerprint"]}
    suggestion = data(client.post(f"/api/projects/{pid}/explainer-plan/layout", json=request))
    assert len(suggestion["geometry"]["aspects"]) == 2
    assert data(client.get(f"/api/projects/{pid}/explainer-plan/history")) == before
    segments = suggestion["segments"]
    for segment in segments:
        segment["needs_fact_review"] = False
    saved = data(client.patch(f"/api/projects/{pid}/explainer-plan", json={"expected_revision": 1,
        "expected_source_fingerprint": request["source_fingerprint"], "segments": segments}))["plan"]
    approved = data(client.post(f"/api/projects/{pid}/explainer-plan/approve", json={"expected_revision": saved["revision"], "source_fingerprint": saved["source_fingerprint"]}))["plan"]
    assert approved["status"] == "approved"
    assert client.post(f"/api/projects/{pid}/explainer-plan/layout", json=request).status_code == 409
    bad = copy.deepcopy(approved["segments"])
    bad[0]["layouts"]["9:16"]["presenter"]["x"] = .92
    changed = data(client.patch(f"/api/projects/{pid}/explainer-plan", json={"expected_revision": approved["revision"],
        "expected_source_fingerprint": approved["source_fingerprint"], "segments": bad}))["plan"]
    refused = client.post(f"/api/projects/{pid}/explainer-plan/approve", json={"expected_revision": changed["revision"], "source_fingerprint": changed["source_fingerprint"]})
    assert refused.status_code == 422 and "Segment" in refused.text
    locked = client.post(f"/api/projects/{pid}/explainer-plan/layout", json={"expected_revision": changed["revision"], "source_fingerprint": changed["source_fingerprint"]})
    assert locked.status_code == 422, "automatic arrangement cannot overwrite an invalid owner lock"


# ---------------------------------------------------------------- Phase 55 (ENH-037): rules v2 waist-up stage

STAGE_METRICS = {"canvasWidth": 1280, "canvasHeight": 1536, "alpha": {"x": .2, "y": .1, "width": .65, "height": .89},
                 "core": {"x": .34, "y": .1, "width": .32, "height": .88}}


def stage_segment(aspect, visual, **presenter):
    spec, stage = geometry.RULES["aspects"][aspect], geometry.RULES["aspects"][aspect]["stage"]
    anchor = presenter.pop("anchor", stage["anchor"])
    height = presenter.pop("height", stage["defaultHeight"])
    placement = {"anchor": anchor, "x": spec["anchors"][anchor], "y": stage["headTop"] + height, "height": height, **presenter}
    panel = geometry.FULL_FRAME if visual["kind"] == "activity" else spec["panels"][anchor]
    return {"id": "s", "visual": visual, "layouts": {aspect: {"presenter": placement, "illustration": panel, "transition": "cut",
                                                               "transition_seconds": .4, "rules_version": geometry.RULES["version"]}}}


CARD = {"kind": "text_card", "title": "Start small", "bullets": ["One action"]}


@pytest.mark.parametrize("aspect", ["16:9", "9:16"])
def test_stage_default_fits_cards_and_full_frame_activities(aspect):
    for visual in (CARD, {"kind": "activity", "activity_id": "act"}):
        record = geometry.validate_segment(stage_segment(aspect, visual), aspect, STAGE_METRICS, {})
        assert record["canvas"]["height"] > 1, "the waist-up figure is taller than the frame"
        assert record["protected"] == ([] if visual["kind"] == "activity" else [stage_segment(aspect, visual)["layouts"][aspect]["illustration"]])


def test_stage_refuses_card_over_the_torso_head_outside_safe_and_old_rules():
    over = stage_segment("16:9", CARD)
    over["layouts"]["16:9"]["illustration"] = geometry.RULES["aspects"]["16:9"]["panels"]["left"]  # the presenter's own side
    with pytest.raises(ValidationError, match="crosses the card"):
        geometry.validate_segment(over, "16:9", STAGE_METRICS, {})
    high = stage_segment("16:9", CARD)
    high["layouts"]["16:9"]["presenter"]["y"] -= .12  # head under the brand line
    with pytest.raises(ValidationError, match="head must stay"):
        geometry.validate_segment(high, "16:9", STAGE_METRICS, {})
    old = stage_segment("16:9", CARD)
    old["layouts"]["16:9"]["rules_version"] = 1
    with pytest.raises(ValidationError, match="outdated layout"):
        geometry.validate_segment(old, "16:9", STAGE_METRICS, {})
    small = stage_segment("16:9", CARD, height=.22)
    with pytest.raises(ValidationError, match="Presenter size"):
        geometry.validate_segment(small, "16:9", STAGE_METRICS, {})


def test_implied_step_edges_take_no_text_line_so_three_steps_fit_vertical():
    steps = {"kind": "diagram", "template": "steps", "title": "Data Analyst Workflow",
             "nodes": [{"id": "a", "label": "Collect", "detail": "Gather raw data"}, {"id": "b", "label": "Clean", "detail": "Fix errors"},
                       {"id": "c", "label": "Analyze", "detail": "Find patterns"}],
             "edges": [{"source": "a", "target": "b"}, {"source": "b", "target": "c"}]}
    assert geometry.shown_edges(steps) == []
    geometry.text_metrics(steps, geometry.RULES["aspects"]["9:16"]["panels"]["center"], "9:16")
    labelled = {**steps, "edges": [{"source": "a", "target": "b", "label": "then"}, {"source": "c", "target": "a"}]}
    assert len(geometry.shown_edges(labelled)) == 2, "labelled or non-consecutive edges still get their line"
    assert len(geometry.shown_edges({**steps, "template": "comparison"})) == 2
