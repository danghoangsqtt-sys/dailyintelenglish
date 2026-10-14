-- Phase 41 (D120): each video project can have its own output folder; the owner ticks which components are exported there
-- (video, vertical video, thumbnail, YouTube texts, Shorts/TikTok clips, audio, script, learning pack). The app copies the
-- ticked components that exist into the folder automatically after every new version.
CREATE TABLE IF NOT EXISTS project_exports (
    project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
    output_dir TEXT NOT NULL,
    items_json TEXT NOT NULL DEFAULT '["video","thumbnail","youtube"]',
    last_sync_at TEXT,
    last_error TEXT,
    updated_at TEXT NOT NULL
);
