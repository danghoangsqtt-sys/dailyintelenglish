-- Phase 19 (ENH-013), Task 19.2 -- additive per-word timestamps for karaoke captions.
-- Nullable, no default. Existing rows read back as NULL; audio_service.py's _row_to_job
-- treats NULL the same as an empty word_timestamps list (no back-fill for old rows --
-- same precedent as chapters_estimated, Task 1.9b). Same additive pattern as
-- 004_youtube_chapters_measured.sql / 005_video_vertical_output.sql.
ALTER TABLE audio_jobs ADD COLUMN word_timestamps_json TEXT;
