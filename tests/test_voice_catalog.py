"""Catalog behavior is tested offline; no production DATA_DIR or Edge requests."""

import asyncio
import json

import pytest

from backend.ai.tts import voice_catalog_service as catalog
from backend.core.config import settings
from backend.core.exceptions import TTSError, ValidationError

ROWS = [
    {"ShortName": "en-US-GuyNeural", "Locale": "en-US", "Gender": "Male"},
    {"ShortName": "en-US-AndrewNeural", "Locale": "en-US", "Gender": "Male", "FriendlyName": "Andrew"},
    {"ShortName": "en-GB-SoniaNeural", "Locale": "en-GB", "Gender": "Female"},
    {"ShortName": "vi-VN-HoaiMyNeural", "Locale": "vi-VN", "Gender": "Female"},
]


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)

    async def fetch():
        return ROWS

    monkeypatch.setattr(catalog.edge_tts, "list_voices", fetch)
    return tmp_path


@pytest.mark.asyncio
async def test_catalog_filters_english_normalizes_optional_fields_and_caches(isolated, monkeypatch):
    result = await catalog.get_catalog()
    assert len(result["voices"]) == 3 and result["stale"] is False
    assert result["fetched_at"]
    assert all(v["engine"] == "edge_tts" for v in result["voices"])

    async def forbidden():
        raise AssertionError("Fresh catalog must not refetch")

    monkeypatch.setattr(catalog.edge_tts, "list_voices", forbidden)
    filtered = await catalog.get_catalog(locale="en-us", gender="male", q="andrew")
    assert [v["voice_id"] for v in filtered["voices"]] == ["en-US-AndrewNeural"]
    assert (isolated / "tts_voice_catalog.json").is_file()


@pytest.mark.asyncio
async def test_failed_refresh_retains_and_labels_last_good_catalog(isolated, monkeypatch):
    original = await catalog.get_catalog()
    path = isolated / "tts_voice_catalog.json"
    before = path.read_bytes()

    async def offline():
        raise ConnectionError("offline")

    monkeypatch.setattr(catalog.edge_tts, "list_voices", offline)
    result = await catalog.get_catalog(refresh=True)
    assert result["stale"] and result["voices"] == original["voices"]
    assert path.read_bytes() == before


@pytest.mark.asyncio
async def test_expired_cache_refreshes_from_provider(isolated, monkeypatch):
    await catalog.get_catalog()
    path = isolated / "tts_voice_catalog.json"
    value = json.loads(path.read_text())
    value["fetched_at"] = 0
    path.write_text(json.dumps(value))

    async def newer():
        return ROWS[:1]

    monkeypatch.setattr(catalog.edge_tts, "list_voices", newer)
    assert len((await catalog.get_catalog())["voices"]) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("rows", [[], {}, [{"ShortName": "vi-VN-HoaiMyNeural", "Locale": "vi-VN"}]])
async def test_invalid_provider_data_without_cache_is_visible_failure(isolated, monkeypatch, rows):
    async def broken():
        return rows

    monkeypatch.setattr(catalog.edge_tts, "list_voices", broken)
    with pytest.raises(TTSError, match="voice list is unavailable"):
        await catalog.get_catalog()
    assert not (isolated / "tts_voice_catalog.json").exists()


@pytest.mark.asyncio
async def test_timeout_without_cache_and_corrupt_cache_do_not_fake_success(isolated, monkeypatch):
    (isolated / "tts_voice_catalog.json").write_text("not-json")
    monkeypatch.setattr(catalog, "VOICE_CATALOG_TIMEOUT_SECONDS", 0.01)

    async def stuck():
        await asyncio.Event().wait()

    monkeypatch.setattr(catalog.edge_tts, "list_voices", stuck)
    with pytest.raises(TTSError):
        await catalog.get_catalog()


@pytest.mark.asyncio
async def test_concurrent_catalog_reads_coalesce_refresh(isolated, monkeypatch):
    calls = 0

    async def fetch():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        return ROWS

    monkeypatch.setattr(catalog.edge_tts, "list_voices", fetch)
    values = await asyncio.gather(*(catalog.get_catalog() for _ in range(3)))
    assert calls == 1 and values[0] == values[1] == values[2]


@pytest.mark.asyncio
@pytest.mark.parametrize("voice_id", ["vi-VN-HoaiMyNeural", "en-US-UnknownNeural", "../secret", ""])
async def test_unknown_or_non_english_voice_is_rejected(isolated, voice_id):
    with pytest.raises(ValidationError):
        await catalog.require_voice(voice_id)
