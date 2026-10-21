-- Phase 57 (ENH-039): the owner's own material for a project -- a dialogue or a vocabulary list -- and whether a
-- dialogue is used word for word or rewritten by the AI; only the approved text and the SHA-256 of a photo it was read
-- from are kept, never the photo. A Solo presentation also says what it presents (a field, a product, a knowledge
-- topic or a how-to); the Solo projects made before have always been knowledge topics.
ALTER TABLE projects ADD COLUMN source_kind TEXT NOT NULL DEFAULT '';
ALTER TABLE projects ADD COLUMN source_text TEXT NOT NULL DEFAULT '';
ALTER TABLE projects ADD COLUMN source_use TEXT NOT NULL DEFAULT 'rewrite';
ALTER TABLE projects ADD COLUMN source_image_sha TEXT NOT NULL DEFAULT '';
ALTER TABLE projects ADD COLUMN explainer_subject TEXT;
UPDATE projects SET explainer_subject = 'topic' WHERE presentation_mode = 'solo_explainer';
