-- Owner decision 2026-10-24: restore plain Edge voices and retire emotion tags.
-- _apply_migration registers retired_cue_text / edge_plain_config for this file.
-- Preserve last-good media on disk; stale statuses prevent treating it as current.
CREATE TEMP TABLE _edge_restore_lines AS
SELECT id, project_id FROM script_lines WHERE retired_cue_text(text) != text;

CREATE TEMP TABLE _edge_restore_speakers AS
SELECT id, project_id FROM speakers
WHERE tts_engine IS NOT 'edge_tts'
   OR (voice_id IS NOT NULL AND voice_id NOT LIKE 'en-%Neural');

CREATE TEMP TABLE _edge_restore_projects AS
SELECT project_id FROM _edge_restore_lines
UNION SELECT project_id FROM _edge_restore_speakers;

UPDATE script_lines SET audio_cache_path = NULL, duration_seconds = NULL
WHERE id IN (SELECT id FROM _edge_restore_lines)
   OR speaker_id IN (SELECT id FROM _edge_restore_speakers);

UPDATE script_lines SET text = retired_cue_text(text)
WHERE id IN (SELECT id FROM _edge_restore_lines);

DELETE FROM script_lines
WHERE id IN (SELECT id FROM _edge_restore_lines) AND trim(text) = '';

UPDATE speakers SET tts_engine = 'edge_tts', voice_description = '',
    voice_id = CASE WHEN id IN (SELECT id FROM _edge_restore_speakers)
                    THEN edge_restored_voice(voice_id, accent, gender) ELSE voice_id END;

UPDATE characters SET default_tts_engine = 'edge_tts', default_voice_description = '',
    default_voice_id = edge_restored_voice(default_voice_id, default_accent, gender);

UPDATE projects SET config_json = edge_plain_config(config_json), source_text = retired_cue_text(source_text);

UPDATE projects SET
    status = CASE WHEN EXISTS (SELECT 1 FROM script_lines sl WHERE sl.project_id = projects.id)
                  THEN 'script_generated' ELSE 'draft' END,
    updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
WHERE id IN (SELECT project_id FROM _edge_restore_projects);

UPDATE audio_jobs SET status = 'error',
    error_message = 'Restored plain Edge speech. Generate audio again; previous files have been kept.'
WHERE project_id IN (SELECT project_id FROM _edge_restore_projects);

UPDATE video_jobs SET status = 'error',
    error_message = 'Restored plain Edge speech. Generate audio and video again; previous files have been kept.'
WHERE project_id IN (SELECT project_id FROM _edge_restore_projects);

UPDATE short_clips SET status = 'proposed'
WHERE project_id IN (SELECT project_id FROM _edge_restore_projects);

DROP TABLE _edge_restore_projects;
DROP TABLE _edge_restore_speakers;
DROP TABLE _edge_restore_lines;
