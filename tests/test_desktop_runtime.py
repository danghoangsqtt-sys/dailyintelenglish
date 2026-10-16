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


@pytest.mark.parametrize("actual", [None, {}, {"product": "other"}, {"product": "studio", "build_id": "old", "instance_id": "owner"},
                                    {"product": "studio", "build_id": "new", "instance_id": "another-db"}])
def test_launcher_never_opens_old_unknown_or_other_database(monkeypatch, actual):
    from backend import desktop_launcher as launcher

    opened = []
    monkeypatch.setattr(launcher, "_read_running_instance", lambda url: actual)
    monkeypatch.setattr(launcher.webbrowser, "open", opened.append)
    with pytest.raises(RuntimeError, match="Finish any running jobs"):
        launcher._reuse_existing_instance("http://127.0.0.1:8000", {"product": "studio", "build_id": "new", "instance_id": "owner"})
    assert not opened


def test_second_click_and_readiness_only_open_matching_build(monkeypatch):
    from backend import desktop_launcher as launcher

    expected = {"product": "studio", "build_id": "new", "instance_id": "owner"}
    opened = []
    monkeypatch.setattr(launcher.webbrowser, "open", opened.append)
    monkeypatch.setattr(launcher, "_read_running_instance", lambda url: expected)
    launcher._reuse_existing_instance("http://127.0.0.1:8000", expected)
    replies = iter([None, {**expected, "build_id": "old"}, expected])
    monkeypatch.setattr(launcher, "_read_running_instance", lambda url: next(replies))
    monkeypatch.setattr(launcher.time, "sleep", lambda delay: None)
    launcher._open_browser_when_ready("http://127.0.0.1:8000", expected)
    assert opened == ["http://127.0.0.1:8000"] * 2


def test_readiness_timeout_does_not_open_competing_process(monkeypatch):
    from backend import desktop_launcher as launcher

    opened = []
    times = iter([0, 0, 2])
    monkeypatch.setattr(launcher.time, "monotonic", lambda: next(times))
    monkeypatch.setattr(launcher.time, "sleep", lambda delay: None)
    monkeypatch.setattr(launcher, "_read_running_instance", lambda url: {})
    monkeypatch.setattr(launcher.webbrowser, "open", opened.append)
    launcher._open_browser_when_ready("http://localhost:8000", {"product": "studio", "build_id": "new", "instance_id": "owner"}, timeout=1)
    assert not opened
