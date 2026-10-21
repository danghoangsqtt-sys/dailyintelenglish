-- Phase 59 (ENH-041): how a Solo presentation is shown -- 'presenter' (the waist-up presenter of Phase 55) or 'vox'
-- (voice-over only, motion graphics). Every Solo project made before has a presenter; conversations keep NULL.
ALTER TABLE projects ADD COLUMN explainer_style TEXT;
UPDATE projects SET explainer_style = 'presenter' WHERE presentation_mode = 'solo_explainer';
