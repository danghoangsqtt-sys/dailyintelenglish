-- Phase 33: reusable character profiles, versioned assets, and pinned project casts.
-- Existing character IDs, asset paths, speaker settings, and cast assignments are preserved.

PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

ALTER TABLE characters ADD COLUMN normalized_name TEXT;
ALTER TABLE characters ADD COLUMN intro TEXT NOT NULL DEFAULT '';
ALTER TABLE characters ADD COLUMN personality_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE characters ADD COLUMN speaking_style TEXT NOT NULL DEFAULT '';
ALTER TABLE characters ADD COLUMN dialogue_behavior TEXT NOT NULL DEFAULT '';
ALTER TABLE characters ADD COLUMN default_accent TEXT NOT NULL DEFAULT '';
ALTER TABLE characters ADD COLUMN default_tts_engine TEXT NOT NULL DEFAULT 'edge_tts';
ALTER TABLE characters ADD COLUMN default_voice_id TEXT NOT NULL DEFAULT '';
ALTER TABLE characters ADD COLUMN default_voice_description TEXT NOT NULL DEFAULT '';
ALTER TABLE characters ADD COLUMN default_speed REAL NOT NULL DEFAULT 1.0;
ALTER TABLE characters ADD COLUMN default_pitch REAL NOT NULL DEFAULT 0.0;
ALTER TABLE characters ADD COLUMN default_volume REAL NOT NULL DEFAULT 1.0;
ALTER TABLE characters ADD COLUMN identity_version INTEGER NOT NULL DEFAULT 1 CHECK (identity_version >= 1);
ALTER TABLE characters ADD COLUMN wizard_step INTEGER NOT NULL DEFAULT 0 CHECK (wizard_step BETWEEN 0 AND 10);
ALTER TABLE characters ADD COLUMN archived_at TEXT;
ALTER TABLE characters ADD COLUMN is_seed INTEGER NOT NULL DEFAULT 0 CHECK (is_seed IN (0, 1));

UPDATE characters SET normalized_name = lower(trim(name));
UPDATE characters SET is_seed = 1 WHERE lower(trim(name)) IN ('lina', 'alex');

-- Reuse one existing project voice as the profile default without changing any speaker row.
UPDATE characters
SET default_accent = COALESCE((
        SELECT s.accent FROM project_cast pc
        JOIN speakers s ON s.project_id = pc.project_id AND s.speaker_index = pc.speaker_index
        WHERE pc.character_id = characters.id AND s.accent IS NOT NULL
        ORDER BY pc.project_id LIMIT 1
    ), default_accent),
    default_tts_engine = COALESCE((
        SELECT s.tts_engine FROM project_cast pc
        JOIN speakers s ON s.project_id = pc.project_id AND s.speaker_index = pc.speaker_index
        WHERE pc.character_id = characters.id AND s.tts_engine IS NOT NULL
        ORDER BY pc.project_id LIMIT 1
    ), default_tts_engine),
    default_voice_id = COALESCE((
        SELECT s.voice_id FROM project_cast pc
        JOIN speakers s ON s.project_id = pc.project_id AND s.speaker_index = pc.speaker_index
        WHERE pc.character_id = characters.id AND s.voice_id IS NOT NULL
        ORDER BY pc.project_id LIMIT 1
    ), default_voice_id),
    default_voice_description = COALESCE((
        SELECT s.voice_description FROM project_cast pc
        JOIN speakers s ON s.project_id = pc.project_id AND s.speaker_index = pc.speaker_index
        WHERE pc.character_id = characters.id AND s.voice_description IS NOT NULL
        ORDER BY pc.project_id LIMIT 1
    ), default_voice_description),
    default_speed = COALESCE((
        SELECT s.speed FROM project_cast pc
        JOIN speakers s ON s.project_id = pc.project_id AND s.speaker_index = pc.speaker_index
        WHERE pc.character_id = characters.id AND s.speed IS NOT NULL
        ORDER BY pc.project_id LIMIT 1
    ), default_speed),
    default_pitch = COALESCE((
        SELECT s.pitch FROM project_cast pc
        JOIN speakers s ON s.project_id = pc.project_id AND s.speaker_index = pc.speaker_index
        WHERE pc.character_id = characters.id AND s.pitch IS NOT NULL
        ORDER BY pc.project_id LIMIT 1
    ), default_pitch),
    default_volume = COALESCE((
        SELECT s.volume FROM project_cast pc
        JOIN speakers s ON s.project_id = pc.project_id AND s.speaker_index = pc.speaker_index
        WHERE pc.character_id = characters.id AND s.volume IS NOT NULL
        ORDER BY pc.project_id LIMIT 1
    ), default_volume);

CREATE UNIQUE INDEX idx_characters_active_normalized_name
ON characters(normalized_name)
WHERE archived_at IS NULL;

ALTER TABLE character_assets ADD COLUMN slot_key TEXT;
ALTER TABLE character_assets ADD COLUMN source TEXT NOT NULL DEFAULT 'legacy_migration';
ALTER TABLE character_assets ADD COLUMN original_filename TEXT;
ALTER TABLE character_assets ADD COLUMN review_state TEXT NOT NULL DEFAULT 'needs_review'
    CHECK (review_state IN ('processing', 'technical_failed', 'needs_review', 'approved', 'rejected', 'stale'));
ALTER TABLE character_assets ADD COLUMN validation_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE character_assets ADD COLUMN identity_version INTEGER NOT NULL DEFAULT 1 CHECK (identity_version >= 1);
ALTER TABLE character_assets ADD COLUMN is_current INTEGER NOT NULL DEFAULT 1 CHECK (is_current IN (0, 1));
ALTER TABLE character_assets ADD COLUMN updated_at TEXT;

UPDATE character_assets
SET review_state = CASE WHEN approved = 1 THEN 'approved' ELSE 'needs_review' END,
    original_filename = replace(path, rtrim(path, replace(path, '/', '')), ''),
    updated_at = created_at,
    slot_key = CASE
        WHEN kind IN ('face', 'full_body', 'portrait_calm', 'portrait_smile', 'portrait_surprised') THEN kind
        ELSE NULL
    END;

-- Only the most recent approved row (or most recent row when none are approved) is current per slot.
UPDATE character_assets AS asset
SET is_current = CASE WHEN asset.id = (
    SELECT candidate.id FROM character_assets AS candidate
    WHERE candidate.character_id = asset.character_id
      AND candidate.identity_version = asset.identity_version
      AND candidate.slot_key = asset.slot_key
    ORDER BY candidate.approved DESC, candidate.created_at DESC, candidate.id DESC
    LIMIT 1
) THEN 1 ELSE 0 END
WHERE asset.slot_key IS NOT NULL;

CREATE INDEX idx_character_assets_character_slot
ON character_assets(character_id, identity_version, slot_key, is_current);
CREATE UNIQUE INDEX idx_character_assets_one_current_slot
ON character_assets(character_id, identity_version, slot_key)
WHERE is_current = 1 AND slot_key IS NOT NULL;

ALTER TABLE project_cast RENAME TO project_cast_v1;
CREATE TABLE project_cast (
  project_id TEXT NOT NULL,
  speaker_index INTEGER NOT NULL,
  character_id TEXT NOT NULL,
  profile_version INTEGER NOT NULL DEFAULT 1 CHECK (profile_version >= 1),
  PRIMARY KEY (project_id, speaker_index),
  UNIQUE (project_id, character_id),
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE RESTRICT
);
INSERT INTO project_cast (project_id, speaker_index, character_id, profile_version)
SELECT pc.project_id, pc.speaker_index, pc.character_id, c.identity_version
FROM project_cast_v1 pc JOIN characters c ON c.id = pc.character_id;
DROP TABLE project_cast_v1;
CREATE INDEX idx_project_cast_character_id ON project_cast(character_id);

COMMIT;
PRAGMA foreign_keys = ON;

