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
