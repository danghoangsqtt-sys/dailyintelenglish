"""Application settings loaded from environment variables / .env file."""

import logging
import os
import sys
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import AI_CLOUD_DEADLINE_SECONDS as _AI_CLOUD_DEADLINE_SECONDS_DEFAULT
from app.core.constants import AI_LEGACY_MODE_ALIASES

logger = logging.getLogger(__name__)


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
    # Phase 18/D21 made cloud the default primary, local the automatic fallback,
    # superseding D9/D11 as the default. AI_MODE is the kill switch: "local" (Ollama
    # only, no cloud), "cloud" (cloud only, no fallback -- a diagnostic escape hatch),
    # or "cloud_first" (cloud first, automatic local fallback -- the default once
    # AI_ALLOW_CLOUD is true and a key/model are configured; otherwise the *effective*
    # mode is always "local" regardless of this value, per invariant 32/D24 -- see
    # `app.services.ai.router.compute_effective_mode`). A legacy stored/env value
    # ("gemini"/"hybrid", from before Phase 18) is migrated once, below.
    # `set_ai_mode` (app/services/settings_service.py) enforces the AI_ALLOW_CLOUD gate.
    AI_MODE: str = "local"
    # Task 14.7: the only switch that re-enables the dormant cloud path. Default
    # false so cloud is never re-enabled by accident -- explicit config, not a
    # migration (ADR-001 A2).
    AI_ALLOW_CLOUD: bool = False
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "qwen3.5:9b"
    OLLAMA_NUM_CTX: int = 16384
    # Generous enough to cover Task 13.1's measured 33.4s cold-load plus real
    # generation time; per-section checkpoint deadlines (Task 13.4) are a separate,
    # smaller-grained concern layered on top of this. Phase 18: this is now the
    # FALLBACK's own budget in cloud_first mode (the primary/cloud phase gets its
    # own, separate AI_CLOUD_DEADLINE_SECONDS below) -- see AIRouter.generate.
    AI_REQUEST_DEADLINE_SECONDS: float = 120.0

    # Phase 18/D22-D24 -- the generic OpenAI-compatible cloud provider (OpenRouter,
    # first). Empty key/model collapses the effective mode to "local" (invariant 32).
    OPENAI_COMPAT_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENAI_COMPAT_MODEL: str = "nvidia/nemotron-3-super-120b-a12b:free"
    OPENAI_COMPAT_API_KEY: str = ""
    AI_CLOUD_DEADLINE_SECONDS: float = _AI_CLOUD_DEADLINE_SECONDS_DEFAULT

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

if settings.AI_MODE in AI_LEGACY_MODE_ALIASES:
    _migrated_mode = AI_LEGACY_MODE_ALIASES[settings.AI_MODE]
    logger.info("ai_mode_migrated from=%s to=%s", settings.AI_MODE, _migrated_mode)
    settings.AI_MODE = _migrated_mode

# Captured once, before Task 12.1's settings_service.py can ever overwrite
# settings.GEMINI_API_KEY with a database-stored value at runtime -- lets "clear the
# stored key" revert to the original .env/environment value instead of going blank.
ENV_GEMINI_API_KEY = settings.GEMINI_API_KEY
# Same pattern for the Phase 18 cloud key (settings_service.py's future clear-key
# handler for it needs this, matching ENV_GEMINI_API_KEY above).
ENV_OPENAI_COMPAT_API_KEY = settings.OPENAI_COMPAT_API_KEY
