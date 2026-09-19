"""Application settings loaded from environment variables / .env file."""

import os
import sys
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_data_dir() -> Path:
    """A frozen PyInstaller build (Task 12.2) can't reliably write next to a
    double-clicked exe (working directory isn't guaranteed, and an install under
    Program Files often isn't user-writable) -- default to a stable, real
    per-user data directory instead. `DIE_DATA_DIR` still overrides either default
    exactly as before; this only changes what happens when it's unset.
    """
    if getattr(sys, "frozen", False):
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
        return base / "DailyIntelEnglishStudio" / "data"
    return Path("data")


class Settings(BaseSettings):
    """Central application configuration.

    Values are read from the process environment first, falling back to
    a `.env` file in the project root. All variables are namespaced under
    the `DIE_` prefix (e.g. `DIE_DEBUG`, `DIE_APP_PORT`) so generic system
    env vars of the same bare name (`DEBUG`, `APP_HOST`, ...) are never
    picked up and can't crash startup with a bad type (e.g. `DEBUG=release`).
    """

    GEMINI_API_KEY: str = ""

    APP_HOST: str = "localhost"
    APP_PORT: int = 8000
    DEBUG: bool = True

    DATA_DIR: Path = Field(default_factory=_default_data_dir)
    OMNIVOICE_MODEL_PATH: Path = Path("models/omnivoice")

    FFMPEG_PATH: str = "ffmpeg"

    # Phase 13 -- local-first AI reliability (docs/architecture/adr-001-local-first-ai.md).
    # AI_MODE is the kill switch: "gemini" (packaged default until local-runtime
    # onboarding is proven), "local" (Ollama only, no cloud fallback -- used for the
    # Gate B operational trial), or "hybrid" (local first, one visible Gemini fallback).
    AI_MODE: str = "gemini"
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "qwen3.5:9b"
    OLLAMA_NUM_CTX: int = 16384
    # Generous enough to cover Task 13.1's measured 33.4s cold-load plus real
    # generation time; per-section checkpoint deadlines (Task 13.4) are a separate,
    # smaller-grained concern layered on top of this.
    AI_REQUEST_DEADLINE_SECONDS: float = 120.0

    model_config = SettingsConfigDict(
        env_prefix="DIE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def db_path(self) -> Path:
        """Path to the SQLite database file inside DATA_DIR."""
        return self.DATA_DIR / "app.db"


settings = Settings()

# Captured once, before Task 12.1's settings_service.py can ever overwrite
# settings.GEMINI_API_KEY with a database-stored value at runtime -- lets "clear the
# stored key" revert to the original .env/environment value instead of going blank.
ENV_GEMINI_API_KEY = settings.GEMINI_API_KEY
