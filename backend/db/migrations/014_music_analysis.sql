-- Task 22.9 (owner request 2026-10-06): automatic track classification. Additive only.
-- pace comes from onset density (stable across a track); bpm is an estimate (tempo detection is
-- ambiguous by 2:3 / 2x). The owner's mood always wins over mood_auto; pace_source says whether
-- the owner overrode the automatic pace.
ALTER TABLE music_tracks ADD COLUMN bpm REAL;
ALTER TABLE music_tracks ADD COLUMN onset_rate REAL;
ALTER TABLE music_tracks ADD COLUMN energy_db REAL;
ALTER TABLE music_tracks ADD COLUMN brightness_hz REAL;
ALTER TABLE music_tracks ADD COLUMN pace TEXT;
ALTER TABLE music_tracks ADD COLUMN pace_source TEXT;
ALTER TABLE music_tracks ADD COLUMN mood_auto TEXT;
ALTER TABLE music_tracks ADD COLUMN analysed_at TEXT;
