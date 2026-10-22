-- Phase 72 (ENH-054): whom a series or a video is for -- 'international' (English explanations), 'vietnamese'
-- (Vietnamese meanings) or 'both'. NULL inherits: a video from its series, a series from the channel (app_settings).
ALTER TABLE channel_series ADD COLUMN audience TEXT;
ALTER TABLE projects ADD COLUMN audience TEXT;
