-- Phase 76: retain the current per-project destinations as legacy until users opt into Topic folders.
ALTER TABLE project_exports ADD COLUMN layout_mode TEXT NOT NULL DEFAULT 'legacy';
ALTER TABLE project_exports ADD COLUMN relative_dir TEXT NOT NULL DEFAULT '';

CREATE TABLE IF NOT EXISTS topic_export_roots (
    topic_key TEXT PRIMARY KEY,
    topic_name TEXT NOT NULL,
    output_dir TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
