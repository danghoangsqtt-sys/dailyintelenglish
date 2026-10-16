"""Desktop identity must distinguish trials and databases without leaking paths."""

import json
import sys

import pytest
from fastapi.testclient import TestClient

from backend.core import build_info


@pytest.fixture(autouse=True)
def clear_identity_cache():
    build_info.get_build_info.cache_clear()
    yield
    build_info.get_build_info.cache_clear()


def test_packaged_identity_changes_for_same_version_rebuild(monkeypatch, tmp_path):
    exe = tmp_path / "Studio.exe"
    exe.write_bytes(b"first code")
    metadata = {"version": "1.4.0-rc.1", "source_commit": "abc", "source_dirty": True}
    (tmp_path / "build-info.json").write_text(json.dumps(metadata))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))
    first = build_info.get_build_info()
    exe.write_bytes(b"new code")
    build_info.get_build_info.cache_clear()
    second = build_info.get_build_info()
    assert first["version"] == second["version"]
    assert first["build_id"] != second["build_id"]
    assert second["source_dirty"]


def test_database_identity_is_separate_and_private(tmp_path):
    first = build_info.get_instance_info(tmp_path / "one")
    second = build_info.get_instance_info(tmp_path / "two")
    assert first["build_id"] == second["build_id"]
    assert first["instance_id"] != second["instance_id"]
    assert str(tmp_path) not in json.dumps(first)


def test_build_endpoint_reports_running_instance(monkeypatch, tmp_path):
    from backend.core.config import settings
    from backend.main import app

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with TestClient(app) as client:
        payload = client.get("/api/system/build").json()
    assert payload["success"]
    assert payload["data"] == build_info.get_instance_info(tmp_path)
