-- Phase 33 proposal only. Task 33.1 must turn this contract into
-- app/db/migrations/018_character_profiles_v2.sql and verify it on a DB copy.

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
ALTER TABLE characters ADD COLUMN identity_version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE characters ADD COLUMN wizard_step INTEGER NOT NULL DEFAULT 0;
ALTER TABLE characters ADD COLUMN archived_at TEXT;
ALTER TABLE characters ADD COLUMN is_seed INTEGER NOT NULL DEFAULT 0;

UPDATE characters
SET normalized_name = lower(trim(name))
WHERE normalized_name IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_characters_active_normalized_name
ON characters(normalized_name)
WHERE archived_at IS NULL;

ALTER TABLE character_assets ADD COLUMN slot_key TEXT;
ALTER TABLE character_assets ADD COLUMN source TEXT NOT NULL DEFAULT 'legacy_migration';
ALTER TABLE character_assets ADD COLUMN original_filename TEXT;
ALTER TABLE character_assets ADD COLUMN review_state TEXT NOT NULL DEFAULT 'needs_review';
ALTER TABLE character_assets ADD COLUMN validation_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE character_assets ADD COLUMN identity_version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE character_assets ADD COLUMN is_current INTEGER NOT NULL DEFAULT 1;
ALTER TABLE character_assets ADD COLUMN updated_at TEXT;

CREATE INDEX IF NOT EXISTS idx_character_assets_character_slot
ON character_assets(character_id, identity_version, slot_key, is_current);

CREATE UNIQUE INDEX IF NOT EXISTS idx_character_assets_one_current_slot
ON character_assets(character_id, identity_version, slot_key)
WHERE is_current = 1 AND slot_key IS NOT NULL;

-- SQLite cannot safely express this ALTER on every supported version. Task 33.1
-- must rebuild project_cast transactionally, preserving rows and foreign keys.
-- Required final columns:
--   project_id TEXT NOT NULL
--   speaker_index INTEGER NOT NULL
--   character_id TEXT NOT NULL
--   profile_version INTEGER NOT NULL DEFAULT 1
-- Required constraints/indexes:
--   PRIMARY KEY (project_id, speaker_index)
--   UNIQUE (project_id, character_id)
--   FOREIGN KEY project_id -> projects(id) ON DELETE CASCADE
--   FOREIGN KEY character_id -> characters(id) ON DELETE RESTRICT

