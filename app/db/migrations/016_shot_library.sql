-- Task 29.4 (ENH-020): the shot library of ready-made pictures of the cast, matched by tags before any GPU time is spent.
-- A shot belongs to ordered characters (its speakers' characters, left to right) and records the face signature of each
-- one: a regenerated character makes its shots stale instead of silently reused. Only `approved` shots are ever reused.
CREATE TABLE IF NOT EXISTS shot_library (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('single', 'duo_close', 'duo_wide')),
    scene_id TEXT NOT NULL,
    character_ids_json TEXT NOT NULL,
    action TEXT NOT NULL DEFAULT '',
    expression TEXT NOT NULL DEFAULT 'calm',
    gaze TEXT NOT NULL DEFAULT 'off',
    face_signature TEXT NOT NULL,
    path TEXT NOT NULL,
    content_sha TEXT NOT NULL UNIQUE,
    review_state TEXT NOT NULL DEFAULT 'pending' CHECK (review_state IN ('pending', 'approved', 'rejected')),
    stale INTEGER NOT NULL DEFAULT 0,
    source_project_id TEXT,
    use_count INTEGER NOT NULL DEFAULT 0,
    last_used_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_shot_library_match ON shot_library (scene_id, kind, review_state, stale);

-- Where a project's shot came from: drawn for this project, or copied from the library.
ALTER TABLE project_shots ADD COLUMN source TEXT NOT NULL DEFAULT 'generated';
ALTER TABLE project_shots ADD COLUMN library_shot_id TEXT;
