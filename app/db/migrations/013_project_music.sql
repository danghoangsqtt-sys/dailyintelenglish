-- Task 22.3 (Phase 22, D45): a project's AI music brief, its 3 previews, the pick and the attached
-- full-length track (a Music Library filename). Additive only.
CREATE TABLE IF NOT EXISTS project_music (
  project_id TEXT PRIMARY KEY,
  style TEXT NOT NULL,
  brief TEXT NOT NULL DEFAULT '',
  duration_s INTEGER NOT NULL,
  source TEXT NOT NULL DEFAULT 'owner',
  previews_json TEXT NOT NULL DEFAULT '[]',
  preview_job_id TEXT,
  picked_seed INTEGER,
  track_filename TEXT,
  full_job_id TEXT,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
