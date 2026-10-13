-- Task 37.2/37.4 (D99, D101): highlight clips for YouTube Shorts and TikTok -- a passage of the episode with a hook
-- title, proposed by the AI and approved by the owner, rendered vertically with its own cover.
CREATE TABLE IF NOT EXISTS short_clips (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    line_from INTEGER NOT NULL,
    line_to INTEGER NOT NULL,
    hook TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'proposed',   -- proposed | approved | rendered
    mp4_path TEXT,
    cover_path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_short_clips_project ON short_clips(project_id);
