-- Phase 84 (owner 2026-10-28): the editor pass of an automatic script -- its scores, notes and whether it was rewritten.
CREATE TABLE IF NOT EXISTS script_reviews (
  project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
  scores_json TEXT NOT NULL CHECK (json_valid(scores_json)),
  notes TEXT NOT NULL DEFAULT '',
  outcome TEXT NOT NULL CHECK (outcome IN ('passed', 'rewritten', 'kept_original')),
  rewritten INTEGER NOT NULL DEFAULT 0,
  words_before INTEGER NOT NULL DEFAULT 0,
  words_after INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
