"""Application settings loaded from environment variables / .env file."""

import logging
import os
import sys
from pathlib import Path

from typing import Literal

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

    FFMPEG_PATH: str = "ffmpeg"

    # Task 19.7 (D19.7-b): the renderer kill switch. Any value other than the exact
    # string "remotion" forces the ffmpeg path regardless of what a request asks for
    # (I36). A request may always downgrade "remotion" -> "ffmpeg" (the safer path is
    # always allowed), but can only ever reach "remotion" when this permits it.
    # Task 19.9 (D38, 2026-10-05): the default is now "remotion", the same pattern as
    # Task 18.11's AI_MODE flip; DIE_VIDEO_RENDERER=ffmpeg still forces the
    # pre-Phase-19 path, and a Remotion failure still falls back to ffmpeg per render.
    VIDEO_RENDERER: Literal["ffmpeg", "remotion"] = "remotion"
    # Task 19.7 (D19.7-h): allows video_renderer_remotion's subprocess calls to let
    # Remotion's own CLI download Chrome Headless Shell on first use (confirmed via a
    # real probe: `remotion render`/`remotion still` call `ensureBrowser()`
    # internally, no extra code needed). False pins the install to whatever browser
    # is already present (or bundled) and lets a missing browser fail fast instead of
    # reaching out to the network -- e.g. for an offline/locked-down deployment.
    REMOTION_ALLOW_DOWNLOAD: bool = True

    # Phase 13 -- local-first AI reliability (docs/architecture/adr-001-local-first-ai.md).
    # Phase 18/D21 made cloud the default primary, local the automatic fallback,
    # superseding D9/D11 as the default. AI_MODE is the kill switch: "local" (Ollama
    # only, no cloud), "cloud" (cloud only, no fallback -- a diagnostic escape hatch),
    # or "cloud_first" (cloud first, automatic local fallback -- the default now that
    # Gate B-11 passed (D31) and AI_ALLOW_CLOUD is true; otherwise the *effective*
    # mode is always "local" regardless of this value, per invariant 32/D24 -- see
    # `app.services.ai.router.compute_effective_mode`). A legacy stored/env value
    # ("gemini"/"hybrid", from before Phase 18) is migrated once, below.
    # `set_ai_mode` (app/services/settings_service.py) enforces the AI_ALLOW_CLOUD gate.
    #
    # Task 18.11 (D31, plan Amendment C's close-out step): flipped from "local" to
    # "cloud_first" after Gate B-11's real PASS (docs/operations/phase18-gate-b11.md --
    # 11/11 complete, B1 median 45s vs ~150s local, ~3x faster, served almost entirely
    # by Gemini 3.1 Flash-Lite) and the owner's acceptance. An install with no cloud
    # key/model configured is still fully unaffected -- invariant 32/D24 collapses the
    # *effective* mode to "local" regardless of this default whenever nothing is
    # configured, so this flip only changes behavior for an install that already has
    # (or later adds) a working key.
    AI_MODE: str = "cloud_first"
    # Task 14.7 introduced this as the only switch that re-enables cloud, default
    # false. Phase 18/Task 18.3, plan Amendment C: default flips to true -- without
    # it, the Settings page could never enable cloud, since `set_ai_mode` enforces
    # this gate.
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

    # Task 20.1 -- shared GPU model manager (app/services/gpu_model_manager.py).
    # GPU_MANAGER_ENABLED is the kill switch: false turns every lease into a
    # pass-through (no lock, no eviction), i.e. exactly the pre-20.1 behaviour.
    # GPU_EVICT_OLLAMA=false keeps qwen resident and makes a short lease fall back
    # instead. Thresholds are measured numbers only (D20.1-e): 6144 MiB for StyleTTS 2
    # sits in the gap between 10286 MiB free at idle and 3916 MiB free with qwen loaded
    # (real nvidia-smi, task-21.1b.md D21.1b-e). The image and music thresholds are added
    # by their own spikes (20.2, Phase 22), not guessed here.
    GPU_MANAGER_ENABLED: bool = True
    GPU_EVICT_OLLAMA: bool = True
    AI_VISUALS_ENABLED: bool = True
    IMAGE_ENGINE: Literal["worker", "fake"] = "worker"
    # Phase 28 (owner, 2026-10-06): pictures come from RealVisXL V5.0 (openrail++, photographic people),
    # sampled with Euler-a as in the spike. An empty repo falls back to SDXL base 1.0 and its default sampler.
    IMAGE_BASE_REPO: str = "SG161222/RealVisXL_V5.0"
    IMAGE_SCHEDULER: Literal["default", "euler_a"] = "euler_a"
    VISUALS_DUO_REFINE: bool = True
    # Task 20.11: re-refine a person whose measured top/bottom colour misses the locked
    # colour, at most this many times per person per shot (0 disables the check).
    VISUALS_COLOUR_RETRIES: int = 2
    # Task 29.5 (ENH-020): a project shot job first copies an approved library shot for every spec it matches (no GPU)
    # and generates only the rest; Task 29.4: with AUTO_ADD every generated shot that passed its checks also goes to the
    # library as `pending` (the owner still approves it once before it can ever be reused).
    VISUALS_USE_LIBRARY: bool = True
    VISUALS_LIBRARY_AUTO_ADD: bool = False
    # Task 29.1 (owner, 2026-10-07: both people stared into the lens): "off" = as before; "words" = gaze words in the
    # prompts; "turned" = the words plus each person's face reference turned toward the other one (a library asset
    # `face_turned`, mirrored for the person on the right; a character without one keeps its front face).
    VISUALS_GAZE: Literal["off", "words", "turned"] = "turned"
    # Task 20.11: re-render a duo whose head-level gap holds a third person (anime-seg
    # occupancy >= 0.5), at most this many times, keeping the emptiest render (0 disables).
    VISUALS_EXTRA_PERSON_RETRIES: int = 2
    # Task 23.2 (spike 23.1 variant b): weight of the scene plate as a second, background-
    # masked IP reference in the shot render, so a scene's shots show the same place
    # (0 disables it: text-only places, the pre-23.2 path).
    VISUALS_SCENE_REFERENCE_SCALE: float = 0.4
    # Task 24.1 (owner E4): a storyboard may need at most this many images per episode.
    VISUALS_IMAGE_CAP: int = 12

    # Phase 32.6b Amendment A -- dedicated, review-gated Activity Vision. Ollama is
    # the measured/default Q4 runtime; direct Hugging Face remains an optional worker
    # that exits after each batch. Both release the model before image/video work.
    ACTIVITY_VISION_PROVIDER: Literal["local", "cloud", "filename"] = "local"
    ACTIVITY_VISION_RUNTIME: Literal["ollama", "huggingface"] = "ollama"
    ACTIVITY_VISION_MODEL: str = "qwen3-vl:4b-instruct-q4_K_M"
    ACTIVITY_VISION_HF_MODEL: str = "Qwen/Qwen3-VL-4B-Instruct"
    ACTIVITY_VISION_PYTHON: Path = Path("venv-image/Scripts/python.exe")
    ACTIVITY_VISION_CACHE_DIR: Path = Path("models/activity-vision")
    ACTIVITY_VISION_TIMEOUT_SECONDS: float = 900.0
    ACTIVITY_VISION_MIN_FREE_MB: int = 10240
    ACTIVITY_VISION_MAX_NEW_TOKENS: int = 220
    # Privacy-safe default: local failure falls back to a filename suggestion. Set
    # true only when the owner explicitly accepts sending a resized copy to Gemini.
    ACTIVITY_VISION_CLOUD_FALLBACK: bool = False

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
    # Task 18.9 (D30): Gemini first -- Gate B-10 found Gemini answered in ~4s at ~1.00x
    # word target, while OpenRouter's free Nemotron timed out 16 times at 75s.
    CLOUD_PROVIDER_ORDER: str = "gemini,openrouter"

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
