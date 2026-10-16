"""Immutable illustration imports, project ownership, normalization and interrupted work."""
import asyncio
import io
import threading
from pathlib import Path

import pytest
from PIL import Image

from backend.content import project_service
from backend.core.config import settings
from backend.core.exceptions import NotFoundError, ValidationError
from backend.library import explainer_assets as assets
from backend.schemas.project import ScriptConfig
from tests.test_explainer_project import solo_config


def picture(size=(400, 300), mode="RGBA", fmt="PNG") -> bytes:
    buffer = io.BytesIO()
    Image.new(mode, size, 0).save(buffer, format=fmt)
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def isolated_images(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)


async def test_upload_is_immutable_project_scoped_and_hash_checked(db):
    project = await project_service.create_project(db, ScriptConfig(**solo_config()))
    pid = project["id"]
    first = await assets.stage_upload(pid, picture(), "first.png")
    published = await assets.publish(db, first)
    await db.commit()
    second = await assets.stage_upload(pid, picture((500, 350)), "second.png")
    await assets.publish(db, second)
    await db.commit()
    assert first["id"] != second["id"]
    assert len(await assets.list_assets(db, pid)) == 2
    assert "path" not in published and published["asset"]["content_hash"] == first["content_hash"]
    row = await assets.get_asset(db, pid, first["id"], 1)
    assert await assets.verified_path(row) == Path(first["path"])
    with pytest.raises(NotFoundError):
        await assets.get_asset(db, "another-project", first["id"], 1)
    with pytest.raises(NotFoundError):
        await assets.get_asset(db, pid, first["id"], 2)
    Path(first["path"]).write_bytes(b"changed outside the application")
    with pytest.raises(NotFoundError, match="changed"):
        await assets.verified_path(row)
    assert Path(second["path"]).is_file(), "invalidating one version must preserve another"
    await project_service.delete_project(db, pid)
    assert await assets.list_assets(db, pid) == []
    await project_service.cleanup_project_artifacts(pid)
    assert not Path(second["path"]).exists()


async def test_decode_normalizes_palette_transparency_and_bounds_output(monkeypatch):
    monkeypatch.setattr(assets, "EXPLAINER_IMAGE_RENDER_MAX_SIDE", 300)
    source = Image.new("P", (600, 400))
    source.info["transparency"] = 0
    buffer = io.BytesIO()
    source.save(buffer, "PNG")
    staged = await assets.stage_upload("project", buffer.getvalue(), "palette.png")
    with Image.open(staged["path"]) as result:
        assert result.format == "PNG" and result.mode == "RGBA"
        assert result.size == (300, 200) and result.getpixel((0, 0))[3] == 0
    await assets.discard(staged)
    assert not Path(staged["path"]).exists()


async def test_exif_orientation_is_applied_before_rendering():
    source = Image.new("RGB", (400, 300), "red")
    exif = Image.Exif()
    exif[274] = 6
    buffer = io.BytesIO()
    source.save(buffer, "JPEG", exif=exif)
    staged = await assets.stage_upload("project", buffer.getvalue(), "rotated.jpg")
    assert (staged["width"], staged["height"]) == (300, 400)
    with Image.open(staged["path"]) as result:
        assert not result.getexif().get(274), "EXIF must not rotate the normalized image again"


@pytest.mark.parametrize("content,filename", [
    (b"", "empty.png"), (b"not an image", "broken.png"),
    (picture((100, 100)), "tiny.png"), (picture(fmt="GIF"), "animation.gif"),
    (picture(), "../escape.png"), (picture(), "..\\escape.png"),
])
async def test_bad_imports_do_not_publish_files(content, filename):
    with pytest.raises(ValidationError):
        await assets.stage_upload("project", content, filename)
    assert not list(settings.DATA_DIR.rglob("*.png"))


async def test_payload_pixel_and_decompression_limits_are_enforced(monkeypatch):
    content = picture()
    monkeypatch.setattr(assets, "EXPLAINER_IMAGE_MAX_BYTES", len(content) - 1)
    with pytest.raises(ValidationError):
        await assets.stage_upload("project", content, "large.png")
    monkeypatch.setattr(assets, "EXPLAINER_IMAGE_MAX_BYTES", len(content) + 1)
    monkeypatch.setattr(assets, "EXPLAINER_IMAGE_MAX_PIXELS", 100_000)
    with pytest.raises(ValidationError):
        await assets.stage_upload("project", content, "pixels.png")
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100_000)
    with pytest.raises(ValidationError):
        await assets.stage_upload("project", content, "bomb.png")


async def test_path_confinement_checks_import_serve_and_cleanup(tmp_path):
    with pytest.raises(ValidationError):
        await assets.stage_upload("../escape", picture(), "image.png")
    outside = tmp_path / "outside.png"
    outside.write_bytes(picture())
    row = {"project_id": "project", "path": str(outside), "content_hash": "a" * 64}
    with pytest.raises(NotFoundError):
        await assets.verified_path(row)
    with pytest.raises(ValidationError):
        await assets.discard(row)
    assert outside.is_file()


async def test_live_mode_or_deleted_project_prevents_publish_and_attempt_can_be_cleaned(db):
    project = await project_service.create_project(db, ScriptConfig(**solo_config()))
    staged = await assets.stage_upload(project["id"], picture(), "image.png")
    await db.execute("UPDATE projects SET presentation_mode='classic',explainer_structure=NULL WHERE id=?", (project["id"],))
    with pytest.raises(ValidationError, match="Solo"):
        await assets.publish(db, staged)
    await project_service.delete_project(db, project["id"])
    with pytest.raises(NotFoundError):
        await assets.publish(db, staged)
    await assets.discard(staged)
    assert not Path(staged["path"]).exists()


async def test_cancelled_decode_finishes_cleanup_without_blocking_event_loop(monkeypatch):
    entered, release = threading.Event(), threading.Event()
    original = assets._stage_sync

    def slow(*args):
        entered.set()
        assert release.wait(5)
        return original(*args)

    monkeypatch.setattr(assets, "_stage_sync", slow)
    task = asyncio.create_task(assets.stage_upload("project", picture(), "cancel.png"))
    assert await asyncio.to_thread(entered.wait, 5)
    task.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not list(settings.DATA_DIR.rglob("*.png")), "cancelled background decode must not leak its completed file"
