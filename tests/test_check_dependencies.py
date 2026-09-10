"""Unit tests for scripts/check_dependencies.py — env-var source and configurable ffmpeg path."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "check_dependencies.py"


def _load_script_module():
    """Load check_dependencies.py as a module without running its __main__ block."""
    spec = importlib.util.spec_from_file_location("check_dependencies_under_test", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def check_deps():
    return _load_script_module()


def test_check_env_file_accepts_key_from_environment(check_deps, monkeypatch):
    monkeypatch.setattr(check_deps.settings, "GEMINI_API_KEY", "a-real-looking-key")

    passed, detail = check_deps.check_env_file()

    assert passed is True
    assert "DIE_GEMINI_API_KEY" in detail


def test_check_env_file_rejects_placeholder(check_deps, monkeypatch):
    monkeypatch.setattr(check_deps.settings, "GEMINI_API_KEY", check_deps.PLACEHOLDER_API_KEY)

    passed, _detail = check_deps.check_env_file()

    assert passed is False


def test_check_ffmpeg_uses_configured_path_not_hardcoded(check_deps, monkeypatch):
    monkeypatch.setattr(check_deps.settings, "FFMPEG_PATH", "totally-custom-ffmpeg-binary-xyz")

    passed, detail = check_deps.check_ffmpeg()

    assert passed is False
    assert "totally-custom-ffmpeg-binary-xyz" in detail


def test_check_ffmpeg_reports_default_path_when_unconfigured(check_deps, monkeypatch):
    monkeypatch.setattr(check_deps.settings, "FFMPEG_PATH", "ffmpeg")

    passed, detail = check_deps.check_ffmpeg()

    if not passed:
        assert "ffmpeg" in detail
