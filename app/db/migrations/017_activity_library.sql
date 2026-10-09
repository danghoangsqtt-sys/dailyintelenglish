-- Phase 32.6a: reusable, review-gated activity illustrations for talking-sprite cutaways.
CREATE TABLE IF NOT EXISTS activity_library (
    id TEXT PRIMARY KEY,
    character_id TEXT REFERENCES characters(id) ON DELETE SET NULL,
    activity TEXT NOT NULL,
    context_tags_json TEXT NOT NULL DEFAULT '[]',
    aliases_json TEXT NOT NULL DEFAULT '[]',
    variant TEXT NOT NULL DEFAULT '',
    path TEXT NOT NULL,
    content_sha TEXT NOT NULL UNIQUE,
    review_state TEXT NOT NULL DEFAULT 'pending' CHECK (review_state IN ('pending', 'approved', 'rejected')),
    use_count INTEGER NOT NULL DEFAULT 0,
    last_used_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_activity_library_match
    ON activity_library (review_state, character_id, activity, last_used_at, use_count);

CREATE TABLE IF NOT EXISTS activity_library_usage (
    id TEXT PRIMARY KEY,
    activity_id TEXT NOT NULL REFERENCES activity_library(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    beat_id TEXT,
    render_id TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_activity_library_usage_activity
    ON activity_library_usage (activity_id, created_at DESC);
