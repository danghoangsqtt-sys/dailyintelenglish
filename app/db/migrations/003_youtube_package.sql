-- Daily Intel English Studio — YouTube Package schema (Task 1.9, Sub-task 1.9a)
--
-- Supersedes the `youtube_packages` table from 001_init.sql: that table was never
-- referenced by any code and had no column for title options, which the task card
-- has always required. Same precedent as 002_learning_content.sql (PM decision
-- 2026-09-10): drop and recreate rather than leave a stale, never-populated shape.
-- `full_transcript`/`vocabulary_formatted`/`grammar_formatted`/`comprehension_formatted`
-- belong to the deferred zip/metadata.txt export (Sub-task 1.9b) and are dropped here
-- rather than added speculatively before that work exists.
DROP TABLE IF EXISTS youtube_packages;

CREATE TABLE IF NOT EXISTS youtube_packages (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL UNIQUE REFERENCES projects(id) ON DELETE CASCADE,
    title_options_json TEXT NOT NULL DEFAULT '[]',  -- JSON: [{variant, text}] x3 (click_worthy, educational, seo)
    description TEXT NOT NULL DEFAULT '',
    chapters_text TEXT NOT NULL DEFAULT '',          -- Plain-text "MM:SS Label" lines, ESTIMATED (see YouTubeService)
    tags TEXT NOT NULL DEFAULT '',                   -- Comma-separated
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_youtube_packages_project_id ON youtube_packages(project_id);
