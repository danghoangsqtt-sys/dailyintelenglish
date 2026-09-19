"""Named constants shared across services. No magic numbers elsewhere."""

# Audio timing
SILENCE_SAME_SPEAKER_MS = 300
SILENCE_DIFFERENT_SPEAKER_MS = 500
TARGET_LOUDNESS_LUFS = -16
MUSIC_DUCKING_MAX_DBFS = -18
MP3_BITRATE = "192k"
WAV_SAMPLE_RATE_HZ = 44100
WAV_BIT_DEPTH = 16

# Music library uploads
MAX_MUSIC_UPLOAD_MB = 50
MAX_MUSIC_UPLOAD_BYTES = MAX_MUSIC_UPLOAD_MB * 1024 * 1024
MUSIC_UPLOAD_CHUNK_BYTES = 1024 * 1024

# Speaker avatar uploads
MAX_AVATAR_UPLOAD_MB = 8
MAX_AVATAR_UPLOAD_BYTES = MAX_AVATAR_UPLOAD_MB * 1024 * 1024
AVATAR_UPLOAD_CHUNK_BYTES = 1024 * 1024
AVATAR_UPLOAD_EXTENSIONS = (".png", ".jpg", ".jpeg")

# Thumbnails
THUMBNAIL_WIDTH_16X9 = 1280
THUMBNAIL_HEIGHT_16X9 = 720
THUMBNAIL_WIDTH_9X16 = 720
THUMBNAIL_HEIGHT_9X16 = 1280
THUMBNAIL_MIN_VARIANTS = 3
THUMBNAIL_MAX_VARIANTS = 5
THUMBNAIL_JPEG_QUALITY = 90
THUMBNAIL_FONT_SIZE_STEP = 2
THUMBNAIL_LINE_SPACING_RATIO = 0.18
THUMBNAIL_MIN_LINE_SPACING = 4
THUMBNAIL_ACCENT_HEIGHT_RATIO = 0.018
THUMBNAIL_TEMPLATE_IDS = (
    "minimal_clean",
    "gradient_bold",
    "modern_split",
    "dynamic_wave",
    "podcast_classic",
)

# Video
VIDEO_FPS = 30
VIDEO_WIDTH_STANDARD = 1280
VIDEO_HEIGHT_STANDARD = 720
VIDEO_WIDTH_SHORTS = 720
VIDEO_HEIGHT_SHORTS = 1280
# VIDEO_WIDTH_SHORTS/VIDEO_HEIGHT_SHORTS existed but were never wired up until Task 2.5b
# closed the real "no 9:16 output exists" gap found by Task 2.1c's QA pass.
VIDEO_ASPECT_RATIOS = ("16:9", "9:16")
VIDEO_TEMPLATE_IDS = ("midnight", "deep_purple", "charcoal_wave")
VIDEO_TEMPLATE_LABELS = {
    "midnight": "Midnight",
    "deep_purple": "Deep Purple",
    "charcoal_wave": "Charcoal Wave",
}

# TTS
MAX_CONCURRENT_TTS = 2
TTS_SPEED_MIN = 0.75
TTS_SPEED_MAX = 1.5
TTS_SPEED_DEFAULT = 1.0
# Only engines tts_service.py can actually dispatch to. "piper"/"google"/"azure" were
# removed 2026-09-18 (found by an independent audit): they were accepted as valid
# speaker.tts_engine values with real-looking validation, but tts_service.py has zero
# synthesis code for any of them -- selecting one silently fell through to Edge TTS
# with no error, no warning, and no honest fallback signal, unlike "omnivoice" (which
# does have a real, documented, honestly-failing code path -- see tts_service.py's
# module docstring). Advertising an engine choice that quietly does something
# different than requested is exactly the "fake capability" this project's own rules
# forbid.
TTS_ENGINES = ["omnivoice", "edge_tts"]

# Edge TTS voice map: accent -> gender -> ShortName, verified live against
# edge_tts.list_voices() on 2026-09-11. "scottish" has no distinct Edge TTS locale,
# so it falls back to the British (en-GB) voices. Edge TTS has no true gender-neutral
# neural voice, so "neutral" falls back to that locale's female voice.
EDGE_TTS_VOICE_MAP: dict[str, dict[str, str]] = {
    "american": {"male": "en-US-GuyNeural", "female": "en-US-JennyNeural", "neutral": "en-US-AriaNeural"},
    "british": {"male": "en-GB-RyanNeural", "female": "en-GB-SoniaNeural", "neutral": "en-GB-LibbyNeural"},
    "australian": {"male": "en-AU-WilliamMultilingualNeural", "female": "en-AU-NatashaNeural", "neutral": "en-AU-NatashaNeural"},
    "canadian": {"male": "en-CA-LiamNeural", "female": "en-CA-ClaraNeural", "neutral": "en-CA-ClaraNeural"},
    "irish": {"male": "en-IE-ConnorNeural", "female": "en-IE-EmilyNeural", "neutral": "en-IE-EmilyNeural"},
    "scottish": {"male": "en-GB-RyanNeural", "female": "en-GB-SoniaNeural", "neutral": "en-GB-LibbyNeural"},
    "indian": {"male": "en-IN-PrabhatNeural", "female": "en-IN-NeerjaNeural", "neutral": "en-IN-NeerjaNeural"},
    "singaporean": {"male": "en-SG-WayneNeural", "female": "en-SG-LunaNeural", "neutral": "en-SG-LunaNeural"},
    "new_zealand": {"male": "en-NZ-MitchellNeural", "female": "en-NZ-MollyNeural", "neutral": "en-NZ-MollyNeural"},
    "south_african": {"male": "en-ZA-LukeNeural", "female": "en-ZA-LeahNeural", "neutral": "en-ZA-LeahNeural"},
}

# Speakers
GENDERS = ["male", "female", "neutral"]
MIN_SPEAKERS = 1
MAX_SPEAKERS = 6

# Gemini API
# gemini-2.0-flash was shut down 2026-06-01; gemini-3.8-flash is Google's current
# "New Stable" default Flash model (ai.google.dev/gemini-api/docs/models, checked 2026-09-10).
# GEMINI_MODEL_FALLBACKS: real Google AI Studio dashboard data (2026-09-14) showed each Flash
# model version tracks its OWN separate RPM/RPD quota bucket on this account (3.8 Flash was at
# 26/20 RPD and 8/5 RPM while 3.7/3.6 Flash sat at 0/20 and 0/5, completely unused) — so when
# the primary model's quota is exhausted, falling back to a same-generation sibling model is a
# real, distinct quota pool, not a workaround. Order matters: newest/most-capable first.
# 3.5-flash / 3.5-flash-lite added the same day to spread load further — this is purely to
# reduce quota contention (confirmed with the user), NOT a per-CEFR-level quality tier; both
# are real GA models (verified live via models.list, no "-preview" suffix), unlike the only
# available Pro-tier model (`gemini-3.1-pro-preview`), which was deliberately NOT added here —
# preview models carry the same instability risk that forced gemini-2.0-flash's forced migration.
# gemini-3.1-flash-lite added at the user's explicit request (2026-09-14) as one more quota
# bucket. Known tradeoff, disclosed to the user before adding: per ai.google.dev's live
# deprecations page it already has an announced shutdown date (2027-05-07) and its own
# Google-recommended replacement is gemini-3.5-flash-lite, already earlier in this list — so it
# adds a 6th quota bucket, not new capability. Kept last since every model ahead of it is
# expected to remain supported longer.
GEMINI_MODEL_FALLBACKS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
]
GEMINI_MODEL = GEMINI_MODEL_FALLBACKS[0]
GEMINI_MAX_RETRIES = 4
GEMINI_RETRY_BASE_DELAY = 1.0  # seconds, exponential backoff
# Real Google AI Studio dashboard data (2026-09-14) showed gemini-3.8-flash's actual limit on
# this account is 5 RPM / 20 RPD — not the 15 RPM previously assumed here without verification.
GEMINI_RATE_LIMIT_RPM = 5

# Domain enums
CEFR_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
GENRES = [
    "instructions",
    "directions",
    "debate",
    "informational",
    "interview",
    "opinion",
    "storytelling",
    "small_talk",
    "negotiation",
    "news",
]
ACCENTS = [
    "american",
    "british",
    "australian",
    "canadian",
    "irish",
    "scottish",
    "indian",
    "singaporean",
    "new_zealand",
    "south_african",
]

# Project state machine
PROJECT_STATUSES = [
    "draft",
    "script_generated",
    "audio_generated",
    "video_generated",
    "complete",
]

# YouTube package limits
YOUTUBE_DESCRIPTION_MAX_CHARS = 5000
YOUTUBE_TAGS_MAX_CHARS = 500
YOUTUBE_TITLE_MAX_CHARS = 100
YOUTUBE_TITLE_VARIANTS = ["click_worthy", "educational", "seo"]

# YouTube chapters: no real audio exists until Task 1.7/AudioService lands, so
# timestamps are estimated from a fixed reading speed, never measured.
YOUTUBE_CHAPTER_WORDS_PER_MINUTE = 150
YOUTUBE_CHAPTER_MIN_LINES = 4  # start a new chapter every N script lines (topic-shift heuristic)

# Phase 13 -- local-first AI provider gateway (app/services/ai/**).
AI_MODES = ("gemini", "local", "hybrid")
# Consecutive local-provider failures before the router's in-process circuit breaker
# opens and hybrid mode skips straight to the Gemini fallback for a cooldown window.
AI_CIRCUIT_FAILURE_THRESHOLD = 3
AI_CIRCUIT_COOLDOWN_SECONDS = 60.0

# Phase 13 -- durable AI generation jobs (app/services/ai_job_service.py, ai_worker.py).
AI_JOB_OPERATIONS = ("script", "learning")
AI_JOB_STATUSES = ("pending", "running", "validating", "complete", "error", "cancelled", "stale")
# How long a worker's claim on a job is valid without a heartbeat before another
# worker (or a restarted app) may treat it as abandoned and reclaim it.
AI_JOB_LEASE_SECONDS = 90
# How often the worker refreshes its lease while actively processing a job.
AI_JOB_HEARTBEAT_SECONDS = 30
# A job reclaimed this many times without reaching a terminal state is forced to
# `error` instead of being retried forever across repeated crash/restart cycles.
AI_JOB_MAX_RECOVERY_ATTEMPTS = 3
# Bounded grace period for an in-flight job to reach a safe checkpoint boundary
# during app shutdown, before the worker stops waiting and returns anyway.
AI_WORKER_SHUTDOWN_GRACE_SECONDS = 10.0
# Bumped whenever the job/checkpoint schema or worker resume semantics change, so a
# job created under an older pipeline can be told apart from a current one.
AI_PIPELINE_VERSION = "13.3"

# Phase 13 -- checkpointed script pipeline (app/services/script_pipeline.py).
# Copied from the already-live "Pace: target about N words per minute" line in each
# prompts/script/cefr_*.txt file -- a single source of truth the pipeline computes
# target word counts from, instead of parsing prompt prose at runtime.
CEFR_WORDS_PER_MINUTE = {"A1": 80, "A2": 90, "B1": 100, "B2": 115, "C1": 130, "C2": 150}
# Midpoint of the plan's "1-2 minute" section spec.
SCRIPT_SECTION_TARGET_MINUTES = 1.5
SCRIPT_SECTION_WORD_TOLERANCE = 0.15
SCRIPT_GLOBAL_WORD_TOLERANCE = 0.10
SCRIPT_SPEAKER_BALANCE_MIN_SHARE = 0.35
SCRIPT_SPEAKER_BALANCE_MAX_SHARE = 0.65
# Same value already hardcoded in script_base.txt's prose "no monologues" rule --
# now also a named constant the new pipeline enforces programmatically.
SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER = 5
SCRIPT_MAX_REPEATED_8GRAM_RATIO = 0.01
SCRIPT_PIPELINE_MAX_REPAIR_ATTEMPTS = 1
