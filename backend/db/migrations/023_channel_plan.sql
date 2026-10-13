-- Task 36.5 (D103-D105): the channel plan -- topics (YouTube playlists) -> series -> episodes (projects), with a
-- publishing calendar.
CREATE TABLE IF NOT EXISTS channel_topics (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    playlist_url TEXT NOT NULL DEFAULT '',
    position INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS channel_series (
    id TEXT PRIMARY KEY,
    topic_id TEXT NOT NULL REFERENCES channel_topics(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    genre TEXT NOT NULL DEFAULT 'small_talk',
    cefr_level TEXT NOT NULL DEFAULT 'B1',
    cast_json TEXT NOT NULL DEFAULT '[]',          -- ordered character ids, one per speaker
    duration_minutes REAL NOT NULL DEFAULT 5.0,
    playlist_url TEXT NOT NULL DEFAULT '',
    position INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_channel_series_topic ON channel_series(topic_id);

CREATE TABLE IF NOT EXISTS channel_episodes (
    id TEXT PRIMARY KEY,
    series_id TEXT NOT NULL REFERENCES channel_series(id) ON DELETE CASCADE,
    number INTEGER NOT NULL,
    title TEXT NOT NULL,
    brief TEXT NOT NULL DEFAULT '',
    project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'planned',       -- planned | created | published
    publish_date TEXT,                            -- YYYY-MM-DD from the calendar
    video_url TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(series_id, number)
);
CREATE INDEX IF NOT EXISTS idx_channel_episodes_project ON channel_episodes(project_id);
