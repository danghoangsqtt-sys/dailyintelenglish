-- Explicit mode: a legacy one-speaker project remains classic.
ALTER TABLE projects ADD COLUMN presentation_mode TEXT NOT NULL DEFAULT 'classic'
CHECK (presentation_mode IN ('classic', 'solo_explainer') AND (presentation_mode != 'solo_explainer' OR num_speakers = 1));
ALTER TABLE projects ADD COLUMN explainer_structure TEXT
CHECK (explainer_structure IS NULL OR explainer_structure IN ('why', 'how', 'list'));

CREATE TABLE project_explainer_plans (
  project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
  revision INTEGER NOT NULL CHECK (revision >= 1),
  status TEXT NOT NULL CHECK (status IN ('draft', 'approved', 'stale')),
  source_fingerprint TEXT NOT NULL CHECK (length(source_fingerprint) = 64),
  plan_json TEXT NOT NULL CHECK (json_valid(plan_json)),
  approved_revision INTEGER,
  approved_snapshot_json TEXT CHECK (approved_snapshot_json IS NULL OR json_valid(approved_snapshot_json)),
  updated_at TEXT NOT NULL
);

CREATE TABLE project_explainer_plan_versions (
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  revision INTEGER NOT NULL CHECK (revision >= 1),
  source_fingerprint TEXT NOT NULL CHECK (length(source_fingerprint) = 64),
  plan_json TEXT NOT NULL CHECK (json_valid(plan_json)),
  created_at TEXT NOT NULL,
  PRIMARY KEY (project_id, revision)
);
