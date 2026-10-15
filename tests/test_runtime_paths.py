"""Bundled read-only assets and linked compute runtimes must resolve separately."""

import sys
from pathlib import Path

import pytest

from backend.core import paths


def test_source_runtime_default_is_the_repository(monkeypatch):
    monkeypatch.delenv("DIE_WORKSPACE_DIR", raising=False)
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    assert paths.get_runtime_root() == Path(__file__).resolve().parents[1]


def test_frozen_assets_stay_bundled_while_compute_uses_the_linked_workspace(monkeypatch, tmp_path):
    bundled = tmp_path / "_internal"
    workspace = tmp_path / "workspace"
    (workspace / "renderer").mkdir(parents=True)
    (workspace / "renderer/package.json").write_text("{}")
    (workspace / "backend/ai/image").mkdir(parents=True)
    (workspace / "backend/ai/image/image_worker.py").write_text("")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundled), raising=False)
    monkeypatch.setenv("DIE_WORKSPACE_DIR", str(workspace))
    assert paths.get_project_root() == bundled
    assert paths.get_runtime_root() == workspace


def test_invalid_explicit_workspace_fails_clearly(monkeypatch, tmp_path):
    monkeypatch.setenv("DIE_WORKSPACE_DIR", str(tmp_path))
    with pytest.raises(RuntimeError, match="DIE_WORKSPACE_DIR"):
        paths.get_runtime_root()
