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

# Video
VIDEO_FPS = 30
VIDEO_WIDTH_STANDARD = 1280
VIDEO_HEIGHT_STANDARD = 720
VIDEO_WIDTH_SHORTS = 720
VIDEO_HEIGHT_SHORTS = 1280

# TTS
MAX_CONCURRENT_TTS = 2
TTS_SPEED_MIN = 0.75
TTS_SPEED_MAX = 1.5
TTS_SPEED_DEFAULT = 1.0
TTS_ENGINES = ["omnivoice", "edge_tts", "piper", "google", "azure"]

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
GEMINI_MODEL = "gemini-3.8-flash"
GEMINI_MAX_RETRIES = 4
GEMINI_RETRY_BASE_DELAY = 1.0  # seconds, exponential backoff
GEMINI_RATE_LIMIT_RPM = 15

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
