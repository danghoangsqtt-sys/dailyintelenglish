"""Unit tests for app/services/avatar_service.py's pure/validation helpers (Task 1.7c)."""

import pytest

from app.core.exceptions import NotFoundError, ValidationError
from app.services import avatar_service


def test_validate_extension_accepts_png_and_jpeg():
    assert avatar_service._validate_extension("face.png") == ".png"
    assert avatar_service._validate_extension("face.JPG") == ".jpg"
    assert avatar_service._validate_extension("face.jpeg") == ".jpeg"


def test_validate_extension_rejects_unsupported_extension():
    with pytest.raises(ValidationError, match="PNG and JPEG"):
        avatar_service._validate_extension("face.gif")


def test_validate_magic_bytes_accepts_real_signatures():
    avatar_service._validate_magic_bytes(".png", b"\x89PNG\r\n\x1a\n" + b"rest")
    avatar_service._validate_magic_bytes(".jpg", b"\xff\xd8\xff" + b"rest")


def test_validate_magic_bytes_rejects_spoofed_content():
    with pytest.raises(ValidationError, match="valid image header"):
        avatar_service._validate_magic_bytes(".png", b"not-a-png")
    with pytest.raises(ValidationError, match="valid image header"):
        avatar_service._validate_magic_bytes(".jpg", b"not-a-jpeg")


def test_avatar_dir_is_scoped_per_project(tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    assert avatar_service._avatar_dir("proj-1") == tmp_path / "avatars" / "proj-1"


def test_finalize_avatar_file_does_not_touch_the_old_file(tmp_path, monkeypatch):
    """Task 10.1 (BUG-019): finalize must place the new upload under its own unique
    path without deleting the previous file -- that's the caller's job, only after
    the surrounding DB transaction has durably committed."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    avatar_dir = avatar_service._avatar_dir("proj-1")
    avatar_dir.mkdir(parents=True)
    old_file = avatar_dir / "sp1.png"
    old_file.write_bytes(b"old")
    temp_file = avatar_dir / ".upload"
    temp_file.write_bytes(b"new")

    final_path = avatar_service._finalize_avatar_file("proj-1", "sp1", ".jpg", temp_file)

    assert final_path.parent == avatar_dir
    assert final_path.name.startswith("sp1.")
    assert final_path.suffix == ".jpg"
    assert final_path != old_file
    assert final_path.read_bytes() == b"new"
    assert not temp_file.exists()
    assert old_file.exists()
    assert old_file.read_bytes() == b"old"


async def test_cleanup_previous_avatar_file_deletes_the_given_path(tmp_path):
    old_file = tmp_path / "sp1.abc123.png"
    old_file.write_bytes(b"old")

    await avatar_service.cleanup_previous_avatar_file(str(old_file))

    assert not old_file.exists()


async def test_cleanup_previous_avatar_file_is_a_noop_for_none_or_missing_path(tmp_path):
    await avatar_service.cleanup_previous_avatar_file(None)
    await avatar_service.cleanup_previous_avatar_file(str(tmp_path / "does-not-exist.png"))


def test_resolve_avatar_sync_rejects_path_outside_project_dir(tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    outside_file = tmp_path / "outside.png"
    outside_file.write_bytes(b"data")

    with pytest.raises(NotFoundError):
        avatar_service._resolve_avatar_sync("proj-1", str(outside_file))


def test_resolve_avatar_sync_rejects_missing_file(tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    avatar_dir = avatar_service._avatar_dir("proj-1")
    avatar_dir.mkdir(parents=True)

    with pytest.raises(NotFoundError):
        avatar_service._resolve_avatar_sync("proj-1", str(avatar_dir / "sp1.png"))
