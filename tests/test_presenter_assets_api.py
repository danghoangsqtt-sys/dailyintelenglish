"""Front import batch failures, identity-version isolation and profile ownership checks."""
import json
import hashlib
import sqlite3
import uuid

from backend.core.config import settings
from backend.library import presenter_asset_plan as front
from tests.test_character_profiles_api import client, create, data  # noqa: F401
from tests.test_presenter_asset_plan import approve, figure_bytes, upload


def test_front_batch_retains_successes_and_reports_unknown_and_unapproved_parent(client):  # noqa: F811
    character = create(client)
    cid = character["id"]
    result = data(client.post(f"/api/visuals/profiles/{cid}/slots/upload-batch?view=front", files=[
        ("files", ("Hoang__calm__closed.png", figure_bytes(), "image/png")),
        ("files", ("smile__closed.png", figure_bytes(), "image/png")),
        ("files", ("blink.png", figure_bytes(), "image/png")),
    ]))
    assert len(result["stored"]) == len(result["unmatched"]) == len(result["failed"]) == 1
    assert result["stored"][0]["slot"] == front.BASE and result["stored"][0]["view"] == "front"
    assert result["unmatched"][0]["file"] == "smile__closed.png"
    assert "Approve" in result["failed"][0]["reason"]
    slots = data(client.get(f"/api/visuals/profiles/{cid}/slots?view=front"))
    assert slots["slots"][0]["asset"]["review_state"] == "needs_review" and not slots["readiness"]["ready"]


def test_front_assets_of_other_identity_version_do_not_count_as_ready(client):  # noqa: F811
    cid = create(client)["id"]
    with sqlite3.connect(settings.db_path) as db:
        for key in front.SLOT_KEYS:
            db.execute("INSERT INTO character_assets (id,character_id,kind,path,approved,created_at,slot_key,source,review_state,"
                       "validation_json,identity_version,is_current,updated_at,facing) VALUES (?,?,'sprite','fixture.png',1,"
                       "'fixture',?,'fixture','approved',?,2,1,'fixture','front')",
                       (str(uuid.uuid4()), cid, "sprite/" + key, json.dumps({"content_hash": "a" * 64})))
    profile = data(client.get(f"/api/visuals/profiles/{cid}"))
    assert profile["identity_version"] == 1 and profile["readiness"]["front_presenter"]["have"] == 0
    assert len(profile["readiness"]["front_presenter"]["missing"]) == 21
    slots = data(client.get(f"/api/visuals/profiles/{cid}/slots?view=front"))
    assert all(card["asset"] is None for card in slots["slots"]) and slots["pack_revision"] is None


def test_front_asset_review_and_download_require_matching_profile(client):  # noqa: F811
    first, second = create(client), create(client, name="Other Owner")
    asset = upload(client, first["id"], front.BASE, figure_bytes())
    assert client.get(f"/api/visuals/profiles/{second['id']}/assets/{asset['id']}/content").status_code == 404
    assert client.put(f"/api/visuals/profiles/{second['id']}/assets/{asset['id']}/review?view=front", json={"decision": "approve"}).status_code == 409
    original = data(client.get(f"/api/visuals/profiles/{first['id']}/slots?view=front"))
    assert original["slots"][0]["asset"]["review_state"] == "needs_review"


def test_duplicate_keeps_voice_and_requires_its_own_front_pack(client):  # noqa: F811
    cid = create(client)["id"]
    asset = upload(client, cid, front.BASE, figure_bytes())
    approve(client, cid, asset)
    copied = data(client.post(f"/api/visuals/profiles/{cid}/duplicate"))
    original = data(client.get(f"/api/visuals/profiles/{cid}"))
    assert original["readiness"]["front_presenter"]["have"] == 1
    assert copied["readiness"]["front_presenter"]["have"] == 0 and not copied["readiness"]["front_presenter"]["ready"]
    assert copied["voice"] == original["voice"]


def test_front_upload_preserves_existing_native_rows_and_image_hashes(client):  # noqa: F811
    from pathlib import Path

    cid = create(client)["id"]
    native_asset = data(client.post(f"/api/visuals/profiles/{cid}/slots/calm__closed/upload",
                                   files={"file": ("native.png", figure_bytes(), "image/png")}))
    data(client.put(f"/api/visuals/profiles/{cid}/assets/{native_asset['id']}/review", json={"decision": "approve"}))
    before = data(client.get(f"/api/visuals/profiles/{cid}"))["readiness"]
    with sqlite3.connect(settings.db_path) as db:
        native_rows = db.execute("SELECT id,path,review_state,is_current,identity_version FROM character_assets "
                                 "WHERE character_id=? AND facing='native' ORDER BY id", (cid,)).fetchall()
    hashes = {row[0]: hashlib.sha256(Path(row[1]).read_bytes()).hexdigest() for row in native_rows}
    front_asset = upload(client, cid, front.BASE, figure_bytes())
    approve(client, cid, front_asset)
    after = data(client.get(f"/api/visuals/profiles/{cid}"))["readiness"]
    for key in ("core_visuals", "talking_starter", "full_sprite_pack", "video_ready", "talking_ready"):
        assert after[key] == before[key]
    assert after["front_presenter"]["have"] == 1
    with sqlite3.connect(settings.db_path) as db:
        assert db.execute("SELECT id,path,review_state,is_current,identity_version FROM character_assets "
                          "WHERE character_id=? AND facing='native' ORDER BY id", (cid,)).fetchall() == native_rows
    assert all(hashlib.sha256(Path(row[1]).read_bytes()).hexdigest() == hashes[row[0]] for row in native_rows)
