-- Phase 62 (ENH-044): automatic content production. One settings row; a run per night (or "Run now"); an item per
-- episode the run worked on, with the step it reached and why it stopped.
CREATE TABLE IF NOT EXISTS automation_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    enabled INTEGER NOT NULL DEFAULT 0,
    window_start TEXT NOT NULL DEFAULT '23:00',
    window_end TEXT NOT NULL DEFAULT '06:00',
    days_ahead INTEGER NOT NULL DEFAULT 3,
    max_per_night INTEGER NOT NULL DEFAULT 2,
    start_with_windows INTEGER NOT NULL DEFAULT 0,
    keep_awake INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL DEFAULT ''
);
INSERT OR IGNORE INTO automation_settings (id) VALUES (1);

CREATE TABLE IF NOT EXISTS automation_runs (
    id TEXT PRIMARY KEY,
    trigger TEXT NOT NULL,                 -- schedule | manual
    status TEXT NOT NULL,                  -- running | done | stopped | error
    message TEXT NOT NULL DEFAULT '',
    started_at TEXT NOT NULL,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS automation_items (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES automation_runs(id) ON DELETE CASCADE,
    episode_id TEXT,
    project_id TEXT,
    title TEXT NOT NULL DEFAULT '',
    step TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,                  -- running | waiting_review | needs_attention | error
    message TEXT NOT NULL DEFAULT '',
    started_at TEXT NOT NULL,
    finished_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_automation_items_run ON automation_items(run_id);
