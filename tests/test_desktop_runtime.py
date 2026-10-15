"""Frozen desktop boot must select paths before importing application settings."""

import json
import os
import subprocess
import sys

import pytest

from backend.core.desktop_runtime import configure_desktop_runtime


def frozen(monkeypatch, tmp_path, values):
    monkeypatch.chdir(os.getcwd())  # restore cwd after the real bootstrap changes it
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    directory = tmp_path / "dist" / "Studio"
    directory.mkdir(parents=True)
    monkeypatch.setattr(sys, "executable", str(directory / "Studio.exe"))
    (directory / "studio-runtime.json").write_text(json.dumps(values), encoding="utf-8")
    for name in ("DIE_WORKSPACE_DIR", "DIE_DATA_DIR"):
        monkeypatch.delenv(name, raising=False)
    return directory


def test_frozen_locator_is_relative_to_exe_not_cwd(monkeypatch, tmp_path):
    frozen(monkeypatch, tmp_path, {"workspace_dir": "../..", "data_dir": "../../data"})
    monkeypatch.chdir(tmp_path.parent)
    configure_desktop_runtime()
    assert os.environ["DIE_WORKSPACE_DIR"] == str(tmp_path)
    assert os.environ["DIE_DATA_DIR"] == str(tmp_path / "data")
    assert os.getcwd() == str(tmp_path)


def test_explicit_environment_overrides_the_local_locator(monkeypatch, tmp_path):
    frozen(monkeypatch, tmp_path, {"workspace_dir": "../..", "data_dir": "../../data"})
    monkeypatch.setenv("DIE_DATA_DIR", str(tmp_path / "isolated-smoke"))
    configure_desktop_runtime()
    assert os.environ["DIE_DATA_DIR"] == str(tmp_path / "isolated-smoke")


@pytest.mark.parametrize("values", [{"data_dir": 1}, {"data_dir": ""}, {"unexpected": "x"}, []])
def test_invalid_locator_stops_instead_of_using_another_database(monkeypatch, tmp_path, values):
    frozen(monkeypatch, tmp_path, values)
    with pytest.raises(ValueError):
        configure_desktop_runtime()


def test_source_launch_does_not_consume_exe_configuration(monkeypatch, tmp_path):
    frozen(monkeypatch, tmp_path, {"data_dir": "another"})
    monkeypatch.setattr(sys, "frozen", False)
    configure_desktop_runtime()
    assert "DIE_DATA_DIR" not in os.environ


def test_launcher_import_defers_application_settings_and_workers():
    result = subprocess.run([sys.executable, "-c", "import sys; import backend.desktop_launcher; assert 'backend.main' not in sys.modules; assert 'backend.core.config' not in sys.modules"],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
