-- Daily Intel English Studio — Database Schema
-- SQLite (aiosqlite)
-- Version: 0.1.0

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,                    -- UUID
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',   -- draft|script_generated|audio_generated|video_generated|complete
    topic TEXT,
    cefr_level TEXT,                        -- A1|A2|B1|B2|C1|C2
    duration_minutes REAL,
    num_speakers INTEGER DEFAULT 2,
    genre TEXT,                             -- debate|instructions|interview|small_talk|...
    accent TEXT,                            -- american|british|australian|...
    language_features TEXT,                 -- JSON blob
    config_json TEXT,                       -- Full ScriptConfig JSON
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Speakers table
CREATE TABLE IF NOT EXISTS speakers (
    id TEXT PRIMARY KEY,                    -- UUID
    project_id TEXT NOT NULL,
    speaker_index INTEGER NOT NULL,         -- 0-based order
    name TEXT NOT NULL,
    gender TEXT,                            -- male|female|neutral
    accent TEXT,
    tts_engine TEXT DEFAULT 'omnivoice',   -- omnivoice|edge_tts|piper|google|azure
    voice_id TEXT,                          -- Engine-specific voice identifier
    voice_description TEXT,                 -- OmniVoice natural language voice design
    speed REAL DEFAULT 1.0,
    pitch REAL DEFAULT 0.0,
    volume REAL DEFAULT 1.0,
    avatar_image_path TEXT,                 -- Path to character image for lips-sync
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Script lines table
CREATE TABLE IF NOT EXISTS script_lines (
    id TEXT PRIMARY KEY,                    -- UUID (e.g., line_001)
    project_id TEXT NOT NULL,
    line_index INTEGER NOT NULL,            -- Order in script
    speaker_id TEXT NOT NULL,
    text TEXT NOT NULL,
    language_notes TEXT,                    -- JSON: {collocations, idioms, grammar_point}
    audio_cache_path TEXT,                  -- Path to cached TTS WAV
    duration_seconds REAL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (speaker_id) REFERENCES speakers(id) ON DELETE CASCADE
);

-- Learning content table (Sprint 1.5A / Task 1.5)
CREATE TABLE IF NOT EXISTS learning_contents (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL UNIQUE REFERENCES projects(id) ON DELETE CASCADE,
    vocabulary_json TEXT NOT NULL DEFAULT '[]',  -- JSON: [{word, part_of_speech, ipa, definition_en, definition_vi, example_sentence}]
    idioms_json TEXT NOT NULL DEFAULT '[]',       -- JSON: [{phrase, meaning_en, meaning_vi, example_sentence}]
    grammar_json TEXT NOT NULL DEFAULT '[]',      -- JSON: [{point, structure, explanation_en, explanation_vi, examples}]
    questions_json TEXT NOT NULL DEFAULT '[]',    -- JSON: [{question, options, correct_answer, explanation}]
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_learning_contents_project_id ON learning_contents(project_id);

-- Audio jobs table
CREATE TABLE IF NOT EXISTS audio_jobs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL UNIQUE,
    status TEXT DEFAULT 'pending',          -- pending|processing|complete|error
    mp3_path TEXT,
    wav_path TEXT,
    timestamps_json TEXT,                   -- JSON: [{start_sec, end_sec, label, speaker_id}]
    background_music TEXT,                  -- filename from music_library
    duration_seconds REAL,
    loudness_lufs REAL,
    error_message TEXT,
    started_at TEXT,
    completed_at TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Video jobs table
CREATE TABLE IF NOT EXISTS video_jobs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL UNIQUE,
    status TEXT DEFAULT 'pending',
    mode TEXT DEFAULT 'background',         -- background|avatar_lipssync
    mp4_path TEXT,
    srt_path TEXT,
    background_image TEXT,
    subtitle_style_json TEXT,              -- JSON: {font, size, color, position}
    error_message TEXT,
    started_at TEXT,
    completed_at TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Thumbnails table
CREATE TABLE IF NOT EXISTS thumbnails (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    template_name TEXT,
    variant_index INTEGER,                  -- 0-4 for A/B variants
    image_path_16x9 TEXT,                  -- 1280x720
    image_path_9x16 TEXT,                  -- 720x1280
    is_selected INTEGER DEFAULT 0,
    created_at TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- YouTube package table
-- Sprint 1.9A / Task 1.9 (migration 003_youtube_package.sql)
CREATE TABLE IF NOT EXISTS youtube_packages (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL UNIQUE REFERENCES projects(id) ON DELETE CASCADE,
    title_options_json TEXT NOT NULL DEFAULT '[]',  -- JSON: [{variant, text}] x3
    description TEXT NOT NULL DEFAULT '',
    chapters_text TEXT NOT NULL DEFAULT '',          -- "MM:SS Label" lines -- estimated or measured, see chapters_estimated
    tags TEXT NOT NULL DEFAULT '',                   -- Comma-separated
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    chapters_estimated INTEGER NOT NULL DEFAULT 1     -- 1 = word-count estimate, 0 = measured from real audio (004_youtube_chapters_measured.sql)
);

CREATE INDEX IF NOT EXISTS idx_youtube_packages_project_id ON youtube_packages(project_id);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_cefr ON projects(cefr_level);
CREATE INDEX IF NOT EXISTS idx_script_lines_project ON script_lines(project_id, line_index);
CREATE INDEX IF NOT EXISTS idx_speakers_project ON speakers(project_id, speaker_index);
