-- Phase 33 (Task 33.2, Amendment A D79): the free-text appearance and outfit of a Quick create profile. The structured
-- legacy columns (hair, eyes, colours, items) stay for the local image generator and are left empty for such profiles.
ALTER TABLE characters ADD COLUMN appearance TEXT NOT NULL DEFAULT '';
ALTER TABLE characters ADD COLUMN outfit TEXT NOT NULL DEFAULT '';
