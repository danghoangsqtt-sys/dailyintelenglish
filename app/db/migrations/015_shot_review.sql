-- Task 28.5: a shot that still fails its checks (garment colour, an extra face) after the retries carries a note
-- for the user (NULL = nothing to check). Cleared when the shot is regenerated.
ALTER TABLE project_shots ADD COLUMN review_note TEXT;
