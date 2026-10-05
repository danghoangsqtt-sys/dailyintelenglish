-- Task 22.2 (Phase 22, ENH-016): provenance for Music Library tracks. Additive only.
-- Files in DATA_DIR/music_library stay the source of truth for the listing; a file with no row is
-- shown as an upload with no provenance (every track uploaded before this task).
CREATE TABLE IF NOT EXISTS music_tracks (
  filename TEXT PRIMARY KEY,
  source TEXT NOT NULL CHECK (source IN ('upload', 'ai')),
  style TEXT, brief TEXT, caption TEXT, seed INTEGER, duration_s REAL,
  model TEXT, licence TEXT, strategy TEXT, job_id TEXT,
  created_at TEXT NOT NULL
);
