-- Task 36.2 (D93): the keyword opening line and the hashtags of a YouTube package.
ALTER TABLE youtube_packages ADD COLUMN hook TEXT NOT NULL DEFAULT '';
ALTER TABLE youtube_packages ADD COLUMN hashtags_json TEXT NOT NULL DEFAULT '[]';  -- JSON: ["LearnEnglish", ...] (no '#')
