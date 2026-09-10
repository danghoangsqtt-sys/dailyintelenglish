"""Named constants shared across services. No magic numbers elsewhere."""

# Audio timing
SILENCE_SAME_SPEAKER_MS = 300
SILENCE_DIFFERENT_SPEAKER_MS = 500
TARGET_LOUDNESS_LUFS = -16
MUSIC_DUCKING_MAX_DBFS = -18
MP3_BITRATE = "192k"
WAV_SAMPLE_RATE_HZ = 44100
WAV_BIT_DEPTH = 16

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

# Speakers
GENDERS = ["male", "female", "neutral"]
MIN_SPEAKERS = 1
MAX_SPEAKERS = 6

# Gemini API
GEMINI_MODEL = "gemini-2.0-flash"
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
