-- Archive scenes without removing plates or historical project references.
ALTER TABLE scenes ADD COLUMN archived_at TEXT;
CREATE INDEX idx_scenes_archived_at ON scenes(archived_at);
