-- Phase 99 (D168): a Doodle story series keeps its story type ('history', 'myth', 'field' or 'story'); NULL for other kinds.
ALTER TABLE channel_series ADD COLUMN explainer_subject TEXT;
