-- Daily Intel English Studio — Add optional 9:16 (vertical) video output tracking
-- (Task 2.5b, closing the real gap found in Task 2.1c's QA pass: no 9:16 output
-- existed anywhere despite ROADMAP.md requiring it be tested).
--
-- Additive (ALTER TABLE), same convention as 004: video_jobs is a live table, this
-- only adds a nullable column, no data loss risk. NULL means no vertical render was
-- requested/produced for that project's video job (the default, backward-compatible
-- case — the 16:9 path is completely unaffected).
ALTER TABLE video_jobs ADD COLUMN mp4_path_vertical TEXT;
