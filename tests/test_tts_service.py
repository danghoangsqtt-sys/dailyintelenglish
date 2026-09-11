"""Tests for TTSService (Task 1.6, Sub-task 1.6a — Edge-TTS-first).

No real network calls: `tts_service._synthesize_edge_tts` is monkeypatched with a fake
async function returning canned bytes, same pattern used for Gemini in
test_script_service.py. `_synthesize_omnivoice` is exercised directly to confirm it
always raises `_OmniVoiceUnavailableError` (honest not-yet-integrated state).
"""

import json

import pytest

from app.core.constants import ACCENTS, EDGE_TTS_VOICE_MAP, GENDERS
from app.core.exceptions import NotFoundError, TTSError
from app.models.project import ScriptConfig, SpeakerConfig
from app.services import project_service, tts_service

FAKE_MP3_BYTES = b"ID3-fake-mp3-bytes-for-tests"


@pytest.fixture(autouse=True)
def no_real_sleep(monkeypatch):
    """Edge TTS retry-on-empty-audio must not actually wait in tests."""

    async def fake_sleep(seconds: float) -> None:
        pass

    monkeypatch.setattr(tts_service.asyncio, "sleep", fake_sleep)


def make_config(**overrides) -> ScriptConfig:
    defaults = dict(
        name="TTS Test Episode",
        topic="Testing text to speech",
        cefr_level="B1",
        duration_minutes=5.0,
        num_speakers=1,
        genre="small_talk",
        accent="american",
        speakers=[SpeakerConfig(name="Alex", gender="male", accent="american")],
    )
    defaults.update(overrides)
    return ScriptConfig(**defaults)


async def _insert_line(db, project_id: str, speaker_id: str, line_id: str = "line-1", text: str = "Hello there.") -> dict:
    await db.execute(
        "INSERT INTO script_lines (id, project_id, line_index, speaker_id, text, language_notes) "
        "VALUES (?, ?, 0, ?, ?, ?)",
        (line_id, project_id, speaker_id, text, json.dumps(None)),
    )
    await db.commit()
    return {"id": line_id, "project_id": project_id, "speaker_id": speaker_id, "text": text}


async def test_synthesize_line_uses_edge_tts_when_engine_is_edge_tts(db, monkeypatch):
    project = await project_service.create_project(db, make_config())
    speaker = project["speakers"][0]
    line = await _insert_line(db, project["id"], speaker["id"])

    async def fake_edge_tts(text: str, spk: dict) -> bytes:
        assert text == "Hello there."
        return FAKE_MP3_BYTES

    monkeypatch.setattr(tts_service, "_synthesize_edge_tts", fake_edge_tts)

    result = await tts_service.synthesize_line(db, project, line)

    assert result["engine_used"] == "edge_tts"
    from pathlib import Path

    audio_path = Path(result["audio_path"])
    assert audio_path.exists()
    assert audio_path.read_bytes() == FAKE_MP3_BYTES
    audio_path.unlink()

    cursor = await db.execute("SELECT audio_cache_path FROM script_lines WHERE id = ?", (line["id"],))
    row = await cursor.fetchone()
    assert row["audio_cache_path"] == result["audio_path"]


async def test_synthesize_line_falls_back_to_edge_tts_when_omnivoice_configured_but_unavailable(db, monkeypatch, tmp_path):
    """Speaker requests OmniVoice, and the model dir exists, but synthesis itself fails ->
    must fall back to Edge TTS rather than raising, per SYSTEM-RULES OmniVoice Rules."""
    project = await project_service.create_project(
        db,
        make_config(speakers=[SpeakerConfig(name="Alex", gender="male", accent="american", tts_engine="omnivoice")]),
    )
    speaker = project["speakers"][0]
    assert speaker["tts_engine"] == "omnivoice"
    line = await _insert_line(db, project["id"], speaker["id"])

    monkeypatch.setattr(tts_service.settings, "OMNIVOICE_MODEL_PATH", tmp_path)  # exists()==True

    calls = {"omnivoice": 0, "edge_tts": 0}

    async def fake_edge_tts(text: str, spk: dict) -> bytes:
        calls["edge_tts"] += 1
        return FAKE_MP3_BYTES

    monkeypatch.setattr(tts_service, "_synthesize_edge_tts", fake_edge_tts)

    result = await tts_service.synthesize_line(db, project, line)

    assert result["engine_used"] == "edge_tts"
    assert calls["edge_tts"] == 1
    from pathlib import Path

    Path(result["audio_path"]).unlink()


async def test_omnivoice_synthesis_always_raises_unavailable_for_now():
    """Honest current state: no model weights on this machine, so OmniVoice never succeeds yet."""
    with pytest.raises(tts_service._OmniVoiceUnavailableError):
        await tts_service._synthesize_omnivoice("text", {"id": "spk-1"})


async def test_synthesize_line_raises_not_found_for_unknown_speaker(db):
    project = await project_service.create_project(db, make_config())
    line = {"id": "line-x", "speaker_id": "does-not-exist", "text": "hi"}

    with pytest.raises(NotFoundError):
        await tts_service.synthesize_line(db, project, line)


async def test_synthesize_edge_tts_raises_tts_error_when_communicate_yields_no_audio(monkeypatch):
    class _EmptyCommunicate:
        def __init__(self, *args, **kwargs):
            pass

        async def stream(self):
            return
            yield  # pragma: no cover - makes this an async generator

    monkeypatch.setattr(tts_service.edge_tts, "Communicate", _EmptyCommunicate)

    with pytest.raises(TTSError):
        await tts_service._synthesize_edge_tts("hi", {"accent": "american", "gender": "male", "speed": 1.0, "volume": 1.0, "pitch": 0.0})


def test_edge_tts_voice_map_covers_every_accent_and_gender():
    for accent in ACCENTS:
        assert accent in EDGE_TTS_VOICE_MAP, f"missing accent {accent} in EDGE_TTS_VOICE_MAP"
        for gender in GENDERS:
            assert gender in EDGE_TTS_VOICE_MAP[accent], f"missing gender {gender} for accent {accent}"
            voice_id = EDGE_TTS_VOICE_MAP[accent][gender]
            assert voice_id.startswith("en-"), voice_id


@pytest.mark.parametrize(
    "speed,expected",
    [(1.0, "+0%"), (1.2, "+20%"), (0.8, "-20%"), (0.75, "-25%"), (1.5, "+50%")],
)
def test_rate_percent_conversion(speed, expected):
    assert tts_service._rate_percent(speed) == expected


@pytest.mark.parametrize("pitch,expected", [(0.0, "+0Hz"), (1.0, "+50Hz"), (-1.0, "-50Hz"), (0.5, "+25Hz")])
def test_pitch_hz_conversion(pitch, expected):
    assert tts_service._pitch_hz(pitch) == expected
