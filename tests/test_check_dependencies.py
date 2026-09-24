"""Unit tests for scripts/check_dependencies.py — cloud provider status and configurable ffmpeg path."""

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


def test_check_cloud_provider_reports_configured_with_model(check_deps, monkeypatch):
    monkeypatch.setattr(check_deps.settings, "OPENAI_COMPAT_API_KEY", "a-real-looking-key")
    monkeypatch.setattr(check_deps.settings, "OPENAI_COMPAT_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")

    passed, detail = check_deps.check_cloud_provider()

    assert passed is True
    assert "nvidia/nemotron-3-super-120b-a12b:free" in detail


def test_check_cloud_provider_reports_not_configured_without_a_key(check_deps, monkeypatch):
    monkeypatch.setattr(check_deps.settings, "OPENAI_COMPAT_API_KEY", "")

    passed, _detail = check_deps.check_cloud_provider()

    assert passed is False


def test_check_cloud_provider_reports_not_configured_without_a_model(check_deps, monkeypatch):
    monkeypatch.setattr(check_deps.settings, "OPENAI_COMPAT_API_KEY", "a-real-looking-key")
    monkeypatch.setattr(check_deps.settings, "OPENAI_COMPAT_MODEL", "")

    passed, _detail = check_deps.check_cloud_provider()

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
