-- Phase 33 (Task 33.1): character profiles v2 -- additive columns on characters/character_assets, a rebuilt project_cast
-- (profile version pin, one character per project, RESTRICT delete). Amendment A (D81-D82): sprite facing per profile and
-- per asset row. One transaction: a failure leaves the database as it was.
BEGIN;

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
-- D82: the way the sprite pack looks by itself; the renderer mirrors a character placed on the other side.
ALTER TABLE characters ADD COLUMN sprite_facing TEXT NOT NULL DEFAULT '';

UPDATE characters SET normalized_name = lower(trim(name)) WHERE normalized_name IS NULL;
UPDATE characters SET sprite_facing = CASE gender WHEN 'male' THEN 'right' ELSE 'left' END WHERE sprite_facing = '';
-- Lina and Alex (the owner's characters) are protected seed profiles; other databases have no such rows.
UPDATE characters SET is_seed = 1
WHERE id IN ('e961d07c-da89-4395-beec-7741df69142d', '0383161f-b197-41af-b1fd-f912253ed42e');

CREATE UNIQUE INDEX IF NOT EXISTS idx_characters_active_normalized_name
ON characters(normalized_name) WHERE archived_at IS NULL;

ALTER TABLE character_assets ADD COLUMN slot_key TEXT;
ALTER TABLE character_assets ADD COLUMN source TEXT NOT NULL DEFAULT 'legacy_migration';
ALTER TABLE character_assets ADD COLUMN original_filename TEXT;
ALTER TABLE character_assets ADD COLUMN review_state TEXT NOT NULL DEFAULT 'needs_review';
ALTER TABLE character_assets ADD COLUMN validation_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE character_assets ADD COLUMN identity_version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE character_assets ADD COLUMN is_current INTEGER NOT NULL DEFAULT 1;
ALTER TABLE character_assets ADD COLUMN updated_at TEXT;
-- D82: 'opposite' rows form an optional pack that faces the other way (used instead of mirroring).
ALTER TABLE character_assets ADD COLUMN facing TEXT NOT NULL DEFAULT 'native';

UPDATE character_assets SET
  slot_key = CASE WHEN kind IN ('full_body', 'portrait_calm', 'portrait_smile', 'portrait_surprised') THEN kind END,
  review_state = CASE WHEN approved = 1 THEN 'approved' ELSE 'needs_review' END,
  updated_at = created_at;

CREATE INDEX IF NOT EXISTS idx_character_assets_character_slot
ON character_assets(character_id, identity_version, slot_key, is_current);
CREATE UNIQUE INDEX IF NOT EXISTS idx_character_assets_one_current_slot
ON character_assets(character_id, identity_version, facing, slot_key)
WHERE is_current = 1 AND slot_key IS NOT NULL;

CREATE TABLE project_cast_v2 (
  project_id TEXT NOT NULL,
  speaker_index INTEGER NOT NULL,
  character_id TEXT NOT NULL,
  profile_version INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY (project_id, speaker_index),
  UNIQUE (project_id, character_id),
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE RESTRICT
);
INSERT INTO project_cast_v2 (project_id, speaker_index, character_id, profile_version)
SELECT pc.project_id, pc.speaker_index, pc.character_id, c.identity_version
FROM project_cast pc JOIN characters c ON c.id = pc.character_id;
DROP TABLE project_cast;
ALTER TABLE project_cast_v2 RENAME TO project_cast;
CREATE INDEX IF NOT EXISTS idx_project_cast_character ON project_cast(character_id);

COMMIT;
