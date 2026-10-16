"""Approved Solo bridge, exact frame duration, immutable assets and publication guards."""
import copy
import json
from pathlib import Path
from functools import partial

import pytest

from backend import main
from backend.content import project_service
from backend.db.database import Database
from backend.db.transactions import read_transaction
from backend.library import explainer_media
from backend.media import video_renderer_remotion as renderer
from tests.test_explainer_api import client, setup, prepared_front_files, synthetic_audio, wait, data, Router  # noqa: F401


def approved_fixture(api, monkeypatch):
    pid, cid, lines, wire = setup(api)
    prepared_front_files(api, cid)
    synthetic_audio(api, pid, lines)
    monkeypatch.setattr(main, "_build_ai_router", lambda: Router(json.dumps(wire)))
    assert wait(api, pid, api.post(f"/api/projects/{pid}/explainer-plan/propose", json={"expected_revision": 0}))["status"] == "complete"
    view = data(api.get(f"/api/projects/{pid}/explainer-plan"))
    suggestion = data(api.post(f"/api/projects/{pid}/explainer-plan/layout", json={"expected_revision": 1, "source_fingerprint": view["current_source_fingerprint"]}))
    for segment in suggestion["segments"]:
        segment["needs_fact_review"] = False
    saved = data(api.patch(f"/api/projects/{pid}/explainer-plan", json={"expected_revision": 1,
        "expected_source_fingerprint": view["current_source_fingerprint"], "segments": suggestion["segments"]}))["plan"]
    approved = data(api.post(f"/api/projects/{pid}/explainer-plan/approve", json={"expected_revision": saved["revision"], "source_fingerprint": saved["source_fingerprint"]}))["plan"]
    return pid, cid, approved


def test_preview_and_production_share_geometry_but_hide_internal_paths(client, monkeypatch, tmp_path):  # noqa: F811
    pid, cid, approved = approved_fixture(client, monkeypatch)
    public = data(client.get(f"/api/projects/{pid}/explainer-plan/preview?aspect=9:16"))
    assert str(tmp_path) not in json.dumps(public)
    assert public["props"]["durationSeconds"] == 4.5
    assert len(public["props"]["solo"]["pictures"]) == 21
    for url in public["props"]["solo"]["pictures"].values():
        assert client.get(url).status_code == 200
    monkeypatch.setattr(renderer, "REMOTION_VISUALS_DIR", tmp_path / "public")
    props = client.portal.call(explainer_media.production_props, Database.instance().connection, pid, "9:16")
    assert props["solo"]["geometry"] == public["props"]["solo"]["geometry"]
    assert props["solo"]["plan"]["revision"] == approved["revision"]
    assert props["layout"] == "vertical" and props["width"] == 1080
    assert len(list((tmp_path / "public").rglob("*.png"))) == 21
    assert all(url.startswith("remotion-render/") for url in props["solo"]["pictures"].values())


def test_layout_edit_invalidates_render_revision_and_requires_reapproval(client, monkeypatch):  # noqa: F811
    pid, _, approved = approved_fixture(client, monkeypatch)

    async def revision():
        async with read_transaction():
            return await project_service.media_input_revision(Database.instance().connection, pid, include_audio=True)
    before = client.portal.call(revision)
    changed = copy.deepcopy(approved["segments"])
    changed[0]["layouts"]["16:9"]["presenter"]["height"] = .20
    data(client.patch(f"/api/projects/{pid}/explainer-plan", json={"expected_revision": approved["revision"],
        "expected_source_fingerprint": approved["source_fingerprint"], "segments": changed}))
    assert before != client.portal.call(revision)
    with pytest.raises(Exception, match="Approve the current"):
        client.portal.call(partial(explainer_media.build_payload, Database.instance().connection, pid, approved=True))


def test_file_tampering_cannot_reuse_approved_pin(client, monkeypatch):  # noqa: F811
    pid, _, _ = approved_fixture(client, monkeypatch)
    payload = client.portal.call(partial(explainer_media.build_payload, Database.instance().connection, pid, approved=True))
    Path(payload["audio_files"][0]["path"]).write_bytes(b"modified")
    with pytest.raises(Exception, match="changed"):
        client.portal.call(partial(explainer_media.build_payload, Database.instance().connection, pid, approved=True))


def test_solo_audio_tail_controls_composition_and_short_frame_window():
    props = {"fps": 30, "introSec": 0, "outroSec": 0, "durationSeconds": 4.5,
             "lines": [{"startSec": 0, "endSec": 2}, {"startSec": 2.3, "endSec": 4.3}]}
    assert renderer.composition_seconds(props) == 4.5
    assert renderer.outro_start_seconds(props) == 4.5
    assert renderer.clip_frames(props, 1, 1) == (51, 134)
