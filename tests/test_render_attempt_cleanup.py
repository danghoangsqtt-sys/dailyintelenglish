"""BUG-054: a render that a newer one replaced as current does not stay on disk forever; nothing else is ever removed."""

import shutil
import uuid

from backend.media import video_service


def _attempt(root, name=None, files=("video_remotion.mp4", "subtitles.srt", "video_remotion.render-1.log")):
    folder = root / (name or uuid.uuid4().hex)
    folder.mkdir(parents=True)
    for file in files:
        (folder / file).write_bytes(b"x")
    return folder


def test_the_replaced_attempt_folder_is_removed_and_the_current_one_kept(tmp_path):
    old, new = _attempt(tmp_path), _attempt(tmp_path)
    assert video_service.remove_superseded_attempt(str(old / "video_remotion.mp4"), tmp_path,
                                                   [str(new / "video_remotion.mp4"), str(new / "subtitles.srt")])
    assert not old.exists() and (new / "video_remotion.mp4").is_file()


def test_a_folder_still_referenced_is_kept(tmp_path):
    old = _attempt(tmp_path, files=("video_remotion.mp4", "video_vertical.mp4"))
    # the horizontal video changed, the vertical one in the same folder is still current
    assert not video_service.remove_superseded_attempt(str(old / "video_remotion.mp4"), tmp_path,
                                                       [str(tmp_path / "x" / "new.mp4"), str(old / "video_vertical.mp4")])
    assert old.is_dir()


def test_only_attempt_folders_directly_inside_the_root_are_touched(tmp_path):
    named = _attempt(tmp_path, "edge-sync-004f489d014849f0a6fe2cedbbe2a431")  # a folder made by hand
    elsewhere = _attempt(tmp_path / "other")  # an attempt folder, but not in this project's root
    for folder in (named, elsewhere):
        assert not video_service.remove_superseded_attempt(str(folder / "video_remotion.mp4"), tmp_path, [])
        assert folder.is_dir()
    assert not video_service.remove_superseded_attempt(None, tmp_path, [])
    assert not video_service.remove_superseded_attempt(str(tmp_path / "a.mp4"), tmp_path, [])  # the root itself


def test_a_file_still_open_leaves_the_folder_for_next_time(tmp_path, monkeypatch):
    old = _attempt(tmp_path)

    def locked(path):
        raise PermissionError(32, "The process cannot access the file because it is being used by another process")

    monkeypatch.setattr(shutil, "rmtree", locked)
    assert not video_service.remove_superseded_attempt(str(old / "video_remotion.mp4"), tmp_path, [])
    assert old.is_dir()
