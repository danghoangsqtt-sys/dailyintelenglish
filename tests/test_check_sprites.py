"""Phase 32: the sprite pack checker (scripts/check_sprites.py) on synthetic pictures."""

import importlib.util
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check_sprites.py"


@pytest.fixture(scope="module")
def checker():
    spec = importlib.util.spec_from_file_location("check_sprites", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _figure(path: Path, head_dx=0, torso_dx=0, size=(1280, 1536)) -> None:
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((500 + head_dx, 100, 780 + head_dx, 380), fill=(200, 160, 140, 255))  # the head
    draw.rectangle((380 + torso_dx, 380, 900 + torso_dx, 1535), fill=(20, 30, 100, 255))  # the torso to the bottom edge
    image.save(path)


def _run(checker, folder: Path, monkeypatch, name="alex") -> int:
    monkeypatch.setattr("sys.argv", ["check_sprites.py", name, "--folder", str(folder)])
    return checker.main()


def test_an_aligned_pack_passes(checker, tmp_path, monkeypatch, capsys):
    _figure(tmp_path / "alex__calm__closed.png")
    _figure(tmp_path / "alex__smile__open.png")
    _figure(tmp_path / "alex__gesture-talk.png")
    assert _run(checker, tmp_path, monkeypatch) == 0
    assert "0 picture(s) failed" in capsys.readouterr().out


def test_a_moved_torso_a_moved_head_and_a_wrong_canvas_fail(checker, tmp_path, monkeypatch, capsys):
    _figure(tmp_path / "alex__calm__closed.png")
    _figure(tmp_path / "alex__smile__open.png", torso_dx=40)  # the body slid sideways
    _figure(tmp_path / "alex__laugh__open.png", head_dx=60)  # the head moved
    Image.new("RGBA", (1000, 1000)).save(tmp_path / "alex__blink.png")  # wrong canvas
    assert _run(checker, tmp_path, monkeypatch) == 1
    out = capsys.readouterr().out
    assert "torso moved" in out and "wrong canvas size" in out and "3 picture(s) failed" in out


def test_a_missing_reference_is_reported(checker, tmp_path, monkeypatch, capsys):
    assert _run(checker, tmp_path, monkeypatch, name="lina") == 1
    assert "missing" in capsys.readouterr().out
