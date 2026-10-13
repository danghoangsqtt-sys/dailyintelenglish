"""Pydantic models for audio mixing requests/responses (Task 1.6, Sub-task 1.6b)."""

from pydantic import BaseModel


class GenerateAudioRequest(BaseModel):
    """Request body for POST /api/projects/{id}/audio/generate.

    `background_music` is an optional filename from `data/music_library/` (Task 1.10) —
    there is no per-project "selected track" column yet (no UI sets one), so it is chosen
    per generate-call.
    """

    background_music: str | None = None


class TimestampOut(BaseModel):
    start_sec: float
    end_sec: float
    label: str
    speaker_id: str


class AudioJobOut(BaseModel):
    """A project's audio mixing job status/result."""

    project_id: str
    status: str
    mp3_path: str | None = None
    wav_path: str | None = None
    timestamps: list[TimestampOut] = []
    background_music: str | None = None
    duration_seconds: float | None = None
    loudness_lufs: float | None = None
    error_message: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
