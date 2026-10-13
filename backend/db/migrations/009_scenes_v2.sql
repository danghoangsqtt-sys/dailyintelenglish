-- Task 23.2 (Phase 23): Scene Library v2. Additive only. `preview_path` (008) is the scene
-- plate: an empty-scene render used as an IP-Adapter reference in shots. `seed` makes the
-- plate reproducible; rows that predate this migration get one at startup (database.py).
ALTER TABLE scenes ADD COLUMN category TEXT NOT NULL DEFAULT 'other';
ALTER TABLE scenes ADD COLUMN time_of_day TEXT NOT NULL DEFAULT 'day';
ALTER TABLE scenes ADD COLUMN seed INTEGER;
