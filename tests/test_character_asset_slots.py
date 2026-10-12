"""Task 33.3 (D84/D86): slot-by-slot prompts and uploads -- renamed to the slot, aligned, checked, reviewed once."""

from __future__ import annotations

import io

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.core.config import settings
from app.main import app
from app.services.visuals.character_asset_service import SLOTS

QUICK = {"name": "Kai", "gender": "male", "accent": "british", "nationality": "Japanese",
         "appearance": "tall, short black hair, round glasses", "outfit": "grey hoodie and jeans"}
GREEN = (0, 177, 64)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with TestClient(app) as test_client:
        yield test_client


def data(response, status=200):
    assert response.status_code == status, response.text
    return response.json()["data"] if status == 200 else response.json()


def _person(size=(600, 760), mouth_open=False, arm_up=False) -> Image.Image:
    """A simple standing figure on flat green, like an outside-AI base picture (feet near the bottom)."""
    picture = Image.new("RGB", size, GREEN)
    draw = ImageDraw.Draw(picture)
    w, h = size
    cx = w // 2
    draw.ellipse((cx - 55, 40, cx + 55, 170), fill=(225, 190, 160))          # head
    draw.rectangle((cx - 30, 165, cx + 30, 195), fill=(225, 190, 160))       # neck
    draw.rectangle((cx - 110, 195, cx + 110, 470), fill=(120, 120, 130))     # hoodie
    draw.rectangle((cx - 100, 470, cx + 100, h - 25), fill=(40, 60, 120))    # jeans
    draw.rectangle((cx - 150, 205, cx - 112, 430), fill=(120, 120, 130))     # left arm
    if arm_up:
        draw.rectangle((cx + 112, 120, cx + 150, 300), fill=(120, 120, 130))
    else:
        draw.rectangle((cx + 112, 205, cx + 150, 430), fill=(120, 120, 130))
    draw.rectangle((cx - 22, 95, cx - 10, 105), fill=(30, 30, 30))           # eyes
    draw.rectangle((cx + 10, 95, cx + 22, 105), fill=(30, 30, 30))
    draw.rectangle((cx - 20, 135, cx + 20, 150 if mouth_open else 140), fill=(150, 40, 50))  # mouth
    return picture


def _bytes(picture: Image.Image, fmt="PNG") -> bytes:
    buffer = io.BytesIO()
    picture.save(buffer, fmt)
    return buffer.getvalue()


def _profile(client):
    return data(client.post("/api/visuals/profiles", json=QUICK))


def _upload(client, profile_id, slot, content, name="whatever_name.png", status=200):
    return data(client.post(f"/api/visuals/profiles/{profile_id}/slots/{slot}/upload",
                            files={"file": (name, content, "image/png")}), status=status)


def _approve(client, profile_id, asset_id):
    return data(client.put(f"/api/visuals/profiles/{profile_id}/assets/{asset_id}/review", json={"decision": "approve"}))


def test_every_profile_has_the_29_sprite_slots_with_prompts_parents_and_regions(client):
    kai = _profile(client)
    cards = {card["key"]: card for card in data(client.get(f"/api/visuals/profiles/{kai['id']}/slots"))["slots"]}
    assert len(cards) == 29 and len(SLOTS) == 29
    base = cards["calm__closed"]
    assert base["parent"] is None and base["file_name"] == "calm__closed.png"
    for words in ("Kai", "Japanese man", "round glasses", "grey hoodie", "#00B140", "30 degrees toward the right",
                  "right shoulder is nearer the camera", "not looking at the camera", "mid-thigh"):
        assert words in base["prompt"]
    assert (cards["smile__open"]["parent"], cards["smile__open"]["region"]) == ("smile__closed", "mouth")
    assert (cards["gesture-wave"]["parent"], cards["gesture-wave"]["region"]) == ("calm__closed", "arms")
    assert cards["blink"]["region"] == "eyes" and cards["gesture-wave__open"]["parent"] == "gesture-wave"
    smile = cards["smile__closed"]["prompt"]  # owner feedback: a short edit prompt barely changed the face
    assert smile.startswith("Edit the attached picture of Kai") and "corners of the mouth turned well up" in smile
    assert "clearly visible" in smile and "Do not redraw" in smile
    assert "the hand on the right side" in cards["gesture-wave"]["prompt"]  # the partner's side
    assert "the hands" not in cards["gesture-wave"]["prompt"].split("Keep everything else")[1]
    assert not cards["smile__closed"]["parent_ready"]


def test_female_base_prompt_faces_left(client):
    lena = data(client.post("/api/visuals/profiles", json={**QUICK, "name": "Lena", "gender": "female"}))
    base = data(client.get(f"/api/visuals/profiles/{lena['id']}/slots"))["slots"][0]
    assert "woman" in base["prompt"] and "toward the left side" in base["prompt"]
    assert "left shoulder is nearer the camera" in base["prompt"]


def test_base_upload_is_renamed_keyed_and_placed_on_the_canvas_and_waits_for_review(client):
    kai = _profile(client)
    asset = _upload(client, kai["id"], "calm__closed", _bytes(_person(), "JPEG"), name="IMG_2034.jpg")
    assert asset["review_state"] == "needs_review" and asset["original_filename"] == "IMG_2034.jpg"
    stored = settings.DATA_DIR / "library" / "characters" / kai["id"] / "v1" / "native" / "calm__closed.png"
    assert stored.is_file()
    canvas = np.asarray(Image.open(stored))
    assert canvas.shape == (1536, 1280, 4) and canvas[0, 0, 3] == 0
    ys = np.where((canvas[..., 3] > 20).any(axis=1))[0]
    assert ys.max() >= 1530 and 130 <= ys.min() <= 170  # feet on the floor, top near FIGURE_TOP
    assert not data(client.get(f"/api/visuals/profiles/{kai['id']}"))["readiness"]["talking_starter"]["have"]


def test_an_edit_waits_for_its_parent_to_be_approved(client):
    kai = _profile(client)
    _upload(client, kai["id"], "calm__closed", _bytes(_person()))
    error = _upload(client, kai["id"], "calm__open", _bytes(_person(mouth_open=True)), status=422)
    assert "approve the calm__closed picture first" in error["error"]


def test_region_edit_at_another_size_is_registered_on_its_parent_and_checked(client):
    kai = _profile(client)
    base = _upload(client, kai["id"], "calm__closed", _bytes(_person()))
    _approve(client, kai["id"], base["id"])
    source = Image.open(io.BytesIO(client.get(f"/api/visuals/profiles/{kai['id']}/slots/calm__closed/input.png").content))
    assert source.size == (1280, 1536) and source.getpixel((5, 5)) == GREEN
    edited = source.copy()
    ImageDraw.Draw(edited).rectangle((610, 520, 690, 560), fill=(150, 40, 50))  # an open mouth, nothing else changed
    edited = edited.resize((854, 1024), Image.Resampling.LANCZOS)  # the outside AI returned a smaller picture
    asset = _upload(client, kai["id"], "calm__open", _bytes(edited))
    assert asset["validation"]["method"] == "region edit" and asset["validation"]["problems"] == []


def test_a_redrawn_picture_is_fitted_to_the_base_instead(client):
    kai = _profile(client)
    base = _upload(client, kai["id"], "calm__closed", _bytes(_person()))
    _approve(client, kai["id"], base["id"])
    redrawn = _person(arm_up=True)
    pixels = np.asarray(redrawn).copy()
    pixels[(pixels == (120, 120, 130)).all(axis=2)] = (90, 140, 200)  # another hoodie: the AI drew the picture again
    redrawn = Image.fromarray(pixels).resize((760, 760))  # and other proportions, so it is no edit of the parent
    asset = _upload(client, kai["id"], "gesture-wave", _bytes(redrawn))
    assert asset["validation"]["method"].startswith("redrawn")


@pytest.mark.parametrize("content,reason", [(b"not a picture", "not a readable picture"), (b"", "empty")])
def test_a_bad_file_never_replaces_the_current_picture(client, content, reason):
    kai = _profile(client)
    base = _upload(client, kai["id"], "calm__closed", _bytes(_person()))
    error = _upload(client, kai["id"], "calm__closed", content, status=422)
    assert reason in error["error"]
    cards = data(client.get(f"/api/visuals/profiles/{kai['id']}/slots"))["slots"]
    assert cards[0]["asset"]["id"] == base["id"]


def test_a_base_without_green_background_is_refused_with_the_reason(client):
    kai = _profile(client)
    grey = _person()
    pixels = np.asarray(grey).copy()
    pixels[(pixels == GREEN).all(axis=2)] = (200, 200, 200)
    error = _upload(client, kai["id"], "calm__closed", _bytes(Image.fromarray(pixels)), status=422)
    assert "#00B140" in error["error"]


def test_approve_all_derives_core_pictures_and_unlocks_readiness(client):
    kai = _profile(client)
    base = _upload(client, kai["id"], "calm__closed", _bytes(_person()))
    _approve(client, kai["id"], base["id"])
    source = Image.open(io.BytesIO(client.get(f"/api/visuals/profiles/{kai['id']}/slots/calm__closed/input.png").content))
    ids = [_upload(client, kai["id"], slot, _bytes(source))["id"] for slot in ("calm__open", "smile__closed",
                                                                                 "surprised__closed", "blink")]
    data(client.post(f"/api/visuals/profiles/{kai['id']}/assets/approve", json={"asset_ids": ids}))
    for slot in ("smile__open", "surprised__open"):
        parent = Image.open(io.BytesIO(client.get(
            f"/api/visuals/profiles/{kai['id']}/slots/{slot.replace('__open', '__closed')}/input.png").content))
        _approve(client, kai["id"], _upload(client, kai["id"], slot, _bytes(parent))["id"])
    readiness = data(client.get(f"/api/visuals/profiles/{kai['id']}"))["readiness"]
    assert readiness["core_visuals"]["ready"], readiness["core_visuals"]
    assert readiness["talking_starter"]["ready"] and readiness["video_ready"] and readiness["talking_ready"]
    portrait = settings.DATA_DIR / "library" / "characters" / kai["id"] / "v1" / "native" / "core_portrait_smile.png"
    assert Image.open(portrait).size == (768, 768)


def test_approving_a_new_base_starts_a_new_identity_version(client):
    kai = _profile(client)
    first = _upload(client, kai["id"], "calm__closed", _bytes(_person()))
    _approve(client, kai["id"], first["id"])
    source = client.get(f"/api/visuals/profiles/{kai['id']}/slots/calm__closed/input.png").content
    _approve(client, kai["id"], _upload(client, kai["id"], "calm__open", source)["id"])
    second = _upload(client, kai["id"], "calm__closed", _bytes(_person(size=(640, 800))))
    _approve(client, kai["id"], second["id"])
    profile = data(client.get(f"/api/visuals/profiles/{kai['id']}"))
    assert profile["identity_version"] == 2
    assert profile["readiness"]["talking_starter"]["have"] == 1  # only the new base; calm__open must be made again
    old_file = settings.DATA_DIR / "library" / "characters" / kai["id"] / "v1" / "native" / "calm__open.png"
    assert old_file.is_file()  # older versions stay on disk for projects that used them


def test_prompt_pack_text_lists_every_slot(client):
    kai = _profile(client)
    text = client.get(f"/api/visuals/profiles/{kai['id']}/prompt-pack.txt").text
    assert text.count("Ô: ") == 29 and "gesture-wave__open.png" in text and "Vùng tô:" in text


def test_bulk_drop_maps_canonical_names_and_lists_the_rest(client):
    kai = _profile(client)
    files = [("files", ("kai__calm__closed.png", _bytes(_person()), "image/png")),
             ("files", ("photo 1.png", _bytes(_person()), "image/png")),
             ("files", ("smile__closed.png", _bytes(_person()), "image/png"))]
    result = data(client.post(f"/api/visuals/profiles/{kai['id']}/slots/upload-batch", files=files))
    assert [item["slot"] for item in result["stored"]] == ["calm__closed"]
    assert [item["file"] for item in result["unmatched"]] == ["photo 1.png"]
    assert result["failed"][0]["slot"] == "smile__closed"  # its parent is not approved yet


def test_a_full_length_picture_is_cut_at_mid_thigh_like_the_other_packs(client):
    """Owner feedback 2026-10-12: a full-length base (feet visible) looked small next to Alex and Lina, who are framed
    from the head to mid-thigh. The upload keeps the head-to-mid-thigh part and fills the canvas height with it."""
    kai = _profile(client)
    _upload(client, kai["id"], "calm__closed", _bytes(_person(size=(600, 900))))  # feet well above the bottom edge
    stored = settings.DATA_DIR / "library" / "characters" / kai["id"] / "v1" / "native" / "calm__closed.png"
    alpha = np.asarray(Image.open(stored))[..., 3] > 20
    ys = np.where(alpha.any(axis=1))[0]
    assert ys.max() >= 1530 and ys.min() <= 170  # the cut edge on the floor, the head near the top
    jeans = np.asarray(Image.open(stored))[..., :3][alpha]
    assert ((jeans == (40, 60, 120)).all(axis=1)).mean() < 0.35  # most of the legs are gone, the hoodie fills the frame


def test_approving_the_base_derives_the_face_references_of_the_shot_pipeline(client):
    """D87: `face` and `face_turned` (512 px, the turned one looking right) come from the approved base sprite."""
    for name, gender in (("Kai", "male"), ("Lena", "female")):
        profile = data(client.post("/api/visuals/profiles", json={**QUICK, "name": name, "gender": gender}))
        base = _upload(client, profile["id"], "calm__closed", _bytes(_person()))
        _approve(client, profile["id"], base["id"])
        folder = settings.DATA_DIR / "library" / "characters" / profile["id"] / "v1" / "native"
        face, turned = Image.open(folder / "core_face.png"), Image.open(folder / "core_face_turned.png")
        assert face.size == turned.size == (512, 512)
        same = np.array_equal(np.asarray(face), np.asarray(turned))
        mirrored = np.array_equal(np.asarray(face)[:, ::-1], np.asarray(turned))
        assert same if gender == "male" else mirrored  # a woman's pack looks left: her turned face is mirrored to look right
