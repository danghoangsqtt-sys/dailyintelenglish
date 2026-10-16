ALTER TABLE channel_series ADD COLUMN presentation_mode TEXT NOT NULL DEFAULT 'classic';
ALTER TABLE channel_series ADD COLUMN explainer_structure TEXT NOT NULL DEFAULT 'why';
