from __future__ import annotations

from contextlib import asynccontextmanager

import pytest

from backend.ai.tts import omnivoice_service
from backend.core.config import settings
from backend.core.exceptions import TTSError


def test_voice_design_instruction_uses_profile_attributes_and_user_description():
    assert omnivoice_service._voice_instruction({
        "gender": "female", "accent": "british", "pitch": 0.6,
        "voice_description": "warm, conversational",
    }) == "female, high pitch, british accent, warm, conversational"


@pytest.mark.asyncio
async def test_synthesize_refuses_missing_local_install_without_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "OMNIVOICE_PYTHON", tmp_path / "python.exe")
    monkeypatch.setattr(settings, "OMNIVOICE_MODEL_PATH", tmp_path / "model")
    with pytest.raises(TTSError, match="not ready"):
        await omnivoice_service.synthesize("hello", {"gender": "female"})


@pytest.mark.asyncio
async def test_synthesize_runs_worker_inside_shared_gpu_lease(tmp_path, monkeypatch):
    python = tmp_path / "python.exe"
    python.touch()
    model = tmp_path / "model"
    model.mkdir()
    (model / "weights.bin").touch()
    monkeypatch.setattr(settings, "OMNIVOICE_PYTHON", python)
    monkeypatch.setattr(settings, "OMNIVOICE_MODEL_PATH", model)
    monkeypatch.setattr(omnivoice_service, "is_available", lambda: True)
    calls = []

    class Manager:
        @asynccontextmanager
        async def lease(self, consumer, min_free_mb):
            calls.append((consumer, min_free_mb, "enter"))
            try:
                yield
            finally:
                calls.append((consumer, min_free_mb, "exit"))

    monkeypatch.setattr(omnivoice_service, "get_gpu_manager", lambda: Manager())
    monkeypatch.setattr(omnivoice_service, "_run_worker_sync", lambda payload: calls.append(payload) or b"wav")

    audio = await omnivoice_service.synthesize(
        "hello", {"gender": "female", "accent": "american", "speed": 1.1},
    )

    assert audio == b"wav"
    assert calls[0][0] == "omnivoice" and calls[0][2] == "enter"
    assert calls[1]["text"] == "hello"
    assert calls[1]["instruct"] == "female, moderate pitch, american accent"
    assert calls[-1][2] == "exit"
