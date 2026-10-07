"""Phase 31: the owner's own pictures go into the Shot Library through an inbox folder (names carry the tags)."""

from __future__ import annotations

import shutil
import sqlite3

import pytest
from PIL import Image

from app.core.config import settings
from app.services.visuals import shot_library_service as lib
from tests.test_shot_library import _library, requests_log  # noqa: F401
from tests.test_visuals_project_api import PROJECT, client, data, locked_character, wait_job  # noqa: F401


def _picture(name: str, size=(1344, 768), colour=(120, 90, 60)) -> None:
    folder = lib.inbox_dir()
    folder.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, colour).save(folder / name)


def _two_characters() -> list[str]:
    lina, alex = locked_character("Lina", "white"), locked_character("Alex", "navy")
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute("UPDATE characters SET gender = 'male' WHERE id = ?", (alex,))
        connection.execute("UPDATE characters SET created_at = '2026-01-01' WHERE id = ?", (lina,))
    return [lina, alex]


def test_the_names_carry_the_tags():
    assert lib.parse_inbox_name("cafe__duo-wide") == {
        "scene": "cafe", "kind": "duo_wide", "reverse": False, "single": None, "pair": None, "action": "",
        "expression": "calm"}
    assert lib.parse_inbox_name("cafe__duo-close-alex-lina")["pair"] == ("alex", "lina")
    parsed = lib.parse_inbox_name("City-street__duo-close-rev__drinking-coffee__smile")
    assert (parsed["kind"], parsed["reverse"], parsed["action"], parsed["expression"]) == (
        "duo_close", True, "drinking coffee", "smile")
    assert lib.parse_inbox_name("park__single-Lina__laugh")["single"] == "lina"
    assert lib.parse_inbox_name("market__duo-wide__walking__2")["action"] == "walking"  # a variant number is ignored
    for bad in ("cafe", "cafe__wide", "cafe__duo"):
        with pytest.raises(ValueError):
            lib.parse_inbox_name(bad)


def test_pictures_in_the_inbox_become_pending_library_shots_with_their_tags(client, requests_log):  # noqa: F811
    lina, alex = _two_characters()
    _picture("cafe__duo-wide.png")
    _picture("Cafe__duo-close-rev__drinking-coffee__smile.jpg", colour=(10, 90, 60))
    _picture("city-street__single-alex.webp", colour=(1, 2, 3))
    shutil.copy(lib.inbox_dir() / "cafe__duo-wide.png", lib.inbox_dir() / "cafe__duo-wide__calm.png")  # same picture again
    _picture("nowhere__duo-wide.png", colour=(9, 9, 9))
    _picture("cafe__zoom.png", colour=(8, 8, 8))
    assert data(client.get("/api/visuals/library/inbox"))["files"][0].lower().startswith("cafe")
    result = data(client.post("/api/visuals/library/inbox/import"))
    assert len(result["imported"]) == 3
    reasons = {item["file"]: item["reason"] for item in result["skipped"]}
    assert "already in the library" in reasons["cafe__duo-wide__calm.png"]
    assert "unknown scene" in reasons["nowhere__duo-wide.png"] and "framing" in reasons["cafe__zoom.png"]
    shots = {(row["scene_id"], row["kind"], row["action"], row["expression"]): row for row in _library(client)}
    wide = shots[("builtin-cafe", "duo_wide", "", "calm")]
    assert wide["character_ids"] == [lina, alex] and wide["review_state"] == "pending"  # the woman left, the man right
    close = shots[("builtin-cafe", "duo_close", "drinking coffee", "smile")]
    assert close["character_ids"] == [alex, lina]  # -rev
    assert shots[("builtin-street", "single", "", "calm")]["character_ids"] == [alex]
    folder = lib.inbox_dir()
    assert sorted(p.name for p in (folder / "imported").iterdir()) == sorted(item["file"] for item in result["imported"])
    assert sorted(lib.list_inbox()) == sorted(reasons)  # only the refused files stay, to be fixed or removed
    assert client.get(wide["content_url"]).status_code == 200


def test_a_picture_that_is_not_16_9_is_cropped_to_it_keeping_the_top(client, requests_log):  # noqa: F811
    _two_characters()
    folder = lib.inbox_dir()
    folder.mkdir(parents=True, exist_ok=True)
    tall = Image.new("RGB", (1448, 1086), (200, 200, 200))
    tall.paste(Image.new("RGB", (1448, 100), (255, 0, 0)), (0, 0))  # a red band at the very top
    tall.save(folder / "cafe__duo-wide.png")
    wide = Image.new("RGB", (2000, 768), (50, 50, 50))
    wide.save(folder / "park__duo-wide.png")
    result = data(client.post("/api/visuals/library/inbox/import"))
    assert [item["cropped"] for item in result["imported"]] == [True, True]
    for row in _library(client):
        picture = Image.open(settings.DATA_DIR / "library" / "shots" / f"{row['id']}.png")
        assert abs(picture.width / picture.height - 16 / 9) < 0.01
    cafe = next(row for row in _library(client) if row["scene_id"] == "builtin-cafe")
    stored = Image.open(settings.DATA_DIR / "library" / "shots" / f"{cafe['id']}.png")
    assert stored.getpixel((10, 10)) == (255, 0, 0)  # the top was kept


def test_an_imported_picture_is_reused_once_approved(client, requests_log):  # noqa: F811
    lina, alex = _two_characters()
    project = data(client.post("/api/projects", json=PROJECT))
    base = f"/api/projects/{project['id']}/visuals"
    data(client.put(f"{base}/cast", json=[{"speaker_index": 0, "character_id": lina},
                                          {"speaker_index": 1, "character_id": alex}]))
    data(client.put(f"{base}/scenes", json=["builtin-cafe"]))
    for kind in ("duo-wide", "duo-close"):
        _picture(f"cafe__{kind}.png", colour=(40 if kind == "duo-wide" else 80, 60, 90))
    for side in ("lina", "alex"):
        _picture(f"cafe__single-{side}.png", colour=(30, 30, 200 if side == "lina" else 100))
    imported = data(client.post("/api/visuals/library/inbox/import"))["imported"]
    assert len(imported) == 4
    wait_job(client, data(client.post(f"{base}/shots")))
    assert all(shot["source"] == "generated" for shot in data(client.get(base))["shots"])  # pending: not reused yet
    for row in _library(client):
        data(client.patch(f"/api/visuals/library/shots/{row['id']}", json={"review_state": "approved"}))
    requests_log.clear()
    wait_job(client, data(client.post(f"{base}/shots")))
    shots = data(client.get(base))["shots"]
    assert [shot["source"] for shot in shots] == ["library"] * 4
    assert not [call for call in requests_log if call.get("command") in ("encode", "generate")]  # no GPU work at all


def test_a_picture_with_the_people_the_other_way_round_is_reused_flipped(client, requests_log):  # noqa: F811
    lina, alex = _two_characters()
    project = data(client.post("/api/projects", json=PROJECT))
    base = f"/api/projects/{project['id']}/visuals"
    # the project's first speaker is Alex, the second Lina: the picture (Lina left, Alex right) is the other way round
    data(client.put(f"{base}/cast", json=[{"speaker_index": 0, "character_id": alex},
                                          {"speaker_index": 1, "character_id": lina}]))
    data(client.put(f"{base}/scenes", json=["builtin-cafe"]))
    folder = lib.inbox_dir()
    folder.mkdir(parents=True, exist_ok=True)
    asymmetric = Image.new("RGB", (1344, 768), (0, 0, 255))
    asymmetric.paste(Image.new("RGB", (672, 768), (255, 0, 0)), (0, 0))  # red on the left, blue on the right
    asymmetric.save(folder / "cafe__duo-wide.png")
    for kind, colour in (("duo-close", (9, 9, 9)), ("single-lina", (8, 8, 8)), ("single-alex", (7, 7, 7))):
        Image.new("RGB", (1344, 768), colour).save(folder / f"cafe__{kind}.png")
    assert len(data(client.post("/api/visuals/library/inbox/import"))["imported"]) == 4
    for row in _library(client):
        data(client.patch(f"/api/visuals/library/shots/{row['id']}", json={"review_state": "approved"}))
    requests_log.clear()
    wait_job(client, data(client.post(f"{base}/shots")))
    shots = data(client.get(base))["shots"]
    assert [shot["source"] for shot in shots] == ["library"] * 4 and not [
        call for call in requests_log if call.get("command") in ("encode", "generate")]
    wide = next(shot for shot in shots if shot["kind"] == "duo_wide")
    picture = Image.open(settings.DATA_DIR / "visuals" / project["id"] / "shots" / wide["id"] / "final.png")
    assert picture.getpixel((10, 10)) == (0, 0, 255) and picture.getpixel((1330, 10)) == (255, 0, 0)  # flipped
