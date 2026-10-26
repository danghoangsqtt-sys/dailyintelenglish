"""Task 33.1: migration 018 (character profiles v2) keeps existing characters, casts and speakers, and adds the
profile/version/facing columns; legacy sprite packs register idempotently; names and casts stay unique."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from PIL import Image

from backend.core.config import settings
from backend.core.exceptions import ConflictError, ValidationError
from backend.db.database import MIGRATIONS_DIR, migration_functions
from backend.schemas.visuals import CharacterInput
from backend.library import library_service, project_visuals_service
from scripts.migrate_character_profiles_v2 import register_legacy_sprites

LINA, ALEX = "e961d07c-da89-4395-beec-7741df69142d", "0383161f-b197-41af-b1fd-f912253ed42e"
MIGRATION_018 = "018_character_profiles_v2.sql"


def _apply(connection: sqlite3.Connection, *, until: str | None = None, only: str | None = None) -> None:
    for name, arg_count, function in migration_functions():
        connection.create_function(name, arg_count, function, deterministic=True)
    for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if only and migration.name != only:
            continue
        if until and migration.name >= until:
            break
        connection.executescript(migration.read_text(encoding="utf-8"))


def _character(connection, character_id, name, gender):
    connection.execute(
        "INSERT INTO characters (id, name, gender, age_group, ethnicity, role, hair, eyes, top_color, top_item, "
        "bottom_color, bottom_item, status, base_seed, created_at, updated_at) VALUES "
        "(?, ?, ?, 'adult', 'Russian', 'host', 'brown', 'brown', 'navy', 'suit jacket', 'navy', 'suit trousers', "
        "'locked', 7, 'now', 'now')",
        (character_id, name, gender),
    )


def _old_database(path: Path) -> sqlite3.Connection:
    """A database at migration 017 holding Lina, Alex, their approved sheet pictures and a two-speaker cast."""
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    _apply(connection, until=MIGRATION_018)
    _character(connection, LINA, "Lina", "female")
    _character(connection, ALEX, "Alex", "male")
    for character_id in (LINA, ALEX):
        for kind, approved in (("candidate", 0), ("full_body", 1), ("portrait_smile", 1)):
            connection.execute(
                "INSERT INTO character_assets (id, character_id, kind, path, approved, created_at) VALUES (?, ?, ?, ?, ?, 'now')",
                (f"{character_id}-{kind}", character_id, kind, f"data/library/characters/{character_id}/{kind}.png", approved),
            )
    connection.execute(
        "INSERT INTO projects (id, name, topic, cefr_level, duration_minutes, num_speakers, genre, accent, status, "
        "created_at, updated_at) VALUES ('p1', 'Demo', 'Mornings', 'B1', 5, 2, 'small_talk', 'american', 'draft', 'now', 'now')"
    )
    for index, (name, speed) in enumerate((("Alex", 1.1), ("Maya", 0.9))):
        connection.execute(
            "INSERT INTO speakers (id, project_id, speaker_index, name, gender, accent, tts_engine, speed) "
            "VALUES (?, 'p1', ?, ?, ?, 'american', 'edge_tts', ?)",
            (f"s{index}", index, name, "male" if index == 0 else "female", speed),
        )
    connection.execute("INSERT INTO project_cast (project_id, speaker_index, character_id) VALUES ('p1', 0, ?)", (ALEX,))
    connection.execute("INSERT INTO project_cast (project_id, speaker_index, character_id) VALUES ('p1', 1, ?)", (LINA,))
    connection.commit()
    return connection


def test_migration_018_keeps_ids_assets_cast_and_speaker_voices(tmp_path):
    with closing(_old_database(tmp_path / "old.db")) as connection:
        speakers_before = connection.execute("SELECT * FROM speakers ORDER BY speaker_index").fetchall()
        _apply(connection, only=MIGRATION_018)

        profiles = connection.execute(
            "SELECT id, name, normalized_name, sprite_facing, is_seed, identity_version FROM characters ORDER BY name"
        ).fetchall()
        assert profiles == [(ALEX, "Alex", "alex", "right", 1, 1), (LINA, "Lina", "lina", "left", 1, 1)]
        assert connection.execute("SELECT * FROM speakers ORDER BY speaker_index").fetchall() == speakers_before
        assert connection.execute(
            "SELECT project_id, speaker_index, character_id, profile_version FROM project_cast ORDER BY speaker_index"
        ).fetchall() == [("p1", 0, ALEX, 1), ("p1", 1, LINA, 1)]
        assets = connection.execute(
            "SELECT kind, slot_key, review_state, facing, is_current FROM character_assets WHERE character_id = ? ORDER BY kind",
            (LINA,),
        ).fetchall()
        assert assets == [("candidate", None, "needs_review", "native", 1),
                          ("full_body", "full_body", "approved", "native", 1),
                          ("portrait_smile", "portrait_smile", "approved", "native", 1)]
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_rebuilt_cast_refuses_a_duplicate_character_and_restricts_delete(tmp_path):
    with closing(_old_database(tmp_path / "old.db")) as connection:
        _apply(connection, only=MIGRATION_018)
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("UPDATE project_cast SET character_id = ? WHERE speaker_index = 0", (LINA,))
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("DELETE FROM characters WHERE id = ?", (ALEX,))


def test_active_names_are_unique_but_archived_names_are_free(tmp_path):
    with closing(sqlite3.connect(tmp_path / "fresh.db")) as connection:
        _apply(connection)
        _character(connection, "a", "Alex", "male")
        connection.execute("UPDATE characters SET normalized_name = 'alex' WHERE id = 'a'")
        _character(connection, "b", "ALEX ", "male")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("UPDATE characters SET normalized_name = 'alex' WHERE id = 'b'")
        connection.execute("UPDATE characters SET archived_at = 'now' WHERE id = 'a'")
        connection.execute("UPDATE characters SET normalized_name = 'alex' WHERE id = 'b'")


def _input(name: str, gender: str = "male") -> CharacterInput:
    return CharacterInput.model_validate({
        "name": name, "gender": gender, "age_group": "adult", "ethnicity": "Russian", "role": "host", "hair": "brown",
        "eyes": "brown", "extra": "", "top_color": "navy blue", "top_item": "suit jacket", "bottom_color": "navy blue",
        "bottom_item": "suit trousers",
    })


@pytest.mark.asyncio
async def test_service_refuses_duplicate_names_and_sets_facing(db):
    alex = await library_service.create_character(db, _input("Alex"))
    lina = await library_service.create_character(db, _input("Lina", "female"))
    assert (alex["normalized_name"], alex["sprite_facing"]) == ("alex", "right")
    assert lina["sprite_facing"] == "left"
    with pytest.raises(ConflictError):
        await library_service.create_character(db, _input("  alex "))
    with pytest.raises(ConflictError):
        await library_service.edit_character(db, lina["id"], library_service.CharacterPatch(name="ALEX"))
    renamed = await library_service.edit_character(db, lina["id"], library_service.CharacterPatch(name="Lena"))
    assert renamed["normalized_name"] == "lena"


@pytest.mark.asyncio
async def test_set_cast_refuses_the_same_character_twice(db, monkeypatch):
    character = await library_service.create_character(db, _input("Alex"))
    await db.execute("UPDATE characters SET status = 'locked' WHERE id = ?", (character["id"],))

    async def two_speakers(_db, _project_id):
        return {"speakers": [{"speaker_index": 0}, {"speaker_index": 1}]}

    monkeypatch.setattr(project_visuals_service.project_service, "get_project", two_speakers)
    with pytest.raises(ValidationError):
        await project_visuals_service.set_cast(db, "p1", [
            {"speaker_index": 0, "character_id": character["id"]},
            {"speaker_index": 1, "character_id": character["id"]},
        ])


def test_legacy_sprites_register_once_as_approved_native_assets(tmp_path):
    data_dir = tmp_path / "data"
    folder = data_dir / "library" / "sprites" / ALEX
    folder.mkdir(parents=True)
    for name in ("calm__closed", "calm__open"):
        Image.new("RGBA", (8, 8)).save(folder / f"{name}.png")
    (folder / "sprite_set.json").write_text(json.dumps({"pictures": {"calm__closed": {}, "calm__open": {}, "gone": {}}}))
    with closing(sqlite3.connect(tmp_path / "fresh.db")) as connection:
        _apply(connection)
        _character(connection, ALEX, "Alex", "male")
        assert register_legacy_sprites(connection, data_dir) == 2  # "gone" has no file and is skipped
        assert register_legacy_sprites(connection, data_dir) == 0
        rows = connection.execute(
            "SELECT kind, slot_key, review_state, source, facing, path FROM character_assets ORDER BY slot_key"
        ).fetchall()
    assert [row[:5] for row in rows] == [("sprite", "sprite/calm__closed", "approved", "legacy_migration", "native"),
                                        ("sprite", "sprite/calm__open", "approved", "legacy_migration", "native")]
    assert rows[0][5].replace("\\", "/") == f"data/library/sprites/{ALEX}/calm__closed.png"


@pytest.mark.asyncio
async def test_app_runner_applies_018_once_and_survives_a_restart(tmp_path, monkeypatch):
    from backend.db import database

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    for _ in range(2):  # a second start must not re-run the ALTERs
        database.Database._instance = None
        await database.init_db()
        await database.Database.instance().close()
    database.Database._instance = None
    with closing(sqlite3.connect(tmp_path / "app.db")) as connection:
        applied = connection.execute("SELECT COUNT(*) FROM schema_migrations WHERE filename = ?", (MIGRATION_018,)).fetchone()
        columns = {row[1] for row in connection.execute("PRAGMA table_info(project_cast)")}
    assert applied == (1,)
    assert "profile_version" in columns


def test_migration_020_fills_quick_profile_fields_for_older_characters(tmp_path):
    with closing(_old_database(tmp_path / "old.db")) as connection:
        connection.execute("UPDATE characters SET hair = 'long dark brown hair', eyes = 'brown eyes', extra = 'fair skin', "
                           "top_color = 'white', top_item = 'mini dress', bottom_color = 'white', bottom_item = 'mini dress' "
                           "WHERE id = ?", (LINA,))
        _apply(connection, only=MIGRATION_018)
        _apply(connection, only="019_character_quick_profile.sql")
        _apply(connection, only="020_backfill_legacy_profiles.sql")
        lina = connection.execute(
            "SELECT appearance, outfit, default_accent, default_voice_id FROM characters WHERE id = ?", (LINA,)).fetchone()
        alex = connection.execute("SELECT outfit, default_voice_id FROM characters WHERE id = ?", (ALEX,)).fetchone()
    assert lina == ("long dark brown hair, brown eyes, fair skin", "white mini dress", "american", "en-US-JennyNeural")
    assert alex == ("navy suit jacket and navy suit trousers", "en-US-GuyNeural")


@pytest.mark.asyncio
async def test_startup_registers_legacy_sprite_packs_once_and_reads_old_relative_paths(db, tmp_path, monkeypatch):
    from backend.library import character_asset_service as assets

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path / "data")
    character = await library_service.create_character(db, _input("Alex"))
    folder = tmp_path / "data" / "library" / "sprites" / character["id"]
    folder.mkdir(parents=True)
    for name in ("calm__closed", "calm__open"):
        Image.new("RGBA", (8, 8)).save(folder / f"{name}.png")
    (folder / "sprite_set.json").write_text(json.dumps({"pictures": {"calm__closed": {}, "calm__open": {}}}))
    assert await assets.register_legacy_sprites(db) == 2
    assert await assets.register_legacy_sprites(db) == 0
    old = assets.stored_path(r"data\library\characters\x\full_body.png")
    assert old == tmp_path / "data" / "library" / "characters" / "x" / "full_body.png"
    assert assets.stored_path(str(folder / "calm__open.png")) == folder / "calm__open.png"
