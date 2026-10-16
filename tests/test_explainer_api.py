"""Real API job dispatch, scoped images and approval pinning with explicitly synthetic media/geometry."""
import copy
import hashlib
import json
import sqlite3
import time
import uuid
import wave
from pathlib import Path

import pytest

from backend import main
from backend.core.config import settings
from backend.db.database import Database
from backend.library import explainer_assets, explainer_service as service, presenter_asset_plan as front
from backend.media import audio_service
from backend.schemas.explainer import ExplainerSegment
from tests.test_explainer_assets import picture
from tests.test_explainer_plan import Router
from tests.test_explainer_project import solo_config
from tests.test_presenter_asset_plan import figure_bytes
from tests.test_visuals_project_api import client, data, locked_character  # noqa: F401


def setup(client):  # noqa: F811
    project = data(client.post("/api/projects", json=solo_config()))
    pid = project["id"]
    cid = locked_character("Hoang", "red")
    data(client.put(f"/api/projects/{pid}/visuals/cast", json=[{"speaker_index": 0, "character_id": cid}]))
    lines = data(client.put(f"/api/projects/{pid}/script", json={"lines": [
        {"speaker_id": project["speakers"][0]["id"], "text": "Small actions become daily habits."},
        {"speaker_id": project["speakers"][0]["id"], "text": "Start with one simple action."},
    ]}))
    segments = [ExplainerSegment(id=f"idea-{i}", intent="Explain a practical idea", line_ids=[line["id"]],
                                 start={"line_id": line["id"], "token_index": 0}, end={"line_id": line["id"], "token_index": 5},
                                 visual={"kind": "text_card", "title": "Start small"}) for i, line in enumerate(lines)]
    wire = {"segments": [{key: value for key, value in segment.model_dump().items() if key in service.ProposedExplainerSegment.model_fields} for segment in segments]}
    return pid, cid, lines, wire


def wait(client, pid, response):  # noqa: F811
    assert response.status_code in (200, 202), response.text
    job = response.json()["data"]
    for _ in range(300):
        current = data(client.get(f"/api/projects/{pid}/ai-jobs/{job['id']}"))
        if current["status"] in ("complete", "error", "stale", "cancelled"):
            return current
        time.sleep(.02)
    pytest.fail("proposal job did not finish")


def test_dedicated_and_generic_job_paths_use_identical_safe_snapshots(client, monkeypatch):  # noqa: F811
    pid, _, _, wire = setup(client)
    router = Router(json.dumps(wire))
    monkeypatch.setattr(main, "_build_ai_router", lambda: router)
    first = wait(client, pid, client.post(f"/api/projects/{pid}/explainer-plan/propose", json={"expected_revision": 0, "idempotency_key": "first"}))
    assert first["status"] == "complete", first
    plan = data(client.get(f"/api/projects/{pid}/explainer-plan"))["plan"]
    assert plan["revision"] == 1 and plan["status"] == "draft"
    second = wait(client, pid, client.post(f"/api/projects/{pid}/ai-jobs", json={"operation": "propose_explainer", "expected_revision": 1}))
    assert second["status"] == "complete" and router.calls == 2
    with sqlite3.connect(settings.db_path) as db:
        snapshots = [json.loads(row[0]) for row in db.execute("SELECT input_snapshot_json FROM ai_generation_jobs WHERE project_id=?", (pid,))]
    assert all({"source_fingerprint", "expected_revision", "source", "previous", "available_assets"} <= item.keys() for item in snapshots)
    replay = client.post(f"/api/projects/{pid}/explainer-plan/propose", json={"expected_revision": 0, "idempotency_key": "first"})
    assert replay.status_code == 200 and replay.json()["data"]["id"] == first["id"]
    assert client.post(f"/api/projects/{pid}/ai-jobs", json={"operation": "propose_explainer"}).status_code == 422
    assert client.post(f"/api/projects/{pid}/ai-jobs", json={"operation": "propose_explainer", "expected_revision": 2, "idempotency_key": "x" * 101}).status_code == 422
    assert len(data(client.get(f"/api/projects/{pid}/explainer-plan/history"))) == 2


def test_image_upload_ownership_hash_and_lock_boundaries(client, monkeypatch):  # noqa: F811
    pid, _, _, _ = setup(client)
    original = explainer_assets.stage_upload

    async def observe(*args):
        from backend.db.transactions import write_lock
        assert not write_lock.locked()
        return await original(*args)

    monkeypatch.setattr(explainer_assets, "stage_upload", observe)
    uploaded = data(client.post(f"/api/projects/{pid}/explainer/assets", files={"file": ("habit.png", picture(), "image/png")}))
    assert client.get(uploaded["preview_url"]).status_code == 200
    other, _, _, _ = setup(client)
    ref = uploaded["asset"]
    assert client.get(f"/api/projects/{other}/explainer/assets/{ref['asset_id']}/1/content").status_code == 404
    assert client.post(f"/api/projects/{pid}/explainer/assets", files={"file": ("broken.png", b"broken", "image/png")}).status_code == 422
    assert len(data(client.get(f"/api/projects/{pid}/explainer/assets"))) == 1
    with sqlite3.connect(settings.db_path) as db:
        path = db.execute("SELECT path FROM project_explainer_assets WHERE id=?", (ref["asset_id"],)).fetchone()[0]
    Path(path).write_bytes(b"tampered")
    assert client.get(uploaded["preview_url"]).status_code == 404


def synthetic_audio(client, pid, lines):  # noqa: F811
    """Silent test files exercise pin/hash/CAS only, never speech or listener acceptance."""
    folder = settings.DATA_DIR / "audio" / pid
    folder.mkdir(parents=True)
    wav, mp3 = folder / "fixture.wav", folder / "fixture.mp3"
    with wave.open(str(wav), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(8000)
        output.writeframes(b"\0\0" * 36000)
    mp3.write_bytes(b"test-only encoded audio placeholder; not a listening fixture")
    timestamps = [{"text": line["text"], "start_sec": i * 2.3, "end_sec": i * 2.3 + 2} for i, line in enumerate(lines)]
    words = [{"line_id": line["id"], "words": [{"text": word, "start_sec": i * 2.3 + .1 + j * .3,
                                               "end_sec": i * 2.3 + .3 + j * .3} for j, word in enumerate(line["text"].split())]} for i, line in enumerate(lines)]

    async def store():
        return await audio_service.save_audio_job(Database.instance().connection, pid, status="complete", mp3_path=str(mp3), wav_path=str(wav),
                                                    timestamps=timestamps, word_timestamps=words, duration_seconds=4.5)
    client.portal.call(store)


def prepared_front_files(api, cid):
    """Seed approved synthetic file versions. Upload/review parent-chain behavior has its own full API suite."""
    folder = settings.DATA_DIR / "library" / "characters" / cid / "v1" / "front" / "assets"
    content = figure_bytes()
    digest = hashlib.sha256(content).hexdigest()
    ids = {slot["key"]: str(uuid.uuid4()) for slot in front.SLOTS}
    rows = []
    for slot in front.SLOTS:
        path = folder / ids[slot["key"]] / (slot["key"] + ".png")
        path.parent.mkdir(parents=True)
        path.write_bytes(content)
        validation = {"content_hash": digest, "front_base_id": ids[front.BASE], "parent_asset_id": ids.get(slot["parent"])}
        rows.append((ids[slot["key"]], cid, str(path), "sprite/" + slot["key"], json.dumps(validation)))

    async def store():
        from backend.db.transactions import write_transaction
        db = Database.instance().connection
        async with write_transaction(db):
            await db.executemany("INSERT INTO character_assets(id,character_id,kind,path,approved,created_at,slot_key,source,review_state,validation_json,identity_version,is_current,updated_at,facing) "
                                 "VALUES(?,?,'sprite',?,1,'fixture',?,'upload','approved',?,1,1,'fixture','front')", rows)
    api.portal.call(store)


def test_approval_pins_real_immutable_front_files_and_refuses_missing_geometry(client, monkeypatch):  # noqa: F811
    pid, cid, lines, wire = setup(client)
    prepared_front_files(client, cid)
    synthetic_audio(client, pid, lines)
    monkeypatch.setattr(main, "_build_ai_router", lambda: Router(json.dumps(wire)))
    assert wait(client, pid, client.post(f"/api/projects/{pid}/explainer-plan/propose", json={"expected_revision": 0}))["status"] == "complete"
    view = data(client.get(f"/api/projects/{pid}/explainer-plan"))
    needs_review = client.post(f"/api/projects/{pid}/explainer-plan/approve", json={"expected_revision": 1, "source_fingerprint": view["plan"]["source_fingerprint"]})
    assert needs_review.status_code == 422 and "knowledge claims" in needs_review.text
    body = {"expected_revision": 1, "expected_source_fingerprint": view["current_source_fingerprint"], "segments": copy.deepcopy(view["plan"]["segments"])}
    illustration = data(client.post(f"/api/projects/{pid}/explainer/assets", files={"file": ("example.png", picture(), "image/png")}))
    body["segments"][0]["visual"] = {"kind": "photo", "asset": illustration["asset"]}
    for segment in body["segments"]:
        segment["needs_fact_review"] = False
    reviewed = data(client.patch(f"/api/projects/{pid}/explainer-plan", json=body))["plan"]
    approval = {"expected_revision": reviewed["revision"], "source_fingerprint": reviewed["source_fingerprint"]}
    refused = client.post(f"/api/projects/{pid}/explainer-plan/approve", json=approval)
    assert refused.status_code == 422 and "missing layouts" in refused.text

    async def geometry_fixture(snapshot, plan):
        from backend.db.transactions import write_lock
        assert not write_lock.locked(), "geometry/image work must run outside the DB lock"
        return {"rules_version": 1, "aspects": {aspect: {"fixture_only": True} for aspect in plan.aspects}}

    # Explicit validator double tests pin/CAS mechanics; it does not certify production geometry.
    async def incomplete_geometry(snapshot, plan):
        return {}

    monkeypatch.setattr(service, "_validate_geometry", incomplete_geometry)
    assert client.post(f"/api/projects/{pid}/explainer-plan/approve", json=approval).status_code == 422
    monkeypatch.setattr(service, "_validate_geometry", geometry_fixture)
    approved = data(client.post(f"/api/projects/{pid}/explainer-plan/approve", json=approval))["plan"]
    assert approved["status"] == "approved" and approved["revision"] == 3
    with sqlite3.connect(settings.db_path) as db:
        pinned = json.loads(db.execute("SELECT approved_snapshot_json FROM project_explainer_plans WHERE project_id=?", (pid,)).fetchone()[0])
    assert len(pinned["front"]["pictures"]) == 21 and len(pinned["audio_files"]) == 2
    assert len(pinned["illustrations"]) == 1 and pinned["illustrations"][0]["content_hash"] == illustration["asset"]["content_hash"]
    assert pinned["timing"][-1]["end_sec"] == 4.5 and pinned["plan"]["revision"] == 3
    assert client.post(f"/api/projects/{pid}/explainer-plan/approve", json=approval).status_code == 409
    assert client.patch(f"/api/projects/{pid}/explainer-plan", json=body).status_code == 409
    data(client.post(f"/api/projects/{pid}/explainer/assets", files={"file": ("unused.png", picture((600, 400)), "image/png")}))
    assert data(client.get(f"/api/projects/{pid}/explainer-plan"))["plan"]["status"] == "approved", "an unrelated upload must not stale reviewed references"
    current_approval = {"expected_revision": 3, "source_fingerprint": approved["source_fingerprint"]}
    front_path = Path(next(iter(pinned["front"]["pictures"].values()))["path"])
    original = front_path.read_bytes()
    front_path.write_bytes(b"modified pinned picture")
    assert client.post(f"/api/projects/{pid}/explainer-plan/approve", json=current_approval).status_code == 404
    front_path.write_bytes(original)

    async def source_changes_during_geometry(snapshot, plan):
        from backend.db.transactions import write_transaction
        db = Database.instance().connection
        async with write_transaction(db):
            await db.execute("UPDATE speakers SET pitch=1 WHERE project_id=?", (pid,))
        return await geometry_fixture(snapshot, plan)

    monkeypatch.setattr(service, "_validate_geometry", source_changes_during_geometry)
    assert client.post(f"/api/projects/{pid}/explainer-plan/approve", json=current_approval).status_code == 409
    assert len(data(client.get(f"/api/projects/{pid}/explainer-plan/history"))) == 3
    assert data(client.get(f"/api/projects/{pid}/explainer-plan"))["plan"]["status"] == "stale"


def test_classic_projects_cannot_use_solo_plan_operations(client):  # noqa: F811
    config = solo_config()
    config.update(presentation_mode="classic", explainer_structure=None)
    project = data(client.post("/api/projects", json=config))
    assert client.get(f"/api/projects/{project['id']}/explainer-plan").status_code == 422
    assert client.post(f"/api/projects/{project['id']}/explainer-plan/propose", json={"expected_revision": 0}).status_code == 422


@pytest.mark.parametrize("invalid", ["duplicate_aspects", "duplicate_segment_ids"])
def test_patch_rejects_duplicates_with_422_and_preserves_history(client, monkeypatch, invalid):  # noqa: F811
    pid, _, _, wire = setup(client)
    monkeypatch.setattr(main, "_build_ai_router", lambda: Router(json.dumps(wire)))
    job = wait(client, pid, client.post(f"/api/projects/{pid}/explainer-plan/propose", json={"expected_revision": 0}))
    assert job["status"] == "complete"
    plan = data(client.get(f"/api/projects/{pid}/explainer-plan"))["plan"]
    before = data(client.get(f"/api/projects/{pid}/explainer-plan/history"))
    good = {"expected_revision": plan["revision"], "expected_source_fingerprint": plan["source_fingerprint"],
            "segments": plan["segments"], "aspects": plan["aspects"]}
    bad = copy.deepcopy(good)
    if invalid == "duplicate_aspects":
        bad["aspects"] = ["16:9", "16:9"]
    else:
        bad["segments"][1]["id"] = bad["segments"][0]["id"]
    client._transport.raise_server_exceptions = False
    response = client.patch(f"/api/projects/{pid}/explainer-plan", json=bad)
    assert response.status_code == 422, response.text
    envelope = response.json()
    assert envelope["success"] is False and envelope["data"] is None
    assert "unique" in envelope["error"].lower()
    assert data(client.get(f"/api/projects/{pid}/explainer-plan/history")) == before
    assert data(client.get(f"/api/projects/{pid}/explainer-plan"))["plan"] == plan
    saved = data(client.patch(f"/api/projects/{pid}/explainer-plan", json=good))["plan"]
    assert saved["revision"] == plan["revision"] + 1


@pytest.mark.parametrize("revision", [True, "0", -1, None])
def test_both_proposal_entries_reject_invalid_revisions(client, revision):  # noqa: F811
    pid, _, _, _ = setup(client)
    for path, extra in (("explainer-plan/propose", {}), ("ai-jobs", {"operation": "propose_explainer"})):
        response = client.post(f"/api/projects/{pid}/{path}", json={"expected_revision": revision, **extra})
        assert response.status_code == 422, response.text
        assert response.json()["success"] is False
    assert data(client.get(f"/api/projects/{pid}/explainer-plan/history")) == []
