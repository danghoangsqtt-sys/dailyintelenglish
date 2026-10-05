-- Task 24.5a (Phase 24): shots made from an approved storyboard. Additive only.
-- action/expression drive the beat prompts and poses (Task 24.3); subject is an insert's picture;
-- beat_position ties an action or insert shot to its beat (NULL for a place's framing set).
-- Insert shots use kind 'insert' and scene_id '' (the column is NOT NULL; an insert has no place).
ALTER TABLE project_shots ADD COLUMN action TEXT NOT NULL DEFAULT '';
ALTER TABLE project_shots ADD COLUMN expression TEXT NOT NULL DEFAULT 'calm';
ALTER TABLE project_shots ADD COLUMN subject TEXT;
ALTER TABLE project_shots ADD COLUMN beat_position INTEGER;
