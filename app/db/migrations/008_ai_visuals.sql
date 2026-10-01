CREATE TABLE IF NOT EXISTS characters (
  id TEXT PRIMARY KEY, name TEXT NOT NULL,
  gender TEXT NOT NULL, age_group TEXT NOT NULL,
  ethnicity TEXT NOT NULL DEFAULT 'Vietnamese',
  role TEXT NOT NULL, hair TEXT NOT NULL, eyes TEXT NOT NULL, extra TEXT NOT NULL DEFAULT '',
  top_color TEXT NOT NULL, top_item TEXT NOT NULL,
  bottom_color TEXT NOT NULL, bottom_item TEXT NOT NULL,
  style_id TEXT NOT NULL DEFAULT 'r3_watercolor',
  status TEXT NOT NULL, base_seed INTEGER NOT NULL,
  reference_asset_id TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS character_assets (
  id TEXT PRIMARY KEY, character_id TEXT NOT NULL,
  kind TEXT NOT NULL, path TEXT NOT NULL, seed INTEGER, prompt_tokens INTEGER,
  prompt_truncated INTEGER NOT NULL DEFAULT 0, approved INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS scenes (
  id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE,
  place TEXT NOT NULL, staging TEXT NOT NULL,
  is_builtin INTEGER NOT NULL DEFAULT 0, preview_path TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS project_cast (
  project_id TEXT NOT NULL, speaker_index INTEGER NOT NULL, character_id TEXT NOT NULL,
  PRIMARY KEY (project_id, speaker_index),
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS project_scenes (
  project_id TEXT NOT NULL, position INTEGER NOT NULL, scene_id TEXT NOT NULL,
  PRIMARY KEY (project_id, position),
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  FOREIGN KEY (scene_id) REFERENCES scenes(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS project_shots (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL, scene_id TEXT NOT NULL,
  kind TEXT NOT NULL, speaker_indexes TEXT NOT NULL,
  seed INTEGER NOT NULL, raw_path TEXT, final_path TEXT,
  prompt_tokens INTEGER, prompt_truncated INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL, error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS image_jobs (
  id TEXT PRIMARY KEY, kind TEXT NOT NULL, target_id TEXT NOT NULL,
  status TEXT NOT NULL, stage TEXT NOT NULL DEFAULT '', progress INTEGER NOT NULL DEFAULT 0,
  payload_json TEXT NOT NULL DEFAULT '{}', result_json TEXT, error TEXT,
  cancel_requested INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_image_jobs_status ON image_jobs(status, created_at);
