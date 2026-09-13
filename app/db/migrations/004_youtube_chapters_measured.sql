-- Daily Intel English Studio — Track whether YouTube chapters are estimated or measured
-- (Task 1.9, Sub-task 1.9b).
--
-- Task 1.7 (VideoService) + Task 1.6 (AudioService) now produce real per-line timestamps,
-- so chapters can be measured instead of estimated once a project's audio has been mixed.
-- Additive (ALTER TABLE), unlike 002/003's drop-and-recreate: those were justified because
-- youtube_packages was dead/unused at the time. It is now a live, working table (Sub-task
-- 1.9a shipped and is in active use), so the correct move going forward is additive.
ALTER TABLE youtube_packages ADD COLUMN chapters_estimated INTEGER NOT NULL DEFAULT 1;
