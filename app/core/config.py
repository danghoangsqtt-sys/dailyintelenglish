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
    # Task 14.7 introduced this as the only switch that re-enables cloud, default
    # false. Phase 18/Task 18.3, plan Amendment C: default flips to true -- without
    # it, the Settings page could never enable cloud, since `set_ai_mode` enforces
    # this gate. AI_MODE still defaults to "local" (unchanged, above): the owner
    # opts into cloud_first from Settings, so a user with no key configured is
    # unaffected either way (invariant 32). Explicit `DIE_AI_ALLOW_CLOUD=false`
    # still fully disables cloud for anyone who wants the old default back.
    AI_ALLOW_CLOUD: bool = True
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
    # Task 18.6 (D27): OpenRouter's native `models: [primary, ...fallbacks]` array --
    # comma-separated (not a pydantic-settings list[str], which needs a JSON-encoded
    # env value) so it matches every other OPENAI_COMPAT_* field's plain-string type.
    # Parsed via app.services.ai.openai_compat_provider.parse_fallback_models.
    OPENAI_COMPAT_FALLBACK_MODELS: str = "google/gemma-4-26b-a4b-it:free,dots-studio/dots-3-note-preview:free"

    # Task 18.8 (D28, Amendment E; defaults revised by Amendment F, the PM's real
    # provider probe -- enh011-nemotron-smoke.md §5): a multi-provider free chain --
    # OpenRouter (above) -> Gemini -> local qwen. OPENAI_COMPAT_*/GEMINI_API_KEY above
    # are reused as-is (not renamed/moved -- see task-18.8.md's migration note).
    # OpenCode Zen: kept as a generic, addable provider (its free tier returned 403
    # "can only be used from within OpenCode" for 6/7 real probed models -- its terms
    # restrict it to the OpenCode client) -- NOT in the default order, not enabled by
    # default. No header/user-agent is ever added to mimic that client.
    OPENCODE_ZEN_BASE_URL: str = "https://opencode.ai/zen/v1"
    OPENCODE_ZEN_API_KEY: str = ""
    OPENCODE_ZEN_MODEL: str = ""
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    # Amendment F: Gemini's free limits are per MODEL per project, so it dispatches as
    # multiple chain entries sharing this one key, each with its own circuit -- comma
    # list, same shape as OPENAI_COMPAT_FALLBACK_MODELS, tried client-side in order
    # (Gemini has no OpenRouter-style server-side models[] array). Real probe results:
    # gemini-3.1-flash-lite (201/200 words, 4s) then gemini-flash-lite-latest (182/200,
    # 2.3s); gemini-2.5-flash is 404 "no longer available", never the default now.
    GEMINI_MODELS: str = "gemini-3.1-flash-lite,gemini-flash-lite-latest"
    # Comma-separated, dispatch order -- an entry with no key configured is skipped
    # silently (point 1). Parsed the same way as OPENAI_COMPAT_FALLBACK_MODELS above.
    CLOUD_PROVIDER_ORDER: str = "openrouter,gemini"

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
# Task 18.8 (D28): same pattern for OpenCode Zen's key -- Gemini's clear-key already
# has ENV_GEMINI_API_KEY above, reused as-is.
ENV_OPENCODE_ZEN_API_KEY = settings.OPENCODE_ZEN_API_KEY
