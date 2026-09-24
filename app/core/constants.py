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
# Bounded ffmpeg render timeout (Task 16.2, ENH-008): a hung encoder must not keep a
# job "rendering" forever. Scales with the audio it has to encode, with a generous floor
# for short clips.
VIDEO_RENDER_TIMEOUT_MIN_SECONDS = 300
VIDEO_RENDER_TIMEOUT_PER_AUDIO_SECOND = 4.0

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
# Phase 18/D21: cloud is now the default primary, local the automatic fallback --
# "gemini"/"hybrid" (naming a specific provider, not a role) are replaced by
# "cloud"/"cloud_first". AI_LEGACY_MODE_ALIASES lets an old stored/env value from
# before Phase 18 migrate once, rather than being rejected outright.
AI_MODES = ("local", "cloud", "cloud_first")
AI_LEGACY_MODE_ALIASES = {"gemini": "cloud", "hybrid": "cloud_first"}
# Consecutive primary-provider failures before the router's in-process circuit
# breaker opens and cloud_first mode skips straight to the local fallback for a
# cooldown window. A config error (bad key/model) opens it immediately instead
# (CircuitBreaker.open_immediately) -- it can't self-resolve on retry.
AI_CIRCUIT_FAILURE_THRESHOLD = 3
AI_CIRCUIT_COOLDOWN_SECONDS = 60.0
# Phase 18: the primary/cloud phase's own time budget, independent of the
# fallback's AI_REQUEST_DEADLINE_SECONDS (app/core/config.py) -- the two are never
# shared (see AIRouter.generate's docstring). Task 18.6 (D27, Amendment D): cut
# 150 -> 75s after Gate B-9 (docs/operations/phase18-gate-b9.md) showed 7 cloud
# timeouts each burning the full 150s before the fallback ran -- Nemotron 3 Super
# answered in 8-28s, and Dots3 (now a default chain fallback) took 70s in the
# smoke probe, still under 75. Mirrored as Settings.AI_CLOUD_DEADLINE_SECONDS's
# default (env-configurable via DIE_AI_CLOUD_DEADLINE_SECONDS), matching this
# same constant so the two can't drift.
AI_CLOUD_DEADLINE_SECONDS = 75.0

# Phase 14 Task 14.1 -- bounded exponential backoff for transient provider errors
# (HTTP 503/429/timeout) only; content-shaped errors keep the old one-immediate-
# retry policy (see AIRouter._TRANSIENT_ERRORS / _CONTENT_RETRY_ERRORS).
AI_TRANSIENT_MAX_ATTEMPTS = 4
AI_TRANSIENT_BACKOFF_BASE_SECONDS = 1.0
AI_TRANSIENT_BACKOFF_MAX_SECONDS = 4.0
AI_BACKOFF_MIN_REMAINING_SECONDS = 5.0

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
# How long the poll loop backs off after an unhandled exception in an iteration
# (Task 16.1, BUG-022), so a transient failure (e.g. "database is locked")
# doesn't spin-retry immediately.
AI_WORKER_LOOP_ERROR_BACKOFF_SECONDS = 5.0
# Bumped whenever the job/checkpoint schema or worker resume semantics change, so a
# job created under an older pipeline can be told apart from a current one.
AI_PIPELINE_VERSION = "13.3"
# Phase 14 Task 14.2 -- job telemetry (ai_job_service.record_generation_call). Caps
# metrics_json["calls"] so a long-running/repaired job's row never grows unbounded;
# oldest entries are dropped once this is exceeded.
AI_JOB_MAX_RECORDED_CALLS = 64

# Phase 13 -- checkpointed script pipeline (app/services/script_pipeline.py).
# Copied from the already-live "Pace: target about N words per minute" line in each
# prompts/script/cefr_*.txt file -- a single source of truth the pipeline computes
# target word counts from, instead of parsing prompt prose at runtime.
#
# Phase 14 Task 14.10 (Amendment G, D13): these values are MEASURED, not assumed --
# the original table (A1-C2: 80/90/100/115/130/150) was never achievable, even at
# TTS_SPEED_MIN (0.75x, the slowest supported speed). PM synthesized the Gate B-3
# winning script via real Edge TTS at 5 speaker speeds and measured actual audio
# duration (data/quality_reviews/phase14/gate-b3/pace-calibration.json); this table
# is that measured pace at each level's new CEFR_DEFAULT_TTS_SPEED default below.
CEFR_WORDS_PER_MINUTE = {"A1": 111, "A2": 111, "B1": 125, "B2": 132, "C1": 145, "C2": 159}
# Phase 14 Task 14.10 (D13): the speaker speed a new speaker gets by default when none
# is explicitly given, one per CEFR level -- paired 1:1 with CEFR_WORDS_PER_MINUTE
# above (that table's values are the measured pace AT this speed, not some other
# speed). All within [TTS_SPEED_MIN, TTS_SPEED_MAX] = [0.75, 1.5].
CEFR_DEFAULT_TTS_SPEED = {"A1": 0.75, "A2": 0.75, "B1": 0.85, "B2": 0.90, "C1": 1.00, "C2": 1.10}
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

# Phase 14 Task 14.3 -- running section budget. SCRIPT_SECTION_WORD_TOLERANCE and
# SCRIPT_GLOBAL_WORD_TOLERANCE above are UNCHANGED (governance: neither may be
# edited in this task -- see task-14.3.md's constants-pin test); a per-section miss
# now carries forward into later sections' effective targets and is a hard gate only
# at the ±10% global total, instead of killing the job at the ±15% per-section check.
SCRIPT_SECTION_CARRY_CAP = 0.35
SCRIPT_LAST_SECTION_CARRY_CAP = 0.5
SCRIPT_PIPELINE_MAX_GLOBAL_BUDGET_REPAIRS = 1

# Phase 14 Task 14.8 -- local hardening. A section still over
# effective_target * (1 + SCRIPT_SECTION_CARRY_CAP) after its one semantic
# repair (SCRIPT_PIPELINE_MAX_REPAIR_ATTEMPTS above, unchanged) gets one more,
# length-only repair pass -- a second, narrower attempt with its own budget,
# not a second semantic repair. 0 disables the pass without a code revert.
SCRIPT_PIPELINE_MAX_LENGTH_REPAIRS = 1

# Phase 14 Task 14.13 (Amendment H, D17) -- Gate B-4's two script failures both
# died on the repeated-8-gram check alone (word count already solved by Task
# 14.10). A global failure that is repetition-only gets one repair of the
# single worst section (attributed by repeated-window start position), bounded
# separately from every other repair budget above. 0 disables the pass without
# a code revert.
SCRIPT_PIPELINE_MAX_REPETITION_REPAIRS = 1
# Caps the section prompt's proactive "avoid these repeated phrases" continuity
# note so it stays bounded as sections accumulate, instead of growing without
# limit across a long episode.
SCRIPT_SECTION_AVOID_PHRASES_MAX = 8

# Phase 15 Task 15.1 -- the section/repair contract asks the model for a short
# alias (S1, S2, ...) rather than a 36-character speaker UUID; a value that
# still looks UUID-shaped (e.g. a dropped/garbled group, the exact real
# trigger case: "ff5f20e0-417b-8d9f-752e844d46f0" vs. the real
# "ff5f20e0-4082-417b-8d9f-752e844d46f0") resolves only if it matches EXACTLY
# ONE known speaker id at this difflib.SequenceMatcher ratio or higher; two or
# more ids tying above this threshold means unknown, never a guess between
# them. 1.0 (exact match only) disables the safety net without a code revert.
SCRIPT_SPEAKER_ID_MATCH_MIN_RATIO = 0.85

# Phase 15 Task 15.2 -- a run of more than SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER
# consecutive lines from one speaker, still present after the one semantic
# repair, gets one bounded merge fix (join text with a space, never
# re-attribute a line to a different speaker) instead of hard-failing the
# job outright. 0 disables the pass without a code revert.
SCRIPT_PIPELINE_MAX_STRUCTURAL_FIXES = 1

# Phase 13 -- grounded learning pipeline (app/services/learning_pipeline.py).
# The prompt gives no explicit target count for vocabulary/idioms -- "at least
# one" is the only honest floor to enforce without inventing an undocumented
# target. Grammar/question ranges are copied from the prompt's own stated
# "1-2 grammar points"/"3-5 questions".
LEARNING_MIN_VOCABULARY = 1
LEARNING_MIN_IDIOMS = 1
LEARNING_MIN_GRAMMAR_POINTS = 1
LEARNING_MAX_GRAMMAR_POINTS = 2
LEARNING_MIN_QUESTIONS = 3
LEARNING_MAX_QUESTIONS = 5
LEARNING_GENERATION_TEMPERATURE = 0.2
