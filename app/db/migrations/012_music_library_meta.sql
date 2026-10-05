-- Task 22.7 (Phase 22, D50/D51): details for hand-downloaded free tracks in the Music Library.
-- Additive only. Files in DATA_DIR/music_library stay the source of truth for the listing; a file
-- with no row gets one lazily (guessed title + measured duration). mood/tags drive auto-select
-- (22.8); licence/attribution drive the YouTube credit line (22.5).
CREATE TABLE IF NOT EXISTS music_tracks (
  filename TEXT PRIMARY KEY,
  title TEXT,
  artist TEXT,
  mood TEXT,
  tags TEXT,
  source TEXT,
  licence TEXT,
  attribution TEXT,
  source_url TEXT,
  duration_s REAL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
