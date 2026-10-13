"""Task 33.6 (D81/D82): men on the left, women on the right, the two facing each other; slot uploads become the renderer's pack."""

from __future__ import annotations

import sqlite3

import aiosqlite
import pytest

from backend.core.config import settings
from backend.media import video_renderer_remotion as remotion
from backend.library import character_asset_service as assets
from backend.library import sprite_service
from tests.test_character_asset_slots import _bytes, _person
from tests.test_podcast_modes import _make_a_plate
from tests.test_sprite_video_props import _audio_job, _give_sprites, _public
from tests.test_visuals_project_api import client, data, setup_project  # noqa: F401


@pytest.mark.parametrize("members,expected", [
    ([(0, "male"), (1, "female")], {0: 0, 1: 1}),
    ([(0, "female"), (1, "male")], {0: 1, 1: 0}),   # the woman speaks first and still stands on the right
    ([(0, "male"), (1, "male")], {0: 0, 1: 1}),     # same gender: speaker order
    ([(0, "female"), (1, "female")], {0: 0, 1: 1}),
    ([(0, "female")], {0: 1}),                      # a lone woman on the right
    ([(0, "male")], {0: 0}),
])
def test_placement_puts_men_left_and_women_right(members, expected):
    assert remotion.sprite_placement(members) == expected


@pytest.mark.parametrize("slot,facing,gender,mirrored", [
    (0, "right", "male", False), (1, "left", "female", False),   # the default packs face each other already
    (1, "right", "male", True), (0, "left", "female", True),     # a same-gender pair: the second one is turned round
    (0, "", "female", True), (1, "", "male", True),              # no recorded facing: the gender's default
])
def test_a_pack_looking_the_other_way_is_mirrored(slot, facing, gender, mirrored):
    assert remotion.sprite_mirrored(slot, facing, gender) is mirrored


def _gender(character_id: str, gender: str, facing: str = "") -> None:
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute("UPDATE characters SET gender = ?, sprite_facing = ? WHERE id = ?", (gender, facing, character_id))


@pytest.mark.asyncio
async def test_a_woman_speaking_first_stands_right_and_her_lines_point_at_her_slot(client, tmp_path, monkeypatch):  # noqa: F811
    project, ids, scenes = setup_project(client, 2, 1)
    _gender(ids[0], "female", "left")  # speaker 1
    _gender(ids[1], "male", "right")   # speaker 2
    _give_sprites(ids[0])
    _give_sprites(ids[1])
    _make_a_plate(scenes[0]["id"])
    _public(tmp_path, monkeypatch)
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        props = await remotion._build_input_props(db, project, _audio_job(project), None, visual_mode="podcast_sprites")
    sprites = props["sprites"]
    by_name = {character["name"]: character for character in sprites["characters"]}
    assert (by_name["Nova"]["slot"], by_name["Mira"]["slot"]) == (1, 0)
    assert not by_name["Nova"]["mirror"] and not by_name["Mira"]["mirror"]
    assert sprites["lines"][0]["slot"] == 1  # the first line is Nova's (speaker 1), on the right


@pytest.mark.asyncio
async def test_two_women_face_each_other_by_mirroring_the_one_on_the_left(client, tmp_path, monkeypatch):  # noqa: F811
    project, ids, scenes = setup_project(client, 2, 1)
    _gender(ids[0], "female", "left")
    _gender(ids[1], "female", "left")
    _give_sprites(ids[0])
    _give_sprites(ids[1])
    _make_a_plate(scenes[0]["id"])
    _public(tmp_path, monkeypatch)
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        props = await remotion._build_input_props(db, project, _audio_job(project), None, visual_mode="podcast_sprites")
    mirrors = {character["slot"]: character["mirror"] for character in props["sprites"]["characters"]}
    assert mirrors == {0: True, 1: False}


def test_approved_slot_uploads_become_the_renderers_sprite_pack(client):  # noqa: F811
    kai = data(client.post("/api/visuals/profiles", json={
        "name": "Kai", "gender": "male", "accent": "british", "appearance": "short black hair", "outfit": "grey hoodie"}))
    upload = client.post(f"/api/visuals/profiles/{kai['id']}/slots/calm__closed/upload",
                         files={"file": ("x.png", _bytes(_person()), "image/png")}).json()["data"]
    assert sprite_service.load_set(kai["id"]) is None  # nothing reaches the video before approval
    data(client.put(f"/api/visuals/profiles/{kai['id']}/assets/{upload['id']}/review", json={"decision": "approve"}))
    source = client.get(f"/api/visuals/profiles/{kai['id']}/slots/calm__closed/input.png").content
    second = client.post(f"/api/visuals/profiles/{kai['id']}/slots/calm__open/upload",
                         files={"file": ("y.png", source, "image/png")}).json()["data"]
    data(client.post(f"/api/visuals/profiles/{kai['id']}/assets/approve", json={"asset_ids": [second["id"]]}))
    pack = sprite_service.load_set(kai["id"])
    assert pack is not None and set(pack["names"]) == {"calm__closed", "calm__open"} and sprite_service.usable(pack)


@pytest.mark.asyncio
async def test_a_legacy_pack_is_never_rewritten_from_its_own_folder(client):  # noqa: F811
    _, ids, _ = setup_project(client, 1, 1)
    _give_sprites(ids[0])
    before = sorted(path.name for path in sprite_service.sprite_dir(ids[0]).iterdir())
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        assert await assets.register_legacy_sprites(db) > 0
        await db.execute("UPDATE character_assets SET review_state = 'approved' WHERE character_id = ?", (ids[0],))
        assert await assets.materialize_sprite_set(db, ids[0]) is None
    assert sorted(path.name for path in sprite_service.sprite_dir(ids[0]).iterdir()) == before


@pytest.mark.parametrize("line_speakers,expected", [
    ([0, 1, 0, 1], [({0, 1}, 0, 3)]),                                    # two people: one segment, the old video
    ([0, 1, 2, 2, 0], [({0, 1}, 0, 1), ({1, 2}, 2, 3), ({0, 2}, 4, 4)]),  # three: each line shows its speaker and partner
    ([2, 0, 2], [({0, 2}, 0, 2)]),                                       # a first line pairs with the next other speaker
    ([0, 0], [({0}, 0, 1)]),                                             # one speaker alone
    ([None, 1, None, 0], [({0, 1}, 0, 3)]),                              # unknown lines keep the pair around them
    ([None], []),
])
def test_segments_show_each_lines_speaker_with_the_person_they_talk_to(line_speakers, expected):
    segments = remotion.sprite_segments(line_speakers)
    assert [(set(segment["pair"]), segment["first"], segment["last"]) for segment in segments] == expected


@pytest.mark.asyncio
async def test_a_three_speaker_project_changes_the_pair_on_screen_by_segment(client, tmp_path, monkeypatch):  # noqa: F811
    from tests.test_visuals_project_api import locked_character

    project, ids, scenes = setup_project(client, 2, 1)
    third = locked_character("Omar", "green")
    _gender(ids[0], "female", "left")  # Nova
    _gender(ids[1], "female", "left")  # Mira
    _gender(third, "male", "right")    # Omar
    for character_id in (*ids, third):
        _give_sprites(character_id)
    _make_a_plate(scenes[0]["id"])
    _public(tmp_path, monkeypatch)
    speakers = [*project["speakers"], {"id": "s-omar", "speaker_index": 2, "name": "Omar", "gender": "male",
                                       "accent": "american"}]
    project = {**project, "speakers": speakers}
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute("INSERT INTO speakers (id, project_id, speaker_index, name, gender, accent, tts_engine) "
                           "VALUES ('s-omar', ?, 2, 'Omar', 'male', 'american', 'edge_tts')", (project["id"],))
        connection.execute("INSERT INTO project_cast (project_id, speaker_index, character_id, profile_version) VALUES (?, 2, ?, 1)",
                           (project["id"], third))
    first, second = project["speakers"][0]["id"], project["speakers"][1]["id"]
    audio = {
        "mp3_path": str(settings.DATA_DIR / "no-such-audio.mp3"),
        "timestamps": [
            {"start_sec": 0.0, "end_sec": 2.0, "label": "Nova", "speaker_id": first, "text": "Hi Mira!"},
            {"start_sec": 2.0, "end_sec": 4.0, "label": "Mira", "speaker_id": second, "text": "Hello!"},
            {"start_sec": 4.0, "end_sec": 6.0, "label": "Omar", "speaker_id": "s-omar", "text": "Can I join?"},
        ],
        "word_timestamps": [{"words": []}] * 3,
    }
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        props = await remotion._build_input_props(db, project, audio, None, visual_mode="podcast_sprites")
    sprites = props["sprites"]
    entries = {(c["name"], c["slot"], c["fromSec"], c["toSec"], c["mirror"]) for c in sprites["characters"]}
    assert entries == {
        ("Nova", 0, 0.0, 4.0, True), ("Mira", 1, 0.0, 4.0, False),   # two women: speaker order, the left one turned round
        ("Omar", 0, 4.0, None, False), ("Mira", 1, 4.0, None, False),  # Omar answers Mira: the man left, the woman right
    }
    assert [line["slot"] for line in sprites["lines"]] == [0, 1, 0]  # every speaker is on screen when talking
    assert max(len([c for c in sprites["characters"] if c["fromSec"] <= t < (c["toSec"] or 99)]) for t in (1, 3, 5)) == 2


def test_a_three_speaker_storyboard_shows_the_two_who_talk_most_in_each_beat(monkeypatch):
    from backend.library import storyboard_service

    monkeypatch.setattr(storyboard_service.settings, "VISUALS_IMAGE_CAP", 15)  # 3 places x 5 framings
    lines = [0, 1, 0, 1, 2, 1, 2, 2, 2, 0, 2, 0]  # beat 1: 0 and 1; beat 2: 2 and 1; beat 3: 2 and 0
    beats = storyboard_service.rule_beats(lines, {0, 1, 2}, ["a", "b", "c"])
    assert [beat.speakers for beat in beats] == [[0, 1], [1, 2], [0, 2]]
    assert all(len(beat.speakers) <= 2 for beat in beats)
