-- Phase 44 (D123): RealVisXL/SDXL, the two-person project shots ("with characters" video) and the two-person Shot
-- Library are removed. Their pictures were zipped to data/backups/ by scripts/archive_old_shots.py before this ran; the
-- rendered videos are kept. Old image jobs of the removed kinds that never finished are closed.
UPDATE image_jobs SET status = 'error', error = 'removed in Phase 44 (D123)', updated_at = datetime('now')
WHERE kind IN ('character_candidates', 'character_sheet', 'project_shots', 'shot_regenerate')
  AND status IN ('pending', 'running');
DROP TABLE IF EXISTS shot_library;
DROP TABLE IF EXISTS project_shots;
