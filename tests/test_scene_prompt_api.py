"""Task 73.4: persisted prompts and safe external background imports, without a GPU."""

import asyncio
import sqlite3
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image, PngImagePlugin

from backend.ai.image import recipes
from backend.core.config import settings
from backend.core.exceptions import ProviderUnavailableError
from backend.db import transactions
from backend.library import library_service as library, scene_prompts
from tests.test_visuals_project_api import client, data  # noqa: F401


SCENE = {
    "name": "Riverside cafe", "place": "a quiet riverside cafe", "staging": "seated", "category": "food",
    "time_of_day": "night", "source_request": "Quán cà phê ven sông vào tối mưa",
    "image_prompt": "A wide riverside cafe interior with warm amber lamps and reflections from rain outside.",
}


def _image(image_format="PNG", size=(640, 480), color="blue"):
    output = BytesIO()
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("untrusted", "must not be copied")
    Image.new("RGB", size, color).save(output, format=image_format, pnginfo=metadata)
    return output.getvalue()


def _create(api_client, **fields):
    return data(api_client.post("/api/visuals/scenes", json={**SCENE, **fields}))


def _upload(api_client, scene_id, content=None, filename="background.png", mime="image/png"):
    return api_client.post(f"/api/visuals/scenes/{scene_id}/background", files={
        "file": (filename, _image() if content is None else content, mime),
    })


def _row(scene_id):
    with sqlite3.connect(settings.db_path) as connection:
        connection.row_factory = sqlite3.Row
        return dict(connection.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,)).fetchone())


def _assert_old_background(api_client, scene_id, before, preview):
    assert _row(scene_id) == before
    assert Path(before["preview_path"]).read_bytes() == preview
    assert api_client.get(f"/api/visuals/scenes/{scene_id}/preview").content == preview


def test_migration_backfills_existing_scene_prompts_without_changing_plate_or_archive():
    migrations = Path(__file__).resolve().parents[1] / "backend/db/migrations"
    with sqlite3.connect(":memory:") as connection:
        for path in sorted(migrations.glob("*.sql")):
            if path.name < "038_scene_prompts.sql":
                connection.executescript(path.read_text(encoding="utf-8"))
        connection.execute(
            "INSERT INTO scenes (id, name, place, staging, preview_path, archived_at, created_at, updated_at) "
            "VALUES ('old', 'Old scene', 'a quiet room', 'standing', 'old.png', 'archived', 'then', 'then')"
        )
        connection.executescript((migrations / "038_scene_prompts.sql").read_text(encoding="utf-8"))
        assert connection.execute(
            "SELECT source_request, image_prompt, preview_path, archived_at, updated_at FROM scenes"
        ).fetchone() == ("", "", "old.png", "archived", "then")


def test_prompt_fields_persist_duplicate_and_default_on_existing_rows(client):  # noqa: F811
    builtin = next(scene for scene in data(client.get("/api/visuals/scenes")) if scene["is_builtin"])
    assert builtin["source_request"] == builtin["image_prompt"] == ""
    scene = _create(client)
    assert scene["source_request"] == SCENE["source_request"] and scene["image_prompt"] == SCENE["image_prompt"]
    copied = data(client.post(f"/api/visuals/scenes/{scene['id']}/duplicate"))
    assert copied["id"] != scene["id"] and copied["preview_url"] is None
    assert copied["source_request"] == scene["source_request"] and copied["image_prompt"] == scene["image_prompt"]
    edited = data(client.patch(f"/api/visuals/scenes/{scene['id']}", json={
        "source_request": "A quiet library", "image_prompt": "Soft light through library windows.",
    }))
    assert edited["source_request"] == "A quiet library" and edited["image_prompt"] == "Soft light through library windows."
    stored = _row(scene["id"])
    assert stored["source_request"] == edited["source_request"] and stored["image_prompt"] == edited["image_prompt"]
    blank = _create(client, name="Legacy compatible", source_request="", image_prompt="")
    assert blank["source_request"] == blank["image_prompt"] == ""


@pytest.mark.parametrize("field,limit", [("source_request", 2000), ("image_prompt", 6000)])
def test_prompt_field_limits_on_create_patch_and_explicit_null(client, field, limit):  # noqa: F811
    scene = _create(client, **{field: "x" * limit})
    assert len(scene[field]) == limit
    assert client.post("/api/visuals/scenes", json={**SCENE, field: "x" * (limit + 1)}).status_code == 422
    base = f"/api/visuals/scenes/{scene['id']}"
    assert client.patch(base, json={field: "x" * (limit + 1)}).status_code == 422
    assert client.patch(base, json={field: None}).status_code == 422
    assert len(_row(scene["id"])[field]) == limit
    assert data(client.patch(base, json={field: ""}))[field] == ""


@pytest.mark.parametrize("patch,invalidates", [
    ({"source_request": "Updated request only"}, False),
    ({"name": "New display name", "category": "city"}, False),
    ({"image_prompt": SCENE["image_prompt"]}, False),
    ({"image_prompt": "A different carefully lit cafe interior."}, True),
    ({"image_prompt": ""}, True),
    ({"place": "a bright library"}, True),
    ({"time_of_day": "morning"}, True),
])
def test_only_effective_prompt_and_place_time_changes_invalidate_plate(client, patch, invalidates):  # noqa: F811
    scene = _create(client)
    data(_upload(client, scene["id"]))
    before = _row(scene["id"])
    updated = data(client.patch(f"/api/visuals/scenes/{scene['id']}", json=patch))
    assert (updated["preview_url"] is None) is invalidates
    assert Path(before["preview_path"]).is_file()
    if not invalidates:
        assert _row(scene["id"])["preview_path"] == before["preview_path"]


@pytest.mark.parametrize("brief", ["Quán cà phê ven sông", "A quiet riverside cafe"])
def test_prompt_drafting_delegates_to_module_outside_db_lock(client, monkeypatch, brief):  # noqa: F811
    async def generate(request):
        assert request == brief
        # A background worker can hold the lock; acquisition proves this request does not.
        async with asyncio.timeout(2):
            async with transactions.read_transaction():
                pass
        return {**SCENE, "source_request": request}

    monkeypatch.setattr(scene_prompts, "generate_scene_prompt", generate)
    drafted = data(client.post("/api/visuals/scenes/prompt", json={"brief": f"  {brief}  "}))
    assert drafted == {**SCENE, "source_request": brief}
    assert not any(scene["name"] == SCENE["name"] for scene in data(client.get("/api/visuals/scenes")))


@pytest.mark.parametrize("body", [{}, {"brief": ""}, {"brief": " \n\t "}, {"brief": "a" * 2001}, {"brief": None}])
def test_invalid_briefs_do_not_call_generator(client, monkeypatch, body):  # noqa: F811
    async def forbidden(brief):
        pytest.fail("Invalid briefs must be rejected before any provider call")

    monkeypatch.setattr(scene_prompts, "generate_scene_prompt", forbidden)
    response = client.post("/api/visuals/scenes/prompt", json=body)
    assert response.status_code == 422 and response.json()["success"] is False


def test_prompt_provider_error_preserves_saved_fields_and_plate(client, monkeypatch):  # noqa: F811
    scene = _create(client)
    data(_upload(client, scene["id"]))
    before = _row(scene["id"])
    preview = Path(before["preview_path"]).read_bytes()

    async def unavailable(brief):
        raise ProviderUnavailableError("Text provider unavailable")

    monkeypatch.setattr(scene_prompts, "generate_scene_prompt", unavailable)
    response = client.post("/api/visuals/scenes/prompt", json={"brief": "Another scene"})
    assert response.status_code == ProviderUnavailableError.status_code and "Text provider unavailable" in response.text
    _assert_old_background(client, scene["id"], before, preview)


def test_get_prompt_uses_shared_recipe_with_custom_and_default_prompts(client, monkeypatch):  # noqa: F811
    scene = _create(client)
    base = f"/api/visuals/scenes/{scene['id']}/prompt"
    assert data(client.get(base)) == {"prompt": recipes.qwen_scene_prompt(_row(scene["id"]))}
    assert SCENE["image_prompt"] in data(client.get(base))["prompt"]
    data(client.patch(f"/api/visuals/scenes/{scene['id']}", json={"image_prompt": ""}))
    assert data(client.get(base)) == {"prompt": recipes.qwen_scene_prompt(_row(scene["id"]))}
    calls = []

    def recipe(row):
        calls.append(row["id"])
        return "Recipe sentinel"

    monkeypatch.setattr(recipes, "qwen_scene_prompt", recipe)
    assert data(client.get(base)) == {"prompt": "Recipe sentinel"} and calls == [scene["id"]]


@pytest.mark.parametrize("image_format,suffix,mime", [
    ("PNG", "png", "image/png"), ("JPEG", "jpg", "image/jpeg"), ("WEBP", "webp", "image/webp"),
])
def test_upload_decodes_reencodes_crops_and_uses_versioned_safe_paths(client, monkeypatch, image_format, suffix, mime):  # noqa: F811
    monkeypatch.setattr(settings, "AI_VISUALS_ENABLED", False)
    scene = _create(client)
    scene_id = scene["id"]
    response = _upload(client, scene_id, _image(image_format, (360, 640)), f"../../outside.{suffix}", mime)
    uploaded = data(response)
    stored = _row(scene_id)
    target = Path(stored["preview_path"])
    assert target.parent == (settings.DATA_DIR / "library/scenes" / scene_id).resolve()
    assert target.name.startswith("background-") and target.suffix == ".png" and len(target.stem) == 43
    assert not (settings.DATA_DIR / "outside.png").exists()
    with Image.open(target) as image:
        assert image.format == "PNG" and image.size == (1280, 720) and image.mode == "RGB"
        assert "untrusted" not in image.info
    preview = client.get(uploaded["preview_url"])
    assert preview.status_code == 200 and preview.headers["content-type"] == "image/png"
    replacement = data(_upload(client, scene_id, _image(color="red")))
    second = Path(_row(scene_id)["preview_path"])
    assert second != target and second.is_file() and target.is_file()
    assert replacement["preview_url"] != uploaded["preview_url"]
    assert stored["source_request"] == scene["source_request"] and stored["image_prompt"] == scene["image_prompt"]


@pytest.mark.parametrize("content,filename", [
    (b"", "empty.png"), (b"not an image", "broken.png"), (_image("GIF"), "disguised.png"),
    (_image(), "picture.svg"), (_image()[:40], "truncated.png"),
])
def test_upload_invalid_types_and_data_preserve_existing_background(client, content, filename):  # noqa: F811
    scene = _create(client)
    data(_upload(client, scene["id"]))
    before = _row(scene["id"])
    preview = Path(before["preview_path"]).read_bytes()
    response = _upload(client, scene["id"], content, filename)
    assert response.status_code == 422 and response.json()["success"] is False
    _assert_old_background(client, scene["id"], before, preview)
    assert len(list(Path(before["preview_path"]).parent.glob("*.png"))) == 1


@pytest.mark.parametrize("limit", ["bytes", "pixels", "pillow"])
def test_upload_limits_preserve_existing_background(client, monkeypatch, limit):  # noqa: F811
    scene = _create(client)
    data(_upload(client, scene["id"]))
    before = _row(scene["id"])
    preview = Path(before["preview_path"]).read_bytes()
    if limit == "bytes":
        monkeypatch.setattr(library, "_SCENE_MAX_UPLOAD_BYTES", 128)
    elif limit == "pixels":
        monkeypatch.setattr(library, "_SCENE_MAX_PIXELS", 100)
    else:
        monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100)
    response = _upload(client, scene["id"])
    assert response.status_code == 422
    _assert_old_background(client, scene["id"], before, preview)


def test_file_write_failure_keeps_old_file_and_database_and_cleans_partial(client, monkeypatch):  # noqa: F811
    scene = _create(client)
    data(_upload(client, scene["id"]))
    before = _row(scene["id"])
    preview = Path(before["preview_path"]).read_bytes()

    def fail_write(target, content):
        target.write_bytes(b"partial")
        raise OSError("disk full")

    monkeypatch.setattr(library, "_write_scene_background", fail_write)
    response = _upload(client, scene["id"])
    assert response.status_code == 500 and "previous background was kept" in response.text
    _assert_old_background(client, scene["id"], before, preview)
    assert list(Path(before["preview_path"]).parent.glob("*.png")) == [Path(before["preview_path"])]


def test_database_commit_failure_rolls_back_and_cleans_new_file(client, monkeypatch):  # noqa: F811
    import aiosqlite

    scene = _create(client)
    data(_upload(client, scene["id"]))
    before = _row(scene["id"])
    preview = Path(before["preview_path"]).read_bytes()

    async def fail_commit(connection):
        raise aiosqlite.OperationalError("commit failed")

    monkeypatch.setattr(aiosqlite.Connection, "commit", fail_commit)
    response = _upload(client, scene["id"])
    assert response.status_code == 500 and "previous background was kept" in response.text
    _assert_old_background(client, scene["id"], before, preview)
    assert list(Path(before["preview_path"]).parent.glob("*.png")) == [Path(before["preview_path"])]


def test_missing_archived_and_missing_file_errors_are_clear(client):  # noqa: F811
    assert client.get("/api/visuals/scenes/missing/prompt").status_code == 404
    assert _upload(client, "missing").status_code == 404
    assert client.patch("/api/visuals/scenes/missing", json={"image_prompt": "test"}).status_code == 404
    scene = _create(client)
    data(_upload(client, scene["id"]))
    data(client.post(f"/api/visuals/scenes/{scene['id']}/archive"))
    before = _row(scene["id"])
    preview = Path(before["preview_path"]).read_bytes()
    assert _upload(client, scene["id"]).status_code == 409
    assert client.patch(f"/api/visuals/scenes/{scene['id']}", json={"image_prompt": "test"}).status_code == 409
    assert client.post(f"/api/visuals/scenes/{scene['id']}/background").status_code == 422
    assert data(client.get(f"/api/visuals/scenes/{scene['id']}/prompt"))["prompt"]
    _assert_old_background(client, scene["id"], before, preview)
    data(client.post(f"/api/visuals/scenes/{scene['id']}/restore"))
    assert data(_upload(client, scene["id"]))["preview_url"]


@pytest.mark.parametrize("change", ["archive", "edit"])
def test_concurrent_scene_changes_during_file_write_reject_swap(client, monkeypatch, change):  # noqa: F811
    scene = _create(client)
    data(_upload(client, scene["id"]))
    before = _row(scene["id"])
    preview = Path(before["preview_path"]).read_bytes()
    original_write = library._write_scene_background

    def change_scene(target, content):
        original_write(target, content)
        with sqlite3.connect(settings.db_path) as connection:
            if change == "archive":
                connection.execute("UPDATE scenes SET archived_at = 'now' WHERE id = ?", (scene["id"],))
            else:
                connection.execute("UPDATE scenes SET updated_at = 'newer' WHERE id = ?", (scene["id"],))

    monkeypatch.setattr(library, "_write_scene_background", change_scene)
    response = _upload(client, scene["id"])
    assert response.status_code == 409
    after = _row(scene["id"])
    assert after["preview_path"] == before["preview_path"]
    assert Path(before["preview_path"]).read_bytes() == preview
    assert list(Path(before["preview_path"]).parent.glob("*.png")) == [Path(before["preview_path"])]


async def test_scene_upload_stream_is_bounded_and_closed():
    class OversizedStream:
        filename = "huge.png"
        closed = False
        reads = 0

        async def read(self, size):
            self.reads += 1
            assert size == library._SCENE_UPLOAD_CHUNK_BYTES
            return b"x" * size

        async def close(self):
            self.closed = True

    stream = OversizedStream()
    from backend.core.exceptions import ValidationError

    with pytest.raises(ValidationError, match="20 MB"):
        await library.read_scene_upload(stream)
    assert stream.closed and stream.reads == 21


async def test_upload_refuses_unsafe_stored_scene_id(db, tmp_path, monkeypatch):
    from starlette.datastructures import UploadFile

    from backend.core.exceptions import ValidationError
    from backend.schemas.visuals import SceneInput

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    scene = await library.create_scene(db, SceneInput.model_validate(SCENE))
    await db.execute("UPDATE scenes SET id = '../outside' WHERE id = ?", (scene["id"],))
    await db.commit()
    upload = UploadFile(BytesIO(_image()), filename="safe.png")
    with pytest.raises(ValidationError, match="storage path"):
        await library.upload_scene_background(db, "../outside", upload)
    assert upload.file.closed
    assert not (tmp_path / "library/outside").exists()
