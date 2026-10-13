-- Task 24.1 (Phase 24): a project's storyboard -- ordered beats that tile the script lines.
-- Additive only. A deleted scene leaves its beats placeless (SET NULL), never deletes them.
CREATE TABLE IF NOT EXISTS project_storyboards (
  project_id TEXT PRIMARY KEY,
  status TEXT NOT NULL DEFAULT 'draft',
  source TEXT NOT NULL DEFAULT 'owner',
  updated_at TEXT NOT NULL,
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS project_beats (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  position INTEGER NOT NULL,
  line_from INTEGER NOT NULL,
  line_to INTEGER NOT NULL,
  kind TEXT NOT NULL,
  scene_id TEXT,
  new_place TEXT,
  speakers_json TEXT NOT NULL DEFAULT '[]',
  action TEXT NOT NULL DEFAULT '',
  expression TEXT NOT NULL DEFAULT 'calm',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (project_id, position),
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  FOREIGN KEY (scene_id) REFERENCES scenes(id) ON DELETE SET NULL
);
